"use client";

export default function ComparePage() {
  return (
    <div className="animate-fadein" style={{ maxWidth: 960 }}>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumb">
          <a href="/">대시보드</a>
          <span className="sep">/</span>
          <span className="now">비교 모드</span>
        </div>
      </div>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div className="session-meta">COMING SOON</div>
        <div className="h1">
          스윙 <span className="em">비교</span> 모드
        </div>
        <p className="text-muted mt-1">나의 전/후 스윙 또는 프로 골퍼와 비교 분석합니다.</p>
      </div>

      {/* Comparison Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Before */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)" }}>
            <div className="flex items-center justify-between">
              <div className="card-title">
                <span className="chip warn" style={{ fontSize: 9, padding: "2px 8px" }}>BEFORE</span>
                4월 10일 스윙
              </div>
              <span className="serif" style={{ fontSize: 24, color: "var(--warn)" }}>72</span>
            </div>
          </div>
          <div style={{ height: 240, background: "var(--bg-3)", display: "grid", placeItems: "center" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 8, opacity: 0.3 }}>🏌️</div>
              <p className="text-muted text-xs">이전 스윙 영상</p>
            </div>
          </div>
        </div>

        {/* After */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)" }}>
            <div className="flex items-center justify-between">
              <div className="card-title">
                <span className="chip ok" style={{ fontSize: 9, padding: "2px 8px" }}>AFTER</span>
                4월 18일 스윙
              </div>
              <span className="serif" style={{ fontSize: 24, color: "var(--ok)" }}>78</span>
            </div>
          </div>
          <div style={{ height: 240, background: "var(--bg-3)", display: "grid", placeItems: "center" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 8, opacity: 0.3 }}>🏌️</div>
              <p className="text-muted text-xs">최신 스윙 영상</p>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Comparison */}
      <div className="card mt-4">
        <div className="card-head">
          <div className="card-title">📊 지표 변화</div>
          <div className="card-sub">BEFORE → AFTER</div>
        </div>
        <div className="metrics-grid">
          {[
            { name: "척추 각도", before: "32.1°", after: "34.4°", delta: "+2.3°", status: "ok" },
            { name: "템포 비율", before: "0.6:1", after: "0.8:1", delta: "+0.2", status: "warn" },
            { name: "헤드 이탈", before: "2.3cm", after: "1.7cm", delta: "-0.6cm", status: "ok" },
            { name: "힙 회전", before: "40°", after: "45°", delta: "+5°", status: "warn" },
          ].map((m) => (
            <div key={m.name} className="metric">
              <div className="metric-head">
                <span className="metric-name">{m.name}</span>
                <span className={`metric-tag ${m.status}`}>
                  {m.status === "ok" ? "개선" : "진행중"}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-muted text-xs">{m.before}</span>
                <span style={{ color: "var(--text-4)" }}>→</span>
                <span className="metric-val" style={{ fontSize: 18 }}>{m.after}</span>
              </div>
              <div className="metric-sub" style={{ color: m.status === "ok" ? "var(--ok)" : "var(--warn)" }}>
                {m.delta}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pro Overlay Section */}
      <div className="card mt-4" style={{ background: "linear-gradient(135deg, rgba(90,169,255,0.06), rgba(212,255,58,0.03))", border: "1px solid rgba(90,169,255,0.2)" }}>
        <div className="flex items-center gap-3">
          <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--blue-dim)", border: "1px solid rgba(90,169,255,0.3)", display: "grid", placeItems: "center", color: "var(--blue)", flexShrink: 0 }}>
            ⛳
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>프로 골퍼와 비교</div>
            <p className="text-muted text-xs">Rory McIlroy, Tiger Woods 등 프로의 스윙 위에 내 포즈를 오버레이합니다.</p>
          </div>
          <button className="btn" disabled style={{ opacity: 0.5 }}>
            준비 중
          </button>
        </div>
      </div>
    </div>
  );
}
