/**
 * 업로드 전에 영상을 640px 폭으로 줄인다.
 *
 * 서버는 어차피 640px 로 줄여서 포즈를 추정한다(pose.py 의 proc_width).
 * 그런데 지금은 폰이 1080p 원본을 그대로 올리고, 서버가 프레임마다 그것을
 * 풀어서 대부분의 픽셀을 버린다. 0.1 CPU 에서 이 낭비가 크다 — 실측에서
 * 파일이 클수록 프레임당 비용이 0.70초에서 2.39초까지 3.4배 올랐다.
 *
 * 미리 줄여 보내면 같은 결과를 얻으면서 업로드와 디코딩 비용이 함께 준다.
 * 14.8MB 영상이 1~2MB 가 되므로 LTE 업로드가 30~60초에서 3~6초로 줄고,
 * 서버 분석도 296초에서 100초 안팎으로 내려간다.
 *
 * 되는 곳에서만 한다. 브라우저가 지원하지 않거나 중간에 실패하면 원본을
 * 그대로 돌려준다 — 최적화 때문에 업로드 자체가 막히면 안 된다.
 */

/** 서버 pose.py 의 proc_width 와 같아야 의미가 있다. */
export const TARGET_WIDTH = 640;

export interface DownscaleResult {
  blob: Blob;
  /** 줄이지 못하고 원본을 그대로 쓰는 경우 사유. 성공이면 undefined. */
  skipped?: string;
  originalBytes: number;
  bytes: number;
}

function pickMimeType(): string | null {
  if (typeof MediaRecorder === "undefined") return null;
  // Safari 는 mp4, Chrome 계열은 webm 을 낸다. 서버가 둘 다 받는다.
  const candidates = [
    "video/mp4",
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/webm",
  ];
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) ?? null;
}

export async function downscaleVideo(
  file: File,
  onProgress?: (ratio: number) => void,
): Promise<DownscaleResult> {
  const originalBytes = file.size;
  const give_up = (reason: string): DownscaleResult => ({
    blob: file,
    skipped: reason,
    originalBytes,
    bytes: originalBytes,
  });

  const mimeType = pickMimeType();
  if (!mimeType) return give_up("이 브라우저는 영상 변환을 지원하지 않습니다");

  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.src = url;
  video.muted = true;
  video.playsInline = true;

  try {
    await new Promise<void>((resolve, reject) => {
      video.onloadedmetadata = () => resolve();
      video.onerror = () => reject(new Error("영상을 읽지 못했습니다"));
    });

    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) return give_up("영상 크기를 알 수 없습니다");
    if (width <= TARGET_WIDTH) return give_up("이미 충분히 작습니다");

    const scale = TARGET_WIDTH / width;
    // 짝수로 맞춘다. 홀수 높이는 일부 인코더가 거부한다.
    const outW = TARGET_WIDTH;
    const outH = Math.round((height * scale) / 2) * 2;

    const canvas = document.createElement("canvas");
    canvas.width = outW;
    canvas.height = outH;
    const ctx = canvas.getContext("2d");
    if (!ctx) return give_up("캔버스를 만들지 못했습니다");

    const stream = canvas.captureStream();
    const chunks: Blob[] = [];
    const recorder = new MediaRecorder(stream, {
      mimeType,
      videoBitsPerSecond: 2_500_000,
    });
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    const done = new Promise<void>((resolve) => {
      recorder.onstop = () => resolve();
    });

    recorder.start();

    // 재생하면서 프레임을 그대로 옮겨 그린다. 1배속으로 도는 이유는,
    // 빠르게 감으면 MediaRecorder 가 실시간으로 기록해 결과물의 시간축이
    // 어긋나기 때문이다. 템포 지표가 프레임 시각에 의존하므로 어긋나면 안 된다.
    const duration = Number.isFinite(video.duration) ? video.duration : 0;
    const draw = () => {
      ctx.drawImage(video, 0, 0, outW, outH);
      if (duration > 0) onProgress?.(Math.min(video.currentTime / duration, 1));
    };

    const hasFrameCallback = "requestVideoFrameCallback" in video;
    let rafId = 0;
    const pump = () => {
      draw();
      if (hasFrameCallback) {
        video.requestVideoFrameCallback(pump);
      } else {
        rafId = requestAnimationFrame(pump);
      }
    };

    await video.play();
    pump();

    await new Promise<void>((resolve) => {
      video.onended = () => resolve();
    });

    if (!hasFrameCallback) cancelAnimationFrame(rafId);
    recorder.stop();
    await done;

    const blob = new Blob(chunks, { type: mimeType.split(";")[0] });
    if (blob.size === 0) return give_up("변환 결과가 비어 있습니다");
    // 줄였는데 오히려 커졌다면 원본이 낫다.
    if (blob.size >= originalBytes) return give_up("원본이 더 작습니다");

    return { blob, originalBytes, bytes: blob.size };
  } catch (err) {
    return give_up(err instanceof Error ? err.message : "영상 변환에 실패했습니다");
  } finally {
    URL.revokeObjectURL(url);
  }
}
