"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import Link from "next/link";

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
  metrics?: Record<string, number> & {
    swing_start_sec?: number;
    swing_end_sec?: number;
  };
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
function RadarChart({ metrics }: { metrics: Record<string, number> }) {
  const axes = [
    { key: "spine_angle", label: "척추 각도", ideal: 37, range: 45 },
    { key: "tempo_ratio", label: "템포 비율", ideal: 3, range: 6 },
    { key: "head_movement", label: "헤드 안정성", ideal: 2, range: 10 },
  ];

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
    const val = metrics[a.key] ?? 0;
    const diff = Math.abs(val - a.ideal) / a.range;
    const pct = Math.max(0.08, 1 - diff);
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
        const val = metrics[a.key];
        return (
          <g key={a.key}>
            <text x={lp.x} y={lp.y - 7} textAnchor="middle" fontSize="10" fill="var(--text-3)">{a.label}</text>
            <text x={lp.x} y={lp.y + 7} textAnchor="middle" fontSize="11" fill="var(--text)" fontWeight="700">
              {val !== undefined ? Number(val).toFixed(1) : "—"}
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

  const metricConfig: Record<string, { label: string; unit: string }> = {
    spine_angle: { label: "척추 각도", unit: "°" },
    head_movement: { label: "헤드 무브먼트", unit: "cm" },
    tempo_ratio: { label: "템포 비율", unit: ":1" },
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
          {Object.keys(metrics).length > 0 ? (
            <>
              <RadarChart metrics={metrics} />
              <div className="metrics-grid w-full">
                {Object.entries(metrics).map(([key, val]) => {
                  const cfg = metricConfig[key];
                  if (!cfg) return null;
                  return (
                    <div key={key} className="metric">
                      <div className="metric-name">{cfg.label}</div>
                      <div className="metric-val">
                        {Number(val).toFixed(1)}
                        <span className="text-muted text-xs" style={{ marginLeft: 2, fontFamily: "inherit", fontStyle: "normal", fontWeight: 400 }}>{cfg.unit}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <p className="text-muted" style={{ padding: "48px 0" }}>
              지표 데이터 없음
            </p>
          )}
        </div>
      </div>

      {/* ── Swing Video Replay ── */}
      {overlays["original_video"] && metrics?.swing_start_sec !== undefined && (() => {
        const personTop = metrics.person_y_min ?? 0.30;
        const cropTop = Math.max(0, personTop - 0.06);
        const showFrac = 1 - cropTop;
        const padPct = (9 / 16) * showFrac * 100;
        const videoH = (1 / showFrac) * 100;
        const videoTop = -(cropTop / showFrac) * 100;

        return (
          <div className="mt-6">
            <div className="card-head">
              <div className="card-title">🎬 스윙 구간 다시보기</div>
            </div>
            <div className="viewer">
              <div style={{ position: "relative", width: "100%", paddingBottom: `${padPct}%`, overflow: "hidden", background: "#000" }}>
                <video
                  key={overlays["original_video"]}
                  controls loop playsInline preload="metadata"
                  style={{ position: "absolute", width: "100%", height: `${videoH}%`, top: `${videoTop}%`, left: 0 }}
                  onLoadedMetadata={(e) => {
                    const v = e.currentTarget;
                    v.currentTime = metrics.swing_start_sec ?? 0;
                  }}
                  onTimeUpdate={(e) => {
                    const v = e.currentTarget;
                    const end = metrics.swing_end_sec ?? v.duration;
                    if (v.currentTime >= end) {
                      v.currentTime = metrics.swing_start_sec ?? 0;
                      v.play().catch(() => {});
                    }
                  }}
                >
                  <source src={overlays["original_video"]} type="video/mp4" />
                </video>
              </div>
              <div className="viewer-controls" style={{ justifyContent: "space-between" }}>
                <span className="mono text-xs text-muted">
                  스윙 구간: {metrics.swing_start_sec?.toFixed(1)}s ~ {metrics.swing_end_sec?.toFixed(1)}s
                  {cropTop > 0.02 && <span style={{ marginLeft: 8, color: "var(--text-4)" }}>· 상단 {Math.round(cropTop * 100)}% 배경 제거</span>}
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
                  >
                    {/* 단계 번호 */}
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      color: p.color,
                      letterSpacing: "0.1em",
                      marginBottom: 4,
                    }}>
                      {p.label.split(".")[0]}.
                    </div>

                    {/* 이미지 — 세로로 길게 (전신 보이도록) */}
                    <div style={{
                      height: 260,
                      borderRadius: 8,
                      overflow: "hidden",
                      background: "#000",
                      marginBottom: 6,
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
