"use client";

import { useState } from "react";

const DEMO_MESSAGES = [
  {
    type: "ok" as const,
    tag: "✅ 잘한 점",
    text: "피니시 자세가 매우 안정적입니다. 밸런스 A등급!",
    items: ["그립과 스탠스가 정석에 가깝습니다", "어드레스에서의 정렬이 일관적입니다"],
  },
  {
    type: "bad" as const,
    tag: "⚠️ 주요 이슈",
    text: "임팩트 시 헤드가 1.7cm 밀리는 현상이 있어요. 척추를 축으로 회전해야 합니다.",
    items: ["헤드 스웨이 드릴 필요", "척추 고정 연습 추천"],
  },
  {
    type: "plan" as const,
    tag: "📋 주간 플랜",
    text: "이번 주 연습 순서를 제안합니다:",
    items: ["① 메트로놈 드릴 · 월/수/금 10분", "② 의자 힙턴 · 화/목 15분", "③ 발 들고 피니시 · 매일 5회"],
  },
];

export default function CoachPage() {
  const [input, setInput] = useState("");

  return (
    <div className="animate-fadein" style={{ maxWidth: 720 }}>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumb">
          <a href="/">대시보드</a>
          <span className="sep">/</span>
          <span className="now">AI 코치</span>
        </div>
      </div>

      {/* Coach Header */}
      <div className="card mb-4" style={{ padding: 16 }}>
        <div className="flex items-center gap-3">
          <div style={{
            width: 44, height: 44, borderRadius: "50%",
            background: "linear-gradient(135deg, var(--accent), #8fc01e)",
            display: "grid", placeItems: "center",
            color: "#0a0c10", fontWeight: 800,
            fontFamily: "'Playfair Display', serif",
            fontStyle: "italic", fontSize: 18,
            position: "relative",
          }}>
            AI
            <div style={{
              position: "absolute", bottom: -1, right: -1,
              width: 10, height: 10, borderRadius: "50%",
              background: "var(--ok)", border: "2px solid var(--bg-2)",
            }} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 14 }}>
              Coach <span className="em">GPT</span>
            </div>
            <span className="mono text-xs text-muted">AI 코칭 · 실시간 분석 기반</span>
          </div>
          <button className="btn sm">🔊 음성 듣기</button>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-col gap-3" style={{ display: "flex", marginBottom: 24 }}>
        {DEMO_MESSAGES.map((msg, i) => (
          <div key={i} className={`msg ${msg.type}`} style={{ maxWidth: "85%" }}>
            <div className="msg-tag" style={{ color: msg.type === "ok" ? "var(--ok)" : msg.type === "bad" ? "var(--danger)" : "var(--text-3)" }}>
              {msg.tag}
            </div>
            <p style={{ marginBottom: 8 }}>{msg.text}</p>
            {msg.items.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12, color: "var(--text-2)", lineHeight: 1.8 }}>
                {msg.items.map((item, j) => (
                  <li key={j}>{item}</li>
                ))}
              </ul>
            )}
          </div>
        ))}

        {/* Effect prediction */}
        <div className="card flex items-center gap-2" style={{ maxWidth: "85%", padding: 12, background: "var(--accent-dim)", border: "1px solid rgba(212,255,58,0.2)" }}>
          <span>⚡</span>
          <span className="text-xs" style={{ color: "var(--accent)" }}>예상 효과: 2주 후 템포 B→A, 비거리 평균 +8y</span>
        </div>
      </div>

      {/* Feedback row */}
      <div className="flex gap-2 mb-4">
        <button className="btn sm" style={{ flex: 1 }}>👍 도움됨</button>
        <button className="btn sm" style={{ flex: 1 }}>👎 별로</button>
      </div>

      <div className="divider" />

      {/* Input */}
      <div className="card flex items-center gap-3" style={{ padding: 12 }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="코치에게 질문하세요..."
          style={{
            flex: 1, padding: "10px 14px",
            borderRadius: 10, fontSize: 13,
            color: "var(--text)", outline: "none",
            background: "var(--bg-3)", border: "1px solid var(--line)",
          }}
          onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
          onBlur={(e) => (e.target.style.borderColor = "var(--line)")}
        />
        <button className="btn primary" disabled={!input.trim()}>
          전송
        </button>
      </div>

      <p className="text-muted text-xs text-center mt-2">
        AI 코치는 분석 결과를 기반으로 답변합니다 · 기능 준비 중
      </p>
    </div>
  );
}
