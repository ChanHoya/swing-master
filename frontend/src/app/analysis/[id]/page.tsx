"use client";

import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import Link from "next/link";
import {
  METRIC_META,
  METRIC_ORDER,
  PHASE_LABELS,
  formatMetric,
  hasValue,
  isLowConfidence,
  metricFillRatio,
  readMeta,
  readMetric,
} from "@/lib/metrics";

/** 재생 속도 선택지. 임팩트는 0.25배속 아래로 내려야 눈에 들어온다. */
const SPEEDS = [1, 0.75, 0.5, 0.25, 0.1] as const;
const SLOW_SPEED = 0.25;

/** 단계 재생 시 앞뒤로 볼 시간(초). 1초 구간을 0.25배속이면 4초쯤 재생된다. */
const PHASE_WINDOW_SEC = 0.5;

// ─── Types ────────────────────────────────────────────────────
interface Issue {
  metric: string;
  severity: "high" | "medium" | "low";
  feedback: string;
}
interface Drill {
  issue_metric: string;
  drill_name: string;
  steps: string[];
  repetitions: string;
  tip: string;
}
interface Feedback {
  overall_score?: number;
  grade?: string;
  top_issues?: Issue[];
  drills?: Drill[];
  encouragement?: string;
}
interface AnalysisResult {
  upload_id: string;
  status: string;
  overall_score?: number;
  grade?: string;
  // 지표 8개는 {value, confidence, unit, measurable} 객체다.
  // "_meta" 키에 촬영 각도·스윙 구간 같은 부가 정보가 함께 온다.
  metrics?: Record<string, unknown>;
  feedback?: Feedback;
  overlay_urls?: Record<string, string>;
  completed_at?: string;
}

// ─── Score Ring ───────────────────────────────────────────────
function ScoreRing({ score, grade }: { score: number; grade: string }) {
  const radius = 58;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;
  const gradeConfig: Record<string, { color: string; bg: string; label: string }> = {
    A: { color: "var(--ok)", bg: "var(--ok-dim)", label: "최우수" },
    B: { color: "var(--accent)", bg: "var(--accent-dim)", label: "우수" },
    C: { color: "var(--warn)", bg: "var(--warn-dim)", label: "보통" },
    D: { color: "var(--danger)", bg: "var(--danger-dim)", label: "미흡" },
  };
  const cfg = gradeConfig[grade] ?? gradeConfig.C;

  return (
    <div className="score-ring-wrap">
      <div style={{ position: "relative", width: 160, height: 160 }}>
        <svg width="160" height="160" style={{ transform: "rotate(-90deg)" }} viewBox="0 0 160 160">
          <circle cx="80" cy="80" r={radius} fill="none" stroke="var(--bg-4)" strokeWidth="14" />
          <circle cx="80" cy="80" r={radius} fill="none" stroke={cfg.color} strokeWidth="14"
            strokeDasharray={circ} strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 1.4s cubic-bezier(.4,0,.2,1)", filter: `drop-shadow(0 0 10px ${cfg.color})` }} />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <span className="serif" style={{ fontSize: 40, color: "var(--text)" }}>{score}</span>
          <span className="text-muted text-xs">/ 100</span>
        </div>
      </div>
      <div className="chip" style={{ background: cfg.bg, color: cfg.color, borderColor: cfg.color + "40" }}>
        {grade}등급 · {cfg.label}
      </div>
    </div>
  );
}

// ─── SVG Radar Chart ─────────────────────────────────────────
function RadarChart({ metrics }: { metrics: Record<string, unknown> }) {
  // 측정된 지표만 축으로 세운다. 측정 못 한 것을 0으로 채우면
  // "완전히 잘못된 스윙"처럼 보인다 — 이 프로젝트가 없애려던 종류의 거짓말이다.
  const axes = METRIC_ORDER.flatMap((key) => {
    const entry = readMetric(metrics, key);
    if (!hasValue(entry)) return [];
    return [{ key, value: entry.value as number, label: METRIC_META[key].label }];
  });

  if (axes.length < 3) return null; // 축이 3개 미만이면 도형이 안 된다

  const size = 240;
  const cx = size / 2;
  const cy = size / 2;
  const r = 85;
  const n = axes.length;

  const polarXY = (angle: number, radius: number) => {
    const rad = (angle - 90) * (Math.PI / 180);
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  };

  const axisData = axes.map((a, i) => {
    const angle = (360 / n) * i;
    const pct = metricFillRatio(a.key, a.value);
    return { ...a, angle, tip: polarXY(angle, r), dot: polarXY(angle, r * pct), pct };
  });

  const dataPath = axisData.map((a, i) => `${i === 0 ? "M" : "L"} ${a.dot.x} ${a.dot.y}`).join(" ") + " Z";

  return (
    <svg width={size} height={size}>
      {[0.25, 0.5, 0.75, 1].map((p) => (
        <polygon key={p}
          points={axisData.map((a) => { const pt = polarXY(a.angle, r * p); return `${pt.x},${pt.y}`; }).join(" ")}
          fill="none" stroke="rgba(212,255,58,0.1)" strokeWidth="1" />
      ))}
      {axisData.map((a) => (
        <line key={a.key} x1={cx} y1={cy} x2={a.tip.x} y2={a.tip.y}
          stroke="rgba(212,255,58,0.2)" strokeWidth="1" />
      ))}
      <path d={dataPath} fill="rgba(212,255,58,0.15)" stroke="var(--accent)" strokeWidth="2.5"
        style={{ filter: "drop-shadow(0 0 6px rgba(212,255,58,0.4))" }} />
      {axisData.map((a) => (
        <circle key={a.key} cx={a.dot.x} cy={a.dot.y} r={6} fill="var(--accent)"
          style={{ filter: "drop-shadow(0 0 4px var(--accent))" }} />
      ))}
      {axisData.map((a) => {
        const lp = polarXY(a.angle, r + 26);
        return (
          <g key={a.key}>
            <text x={lp.x} y={lp.y - 7} textAnchor="middle" fontSize="10" fill="var(--text-3)">{a.label}</text>
            <text x={lp.x} y={lp.y + 7} textAnchor="middle" fontSize="11" fill="var(--text)" fontWeight="700">
              {a.value.toFixed(1)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ─── Severity Config ─────────────────────────────────────────
const SEV: Record<string, { label: string; cls: string; icon: string }> = {
  high:   { label: "높음", cls: "bad",  icon: "🔴" },
  medium: { label: "중간", cls: "warn", icon: "🟡" },
  low:    { label: "낮음", cls: "ok",   icon: "🟢" },
};

// ─── Page ────────────────────────────────────────────────────
export default function AnalysisResultPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  // 훅은 조기 반환보다 앞에 있어야 한다. 로딩·에러 분기가 아래에 있다.
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const videoSectionRef = useRef<HTMLDivElement | null>(null);
  const [speed, setSpeed] = useState<number>(1);
  const [loopRange, setLoopRange] = useState<{ start: number; end: number } | null>(null);
  const [activePhase, setActivePhase] = useState<string | null>(null);

  const { data: result, isLoading, isError } = useQuery<AnalysisResult>({
    queryKey: ["analysisResult", id],
    queryFn: async () => {
      const res = await apiClient.get(`/analysis/${id}/result`);
      return res.data;
    },
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: 16 }}>
        <div style={{ width: 48, height: 48, borderRadius: "50%", border: "3px solid var(--bg-4)", borderTopColor: "var(--accent)" }} className="animate-spin" />
        <p className="text-muted">결과를 불러오는 중입니다...</p>
      </div>
    );
  }

  if (isError || !result) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: 16, textAlign: "center" }}>
        <div style={{ fontSize: 48 }}>😔</div>
        <div className="h2">결과를 불러오지 못했습니다.</div>
        <p className="text-muted">분석 데이터가 없거나 잘못된 접근입니다.</p>
        <button onClick={() => router.push("/upload")} className="btn primary lg mt-2">
          다시 업로드 하기
        </button>
      </div>
    );
  }

  const fb = result.feedback ?? {};
  const overallScore = result.overall_score ?? fb.overall_score ?? 0;
  const grade = result.grade ?? fb.grade ?? "C";
  const issues: Issue[] = fb.top_issues?.filter((i) => i.metric !== "시스템") ?? [];
  const drills: Drill[] = fb.drills ?? [];
  const encouragement = fb.encouragement ?? "";
  const metrics = result.metrics ?? {};
  const overlays = result.overlay_urls ?? {};
  const hasAiFeedback = issues.length > 0 || drills.length > 0;

  const meta = readMeta(metrics);
  const measuredCount = METRIC_ORDER.filter((k) =>
    hasValue(readMetric(metrics, k)),
  ).length;

  /**
   * 단계 카드를 눌렀을 때 영상을 그 지점으로 옮긴다.
   *
   * loop=false 면 그 지점에 멈춰 세워 두고 사용자가 재생 버튼을 누르게 한다.
   * loop=true 면 앞뒤 PHASE_WINDOW_SEC 만큼을 0.25배속으로 반복 재생한다.
   * 임팩트처럼 순식간에 지나가는 구간을 눈으로 보려면 느리게 돌려야 한다.
   */
  const goToPhase = (phase: string, loop: boolean) => {
    const at = meta.phase_seconds?.[phase];
    const video = videoRef.current;
    if (at === undefined || !video) return;

    setActivePhase(phase);
    videoSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });

    if (loop) {
      const start = Math.max(0, at - PHASE_WINDOW_SEC);
      const end = at + PHASE_WINDOW_SEC;
      setLoopRange({ start, end });
      setSpeed(SLOW_SPEED);
      video.playbackRate = SLOW_SPEED;
      video.currentTime = start;
      video.play().catch(() => {});
    } else {
      setLoopRange(null);
      video.currentTime = at;
      video.pause();
    }
  };

  return (
    <div className="animate-fadein" style={{ maxWidth: 960 }}>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumb">
          <a href="/">대시보드</a>
          <span className="sep">/</span>
          <span className="now">분석 리포트</span>
        </div>
        <div className="topbar-actions">
          <button className="btn">📤 코치에게</button>
          <button className="btn">PDF</button>
        </div>
      </div>

      {/* Header Block */}
      <div className="header-block">
        <div>
          <div className="session-meta">SWING ANALYSIS REPORT</div>
          <div className="h1">
            스윙 <span className="em">진단 리포트</span>
          </div>
          {result.completed_at && (
            <p className="text-muted text-small mt-1">
              {new Date(result.completed_at).toLocaleString("ko-KR", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" })}
            </p>
          )}
        </div>
        <div className="header-stats">
          <div className="h-stat">
            <div className="val hi">{overallScore}</div>
            <div className="lbl">SCORE</div>
          </div>
          <div className="h-stat">
            <div className="val">{grade}</div>
            <div className="lbl">GRADE</div>
          </div>
        </div>
      </div>

      {/* Score + Radar */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: 24 }}>
          <div className="card-sub">종합 점수</div>
          <ScoreRing score={overallScore} grade={grade} />
          {encouragement && !encouragement.startsWith("피드백 생성 중") && (
            <p className="text-muted text-small text-center" style={{ maxWidth: 280 }}>
              {encouragement}
            </p>
          )}
        </div>

        <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: 24 }}>
          <div className="card-sub">스윙 지표 레이더</div>
          {measuredCount > 0 ? (
            <>
              <RadarChart metrics={metrics} />
              <p className="text-muted text-xs">
                8개 중 {measuredCount}개 측정됨
              </p>
              <div className="metrics-grid w-full">
                {METRIC_ORDER.map((key) => {
                  const meta = METRIC_META[key];
                  const entry = readMetric(metrics, key);
                  const measured = hasValue(entry);
                  return (
                    <div key={key} className="metric">
                      <div className="metric-name">
                        {meta.label}
                        {meta.note && (
                          <span className="text-muted text-xs" style={{ marginLeft: 4 }}>
                            ({meta.note})
                          </span>
                        )}
                      </div>
                      <div
                        className="metric-val"
                        style={measured ? undefined : { fontSize: 13, color: "var(--text-3)" }}
                      >
                        {formatMetric(entry)}
                      </div>
                      {isLowConfidence(entry) && (
                        <div className="text-muted text-xs">인식 불안정</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <p className="text-muted" style={{ padding: "48px 0" }}>
              지표를 측정하지 못했습니다. 전신이 화면에 들어오도록
              조금 더 멀리서 다시 촬영해 주세요.
            </p>
          )}
        </div>
      </div>

      {/* ── Swing Video Replay ── */}
      {overlays["original_video"] && meta.swing_start_sec !== undefined && (() => {
        // 예전에는 person_y_min 으로 상단 배경을 잘라냈으나 그 지표는 제거됐다.
        // 영상을 그대로 보여주고 재생 구간만 스윙에 맞춘다.
        const padPct = (9 / 16) * 100;
        const startSec = meta.swing_start_sec ?? 0;
        const endSec = meta.swing_end_sec;

        return (
          <div className="mt-6" ref={videoSectionRef}>
            <div className="card-head">
              <div className="card-title">🎬 스윙 구간 다시보기</div>
            </div>
            <div className="viewer">
              <div style={{ position: "relative", width: "100%", paddingBottom: `${padPct}%`, overflow: "hidden", background: "#000" }}>
                <video
                  ref={videoRef}
                  key={overlays["original_video"]}
                  controls playsInline preload="metadata"
                  style={{ position: "absolute", width: "100%", height: "100%", top: 0, left: 0, objectFit: "contain" }}
                  onLoadedMetadata={(e) => {
                    e.currentTarget.currentTime = startSec;
                    e.currentTarget.playbackRate = speed;
                  }}
                  onTimeUpdate={(e) => {
                    const v = e.currentTarget;
                    // 구간 반복. 단계 재생 중이면 그 좁은 구간을, 아니면 스윙 전체를 돈다.
                    const lo = loopRange ? loopRange.start : startSec;
                    const hi = loopRange ? loopRange.end : (endSec ?? v.duration);
                    if (v.currentTime >= hi) {
                      v.currentTime = lo;
                      v.play().catch(() => {});
                    }
                  }}
                >
                  <source src={overlays["original_video"]} type="video/mp4" />
                </video>
              </div>

              {/* 재생 속도 */}
              <div className="viewer-controls" style={{ gap: 8, flexWrap: "wrap" }}>
                <span className="text-xs text-muted">재생 속도</span>
                {SPEEDS.map((s) => (
                  <button
                    key={s}
                    className={`chip ${speed === s ? "accent" : ""}`}
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      setSpeed(s);
                      if (videoRef.current) videoRef.current.playbackRate = s;
                    }}
                  >
                    {s}×
                  </button>
                ))}
                {loopRange && (
                  <button
                    className="chip"
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      setLoopRange(null);
                      setActivePhase(null);
                      if (videoRef.current) videoRef.current.currentTime = startSec;
                    }}
                  >
                    전체 구간으로
                  </button>
                )}
              </div>

              <div className="viewer-controls" style={{ justifyContent: "space-between" }}>
                <span className="mono text-xs text-muted">
                  {loopRange
                    ? `${PHASE_LABELS[activePhase ?? ""] ?? "구간"} 반복: ${loopRange.start.toFixed(1)}s ~ ${loopRange.end.toFixed(1)}s`
                    : `스윙 구간: ${startSec.toFixed(1)}s ~ ${endSec?.toFixed(1)}s`}
                </span>
                <a href={overlays["original_video"]} download target="_blank" className="btn sm">
                  ↓ 원본 다운로드
                </a>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ── 7단계 스윙 분석 스트립 ── */}
      {Object.keys(overlays).length > 0 && (() => {
        const PHASES_7 = [
          { key: "address",       label: "1.어드레스",    color: "var(--accent)" },
          { key: "takeaway",      label: "2.테이크백",    color: "var(--purple)" },
          { key: "top",           label: "3.탑",          color: "var(--danger)" },
          { key: "downswing",     label: "4.다운스윙",    color: "var(--warn)" },
          { key: "impact",        label: "5.임팩트",      color: "var(--danger)" },
          { key: "followthrough", label: "6.팔로우스루",  color: "var(--ok)" },
          { key: "finish",        label: "7.피니시",      color: "var(--blue)" },
        ];
        const available = PHASES_7.filter((p) => overlays[p.key]);
        if (available.length === 0) return null;
        return (
          <div className="mt-6">
            <div className="card-head">
              <div className="card-title">📸 7단계 스윙 분석</div>
              <Link href="/guide" className="btn sm">
                7단계 가이드 →
              </Link>
            </div>

            {/* 가로 스크롤 스트립 — 세로 충분히 확보 */}
            <div style={{ overflowX: "auto", paddingBottom: 8 }}>
              <div style={{
                display: "flex",
                gap: 8,
                minWidth: `${available.length * 148}px`,
              }}>
                {available.map((p) => (
                  <div
                    key={p.key}
                    style={{
                      width: 140,
                      flexShrink: 0,
                      background: "var(--bg-3)",
                      border: `1px solid color-mix(in srgb, ${p.color} 30%, transparent)`,
                      borderRadius: 12,
                      padding: 6,
                      cursor: "pointer",
                      transition: "transform 0.2s, border-color 0.2s",
                    }}
                    onMouseEnter={e => {
                      (e.currentTarget as HTMLElement).style.transform = "translateY(-3px)";
                      (e.currentTarget as HTMLElement).style.borderColor = p.color;
                    }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLElement).style.transform = "none";
                      (e.currentTarget as HTMLElement).style.borderColor = `color-mix(in srgb, ${p.color} 30%, transparent)`;
                    }}
                    // 카드를 누르면 영상을 그 단계로 옮기고 멈춰 둔다.
                    // 재생은 사용자가 영상의 재생 버튼으로 시작한다.
                    onClick={() => goToPhase(p.key, false)}
                  >
                    {/* 단계 번호 + 시각 */}
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 4,
                    }}>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10,
                        color: p.color,
                        letterSpacing: "0.1em",
                      }}>
                        {p.label.split(".")[0]}.
                      </span>
                      {meta.phase_seconds?.[p.key] !== undefined && (
                        <span className="mono text-xs text-muted">
                          {meta.phase_seconds[p.key].toFixed(1)}s
                        </span>
                      )}
                    </div>

                    {/* 이미지 — 세로로 길게 (전신 보이도록) */}
                    <div style={{
                      position: "relative",
                      height: 260,
                      borderRadius: 8,
                      overflow: "hidden",
                      background: "#000",
                      marginBottom: 6,
                      outline: activePhase === p.key ? `2px solid ${p.color}` : "none",
                    }}>
                      <img
                        src={overlays[p.key]}
                        alt={p.label}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "contain",   // 잘리지 않고 전신 표시
                          objectPosition: "center",
                          display: "block",
                        }}
                      />

                      {/* 이 단계 전후를 느리게 반복 재생한다.
                          카드 클릭(이동)과 구분되도록 이벤트 전파를 막는다. */}
                      {meta.phase_seconds?.[p.key] !== undefined && (
                        <button
                          aria-label={`${p.label} 구간 느리게 반복 재생`}
                          onClick={(e) => {
                            e.stopPropagation();
                            goToPhase(p.key, true);
                          }}
                          style={{
                            position: "absolute",
                            left: "50%",
                            top: "50%",
                            transform: "translate(-50%, -50%)",
                            width: 44,
                            height: 44,
                            borderRadius: "50%",
                            border: `2px solid ${p.color}`,
                            background: "rgba(0,0,0,0.55)",
                            color: p.color,
                            fontSize: 16,
                            cursor: "pointer",
                            display: "grid",
                            placeItems: "center",
                          }}
                        >
                          ▶
                        </button>
                      )}
                    </div>

                    {/* 단계명 */}
                    <div style={{
                      textAlign: "center",
                      fontSize: 11,
                      fontWeight: 700,
                      color: p.color,
                      padding: "2px 0",
                    }}>
                      {p.label.split(".")[1]}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 진행 바 */}
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              {available.map((p) => (
                <div
                  key={p.key}
                  style={{ flex: 1, height: 3, borderRadius: 2, background: p.color, opacity: 0.5 }}
                />
              ))}
            </div>
          </div>
        );
      })()}

      {/* ── AI Feedback ── */}
      {hasAiFeedback ? (
        <>
          {/* Issues */}
          {issues.length > 0 && (
            <div className="mt-6">
              <div className="card-head">
                <div className="card-title">🎯 주요 교정 포인트</div>
              </div>
              <div className="flex-col gap-2" style={{ display: "flex" }}>
                {issues.map((issue, i) => {
                  const sev = SEV[issue.severity] ?? SEV.low;
                  return (
                    <div key={i} className="card flex items-center gap-3" style={{ padding: 16 }}>
                      <div
                        style={{
                          width: 4,
                          alignSelf: "stretch",
                          borderRadius: 2,
                          background: sev.cls === "bad" ? "var(--danger)" : sev.cls === "warn" ? "var(--warn)" : "var(--ok)",
                        }}
                      />
                      <div style={{ flex: 1 }}>
                        <div className="flex items-center gap-2 mb-1">
                          <span>{sev.icon}</span>
                          <span style={{ fontWeight: 700, fontSize: 14 }}>{issue.metric}</span>
                          <span className={`chip ${sev.cls}`} style={{ fontSize: 9, padding: "2px 6px", marginLeft: "auto" }}>
                            심각도 {sev.label}
                          </span>
                        </div>
                        <p className="text-muted text-small">{issue.feedback}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Drills */}
          {drills.length > 0 && (
            <div className="mt-6">
              <div className="card-head">
                <div className="card-title">🏋️ 맞춤 교정 드릴</div>
              </div>
              <div className="grid grid-2 gap-3" style={{ gap: 12 }}>
                {drills.map((drill, i) => (
                  <div
                    key={i}
                    className="card"
                    style={{
                      background: "linear-gradient(135deg, rgba(212,255,58,0.06) 0%, rgba(212,255,58,0.01) 100%)",
                      border: "1px solid rgba(212,255,58,0.15)",
                    }}
                  >
                    <div className="flex justify-between items-start gap-3 mb-3">
                      <div className="card-title" style={{ color: "var(--accent)" }}>{drill.drill_name}</div>
                      <span className="chip mono">{drill.repetitions}</span>
                    </div>
                    <ol style={{ margin: 0, paddingLeft: 20, fontSize: 12, color: "var(--text-2)", lineHeight: 1.8 }}>
                      {drill.steps.map((step, j) => (
                        <li key={j}>{step}</li>
                      ))}
                    </ol>
                    {drill.tip && (
                      <div className="msg plan mt-2 flex gap-2" style={{ fontSize: 12 }}>
                        <span>💡</span>
                        <span style={{ color: "var(--accent)" }}>{drill.tip}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="card mt-6" style={{ textAlign: "center", padding: 24, background: "var(--warn-dim)", border: "1px solid rgba(255,184,77,0.2)" }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>⚠️</div>
          <div className="h3" style={{ color: "var(--warn)" }}>AI 피드백을 불러오지 못했습니다</div>
          <p className="text-muted text-small mt-1">Gemini API 서버가 일시적으로 혼잡합니다. 스켈레톤 분석은 정상적으로 완료되었습니다.</p>
          <button onClick={() => window.location.reload()} className="btn mt-3" style={{ borderColor: "rgba(255,184,77,0.3)", color: "var(--warn)" }}>
            새로고침하여 다시 시도
          </button>
        </div>
      )}

      {/* CTA */}
      <div className="text-center mt-6 mb-4">
        <button onClick={() => router.push("/upload")} className="btn primary lg">
          새 영상 분석하기 →
        </button>
      </div>
    </div>
  );
}
