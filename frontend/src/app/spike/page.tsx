"use client";

import { useRef, useState } from "react";
import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";

// 일회용 측정 페이지. 설계의 유일한 미검증 전제인 "폰에서 MediaPipe 가
// 쓸 만한 속도로 도는가" 를 재기 위한 것이다. 전환이 끝나면 삭제한다.
//
// video 를 DOM 에 붙여 둔다. 화면에 없는 비디오는 모바일에서
// requestVideoFrameCallback 이 오지 않아 조용히 멈춘다 — 첫 측정이
// 그렇게 실패했다.
type Delegate = "GPU" | "CPU";

interface Collected {
  t: number;
  world: number[][];
  xy: number[][];
  vis: number[];
}

const CALLBACK_WAIT_MS = 4000;

export default function SpikePage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [delegate, setDelegate] = useState<Delegate>("GPU");
  const [busy, setBusy] = useState(false);
  const say = (s: string) => setLog((prev) => [...prev, s]);

  const run = async (file: File) => {
    const video = videoRef.current;
    if (!video) return;
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

      video.src = URL.createObjectURL(file);
      await new Promise<void>((resolve, reject) => {
        video.onloadedmetadata = () => resolve();
        video.onerror = () => reject(new Error("영상을 읽지 못했습니다"));
      });
      const duration = video.duration;
      say(`영상 ${video.videoWidth}x${video.videoHeight}, ${duration.toFixed(1)}초, ${(file.size / 1048576).toFixed(1)}MB`);

      const collected: Collected[] = [];
      let ticks = 0;
      const snap = (t: number) => {
        ticks += 1;
        const res = landmarker.detectForVideo(video, performance.now());
        if (res.worldLandmarks.length > 0 && res.landmarks.length > 0) {
          collected.push({
            t,
            world: res.worldLandmarks[0].map((l) => [l.x, l.y, l.z]),
            xy: res.landmarks[0].map((l) => [l.x, l.y]),
            vis: res.landmarks[0].map((l) => l.visibility ?? 0),
          });
        }
      };

      const t1 = performance.now();
      let mode = "재생";
      say("재생하며 추출 시도…");

      await video.play().catch((e) => {
        say(`재생 거부됨: ${e instanceof Error ? e.message : String(e)}`);
      });

      const played = await new Promise<boolean>((resolve) => {
        let settled = false;
        const finish = (ok: boolean) => {
          if (!settled) { settled = true; resolve(ok); }
        };
        // 콜백이 아예 오지 않으면 다른 방법으로 넘어간다.
        const watchdog = setTimeout(() => {
          if (ticks === 0) {
            say(`프레임 콜백이 ${CALLBACK_WAIT_MS / 1000}초간 오지 않음 — 탐색 방식으로 전환`);
            finish(false);
          }
        }, CALLBACK_WAIT_MS);
        const tick = () => {
          if (video.ended) { clearTimeout(watchdog); finish(true); return; }
          snap(video.currentTime);
          if (ticks % 30 === 0) say(`  …${ticks}프레임 (${video.currentTime.toFixed(1)}초)`);
          video.requestVideoFrameCallback(tick);
        };
        video.requestVideoFrameCallback(tick);
      });

      if (!played) {
        // 탐색 방식: currentTime 을 옮기고 seeked 를 기다린다. 느리지만
        // 콜백에 의존하지 않는다.
        mode = "탐색";
        video.pause();
        collected.length = 0;
        ticks = 0;
        const step = 1 / 30;
        for (let t = 0; t < duration; t += step) {
          video.currentTime = t;
          const ok = await new Promise<boolean>((resolve) => {
            const to = setTimeout(() => resolve(false), 2000);
            video.onseeked = () => { clearTimeout(to); resolve(true); };
          });
          if (!ok) { say(`  탐색 실패 (${t.toFixed(1)}초)`); break; }
          snap(t);
          if (ticks % 30 === 0) say(`  …${ticks}프레임 (${t.toFixed(1)}초)`);
        }
      }

      const secs = (performance.now() - t1) / 1000;
      const rate = collected.length / Math.max(ticks, 1);
      say(`추출 ${secs.toFixed(1)}초 (${mode}) | 프레임 ${ticks}개 | 포즈 인식 ${collected.length}개 (${(rate * 100).toFixed(0)}%)`);
      say(`프레임당 ${((secs * 1000) / Math.max(ticks, 1)).toFixed(0)}ms`);
      say(
        ticks === 0
          ? "판정: 불가 (프레임을 하나도 읽지 못함)"
          : secs <= 10 && rate >= 0.8
            ? "판정: 통과 (10초 이내, 인식률 80% 이상)"
            : secs <= 20
              ? "판정: 보고 후 결정 (10~20초)"
              : "판정: 불가 (20초 초과)",
      );

      if (collected.length > 0) {
        const payload = {
          fps: duration > 0 ? ticks / duration : 30,
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
        say("landmarks.json 내려받음 — 서버 대조에 쓴다");
      }
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

      {/* DOM 에 붙여 둔다. 화면에 없으면 모바일에서 프레임 콜백이 오지 않는다. */}
      <video
        ref={videoRef}
        muted
        playsInline
        style={{ width: 160, marginTop: 16, borderRadius: 8, background: "#000" }}
      />

      <pre style={{ marginTop: 16, fontSize: 13, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>
        {log.join("\n")}
      </pre>
    </div>
  );
}
