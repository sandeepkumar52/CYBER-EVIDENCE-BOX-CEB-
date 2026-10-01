import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from fastapi import HTTPException, status

logger = logging.getLogger("ceb.storage.file_manager")


def validate_sandboxed_path(mount_point: str, requested_rel_path: str) -> Path:
    """
    Strictly sandboxes all operations inside the designated USB mount point.
    Prevents path traversal, access to /etc, /root, or parent directories.
    """
    if not mount_point:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="USB Storage device is not mounted or mount point is undefined",
        )

    base = Path(mount_point).resolve()
    if not base.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mount point directory does not exist or device is disconnected",
        )

    raw = requested_rel_path.strip()
    if not raw or raw in ("/", "\\", "."):
        return base

    # Check for direct system root path attempts
    lower_raw = raw.lower().replace("\\", "/")
    forbidden_prefixes = (
        "/etc", "/root", "/home", "/var", "/usr", "/bin", "/sbin", "/sys", "/proc", "/dev", "/boot",
        "//", "/windows", "c:/", "d:/", "e:/"
    )
    if any(lower_raw.startswith(p) for p in forbidden_prefixes) or (len(raw) >= 2 and raw[1] == ":"):
        logger.warning(f"Path traversal attempt blocked: requested={raw}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access denied: Path traversal detected outside of mounted USB storage",
        )

    clean_rel = raw.lstrip("/\\")
    target = (base / clean_rel).resolve()

    # Verify target stays strictly inside base
    try:
        target.relative_to(base)
    except ValueError:
        logger.warning(f"Path traversal attempt blocked: base={base}, target={target}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access denied: Path traversal detected outside of mounted USB storage",
        )

    return target



class StorageFileManager:
    def list_files(self, mount_point: str, rel_path: str = "/") -> Dict[str, Any]:
        target_dir = validate_sandboxed_path(mount_point, rel_path)
        if not target_dir.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested path '{rel_path}' is not a directory",
            )

        items: List[Dict[str, Any]] = []
        try:
            for entry in sorted(target_dir.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
                stat = entry.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                is_directory = entry.is_dir()

                items.append({
                    "name": entry.name,
                    "type": "directory" if is_directory else "file",
                    "size": stat.st_size if not is_directory else 0,
                    "modified": mtime,
                    "path": "/" + str(entry.relative_to(Path(mount_point).resolve())).replace("\\", "/"),
                })
        except Exception as e:
            logger.error(f"Error listing files in {target_dir}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read directory: {str(e)}",
            )

        clean_display_path = "/" + str(target_dir.relative_to(Path(mount_point).resolve())).replace("\\", "/").lstrip("/")
        if clean_display_path == "/.":
            clean_display_path = "/"

        return {
            "path": clean_display_path,
            "items": items,
            "count": len(items),
        }

    def get_file_info(self, mount_point: str, rel_path: str) -> Dict[str, Any]:
        target = validate_sandboxed_path(mount_point, rel_path)
        if not target.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: '{rel_path}'",
            )

        stat = target.stat()
        is_directory = target.is_dir()
        return {
            "name": target.name,
            "path": "/" + str(target.relative_to(Path(mount_point).resolve())).replace("\\", "/"),
            "type": "directory" if is_directory else "file",
            "size": stat.st_size if not is_directory else 0,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "extension": target.suffix if not is_directory else None,
        }

    def make_directory(self, mount_point: str, parent_rel_path: str, dir_name: str) -> Dict[str, Any]:
        parent = validate_sandboxed_path(mount_point, parent_rel_path)
        safe_name = "".join(c for c in dir_name if c.isalnum() or c in ("-", "_", " ")).strip()
        if not safe_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid directory name. Must contain alphanumeric characters.",
            )

        new_dir = parent / safe_name
        validate_sandboxed_path(mount_point, str(new_dir.relative_to(Path(mount_point).resolve())))

        if new_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Directory '{safe_name}' already exists",
            )

        new_dir.mkdir(parents=False, exist_ok=False)
        return {
            "message": f"Directory '{safe_name}' created successfully",
            "name": safe_name,
            "path": "/" + str(new_dir.relative_to(Path(mount_point).resolve())).replace("\\", "/"),
        }

    def copy_item(self, mount_point: str, src_rel: str, dst_rel: str) -> Dict[str, Any]:
        src = validate_sandboxed_path(mount_point, src_rel)
        dst = validate_sandboxed_path(mount_point, dst_rel)

        if not src.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source item not found")

        if dst.is_dir() and src.is_file():
            dst = dst / src.name

        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

        return {
            "message": "Item copied successfully",
            "source": src_rel,
            "destination": dst_rel,
        }

    def move_item(self, mount_point: str, src_rel: str, dst_rel: str) -> Dict[str, Any]:
        src = validate_sandboxed_path(mount_point, src_rel)
        dst = validate_sandboxed_path(mount_point, dst_rel)

        if not src.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source item not found")

        shutil.move(str(src), str(dst))
        return {
            "message": "Item moved successfully",
            "source": src_rel,
            "destination": dst_rel,
        }

    def delete_item(self, mount_point: str, rel_path: str) -> Dict[str, Any]:
        target = validate_sandboxed_path(mount_point, rel_path)
        base = Path(mount_point).resolve()

        if target == base:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the root USB mount point",
            )

        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        name = target.name
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

        return {
            "message": f"Successfully deleted '{name}'",
            "deletedPath": rel_path,
        }


# Global instance
storage_file_manager = StorageFileManager()
