"use client";

export default function ProgressPage() {
  return (
    <div className="animate-fadein" style={{ maxWidth: 960 }}>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumb">
          <a href="/">대시보드</a>
          <span className="sep">/</span>
          <span className="now">진행률</span>
        </div>
      </div>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div className="session-meta">PROGRESS DASHBOARD</div>
        <div className="h1">
          성장 <span className="em">대시보드</span>
        </div>
        <p className="text-muted mt-1">스윙 점수 추이와 연습 기록을 한눈에 확인합니다.</p>
      </div>

      {/* Stats Row */}
      <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
        {[
          { label: "총 분석", value: "24", unit: "회" },
          { label: "평균 점수", value: "76", unit: "점" },
          { label: "최고 점수", value: "85", unit: "점" },
          { label: "연속 연습", value: "7", unit: "일" },
        ].map((s) => (
          <div key={s.label} className="card text-center" style={{ padding: 16 }}>
            <div className="text-muted text-xs mb-1">{s.label}</div>
            <div className="flex items-center justify-center gap-1">
              <span className="serif" style={{ fontSize: 32, color: "var(--text)" }}>{s.value}</span>
              <span className="text-muted text-xs">{s.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Score Trend Chart */}
      <div className="card mb-4">
        <div className="card-head">
          <div className="card-title">📈 점수 추이 · 30일</div>
          <div className="card-sub">TREND</div>
        </div>
        <div style={{ height: 160, display: "flex", alignItems: "flex-end", gap: 4, padding: "0 8px" }}>
          {[62, 68, 65, 72, 70, 74, 71, 75, 73, 78, 76, 80, 78, 82, 79, 76, 80, 82, 84, 81, 78, 82, 85, 83, 80, 78, 82, 84, 81, 78].map((val, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                height: `${((val - 55) / 35) * 100}%`,
                background: i === 22
                  ? "var(--accent)"
                  : `var(--bg-${val > 78 ? "5" : "4"})`,
                borderRadius: "3px 3px 0 0",
                transition: "height 0.3s ease",
                minWidth: 2,
              }}
              title={`Day ${i + 1}: ${val}점`}
            />
          ))}
        </div>
        <div className="flex justify-between mt-2">
          <span className="mono text-xs text-muted">3월 20일</span>
          <span className="mono text-xs text-muted">4월 18일</span>
        </div>
      </div>

      {/* Category Progress */}
      <div className="card mb-4">
        <div className="card-head">
          <div className="card-title">🎯 카테고리별 진행</div>
        </div>
        <div className="flex-col gap-3" style={{ display: "flex" }}>
          {[
            { name: "척추 각도", pct: 85, status: "ok", val: "34.4°", target: "32~36°" },
            { name: "템포 비율", pct: 35, status: "bad", val: "0.8:1", target: "3:1" },
            { name: "헤드 안정", pct: 55, status: "warn", val: "1.7cm", target: "< 1.0cm" },
            { name: "힙 회전", pct: 65, status: "warn", val: "45°", target: "55°" },
            { name: "어깨 회전", pct: 90, status: "ok", val: "88°", target: "85~95°" },
            { name: "체중 전환", pct: 50, status: "warn", val: "62%", target: "80%" },
          ].map((item) => (
            <div key={item.name} className="flex items-center gap-3">
              <span style={{ width: 80, fontSize: 12, color: "var(--text-2)" }}>{item.name}</span>
              <div style={{ flex: 1 }}>
                <div className="metric-bar" style={{ height: 6 }}>
                  <div
                    className={`metric-bar-fill ${item.status}`}
                    style={{ width: `${item.pct}%` }}
                  />
                </div>
              </div>
              <span className="mono text-xs" style={{ width: 40, textAlign: "right", color: "var(--text-2)" }}>
                {item.val}
              </span>
              <span className={`metric-tag ${item.status}`}>
                {item.status === "ok" ? "OK" : item.status === "warn" ? "주의" : "교정"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Achievement Badges */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">🏆 달성 배지</div>
          <div className="card-sub">3 / 8 획득</div>
        </div>
        <div className="flex gap-3" style={{ flexWrap: "wrap" }}>
          {[
            { icon: "🔥", name: "7일 연속", done: true },
            { icon: "🎯", name: "80점 달성", done: true },
            { icon: "📊", name: "10회 분석", done: true },
            { icon: "⭐", name: "A등급", done: false },
            { icon: "🏌️", name: "풀스윙 마스터", done: false },
            { icon: "📈", name: "30일 꾸준히", done: false },
          ].map((badge) => (
            <div
              key={badge.name}
              className="card"
              style={{
                padding: 12,
                textAlign: "center",
                width: 90,
                opacity: badge.done ? 1 : 0.35,
                background: badge.done ? "var(--accent-dim)" : "var(--bg-3)",
                border: badge.done ? "1px solid rgba(212,255,58,0.3)" : "1px solid var(--line)",
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 4 }}>{badge.icon}</div>
              <div style={{ fontSize: 10, fontWeight: 600 }}>{badge.name}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
