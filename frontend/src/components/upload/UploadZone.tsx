"use client";

import { useCallback, useRef, useState } from "react";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
}

const ACCEPTED_TYPES = ["video/mp4", "video/quicktime"];
const MAX_SIZE_MB = 100;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export default function UploadZone({ onFileSelected }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return "MP4 또는 MOV 파일만 업로드할 수 있습니다.";
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `파일 크기는 ${MAX_SIZE_MB}MB 이하여야 합니다.`;
    }
    return null;
  };

  const handleFile = useCallback(
    (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      setError(null);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="w-full">
      {/* Drop Zone */}
      <div
        id="upload-drop-zone"
        role="button"
        tabIndex={0}
        aria-label="골프 스윙 영상 업로드 영역 — 파일을 드래그하거나 클릭하세요"
        className={`drop-zone glass-card rounded-2xl p-12 flex flex-col items-center gap-5 cursor-pointer select-none transition-all ${
          isDragging ? "drag-over" : ""
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      >
        {/* Icon */}
        <div className="animate-float">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-cyan-400/20 border border-indigo-500/30 flex items-center justify-center">
            <svg
              className="w-10 h-10 text-indigo-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M15 10l4.553-2.336A1 1 0 0121 8.582v6.836a1 1 0 01-1.447.894L15 14M4 8a2 2 0 012-2h9a2 2 0 012 2v8a2 2 0 01-2 2H6a2 2 0 01-2-2V8z"
              />
            </svg>
          </div>
        </div>

        {/* Text */}
        <div className="text-center">
          <p className="text-lg font-semibold text-white mb-1">
            스윙 영상을 여기에 드래그하거나
          </p>
          <p className="text-slate-400 text-sm">
            클릭해서 파일을 선택하세요
          </p>
        </div>

        {/* Chips */}
        <div className="flex items-center gap-3">
          {["MP4", "MOV"].map((fmt) => (
            <span
              key={fmt}
              className="px-3 py-1 rounded-full bg-slate-800 text-xs text-slate-300 font-mono border border-slate-700"
            >
              {fmt}
            </span>
          ))}
          <span className="text-slate-600 text-xs">최대 100MB · 5~30초</span>
        </div>

        {/* Hidden input */}
        <input
          ref={inputRef}
          id="upload-file-input"
          type="file"
          accept="video/mp4,video/quicktime"
          className="hidden"
          onChange={handleInputChange}
          aria-hidden="true"
        />
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          id="upload-error"
          className="mt-3 flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3"
        >
          <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </div>
      )}
    </div>
  );
}
