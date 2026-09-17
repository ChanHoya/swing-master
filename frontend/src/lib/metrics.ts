// 백엔드 metrics_to_json() 이 돌려주는 지표 한 건의 모양.
//
// value 가 null 인 경우는 두 가지이고, 화면에서 다르게 안내해야 한다.
//   measurable=false : 이 촬영 각도에서는 애초에 측정할 수 없다
//   measurable=true  : 각도는 맞았지만 계산에 실패했다
export interface MetricEntry {
  value: number | null;
  confidence: number;
  unit: string;
  measurable: boolean;
}

interface MetricMeta {
  label: string;
  ideal: number;
  /** 이 폭만큼 벗어나면 0점. 백엔드 rules.py 의 tolerance 와 같은 값이다. */
  tolerance: number;
  note?: string;
}

export const METRIC_META: Record<string, MetricMeta> = {
  spine_angle: { label: "척추 각도", ideal: 37, tolerance: 25 },
  knee_flex: { label: "무릎 굴곡", ideal: 25, tolerance: 20 },
  shoulder_rotation: { label: "어깨 회전", ideal: 90, tolerance: 45 },
  hip_rotation: { label: "힙 회전", ideal: 45, tolerance: 30 },
  x_factor: { label: "X-팩터", ideal: 45, tolerance: 35 },
  head_movement: { label: "헤드 무브먼트", ideal: 2, tolerance: 10 },
  weight_shift: { label: "체중 이동", ideal: 15, tolerance: 15, note: "추정치" },
  tempo_ratio: { label: "템포 비율", ideal: 3, tolerance: 2 },
};

/** 화면에 보여줄 순서. 회전 지표를 앞에 둔다. */
export const METRIC_ORDER: string[] = [
  "shoulder_rotation",
  "hip_rotation",
  "x_factor",
  "spine_angle",
  "knee_flex",
  "tempo_ratio",
  "head_movement",
  "weight_shift",
];

/** 이 값 미만이면 랜드마크 인식이 불안정했다는 뜻이다. */
const LOW_CONFIDENCE = 0.5;

function isMetricEntry(value: unknown): value is MetricEntry {
  if (typeof value !== "object" || value === null) return false;
  const entry = value as Record<string, unknown>;
  return (
    (typeof entry.value === "number" || entry.value === null) &&
    typeof entry.measurable === "boolean"
  );
}

/** 백엔드 응답에서 지표 한 건을 안전하게 꺼낸다. 모양이 다르면 undefined. */
export function readMetric(
  metrics: Record<string, unknown> | undefined,
  key: string,
): MetricEntry | undefined {
  const entry = metrics?.[key];
  return isMetricEntry(entry) ? entry : undefined;
}

/** metrics 페이로드의 "_meta" 에 함께 오는 부가 정보. */
export interface SwingMeta {
  camera_angle?: string;
  swing_start_sec?: number;
  swing_end_sec?: number;
  measured_count?: number;
  total_count?: number;
}

/** "_meta" 를 안전하게 꺼낸다. 없거나 모양이 다르면 빈 객체. */
export function readMeta(metrics: Record<string, unknown> | undefined): SwingMeta {
  const meta = metrics?.["_meta"];
  if (typeof meta !== "object" || meta === null) return {};
  const raw = meta as Record<string, unknown>;
  const num = (key: string): number | undefined =>
    typeof raw[key] === "number" ? (raw[key] as number) : undefined;
  return {
    camera_angle: typeof raw.camera_angle === "string" ? raw.camera_angle : undefined,
    swing_start_sec: num("swing_start_sec"),
    swing_end_sec: num("swing_end_sec"),
    measured_count: num("measured_count"),
    total_count: num("total_count"),
  };
}

/** 측정값을 화면 문자열로 바꾼다. 없는 값을 지어내지 않는다. */
export function formatMetric(entry: MetricEntry | undefined): string {
  if (!entry) return "—";
  if (!entry.measurable) return "이 각도에서는 측정 불가";
  if (entry.value === null) return "측정 실패";
  return `${entry.value}${entry.unit}`;
}

/** 값이 실제로 있는가. 레이더 차트에 그릴지 판단할 때 쓴다. */
export function hasValue(entry: MetricEntry | undefined): entry is MetricEntry {
  return entry !== undefined && entry.value !== null;
}

/** 랜드마크 인식이 불안정했는가. 화면에 경고를 붙인다. */
export function isLowConfidence(entry: MetricEntry | undefined): boolean {
  return hasValue(entry) && entry.confidence < LOW_CONFIDENCE;
}

/**
 * 기준값에 얼마나 가까운가를 0~1 로. 레이더 차트 반지름 비율로 쓴다.
 * 백엔드 rules.score_metric 과 같은 계산이다.
 */
export function metricFillRatio(key: string, value: number): number {
  const meta = METRIC_META[key];
  if (!meta) return 0;
  const deviation = Math.abs(value - meta.ideal) / meta.tolerance;
  return Math.max(0.08, Math.min(1, 1 - deviation));
}
