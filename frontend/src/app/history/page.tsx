"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/lib/api";

interface HistoryItem {
  analysis_id: string;
  upload_id: string;
  status: string;
  overall_score: number | null;
  grade: string | null;
  thumbnail: string | null;
  completed_at: string | null;
}

interface HistoryData {
  total: number;
  average_score: number | null;
  analyses: HistoryItem[];
}

function ScoreBadge({ score, grade }: { score: number | null; grade: string | null }) {
  const colors: Record<string, string> = {
    A: "var(--ok)", B: "var(--accent)", C: "var(--warn)", D: "var(--danger)",
  };
  const color = grade ? (colors[grade] ?? "var(--accent)") : "var(--text-4)";
  return (
    <div className="flex items-center gap-2">
      <div
        style={{
          width: 44, height: 44,
          borderRadius: "50%",
          display: "grid", placeItems: "center",
          background: `color-mix(in srgb, ${color} 15%, transparent)`,
          border: `2px solid ${color}`,
          fontSize: 14, fontWeight: 800, color,
          fontFamily: "'Playfair Display', serif",
          fontStyle: "italic",
        }}
      >
        {score ?? "—"}
      </div>
      {grade && (
        <span className="chip mono" style={{ background: `color-mix(in srgb, ${color} 12%, transparent)`, color, borderColor: color }}>
          {grade}등급
        </span>
      )}
    </div>
  );
}

export default function HistoryPage() {
  const { user } = useAuth();
  const router = useRouter();

  const { data, isLoading, isError } = useQuery<HistoryData>({
    queryKey: ["history", user?.user_id],
    queryFn: async () => {
      const res = await apiClient.get("/history");
      return res.data;
    },
    enabled: !!user,
  });

  if (!user) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: 16, textAlign: "center" }}>
        <div style={{ fontSize: 48 }}>🔒</div>
        <div className="h2">로그인이 필요합니다</div>
        <p className="text-muted">분석 기록을 보려면 로그인해주세요.</p>
        <button onClick={() => router.push("/")} className="btn primary lg mt-2">
          홈으로 이동
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: 16 }}>
        <div style={{ width: 48, height: 48, borderRadius: "50%", border: "3px solid var(--bg-4)", borderTopColor: "var(--accent)" }} className="animate-spin" />
        <p className="text-muted">이력을 불러오는 중...</p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", gap: 16, textAlign: "center" }}>
        <div style={{ fontSize: 48 }}>😔</div>
        <div className="h2">이력을 불러오지 못했습니다</div>
      </div>
    );
  }

  return (
    <div className="animate-fadein" style={{ maxWidth: 800 }}>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumb">
          <a href="/">대시보드</a>
          <span className="sep">/</span>
          <span className="now">분석 기록</span>
        </div>
      </div>

      {/* Header */}
      <div className="header-block">
        <div>
          <div className="session-meta">ANALYSIS HISTORY</div>
          <div className="h1">내 분석 <span className="em">기록</span></div>
          <p className="text-muted text-small mt-1">{user.email}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-3 gap-3 mb-4">
        {[
          { label: "총 분석 수", value: `${data.total}건` },
          { label: "평균 점수", value: data.average_score != null ? `${data.average_score}점` : "—" },
          { label: "최근 활동", value: data.analyses[0]?.completed_at
            ? new Date(data.analyses[0].completed_at).toLocaleDateString("ko-KR") : "—" },
        ].map((s) => (
          <div key={s.label} className="card text-center" style={{ padding: 16 }}>
            <div className="text-muted text-xs mb-1">{s.label}</div>
            <div className="serif" style={{ fontSize: 28, color: "var(--text)" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* List */}
      {data.analyses.length === 0 ? (
        <div className="card text-center" style={{ padding: 48 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🏌️</div>
          <p className="text-muted">아직 분석 기록이 없습니다.</p>
          <button onClick={() => router.push("/upload")} className="btn primary mt-3">
            첫 스윙 분석하기
          </button>
        </div>
      ) : (
        <div className="flex-col gap-2" style={{ display: "flex" }}>
          {data.analyses.map((item) => (
            <div
              key={item.analysis_id}
              className="card flex items-center gap-3"
              style={{ padding: 14, cursor: "pointer", transition: "border-color 0.15s" }}
              onClick={() => router.push(`/analysis/${item.upload_id}`)}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--line)")}
            >
              {/* Thumbnail */}
              <div
                style={{
                  width: 72, height: 50,
                  borderRadius: 10,
                  overflow: "hidden",
                  background: "var(--bg-3)",
                  flexShrink: 0,
                }}
              >
                {item.thumbnail ? (
                  <img src={item.thumbnail} alt="썸네일" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                ) : (
                  <div style={{ width: "100%", height: "100%", display: "grid", placeItems: "center", color: "var(--text-4)", fontSize: 24 }}>⛳</div>
                )}
              </div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 13 }}>스윙 분석</div>
                <div className="text-muted text-xs mt-1">
                  {item.completed_at
                    ? new Date(item.completed_at).toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                    : "분석 중..."}
                </div>
              </div>

              {/* Score */}
              <ScoreBadge score={item.overall_score} grade={item.grade} />

              {/* Arrow */}
              <span style={{ color: "var(--text-4)", fontSize: 18 }}>›</span>
            </div>
          ))}
        </div>
      )}

      {/* CTA */}
      <div className="text-center mt-6">
        <button onClick={() => router.push("/upload")} className="btn primary lg">
          새 영상 분석하기 →
        </button>
      </div>
    </div>
  );
}
