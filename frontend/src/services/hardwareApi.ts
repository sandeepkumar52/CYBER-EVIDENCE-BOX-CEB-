import api from "./api";
import type {
  USBDevice,
  HardwareSubsystemStatus,
  USBStorageDevice,
  StorageSubsystemStatus,
  StorageFilesResponse,
  StorageExportResult,
} from "../types";

// ==========================================
// USB SERIAL / HARDWARE API
// ==========================================

export const getUSBHardwareDevices = async (): Promise<USBDevice[]> => {
  try {
    const response = await api.get<{ devices: any[] }>("/api/hardware/usb");
    const rawList = Array.isArray(response.data?.devices)
      ? response.data.devices
      : Array.isArray(response.data)
      ? response.data
      : [];

    return rawList.map((d: any) => ({
      ...d,
      port: d.port || d.devicePath || d.device || "Unknown Port",
      devicePath: d.devicePath || d.port || d.device || "Unknown Port",
      name: d.name || d.product || d.description || "USB Device",
      product: d.product || d.name || d.description || "USB Device",
      role: (d.role || d.matchedRole || "generic").toLowerCase(),
      matchedRole: d.matchedRole || d.role || null,
      status: d.status || "disconnected",
      vid: d.vid || d.vendorId || null,
      pid: d.pid || d.productId || null,
      baudRate: d.baudRate || 115200,
      isMock: Boolean(d.isMock),
    }));
  } catch (err) {
    console.error("[CEB API] Failed to fetch USB hardware devices:", err);
    return [];
  }
};

export const getHardwareSubsystemStatus = async (): Promise<HardwareSubsystemStatus> => {
  try {
    const response = await api.get<HardwareSubsystemStatus>("/api/hardware/usb/status");
    return {
      mode: response.data?.mode || "auto",
      scanIntervalSeconds: response.data?.scanIntervalSeconds || 2,
      scanActive: response.data?.scanActive ?? true,
      totalDevices: response.data?.totalDevices ?? 0,
      connectedCount: response.data?.connectedCount ?? 0,
      devices: Array.isArray(response.data?.devices) ? response.data.devices : [],
      system: response.data?.system || "healthy",
      usb: response.data?.usb || "healthy",
    };
  } catch (err) {
    console.error("[CEB API] Failed to fetch hardware subsystem status:", err);
    return {
      mode: "auto",
      scanIntervalSeconds: 2,
      scanActive: false,
      totalDevices: 0,
      connectedCount: 0,
      devices: [],
      system: "offline",
      usb: "offline",
    };
  }
};

export const connectUSBSerialDevice = async (
  port: string,
  baudRate?: number
): Promise<{ status: string; message: string; device?: USBDevice }> => {
  const response = await api.post("/api/hardware/usb/connect", {
    devicePath: port,
    port,
    baudRate: baudRate || 115200,
  });
  return response.data;
};

export const disconnectUSBSerialDevice = async (
  port: string
): Promise<{ status: string; message: string }> => {
  const response = await api.post("/api/hardware/usb/disconnect", {
    devicePath: port,
    port,
  });
  return response.data;
};

export const writeUSBSerialData = async (
  port: string,
  data: string
): Promise<{ status: string; bytesWritten?: number; bytesSent?: number }> => {
  const response = await api.post("/api/hardware/usb/write", {
    devicePath: port,
    port,
    data,
  });
  return response.data;
};

export const readUSBSerialBuffer = async (
  port: string,
  lines: number = 30
): Promise<{ port: string; devicePath?: string; count: number; lines: string[] }> => {
  const response = await api.get(
    `/api/hardware/usb/read?devicePath=${encodeURIComponent(port)}&limit=${lines}`
  );
  return {
    port,
    devicePath: response.data?.devicePath || port,
    count: response.data?.count || (Array.isArray(response.data?.lines) ? response.data.lines.length : 0),
    lines: Array.isArray(response.data?.lines) ? response.data.lines : [],
  };
};

// ==========================================
// USB STORAGE / PENDRIVE API
// ==========================================

export const getUSBStorageDevices = async (): Promise<USBStorageDevice[]> => {
  try {
    const response = await api.get<{ devices: any[] }>("/api/storage/devices");
    const rawList = Array.isArray(response.data?.devices)
      ? response.data.devices
      : Array.isArray(response.data)
      ? response.data
      : [];

    return rawList.map((dev: any) => ({
      ...dev,
      device: dev.device || "/dev/unknown",
      name: dev.name || dev.model || "USB Flash Drive",
      mountPoint: dev.mountPoint || dev.mount_point || null,
      filesystem: dev.filesystem || dev.fstype || "unknown",
      totalBytes: Number(dev.totalBytes || dev.total_bytes || 0),
      usedBytes: Number(dev.usedBytes || dev.used_bytes || 0),
      freeBytes: Number(dev.freeBytes || dev.free_bytes || 0),
      mounted: Boolean(dev.mounted),
      readOnly: Boolean(dev.readOnly || dev.read_only),
      status: dev.status || (dev.mounted ? "mounted" : "connected"),
      isMock: Boolean(dev.isMock || dev.is_mock),
    }));
  } catch (err) {
    console.error("[CEB API] Failed to fetch USB storage devices:", err);
    return [];
  }
};

export const getStorageSubsystemStatus = async (): Promise<StorageSubsystemStatus> => {
  try {
    const response = await api.get<StorageSubsystemStatus>("/api/storage/status");
    return {
      totalStorageDevices: response.data?.totalStorageDevices ?? 0,
      mountedCount: response.data?.mountedCount ?? 0,
      totalBytes: Number(response.data?.totalBytes || 0),
      usedBytes: Number(response.data?.usedBytes || 0),
      freeBytes: Number(response.data?.freeBytes || 0),
      devices: Array.isArray(response.data?.devices) ? response.data.devices : [],
      autoExportEnabled: Boolean(response.data?.autoExportEnabled),
      lastScanTime: response.data?.lastScanTime || new Date().toISOString(),
      status: response.data?.status || "healthy",
    };
  } catch (err) {
    console.error("[CEB API] Failed to fetch storage subsystem status:", err);
    return {
      totalStorageDevices: 0,
      mountedCount: 0,
      totalBytes: 0,
      usedBytes: 0,
      freeBytes: 0,
      devices: [],
      status: "offline",
    };
  }
};

export const listStorageFiles = async (
  device: string,
  path: string = "/"
): Promise<StorageFilesResponse> => {
  const response = await api.get<StorageFilesResponse>(
    `/api/storage/files?device=${encodeURIComponent(device)}&path=${encodeURIComponent(path)}`
  );
  return {
    path: response.data?.path || path,
    device: response.data?.device || device,
    mountPoint: response.data?.mountPoint || "",
    items: Array.isArray(response.data?.items) ? response.data.items : [],
  };
};

export const createStorageDirectory = async (
  device: string,
  path: string,
  dirName: string
): Promise<{ status: string; message: string; path?: string }> => {
  const response = await api.post("/api/storage/mkdir", {
    device,
    path,
    dirName,
  });
  return response.data;
};

export const deleteStorageFile = async (
  device: string,
  path: string
): Promise<{ status: string; message: string }> => {
  const response = await api.delete(
    `/api/storage/file?device=${encodeURIComponent(device)}&path=${encodeURIComponent(path)}`
  );
  return response.data;
};

export const copyStorageFile = async (
  device: string,
  srcPath: string,
  dstPath: string
): Promise<{ status: string; message: string }> => {
  const response = await api.post("/api/storage/copy", {
    device,
    srcPath,
    dstPath,
  });
  return response.data;
};

export const moveStorageFile = async (
  device: string,
  srcPath: string,
  dstPath: string
): Promise<{ status: string; message: string }> => {
  const response = await api.post("/api/storage/move", {
    device,
    srcPath,
    dstPath,
  });
  return response.data;
};

export const ejectStorageDevice = async (
  device: string
): Promise<{ status: string; message: string; readyToRemove: boolean; device: string }> => {
  const response = await api.post("/api/storage/eject", { device });
  return response.data;
};

export interface ExportDataOptions {
  device: string;
  includeCases?: boolean;
  includeEvidence?: boolean;
  includeCustody?: boolean;
  includeAuditLogs?: boolean;
}

export const exportDataToUSBStorage = async (
  options: ExportDataOptions
): Promise<StorageExportResult> => {
  const response = await api.post("/api/storage/export", {
    device: options.device,
    includeCases: options.includeCases ?? true,
    includeEvidence: options.includeEvidence ?? true,
    includeCustody: options.includeCustody ?? true,
    includeAuditLogs: options.includeAuditLogs ?? true,
  });
  return {
    status: response.data?.status || "success",
    message: response.data?.message || "Export complete",
    targetDevice: response.data?.targetDevice || options.device,
    savedPath: response.data?.savedPath || "/CEB_DATA/",
    exportedAt: response.data?.exportedAt || new Date().toISOString(),
    files: Array.isArray(response.data?.files) ? response.data.files : [],
  };
};

export const toggleMockStorageDevice = async (
  action: "add" | "remove",
  device: string = "/dev/sda1",
  name?: string
): Promise<{ status: string; message: string }> => {
  const response = await api.post("/api/storage/mock/toggle", {
    action,
    device,
    name,
  });
  return response.data;
};

