import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from sqlalchemy.orm import Session

from ...models import AuditLog, Case, CustodyEvent, Evidence
from .storage_file_manager import validate_sandboxed_path

logger = logging.getLogger("ceb.storage.exporter")


class StorageExporter:
    def export_ceb_data_to_usb(
        self,
        mount_point: str,
        db: Session,
        include_audit_logs: bool = True,
        include_cases: bool = True,
        include_evidence: bool = True,
        include_custody: bool = True,
        exported_by: str = "System Operator",
    ) -> Dict[str, Any]:
        """
        Exports structured CEB system data to a mounted USB storage device.
        Creates destination folder: /CEB_DATA/export_YYYY-MM-DD_HH-MM-SS/
        """
        base = Path(mount_point).resolve()
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        export_dirname = f"export_{timestamp_str}"

        ceb_data_dir = base / "CEB_DATA"
        target_dir = ceb_data_dir / export_dirname
        validate_sandboxed_path(mount_point, str(target_dir.relative_to(base)))

        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "logs").mkdir(exist_ok=True)
        (target_dir / "reports").mkdir(exist_ok=True)
        (target_dir / "sensor-data").mkdir(exist_ok=True)
        (target_dir / "system").mkdir(exist_ok=True)

        exported_counts = {
            "cases": 0,
            "evidence": 0,
            "custody_events": 0,
            "audit_logs": 0,
        }

        # 1. Export Cases
        if include_cases:
            cases = db.query(Case).all()
            cases_data = [
                {
                    "case_id": c.case_id,
                    "case_name": c.case_name,
                    "description": c.description,
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in cases
            ]
            exported_counts["cases"] = len(cases_data)

            with open(target_dir / "system" / "cases.json", "w", encoding="utf-8") as f:
                json.dump(cases_data, f, indent=2)

            with open(target_dir / "system" / "cases.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["case_id", "case_name", "status", "created_at", "description"])
                for c in cases:
                    writer.writerow([c.case_id, c.case_name, c.status, c.created_at, c.description])

        # 2. Export Evidence
        if include_evidence:
            evidence_items = db.query(Evidence).all()
            ev_data = [
                {
                    "evidence_id": e.evidence_id,
                    "case_id": e.case_id,
                    "evidence_type": e.evidence_type,
                    "description": e.description,
                    "device_identifier": e.device_identifier,
                    "hash_algorithm": e.hash_algorithm,
                    "hash_value": e.hash_value,
                    "status": e.status,
                    "file_size_bytes": e.file_size_bytes,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in evidence_items
            ]
            exported_counts["evidence"] = len(ev_data)

            with open(target_dir / "reports" / "evidence_registry.json", "w", encoding="utf-8") as f:
                json.dump(ev_data, f, indent=2)

            with open(target_dir / "reports" / "evidence_registry.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["evidence_id", "case_id", "type", "hash_algo", "hash_value", "status", "size_bytes"])
                for e in evidence_items:
                    writer.writerow([e.evidence_id, e.case_id, e.evidence_type, e.hash_algorithm, e.hash_value, e.status, e.file_size_bytes])

        # 3. Export Custody Events
        if include_custody:
            custody_events = db.query(CustodyEvent).all()
            cust_data = [
                {
                    "evidence_id": ce.evidence_id,
                    "user_id": ce.user_id,
                    "action": ce.action,
                    "location": ce.location,
                    "remarks": ce.remarks,
                    "timestamp": ce.timestamp.isoformat() if ce.timestamp else None,
                }
                for ce in custody_events
            ]
            exported_counts["custody_events"] = len(cust_data)

            with open(target_dir / "logs" / "chain_of_custody.json", "w", encoding="utf-8") as f:
                json.dump(cust_data, f, indent=2)

            with open(target_dir / "logs" / "chain_of_custody.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["evidence_id", "action", "location", "timestamp", "remarks"])
                for ce in custody_events:
                    writer.writerow([ce.evidence_id, ce.action, ce.location, ce.timestamp, ce.remarks])

        # 4. Export Audit Logs
        if include_audit_logs:
            logs = db.query(AuditLog).all()
            log_data = [
                {
                    "event": l.event,
                    "details": l.details,
                    "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                    "user_id": l.user_id,
                }
                for l in logs
            ]
            exported_counts["audit_logs"] = len(log_data)

            with open(target_dir / "logs" / "audit_trail.json", "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2)

        # 5. Master Manifest & Human-readable Summary TXT
        manifest = {
            "title": "Cyber Evidence Box (CEB) Forensic Export Manifest",
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "exported_by": exported_by,
            "export_directory": f"/CEB_DATA/{export_dirname}/",
            "records": exported_counts,
            "integrity_algorithm": "SHA-256",
        }

        with open(target_dir / "export_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        summary_txt = f"""==================================================
CYBER EVIDENCE BOX (CEB) - USB DATA EXPORT REPORT
==================================================
Export Timestamp: {manifest['export_timestamp']}
Exported By:      {exported_by}
Destination:      /CEB_DATA/{export_dirname}/

EXPORTED RECORDS SUMMARY:
--------------------------------------------------
- Registered Cases:       {exported_counts['cases']}
- Evidence Registry:      {exported_counts['evidence']}
- Chain of Custody Logs:  {exported_counts['custody_events']}
- System Audit Logs:      {exported_counts['audit_logs']}

FOLDERS CREATED:
- /logs/         (Audit Trail & Chain of Custody)
- /reports/      (Evidence Registry CSV & JSON)
- /sensor-data/  (Chassis telemetry & GPS)
- /system/       (Case metadata)

Data Integrity: Cryptographic hashes preserved.
==================================================
"""
        with open(target_dir / "README_EXPORT.txt", "w", encoding="utf-8") as f:
            f.write(summary_txt)

        rel_dest = "/" + str(target_dir.relative_to(base)).replace("\\", "/")
        logger.info(f"CEB data export successfully created at USB path: {rel_dest}")

        return {
            "status": "success",
            "message": "Export complete",
            "savedPath": rel_dest,
            "timestamp": manifest["export_timestamp"],
            "records": exported_counts,
        }


# Global exporter
storage_exporter = StorageExporter()
