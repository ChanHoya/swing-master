"use client";

import Link from "next/link";

export default function HomePage() {
  return (
    <div className="animate-fadein">
      {/* Topbar */}
      <div className="topbar">
        <div className="crumb">
          <span className="now">대시보드</span>
        </div>
        <div className="topbar-actions">
          <Link href="/upload" className="btn primary">
            + 새 분석
          </Link>
        </div>
      </div>

      {/* Hero Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Big CTA Card */}
        <div
          className="card"
          style={{
            minHeight: 180,
            background:
              "linear-gradient(135deg, rgba(212,255,58,0.08) 0%, rgba(212,255,58,0.02) 100%)",
            border: "1px solid rgba(212,255,58,0.2)",
          }}
        >
          <div className="session-meta">PRIMARY ACTION</div>
          <div className="h1" style={{ fontSize: 32, lineHeight: 1.1 }}>
            새 스윙<br />
            <span className="em">분석하기</span>
          </div>
          <div className="flex gap-2 mt-3">
            <Link href="/upload" className="btn primary">
              📤 영상 업로드
            </Link>
            <Link href="/guide" className="btn">
              🏌️ 촬영 가이드
            </Link>
          </div>
          <p className="mono mt-2" style={{ fontSize: 10, color: "var(--text-3)" }}>
            · 분석 ~30초 · 클럽/각도 자동 인식
          </p>
        </div>

        {/* Quick Stats */}
        <div className="flex-col gap-3" style={{ display: "flex" }}>
          <div className="card flex items-center gap-3">
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                border: "2px solid var(--accent)",
                display: "grid",
                placeItems: "center",
                background: "var(--accent-dim)",
              }}
            >
              <span className="serif" style={{ fontSize: 18, color: "var(--accent)" }}>
                78
              </span>
            </div>
            <div style={{ flex: 1 }}>
              <div className="text-muted text-xs">평균 점수</div>
              <div className="flex items-center gap-2">
                <span style={{ fontSize: 17, fontWeight: 700 }}>B등급</span>
                <span className="chip ok" style={{ fontSize: 9, padding: "2px 6px" }}>
                  ↑ +5
                </span>
              </div>
            </div>
          </div>

          <div className="card flex items-center gap-3">
            <span style={{ fontSize: 24 }}>🔥</span>
            <div style={{ flex: 1 }}>
              <div className="text-muted text-xs">연속 연습</div>
              <div style={{ fontSize: 17, fontWeight: 700 }}>7일째</div>
            </div>
          </div>

          <div className="card flex items-center gap-3">
            <span style={{ fontSize: 24 }}>⛳</span>
            <div style={{ flex: 1 }}>
              <div className="text-muted text-xs">다음 라운드</div>
              <div style={{ fontSize: 15, fontWeight: 700 }}>4월 21일 · 안양CC</div>
            </div>
          </div>
        </div>
      </div>

      <div className="divider" />

      {/* Checkup Widgets */}
      <div className="session-meta" style={{ marginBottom: 12 }}>체크업 위젯</div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        {[
          { k: "템포", v: "B", pct: 70 },
          { k: "힙회전", v: "C", pct: 55 },
          { k: "척추각", v: "A", pct: 85 },
          { k: "체중이동", v: "B", pct: 68 },
        ].map((item) => (
          <div key={item.k} className="card" style={{ textAlign: "center", padding: 14 }}>
            <div className="text-muted text-xs">{item.k}</div>
            <div
              className="serif"
              style={{ fontSize: 28, color: "var(--text)", marginTop: 4 }}
            >
              {item.v}
            </div>
            <div className="metric-bar" style={{ marginTop: 8 }}>
              <div
                className="metric-bar-fill"
                style={{ width: `${item.pct}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="divider" />

      {/* Recent Activity */}
      <div className="session-meta" style={{ marginBottom: 12 }}>최근 활동</div>
      <div className="flex-col gap-2" style={{ display: "flex" }}>
        {[
          { date: "오늘", title: "드라이버 스윙 분석", score: 78, tag: "템포↑", chip: "ok" },
          { date: "어제", title: "아이언 연습 세션", score: 72, tag: "힙회전↓", chip: "bad" },
          { date: "4월 15일", title: "코치 피드백 받음", score: null, tag: "읽지 않음", chip: "warn" },
        ].map((item, i) => (
          <div key={i} className="card flex items-center gap-3" style={{ padding: 14 }}>
            <div style={{ width: 60, textAlign: "right" }}>
              <span className="text-muted text-xs">{item.date}</span>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 13 }}>{item.title}</div>
              <div className="flex items-center gap-2 mt-1">
                {item.score !== null && (
                  <span className="text-xs text-2">
                    점수 <strong>{item.score}</strong>
                  </span>
                )}
                <span className={`chip ${item.chip}`} style={{ fontSize: 9, padding: "2px 6px" }}>
                  {item.tag}
                </span>
              </div>
            </div>
            <Link href="/upload" className="btn sm">
              열기 →
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
