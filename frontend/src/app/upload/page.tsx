"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { CAMERA_ANGLES, CLUBS, type CameraAngle } from "@/lib/metrics";
import { useAuth } from "@/context/AuthContext";
import AuthModal from "@/components/auth/AuthModal";

export default function UploadPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  // 촬영 각도는 어떤 지표를 계산할 수 있는지를 결정하므로 반드시 보낸다.
  const [cameraAngle, setCameraAngle] = useState<CameraAngle>("down_the_line");
  const [club, setClub] = useState<string>("드라이버");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. 영상 파일 업로드 Mutation
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("camera_angle", cameraAngle);
      formData.append("club", club);

      const response = await apiClient.post("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const pct = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress(pct);
          }
        },
      });
      return response.data;
    },
  });

  const uploadId = uploadMutation.data?.upload_id;

  // 2. 분석 상태 Polling
  const { data: statusData, isError: isStatusError } = useQuery({
    queryKey: ["analysisStatus", uploadId],
    queryFn: async () => {
      const res = await apiClient.get(`/analysis/${uploadId}/status`);
      return res.data;
    },
    enabled: !!uploadId,
    refetchInterval: (query) => {
      const state = query.state.data?.status;
      return state === "done" || state === "failed" ? false : 2000;
    },
  });

  // 분석이 끝나면 결과 화면으로 넘어간다.
  //
  // 예전에는 refetchInterval 안에서 router.push 를 불렀는데, 그 함수는
  // 다음 폴링 간격을 정하는 순수 계산이고 React 가 렌더 도중 호출할 수 있다.
  // 거기서 화면 전환을 일으키면 무시될 수 있고, 한 번 false 를 돌려준 뒤로는
  // 다시 호출되지 않아 재시도 기회조차 없다. 그래서 "분석 완료! 결과를
  // 불러옵니다."에서 영영 멈췄다.
  useEffect(() => {
    if (uploadId && statusData?.status === "done") {
      router.push(`/analysis/${uploadId}`);
    }
  }, [uploadId, statusData?.status, router]);

  const validateFile = (file: File): string | null => {
    if (
      !["video/mp4", "video/quicktime"].includes(file.type)
    ) {
      return "MP4 또는 MOV 파일만 업로드할 수 있습니다.";
    }
    if (file.size > 100 * 1024 * 1024) {
      return `파일 크기는 100MB 이하여야 합니다.`;
    }
    return null;
  };

  const handleFile = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setSelectedFile(file);
    uploadMutation.reset();
    setUploadProgress(0);
  };

  const handleStartAnalysis = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile);
    }
  };

  const isWorking =
    uploadMutation.isPending ||
    (uploadId &&
      statusData?.status !== "done" &&
      statusData?.status !== "failed");

  let statusMessage = "대기 중";
  if (uploadMutation.isPending)
    statusMessage = `서버로 비디오 업로드 중... (${uploadProgress}%)`;
  else if (statusData?.status === "queued")
    statusMessage = "AI 분석 대기열에 등록되었습니다...";
  else if (statusData?.status === "processing")
    statusMessage = "관절 포즈 인식 및 스윙 분석 중입니다...";
  else if (statusData?.status === "done")
    statusMessage = "분석 완료! 결과를 불러옵니다.";
  else if (statusData?.status === "failed")
    statusMessage = "분석에 실패했습니다. 다른 영상으로 시도해보세요.";

  // 업로드는 로그인이 필요하다. 훅을 모두 선언한 뒤에 갈라낸다 —
  // 조건부 훅 호출은 React 규칙 위반이다.
  //
  // 앞에서 막는 이유: 그러지 않으면 폰에서 영상을 고르고 업로드까지 마친
  // 뒤에야 401 을 맞는다. 모바일에서 특히 나쁜 경험이다.
  if (!user) {
    return (
      <div className="animate-fadein" style={{ maxWidth: 720, padding: 24, textAlign: "center" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
          로그인이 필요합니다
        </h2>
        <p style={{ fontSize: 13, color: "var(--text-3)", marginBottom: 20, lineHeight: 1.6 }}>
          스윙 영상을 분석하려면 먼저 로그인해 주세요.
        </p>
        <button
          onClick={() => setShowAuth(true)}
          style={{
            padding: "12px 24px",
            borderRadius: 10,
            border: "none",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            background: "var(--accent)",
            color: "#0a0c10",
          }}
        >
          로그인 / 회원가입
        </button>
        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </div>
    );
  }

  return (
    <div className="animate-fadein" style={{ maxWidth: 720 }}>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumb">
          <a href="/">대시보드</a>
          <span className="sep">/</span>
          <span className="now">영상 업로드</span>
        </div>
      </div>

      {/* Header */}
      <div className="h1 mb-1">
        스윙 영상 <span className="em">업로드</span>
      </div>
      <p className="text-muted mb-4">MP4 / MOV · 최대 100MB · 5~30초</p>

      {/* Drop Zone */}
      {!isWorking && !uploadId && (
        // label 로 감싸면 브라우저가 네이티브로 파일 선택창을 연다.
        // 예전에는 div 의 onClick 에서 input.click() 을 불렀는데, iOS 사파리는
        // display:none 인 input 에 대한 JS 클릭을 무시해 폰에서 아무 반응이
        // 없었다. label+htmlFor 는 JS 없이 동작하므로 기기를 가리지 않는다.
        <label
          id="upload-drop-zone"
          htmlFor="upload-file-input"
          aria-label="골프 스윙 영상 업로드 영역"
          className={`drop-zone select-none ${isDragging ? "drag-over" : ""}`}
          style={{ cursor: "pointer" }}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
          }}
        >
          {/* Icon */}
          <div className="animate-float">
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 16,
                background: "var(--accent-dim)",
                border: "1px solid rgba(212,255,58,0.3)",
                display: "grid",
                placeItems: "center",
              }}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--accent)"
                strokeWidth="1.8"
                strokeLinecap="round"
              >
                <path d="M12 3v12" />
                <path d="M7 8l5-5 5 5" />
                <rect x="3" y="17" width="18" height="4" rx="1" />
              </svg>
            </div>
          </div>

          {/* Text */}
          <div className="text-center">
            <p style={{ fontSize: 16, fontWeight: 600, color: "var(--text)" }}>
              탭해서 영상 선택하기
            </p>
            <p className="text-muted text-small mt-1">
              PC 에서는 여기로 드래그해도 됩니다
            </p>
          </div>

          {/* Chips */}
          <div className="flex items-center gap-2">
            <span className="chip mono">MP4</span>
            <span className="chip mono">MOV</span>
            <span className="text-muted text-xs">최대 100MB</span>
          </div>

          {/* accept 는 video/* 로 넓게 둔다. mp4/quicktime 만 지정하면
              안드로이드 파일 탐색기가 아무것도 보여주지 않는 일이 있다.
              실제 형식 검사는 validateFile() 이 한다.

              display:none 대신 화면 밖으로 밀어낸다. iOS 사파리는
              display:none 인 input 을 다루지 못한다. */}
          <input
            id="upload-file-input"
            type="file"
            accept="video/*"
            style={{
              position: "absolute",
              width: 1,
              height: 1,
              opacity: 0,
              pointerEvents: "none",
            }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </label>
      )}

      {/* capture 속성이 있으면 폰에서 카메라가 바로 열린다.
          PC 브라우저는 이 속성을 무시하고 파일 선택창을 띄운다. */}
      {!isWorking && !uploadId && (
        <label
          htmlFor="upload-camera-input"
          className="btn primary w-full mt-3"
          style={{
            padding: 14,
            cursor: "pointer",
            display: "flex",
            justifyContent: "center",
          }}
        >
          📹 폰으로 바로 촬영하기
          <input
            id="upload-camera-input"
            type="file"
            accept="video/*"
            capture="environment"
            style={{
              position: "absolute",
              width: 1,
              height: 1,
              opacity: 0,
              pointerEvents: "none",
            }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </label>
      )}

      {/* Working State */}
      {(isWorking || uploadId) && (
        <div className="card" style={{ padding: 40, textAlign: "center" }}>
          {!statusData || statusData.status !== "failed" ? (
            <div style={{ marginBottom: 24 }}>
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: "50%",
                  border: "3px solid var(--bg-4)",
                  borderTopColor: "var(--accent)",
                  margin: "0 auto",
                }}
                className="animate-spin"
              />
            </div>
          ) : (
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
          )}

          <div className="h3 mb-2">{statusMessage}</div>

          {uploadMutation.isPending && (
            <div
              style={{
                maxWidth: 320,
                margin: "16px auto 0",
                height: 6,
                background: "var(--bg-4)",
                borderRadius: 3,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${uploadProgress}%`,
                  height: "100%",
                  background: "var(--accent)",
                  borderRadius: 3,
                  transition: "width 0.3s ease",
                }}
              />
            </div>
          )}

          {isStatusError && (
            <div
              className="msg bad mt-3"
              style={{ maxWidth: 400, margin: "12px auto 0" }}
            >
              서버 연결 상태를 확인해주세요.
            </div>
          )}

          {uploadMutation.isError && (
            <div className="mt-3" style={{ textAlign: "center" }}>
              <div className="msg bad">
                업로드 오류:{" "}
                {(uploadMutation.error as any)?.response?.data?.detail ||
                  uploadMutation.error.message}
              </div>
              <button
                onClick={() => uploadMutation.reset()}
                className="btn mt-2"
              >
                다시 시도
              </button>
            </div>
          )}
        </div>
      )}

      {/* Selected File Preview */}
      {selectedFile &&
        !isWorking &&
        !uploadId &&
        !uploadMutation.isError && (
          <div
            id="selected-file-preview"
            className="card flex items-center justify-between animate-fadein mt-3"
            style={{ padding: 14 }}
          >
            <div className="flex items-center gap-3">
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: "var(--accent-dim)",
                  border: "1px solid rgba(212,255,58,0.3)",
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                >
                  <rect x="2.5" y="6.5" width="13" height="11" rx="2" />
                  <path d="M16 10l5-2v8l-5-2z" />
                </svg>
              </div>
              <div>
                <p style={{ fontSize: 13, fontWeight: 600 }}>
                  {selectedFile.name}
                </p>
                <p className="text-muted text-xs">
                  {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                </p>
              </div>
            </div>
            <button
              id="start-analysis-btn"
              className="btn primary"
              onClick={handleStartAnalysis}
              disabled={uploadMutation.isPending}
            >
              분석 시작 →
            </button>
          </div>
        )}

      {/* Error */}
      {error && (
        <div className="msg bad mt-2 flex items-center gap-2">
          ⚠️ {error}
        </div>
      )}

      {/* Clubs & Angle Selector */}
      {!isWorking && !uploadId && (
        <div className="mt-4" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div className="card">
            <div className="card-sub mb-2">1. 클럽 선택</div>
            <div className="flex gap-2" style={{ flexWrap: "wrap" }}>
              {CLUBS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setClub(c)}
                  className={`chip ${club === c ? "accent" : ""}`}
                  style={{ cursor: "pointer", fontSize: 11, border: "none" }}
                  aria-pressed={club === c}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="card-sub mb-2">2. 촬영 각도</div>
            <div className="flex gap-2" style={{ flexWrap: "wrap" }}>
              {CAMERA_ANGLES.map((a) => (
                <button
                  key={a.value}
                  type="button"
                  onClick={() => setCameraAngle(a.value)}
                  className={`chip ${cameraAngle === a.value ? "blue" : ""}`}
                  style={{ cursor: "pointer", border: "none" }}
                  aria-pressed={cameraAngle === a.value}
                  title={a.hint}
                >
                  {a.label}
                </button>
              ))}
            </div>
            <p className="text-muted text-xs mt-2" style={{ lineHeight: 1.5 }}>
              {cameraAngle === "down_the_line" &&
                "타겟 라인 뒤에서 촬영 — 어깨·힙 회전과 X-팩터를 측정합니다."}
              {cameraAngle === "face_on" &&
                "골퍼를 마주 보고 촬영 — 헤드 무브먼트와 체중 이동을 측정합니다."}
              {cameraAngle === "angled" &&
                "비스듬히 촬영 — 척추 각도·무릎 굴곡·템포만 측정할 수 있습니다."}
            </p>
          </div>
        </div>
      )}

      {/* Tips */}
      {!isWorking && !uploadId && (
        <div
          className="card mt-3"
          style={{
            background: "var(--ok-dim)",
            border: "1px solid rgba(77,214,138,0.2)",
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <span style={{ color: "var(--ok)" }}>✓</span>
            <span style={{ fontSize: 14, fontWeight: 700 }}>
              잘 찍히는 영상 팁
            </span>
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 24,
              fontSize: 12,
              color: "var(--text-2)",
              lineHeight: 2,
            }}
          >
            <li>전신이 화면에 들어오도록 (머리~발끝)</li>
            <li>정면 또는 측면에서 촬영 (45° 이상 각도 지양)</li>
            <li>스윙 전체 동작 포함 (어드레스~피니시)</li>
            <li>밝은 조명, 단색 배경 권장</li>
          </ul>
        </div>
      )}
    </div>
  );
}
