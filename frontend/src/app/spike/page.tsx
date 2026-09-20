"use client";

import { useState } from "react";
import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";

// 일회용 측정 페이지. 설계의 유일한 미검증 전제인 "폰에서 MediaPipe 가
// 쓸 만한 속도로 도는가" 를 재기 위한 것이다. 전환이 끝나면 삭제한다.
//
// 좌표도 함께 내려받는다. 브라우저 MediaPipe(WASM)와 서버 MediaPipe(네이티브)가
// 같은 모델이라도 좌표가 완전히 같지는 않아, 지표가 얼마나 달라지는지
// scripts/compare_landmarks.py 로 대조해야 한다.
type Delegate = "GPU" | "CPU";

interface Collected {
  t: number;
  world: number[][];
  xy: number[][];
  vis: number[];
}

export default function SpikePage() {
  const [log, setLog] = useState<string[]>([]);
  const [delegate, setDelegate] = useState<Delegate>("GPU");
  const [busy, setBusy] = useState(false);
  const say = (s: string) => setLog((prev) => [...prev, s]);

  const run = async (file: File) => {
    setBusy(true);
    setLog([]);
    try {
      const t0 = performance.now();
      const fileset = await FilesetResolver.forVisionTasks("/mp-wasm");
      const landmarker = await PoseLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: "/pose_landmarker_lite.task", delegate },
        runningMode: "VIDEO",
        numPoses: 1,
        minPoseDetectionConfidence: 0.25,
        minPosePresenceConfidence: 0.25,
        minTrackingConfidence: 0.25,
      });
      say(`모델 로딩 ${((performance.now() - t0) / 1000).toFixed(1)}초 (${delegate})`);

      const video = document.createElement("video");
      video.src = URL.createObjectURL(file);
      video.muted = true;
      video.playsInline = true;
      await new Promise<void>((resolve, reject) => {
        video.onloadedmetadata = () => resolve();
        video.onerror = () => reject(new Error("영상을 읽지 못했습니다"));
      });
      say(
        `영상 ${video.videoWidth}x${video.videoHeight}, ${video.duration.toFixed(1)}초, ` +
          `${(file.size / 1048576).toFixed(1)}MB`,
      );

      const collected: Collected[] = [];
      let ticks = 0;
      const t1 = performance.now();
      await video.play();
      await new Promise<void>((resolve) => {
        const tick = () => {
          if (video.ended) {
            resolve();
            return;
          }
          ticks += 1;
          const res = landmarker.detectForVideo(video, performance.now());
          if (res.worldLandmarks.length > 0 && res.landmarks.length > 0) {
            collected.push({
              t: video.currentTime,
              world: res.worldLandmarks[0].map((l) => [l.x, l.y, l.z]),
              xy: res.landmarks[0].map((l) => [l.x, l.y]),
              vis: res.landmarks[0].map((l) => l.visibility ?? 0),
            });
          }
          video.requestVideoFrameCallback(tick);
        };
        video.requestVideoFrameCallback(tick);
      });

      const secs = (performance.now() - t1) / 1000;
      const rate = collected.length / Math.max(ticks, 1);
      say(`추출 ${secs.toFixed(1)}초 | 프레임 ${ticks}개 | 포즈 인식 ${collected.length}개 (${(rate * 100).toFixed(0)}%)`);
      say(`프레임당 ${((secs * 1000) / Math.max(ticks, 1)).toFixed(0)}ms`);
      say(
        secs <= 10 && rate >= 0.8
          ? "판정: 통과 (10초 이내, 인식률 80% 이상)"
          : secs <= 20
            ? "판정: 보고 후 결정 (10~20초)"
            : "판정: 불가 (20초 초과)",
      );

      const payload = {
        fps: video.duration > 0 ? ticks / video.duration : 30,
        resolution: [video.videoWidth, video.videoHeight],
        frames: collected,
      };
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(payload)], { type: "application/json" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "landmarks.json";
      a.click();
      URL.revokeObjectURL(url);
      URL.revokeObjectURL(video.src);
      say("landmarks.json 내려받음 — 서버 대조에 쓴다");
    } catch (err) {
      say(`실패: ${err instanceof Error ? err.message : String(err)}`);
      say("GPU 로 실패했다면 CPU 로 바꿔 다시 재 본다");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 720 }}>
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>
        포즈 추출 속도 측정
      </h1>
      <p className="text-muted" style={{ fontSize: 13, marginBottom: 16 }}>
        스윙 영상을 고르면 이 기기에서 좌표를 뽑는 데 걸리는 시간을 잽니다.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {(["GPU", "CPU"] as const).map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDelegate(d)}
            className={`chip ${delegate === d ? "accent" : ""}`}
            style={{ cursor: "pointer", border: "none" }}
          >
            {d}
          </button>
        ))}
      </div>

      <input
        type="file"
        accept="video/*"
        disabled={busy}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void run(f);
        }}
      />

      <pre style={{ marginTop: 20, fontSize: 13, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>
        {log.join("\n")}
      </pre>
    </div>
  );
}
