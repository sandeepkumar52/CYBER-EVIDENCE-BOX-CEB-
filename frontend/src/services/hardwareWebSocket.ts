type EventHandler = (payload: any) => void;

class HardwareWebSocketService {
  private socket: WebSocket | null = null;
  private listeners: Map<string, Set<EventHandler>> = new Map();
  private reconnectTimer: any = null;
  private isConnecting: boolean = false;
  private url: string;

  constructor() {
    // Dynamically determine WebSocket URL based on window.location
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname || "127.0.0.1";
    this.url = `${protocol}//${host}:8000/hardware/ws`;
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }
    if (this.isConnecting) return;

    this.isConnecting = true;
    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.isConnecting = false;
        // console.log("[CEB WS] Connected to Hardware WebSocket");
        this.emit("ws:open", { status: "connected" });
      };

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const eventType = message.event;
          if (eventType) {
            this.emit(eventType, message.data || message);
          }
        } catch (e) {
          console.error("[CEB WS] Parse error:", e);
        }
      };

      this.socket.onclose = () => {
        this.isConnecting = false;
        this.socket = null;
        this.emit("ws:close", { status: "disconnected" });
        this.scheduleReconnect();
      };

      this.socket.onerror = (error) => {
        console.warn("[CEB WS] Hardware socket error:", error);
        if (this.socket) {
          this.socket.close();
        }
      };
    } catch {
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, 3000);
    }
  }

  public on(event: string, handler: EventHandler): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);

    // Auto-connect if listening
    if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
      this.connect();
    }

    return () => {
      this.off(event, handler);
    };
  }

  public off(event: string, handler: EventHandler): void {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  public emit(event: string, payload: any): void {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.forEach((h) => {
        try {
          h(payload);
        } catch (err) {
          console.error(`[CEB WS] Handler error for ${event}:`, err);
        }
      });
    }

    // Also trigger wildcard / catch-all handlers
    const allHandlers = this.listeners.get("*");
    if (allHandlers) {
      allHandlers.forEach((h) => {
        try {
          h({ event, data: payload });
        } catch (err) {
          console.error(`[CEB WS] Wildcard handler error for ${event}:`, err);
        }
      });
    }
  }

  public disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export const hardwareWebSocket = new HardwareWebSocketService();
