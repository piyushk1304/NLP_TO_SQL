import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileText, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { uploadFile } from "../services/api";
import { formatFileSize } from "../utils/helpers";
import toast from "react-hot-toast";

const UploadModal = ({ onClose, onSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  const onDrop = useCallback((accepted, rejected) => {
    setError(null);
    if (rejected.length) {
      setError("Invalid file type. Please upload CSV or Excel files only.");
      return;
    }
    if (accepted.length) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
    },
    multiple: false,
    maxSize: 50 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const result = await uploadFile(file, setProgress);
      toast.success("File uploaded successfully!");
      onSuccess(result);
      onClose();
    } catch (err) {
      setError(err.message || "Upload failed. Please try again.");
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title">
            <Upload size={18} />
            <span>Upload Dataset</span>
          </div>
          <button className="modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? "dropzone-active" : ""} ${file ? "dropzone-filled" : ""}`}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="file-preview">
                <CheckCircle2 size={32} className="text-emerald-400" />
                <div className="file-name">{file.name}</div>
                <div className="file-size">{formatFileSize(file.size)}</div>
                <button
                  className="change-file-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                >
                  Change file
                </button>
              </div>
            ) : (
              <div className="dropzone-placeholder">
                <div className="drop-icon">
                  <FileText size={36} />
                </div>
                <p className="drop-title">
                  {isDragActive ? "Drop your file here" : "Drag & drop your file here"}
                </p>
                <p className="drop-sub">or click to browse</p>
                <div className="drop-formats">
                  <span>CSV</span>
                  <span>XLSX</span>
                  <span>XLS</span>
                </div>
                <p className="drop-limit">Maximum file size: 50 MB</p>
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="upload-error">
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          )}

          {/* Progress */}
          {uploading && (
            <div className="progress-wrapper">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="progress-text">{progress}%</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn-cancel" onClick={onClose} disabled={uploading}>
            Cancel
          </button>
          <button
            className="btn-upload"
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            {uploading ? (
              <>
                <Loader2 size={15} className="spin" />
                <span>Uploading…</span>
              </>
            ) : (
              <>
                <Upload size={15} />
                <span>Upload</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadModal;