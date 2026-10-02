import React, { useState, useEffect } from "react";
import {
  Folder,
  FileText,
  ArrowLeft,
  Trash2,
  FolderPlus,
  RefreshCw,
  X,
  ExternalLink,
  Download,
  AlertTriangle,
  HardDrive,
} from "lucide-react";
import type { USBStorageDevice, StorageFileItem } from "../../types";
import {
  listStorageFiles,
  createStorageDirectory,
  deleteStorageFile,
  ejectStorageDevice,
} from "../../services/hardwareApi";

interface Props {
  device: USBStorageDevice;
  isOpen: boolean;
  onClose: () => void;
  onOpenExportModal: (device: USBStorageDevice) => void;
  onEjected: () => void;
}

export const FileManagerModal: React.FC<Props> = ({
  device,
  isOpen,
  onClose,
  onOpenExportModal,
  onEjected,
}) => {
  const [currentPath, setCurrentPath] = useState<string>("/");
  const [items, setItems] = useState<StorageFileItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Selection state
  const [selectedItem, setSelectedItem] = useState<StorageFileItem | null>(null);

  // New folder dialog
  const [showMkdir, setShowMkdir] = useState<boolean>(false);
  const [newDirName, setNewDirName] = useState<string>("");

  // Delete confirm dialog
  const [itemToDelete, setItemToDelete] = useState<StorageFileItem | null>(null);

  const fetchDirectory = async (targetPath: string) => {
    setLoading(true);
    setErrorMsg(null);
    setSelectedItem(null);
    try {
      const res = await listStorageFiles(device.device, targetPath);
      setItems(res.items || []);
      setCurrentPath(res.path || targetPath);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to load directory items.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && device) {
      setCurrentPath("/");
      fetchDirectory("/");
    }
  }, [isOpen, device]);

  if (!isOpen) return null;

  const handleNavigateUp = () => {
    if (currentPath === "/" || currentPath === "") return;
    const parts = currentPath.split("/").filter(Boolean);
    parts.pop();
    const parent = "/" + parts.join("/");
    fetchDirectory(parent);
  };

  const handleOpenFolder = (item: StorageFileItem) => {
    if (item.type === "directory") {
      const nextPath = currentPath === "/" ? `/${item.name}` : `${currentPath}/${item.name}`;
      fetchDirectory(nextPath);
    }
  };

  const handleCreateDirectory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDirName.trim()) return;

    try {
      await createStorageDirectory(device.device, currentPath, newDirName.trim());
      setNewDirName("");
      setShowMkdir(false);
      fetchDirectory(currentPath);
    } catch (err: any) {
      alert(`Directory creation failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDeleteItem = async () => {
    if (!itemToDelete) return;
    try {
      const targetPath =
        currentPath === "/" ? `/${itemToDelete.name}` : `${currentPath}/${itemToDelete.name}`;
      await deleteStorageFile(device.device, targetPath);
      setItemToDelete(null);
      fetchDirectory(currentPath);
    } catch (err: any) {
      alert(`Deletion failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleEject = async () => {
    if (!window.confirm(`Safely unmount and eject ${device.name}?`)) return;
    try {
      await ejectStorageDevice(device.device);
      alert("USB READY TO REMOVE");
      onEjected();
      onClose();
    } catch (err: any) {
      alert(`Eject failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  const formatSize = (bytes: number): string => {
    if (!bytes || bytes <= 0 || isNaN(bytes)) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  return (
    <div className="file-manager-overlay" onClick={onClose}>
      <div className="file-manager-dialog" onClick={(e) => e.stopPropagation()}>
        {/* HEADER */}
        <div className="file-manager-header">
          <div className="flex-row items-center gap-3">
            <div className="fm-icon-badge">
              <HardDrive size={22} />
            </div>
            <div>
              <h3>USB FILE EXPLORER</h3>
              <span>
                {device.name || device.model || "USB Flash Drive"} · {device.device} · {(device.filesystem || "UNKNOWN").toUpperCase()}
              </span>
            </div>
          </div>

          <div className="flex-row items-center gap-2">
            <button
              className="btn-touch btn-danger"
              onClick={handleEject}
              title="Safely unmount USB"
            >
              <ExternalLink size={16} /> EJECT
            </button>
            <button className="btn-close-touch" onClick={onClose}>
              <X size={22} />
            </button>
          </div>
        </div>

        {/* TOUCH CONTROLS / TOOLBAR */}
        <div className="file-manager-toolbar">
          <div className="flex-row items-center gap-2 flex-grow">
            <button
              className="btn-touch btn-secondary"
              onClick={handleNavigateUp}
              disabled={currentPath === "/" || currentPath === ""}
            >
              <ArrowLeft size={18} />
              BACK
            </button>

            <div className="current-path-display">
              <span className="drive-label">USB:</span>
              <span className="path-text">{currentPath}</span>
            </div>
          </div>

          <div className="flex-row items-center gap-2">
            <button
              className="btn-touch btn-secondary"
              onClick={() => setShowMkdir(true)}
              title="Create New Directory"
            >
              <FolderPlus size={18} />
              NEW FOLDER
            </button>

            <button
              className="btn-touch btn-secondary"
              onClick={() => onOpenExportModal(device)}
              title="Export CEB Data"
            >
              <Download size={18} />
              EXPORT
            </button>

            <button
              className="btn-touch btn-secondary"
              onClick={() => fetchDirectory(currentPath)}
              title="Refresh Directory"
            >
              <RefreshCw size={18} />
            </button>
          </div>
        </div>

        {/* ERROR NOTIFICATION */}
        {errorMsg && (
          <div className="fm-error-banner">
            <AlertTriangle size={18} />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* FILE / FOLDER LIST */}
        <div className="file-manager-list">
          {loading ? (
            <div className="fm-loading-state">
              <RefreshCw size={30} className="animate-spin" />
              <span>Scanning USB Storage filesystem...</span>
            </div>
          ) : items.length === 0 ? (
            <div className="fm-empty-state">
              <Folder size={48} style={{ opacity: 0.3, marginBottom: "12px" }} />
              <p>This directory is empty.</p>
              <small>Export CEB data or create a new folder using the buttons above.</small>
            </div>
          ) : (
            <div className="fm-grid">
              {items.map((item) => {
                const isSelected = selectedItem?.name === item.name;
                const isDir = item.type === "directory";

                return (
                  <div
                    key={item.name}
                    className={`fm-item-row ${isSelected ? "item-selected" : ""}`}
                    onClick={() => setSelectedItem(item)}
                    onDoubleClick={() => handleOpenFolder(item)}
                  >
                    <div className="fm-item-icon">
                      {isDir ? (
                        <Folder size={26} className="text-amber-400" />
                      ) : (
                        <FileText size={26} className="text-blue-400" />
                      )}
                    </div>

                    <div className="fm-item-details">
                      <strong className="item-name">{item.name}</strong>
                      <span className="item-meta">
                        {isDir ? "Folder" : formatSize(item.size)} · {item.modified}
                      </span>
                    </div>

                    <div className="fm-item-actions">
                      {isDir && (
                        <button
                          className="btn-touch btn-small btn-primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenFolder(item);
                          }}
                        >
                          OPEN
                        </button>
                      )}

                      <button
                        className="btn-touch btn-small btn-danger"
                        onClick={(e) => {
                          e.stopPropagation();
                          setItemToDelete(item);
                        }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* FOOTER ACTIONS BAR */}
        <div className="file-manager-footer">
          <div className="selection-info">
            {selectedItem ? (
              <span>
                Selected: <strong>{selectedItem.name}</strong> (
                {selectedItem.type === "directory" ? "Directory" : formatSize(selectedItem.size)})
              </span>
            ) : (
              <span>{items.length} items total in current directory</span>
            )}
          </div>

          <div className="flex-row items-center gap-2">
            {selectedItem?.type === "directory" && (
              <button
                className="btn-touch btn-primary"
                onClick={() => handleOpenFolder(selectedItem)}
              >
                OPEN FOLDER
              </button>
            )}
            <button className="btn-touch btn-secondary" onClick={onClose}>
              CLOSE
            </button>
          </div>
        </div>

        {/* CREATE DIRECTORY POPUP */}
        {showMkdir && (
          <div className="fm-sub-modal-backdrop">
            <div className="fm-sub-modal">
              <h4>Create New Directory</h4>
              <p>Enter a folder name on {device.name}:</p>
              <form onSubmit={handleCreateDirectory}>
                <input
                  type="text"
                  placeholder="e.g. CASE_EXPORTS_2026"
                  value={newDirName}
                  onChange={(e) => setNewDirName(e.target.value)}
                  className="touch-text-input"
                  autoFocus
                />
                <div className="flex-row justify-end gap-2" style={{ marginTop: "16px" }}>
                  <button
                    type="button"
                    className="btn-touch btn-secondary"
                    onClick={() => setShowMkdir(false)}
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn-touch btn-primary">
                    Create Folder
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* DELETE CONFIRMATION POPUP */}
        {itemToDelete && (
          <div className="fm-sub-modal-backdrop">
            <div className="fm-sub-modal">
              <div className="flex-row items-center gap-2 text-danger">
                <AlertTriangle size={24} />
                <h4 style={{ margin: 0 }}>Confirm File Deletion</h4>
              </div>
              <p style={{ marginTop: "12px" }}>
                Are you sure you want to permanently delete <strong>{itemToDelete.name}</strong> from{" "}
                {device.name}?
              </p>
              <p className="text-warning-sm">This action cannot be undone.</p>
              <div className="flex-row justify-end gap-2" style={{ marginTop: "16px" }}>
                <button
                  className="btn-touch btn-secondary"
                  onClick={() => setItemToDelete(null)}
                >
                  Cancel
                </button>
                <button className="btn-touch btn-danger" onClick={handleDeleteItem}>
                  Yes, Delete Item
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
