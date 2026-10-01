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
  const response = await api.get<{ devices: USBDevice[] }>("/api/hardware/usb");
  return response.data.devices;
};

export const getHardwareSubsystemStatus = async (): Promise<HardwareSubsystemStatus> => {
  const response = await api.get<HardwareSubsystemStatus>("/api/hardware/usb/status");
  return response.data;
};

export const connectUSBSerialDevice = async (
  port: string,
  baudRate?: number
): Promise<{ status: string; message: string; device: USBDevice }> => {
  const response = await api.post("/api/hardware/usb/connect", {
    port,
    baudRate,
  });
  return response.data;
};

export const disconnectUSBSerialDevice = async (
  port: string
): Promise<{ status: string; message: string }> => {
  const response = await api.post("/api/hardware/usb/disconnect", { port });
  return response.data;
};

export const writeUSBSerialData = async (
  port: string,
  data: string
): Promise<{ status: string; bytesWritten: number }> => {
  const response = await api.post("/api/hardware/usb/write", { port, data });
  return response.data;
};

export const readUSBSerialBuffer = async (
  port: string,
  lines: number = 30
): Promise<{ port: string; count: number; lines: string[] }> => {
  const response = await api.get(`/api/hardware/usb/read?port=${encodeURIComponent(port)}&lines=${lines}`);
  return response.data;
};

// ==========================================
// USB STORAGE / PENDRIVE API
// ==========================================

export const getUSBStorageDevices = async (): Promise<USBStorageDevice[]> => {
  const response = await api.get<{ devices: USBStorageDevice[] }>("/api/storage/devices");
  return response.data.devices;
};

export const getStorageSubsystemStatus = async (): Promise<StorageSubsystemStatus> => {
  const response = await api.get<StorageSubsystemStatus>("/api/storage/status");
  return response.data;
};

export const listStorageFiles = async (
  device: string,
  path: string = "/"
): Promise<StorageFilesResponse> => {
  const response = await api.get<StorageFilesResponse>(
    `/api/storage/files?device=${encodeURIComponent(device)}&path=${encodeURIComponent(path)}`
  );
  return response.data;
};

export const createStorageDirectory = async (
  device: string,
  path: string,
  dirName: string
): Promise<{ status: string; message: string; path: string }> => {
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
  const response = await api.post("/api/storage/export", options);
  return response.data;
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
