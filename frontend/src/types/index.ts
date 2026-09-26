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
