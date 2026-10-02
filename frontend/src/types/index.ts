export type UserRole = "Admin" | "Investigator" | "Viewer";

export interface User {
  id: number;
  username: string;
  role: UserRole;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type CaseStatus = "Active" | "Under Investigation" | "Closed" | "Archived";

export interface Case {
  id: number;
  case_id: string;
  case_name: string;
  description: string | null;
  status: CaseStatus;
  is_archived: boolean;
  created_by: number;
  created_at: string;
  creator?: User;
  evidence_count?: number;
}

export type EvidenceType =
  | "Disk Image"
  | "USB Device"
  | "Memory Dump"
  | "Log File"
  | "Document"
  | "Mobile Device"
  | "Network Capture"
  | "Other";

export type EvidenceStatus =
  | "Registered"
  | "Acquired"
  | "Verified"
  | "Secured"
  | "Transferred"
  | "Archived";

export interface Evidence {
  id: number;
  evidence_id: string;
  case_id: number;
  evidence_type: EvidenceType;
  description: string | null;
  device_identifier: string | null;
  hash_algorithm: string | null;
  hash_value: string | null;
  storage_path: string | null;
  file_size_bytes: number | null;
  status: EvidenceStatus;
  created_at: string;
  is_encrypted?: boolean;
  encrypted_sha256?: string | null;
}

export interface EvidenceVerifyResult {
  evidence_id: string;
  is_valid: boolean;
  expected_hash: string | null;
  computed_hash: string | null;
  message: string;
}

export interface CustodyEvent {
  id: number;
  evidence_id: number;
  user_id: number;
  action: string;
  location: string | null;
  remarks: string | null;
  timestamp: string;
  user?: User;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  event: string;
  details: string | null;
  timestamp: string;
  user?: User;
}

export interface DashboardStats {
  total_cases: number;
  active_cases: number;
  total_evidence: number;
  verified_evidence: number;
  storage_used_bytes: number;
  recent_custody_events: CustodyEvent[];
  recent_audit_logs: AuditLog[];
}

// ==========================================
// USB HARDWARE / SERIAL DEVICES
// ==========================================
export type USBDeviceRole = "esp32" | "gps" | "arduino" | "sensor" | "generic" | string;
export type USBConnectionStatus = "connected" | "disconnected" | "connecting" | "error" | string;

export interface USBDevice {
  port?: string;
  devicePath?: string;
  name?: string;
  product?: string;
  role?: USBDeviceRole;
  matchedRole?: string | null;
  roleName?: string | null;
  vid?: string | null;
  pid?: string | null;
  vendorId?: string | null;
  productId?: string | null;
  serialNumber?: string | null;
  manufacturer?: string | null;
  description?: string | null;
  baudRate?: number;
  status: USBConnectionStatus;
  isMock?: boolean;
  lastSeen?: string;
  lastCommunicationTime?: string | null;
  lastData?: string | null;
  error?: string | null;
}

export interface HardwareSubsystemStatus {
  mode?: "hardware" | "mock" | "auto" | "production" | string;
  scanIntervalSeconds?: number;
  scanActive?: boolean;
  totalDevices?: number;
  connectedCount?: number;
  devices?: USBDevice[];
  system?: string;
  usb?: string;
}

export interface SerialDataPacket {
  port?: string;
  devicePath?: string;
  data: string;
  role?: string;
  timestamp?: string;
}

// ==========================================
// USB STORAGE / PENDRIVE MANAGEMENT
// ==========================================
export type StorageStatus = "connected" | "mounted" | "unmounted" | "ejecting" | "ejected" | "error" | string;

export interface USBStorageDevice {
  device: string;
  name: string;
  vendor?: string | null;
  model?: string | null;
  serialNumber?: string | null;
  partition?: string | null;
  mountPoint?: string | null;
  filesystem?: string | null;
  totalBytes?: number;
  usedBytes?: number;
  freeBytes?: number;
  mounted?: boolean;
  readOnly?: boolean;
  status?: StorageStatus;
  isMock?: boolean;
  lastSeen?: string;
  error?: string | null;
}

export interface StorageSubsystemStatus {
  totalStorageDevices?: number;
  mountedCount?: number;
  totalBytes?: number;
  usedBytes?: number;
  freeBytes?: number;
  devices?: USBStorageDevice[];
  autoExportEnabled?: boolean;
  lastScanTime?: string;
  status?: string;
}

export interface StorageFileItem {
  name: string;
  type: "file" | "directory";
  size: number;
  modified: string;
}

export interface StorageFilesResponse {
  path: string;
  device: string;
  mountPoint: string;
  items: StorageFileItem[];
}

export interface StorageExportResult {
  status: string;
  message: string;
  targetDevice: string;
  savedPath: string;
  exportedAt: string;
  files: string[];
}
