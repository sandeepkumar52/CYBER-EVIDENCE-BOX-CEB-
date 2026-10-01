import collections
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from .usb_detector import is_valid_device_path
from .usb_events import hardware_events

logger = logging.getLogger("ceb.hardware.serial")

try:
    import serial
    HAS_PYSERIAL = True
except ImportError:
    HAS_PYSERIAL = False


PARITY_MAP = {
    "none": serial.PARITY_NONE if HAS_PYSERIAL else "N",
    "even": serial.PARITY_EVEN if HAS_PYSERIAL else "E",
    "odd": serial.PARITY_ODD if HAS_PYSERIAL else "O",
    "mark": serial.PARITY_MARK if HAS_PYSERIAL else "M",
    "space": serial.PARITY_SPACE if HAS_PYSERIAL else "S",
}

STOPBITS_MAP = {
    1: serial.STOPBITS_ONE if HAS_PYSERIAL else 1,
    1.5: serial.STOPBITS_ONE_POINT_FIVE if HAS_PYSERIAL else 1.5,
    2: serial.STOPBITS_TWO if HAS_PYSERIAL else 2,
}

DATABITS_MAP = {
    5: serial.FIVEBITS if HAS_PYSERIAL else 5,
    6: serial.SIXBITS if HAS_PYSERIAL else 6,
    7: serial.SEVENBITS if HAS_PYSERIAL else 7,
    8: serial.EIGHTBITS if HAS_PYSERIAL else 8,
}


@dataclass
class ConnectionState:
    device_path: str
    status: str = "disconnected"  # "connected", "connecting", "disconnected", "error"
    baud_rate: int = 115200
    data_bits: int = 8
    stop_bits: int = 1
    parity: str = "none"
    timeout: float = 1.0
    is_mock: bool = False
    role: Optional[str] = None
    serial_obj: Any = None
    reader_thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    buffer: Deque[str] = field(default_factory=lambda: collections.deque(maxlen=100))
    last_data: Optional[str] = None
    last_comm_time: Optional[str] = None
    error: Optional[str] = None


class SerialManager:
    def __init__(self):
        self._connections: Dict[str, ConnectionState] = {}
        self._lock = threading.Lock()

    def get_connection(self, device_path: str) -> Optional[ConnectionState]:
        with self._lock:
            return self._connections.get(device_path)

    def is_connected(self, device_path: str) -> bool:
        with self._lock:
            conn = self._connections.get(device_path)
            return conn is not None and conn.status == "connected"

    def connect(
        self,
        device_path: str,
        baud_rate: int = 115200,
        data_bits: int = 8,
        stop_bits: int = 1,
        parity: str = "none",
        timeout: float = 1.0,
        is_mock: bool = False,
        role: Optional[str] = None,
    ) -> bool:
        if not is_valid_device_path(device_path):
            raise ValueError(f"Invalid device path format: {device_path}")

        with self._lock:
            existing = self._connections.get(device_path)
            if existing and existing.status == "connected":
                logger.info(f"Device {device_path} is already connected. Skipping duplicate connect.")
                return True

            conn = ConnectionState(
                device_path=device_path,
                status="connecting",
                baud_rate=baud_rate,
                data_bits=data_bits,
                stop_bits=stop_bits,
                parity=parity.lower(),
                timeout=timeout,
                is_mock=is_mock,
                role=role,
            )
            self._connections[device_path] = conn

        logger.info(f"Opening connection to {device_path} (baudRate={baud_rate}, mock={is_mock})")

        if is_mock or not HAS_PYSERIAL or device_path.startswith("MOCK_"):
            # Mock serial stream
            conn.is_mock = True
            conn.status = "connected"
            conn.last_comm_time = datetime.now(timezone.utc).isoformat()
            conn.reader_thread = threading.Thread(
                target=self._mock_reader_loop,
                args=(conn,),
                daemon=True,
                name=f"MockSerial-{device_path}",
            )
            conn.reader_thread.start()

            hardware_events.dispatch_from_thread(
                "usb:connected",
                {
                    "devicePath": device_path,
                    "baudRate": baud_rate,
                    "role": role,
                    "status": "connected",
                    "isMock": True,
                },
            )
            return True

        # Real hardware serial connection
        try:
            s_parity = PARITY_MAP.get(conn.parity, serial.PARITY_NONE)
            s_stop = STOPBITS_MAP.get(conn.stop_bits, serial.STOPBITS_ONE)
            s_data = DATABITS_MAP.get(conn.data_bits, serial.EIGHTBITS)

            ser = serial.Serial(
                port=device_path,
                baudrate=baud_rate,
                bytesize=s_data,
                parity=s_parity,
                stopbits=s_stop,
                timeout=timeout,
            )
            conn.serial_obj = ser
            conn.status = "connected"
            conn.error = None
            conn.last_comm_time = datetime.now(timezone.utc).isoformat()

            conn.reader_thread = threading.Thread(
                target=self._real_reader_loop,
                args=(conn,),
                daemon=True,
                name=f"RealSerial-{device_path}",
            )
            conn.reader_thread.start()

            hardware_events.dispatch_from_thread(
                "usb:connected",
                {
                    "devicePath": device_path,
                    "baudRate": baud_rate,
                    "role": role,
                    "status": "connected",
                    "isMock": False,
                },
            )
            return True
        except Exception as e:
            conn.status = "error"
            conn.error = str(e)
            logger.error(f"Failed to connect to {device_path}: {e}")
            hardware_events.dispatch_from_thread(
                "usb:error",
                {"devicePath": device_path, "error": str(e)},
            )
            return False

    def disconnect(self, device_path: str) -> bool:
        with self._lock:
            conn = self._connections.get(device_path)
            if not conn:
                return True

        conn.stop_event.set()

        if conn.serial_obj:
            try:
                conn.serial_obj.close()
            except Exception as e:
                logger.debug(f"Note closing serial port {device_path}: {e}")
            conn.serial_obj = None

        if conn.reader_thread and conn.reader_thread.is_alive():
            conn.reader_thread.join(timeout=0.5)

        conn.status = "disconnected"
        logger.info(f"Disconnected from {device_path}")

        hardware_events.dispatch_from_thread(
            "usb:disconnected",
            {"devicePath": device_path, "status": "disconnected"},
        )
        return True

    def write(self, device_path: str, data: str | bytes) -> bool:
        conn = self.get_connection(device_path)
        if not conn or conn.status != "connected":
            raise RuntimeError(f"Device {device_path} is not connected")

        payload = data.encode("utf-8") if isinstance(data, str) else data
        if len(payload) > 4096:
            raise ValueError("Payload size exceeds maximum allowed length of 4096 bytes")

        conn.last_comm_time = datetime.now(timezone.utc).isoformat()

        if conn.is_mock:
            # Handle mock reply
            text_str = payload.decode("utf-8", errors="replace").strip()
            logger.debug(f"[MockSerial Write {device_path}]: {text_str}")
            reply = f"[ACK: {text_str}]"
            conn.buffer.append(f">> {text_str}")
            conn.buffer.append(f"<< {reply}")
            conn.last_data = reply
            hardware_events.dispatch_from_thread(
                "usb:data",
                {"devicePath": device_path, "data": reply, "direction": "in"},
            )
            return True

        if conn.serial_obj:
            try:
                conn.serial_obj.write(payload)
                conn.serial_obj.flush()
                return True
            except Exception as e:
                conn.status = "error"
                conn.error = str(e)
                logger.error(f"Error writing to serial port {device_path}: {e}")
                hardware_events.dispatch_from_thread(
                    "usb:error",
                    {"devicePath": device_path, "error": str(e)},
                )
                return False

        return False

    def read_buffer(self, device_path: str, limit: int = 50) -> List[str]:
        conn = self.get_connection(device_path)
        if not conn:
            return []
        return list(conn.buffer)[-limit:]

    def _real_reader_loop(self, conn: ConnectionState) -> None:
        ser = conn.serial_obj
        logger.info(f"Started real reader loop for {conn.device_path}")
        while not conn.stop_event.is_set() and ser and ser.is_open:
            try:
                if ser.in_waiting:
                    line = ser.readline().decode("utf-8", errors="replace").strip()
                    if line:
                        conn.buffer.append(line)
                        conn.last_data = line
                        conn.last_comm_time = datetime.now(timezone.utc).isoformat()
                        hardware_events.dispatch_from_thread(
                            "usb:data",
                            {"devicePath": conn.device_path, "data": line, "direction": "in"},
                        )
                else:
                    time.sleep(0.05)
            except Exception as e:
                if not conn.stop_event.is_set():
                    logger.warning(f"Error in reader thread for {conn.device_path}: {e}")
                    conn.status = "error"
                    conn.error = str(e)
                    hardware_events.dispatch_from_thread(
                        "usb:error",
                        {"devicePath": conn.device_path, "error": str(e)},
                    )
                break
        logger.info(f"Exited real reader loop for {conn.device_path}")

    def _mock_reader_loop(self, conn: ConnectionState) -> None:
        logger.info(f"Started mock reader loop for {conn.device_path} (role={conn.role})")
        counter = 0

        while not conn.stop_event.is_set():
            time.sleep(1.5)
            counter += 1
            if conn.stop_event.is_set():
                break

            role = (conn.role or "").lower()
            if "gps" in role or "gps" in conn.device_path.lower():
                # Realistic NMEA sentences
                nmea = f"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47 [fix={counter}]"
                conn.buffer.append(nmea)
                conn.last_data = nmea
                conn.last_comm_time = datetime.now(timezone.utc).isoformat()
                hardware_events.dispatch_from_thread(
                    "usb:data",
                    {"devicePath": conn.device_path, "data": nmea, "direction": "in"},
                )
            else:
                # ESP32 telemetry
                telemetry = f'{{"device":"CEB-ESP32","status":"OK","lock":true,"tamper":false,"temp":24.5,"hb":{counter}}}'
                conn.buffer.append(telemetry)
                conn.last_data = telemetry
                conn.last_comm_time = datetime.now(timezone.utc).isoformat()
                hardware_events.dispatch_from_thread(
                    "usb:data",
                    {"devicePath": conn.device_path, "data": telemetry, "direction": "in"},
                )


# Global serial manager instance
serial_manager = SerialManager()
