"use client";

import Link from "next/link";

const PHASES = [
  {
    num: 1, key: "address", name: "어드레스", en: "Address",
    color: "var(--accent)", icon: "🏌️",
    desc: "공을 치기 위한 준비자세. 스윙동작을 하기 위해 정지상태의 기본자세로 절대 클럽이 움직이는대로 시선이 따라가지 않도록 하며 공을 양 발 사이에 놓고 섭니다.",
    tips: ["발 너비는 어깨 너비", "무게 중심은 발 중앙", "그립은 가볍게, 팔은 자연스럽게", "시선은 공에 고정"],
    checkpoint: "정지 상태에서 안정적인 셋업",
  },
  {
    num: 2, key: "takeaway", name: "테이크백", en: "Takeaway",
    color: "var(--purple)", icon: "↪️",
    desc: "골프채가 정지상태인 어드레스 상태에서 허리까지 뒤로 백스윙을 하는 과정. 클럽페이스는 정면을 향하게 합니다.",
    tips: ["클럽헤드가 낮게 유지", "손목 꺾지 않고 어깨·팔 하나로", "클럽페이스 정면 유지", "체중 오른발로 이동 시작"],
    checkpoint: "손이 허리 높이에 위치",
  },
  {
    num: 3, key: "top", name: "탑", en: "Top",
    color: "var(--danger)", icon: "⬆️",
    desc: "골프헤드가 백스윙으로 머리부근까지 가장 위에 올려져 있는 상태. 클럽페이스는 정면인 상태이며 지면과 평행선을 유지하고 왼쪽 손목은 펴지고 오른쪽 손목은 꺾여있는 상태.",
    tips: ["클럽 샤프트 지면 평행", "왼팔을 가능한 곧게 유지", "체중 약 80%가 오른발에", "머리는 고정"],
    checkpoint: "클럽헤드 최고점 도달",
  },
  {
    num: 4, key: "downswing", name: "다운스윙", en: "Downswing",
    color: "var(--warn)", icon: "⬇️",
    desc: "어깨를 힘껏 내려 공을 타격하기 직전까지의 구간. 탑에서 공을 맞을때까지의 구간이며 체중이동과 스윙을 조절하며 힘과 스피드를 조절해야 합니다.",
    tips: ["하체가 먼저 리드", "클럽이 인사이드에서 내려오도록", "손목의 힘을 최대한 유지 (지연 해제)", "체중을 왼발로 이동"],
    checkpoint: "최대 파워 축적 구간",
  },
  {
    num: 5, key: "impact", name: "임팩트", en: "Impact",
    color: "var(--danger)", icon: "💥",
    desc: "공을 타격하는 순간. 클럽페이스가 목표선과 직각이 되게 하고 손목힘을 최대한 빼주며 다리의 균형을 오른쪽에서 왼쪽으로 가게 하여 줍니다.",
    tips: ["클럽페이스 목표 방향과 직각", "왼팔 펴고 손목 해제", "체중 완전히 왼발로", "머리 고정 유지"],
    checkpoint: "볼 타격 순간 — 스윙 핵심",
  },
  {
    num: 6, key: "followthrough", name: "팔로우스루", en: "Follow-through",
    color: "var(--ok)", icon: "🌀",
    desc: "임팩트가 끝났다고 동작이 끝난 것이 아니고 골프 클럽이 몸의 뒷쪽으로 원심력에 의해 움직이는 구간. 공의 방향과 거리가 결정됩니다.",
    tips: ["왼쪽 손목을 반드시 펴주기", "양팔 힘으로 회전", "오른손이 왼손 위로", "클럽이 왼 어깨 방향으로"],
    checkpoint: "임팩트 후 원심력으로 회전",
  },
  {
    num: 7, key: "finish", name: "피니시", en: "Finish",
    color: "var(--blue)", icon: "🏁",
    desc: "골프 스윙을 마치는 자세로 몸의 균형감각을 유지하고 눈은 전방을 바라보며 자세를 유지시켜줍니다.",
    tips: ["몸이 목표 방향으로 완전히 회전", "체중 99% 왼발에", "클럽이 등 뒤로 넘어감", "균형 유지하며 볼 날아가는 방향 주시"],
    checkpoint: "완전한 회전 완료 + 균형 유지",
  },
];

const svgColors = ["#d4ff3a","#b985ff","#ff5a47","#ffb84d","#ff5a47","#4dd68a","#5aa9ff"];

function SwingStripIllustration() {
  const labels = ["어드레스","테이크백","탑","다운스윙","임팩트","팔로우스루","피니시"];
  const poses = [
    { cx:50, handX:0,  handY:58, clubAngle:180,  clubLen:38, bodyTilt:5,  leftLeg:-8, rightLeg:8  },
    { cx:50, handX:12, handY:52, clubAngle:110,  clubLen:38, bodyTilt:3,  leftLeg:-8, rightLeg:8  },
    { cx:50, handX:10, handY:30, clubAngle:50,   clubLen:38, bodyTilt:0,  leftLeg:-8, rightLeg:8  },
    { cx:50, handX:8,  handY:45, clubAngle:95,   clubLen:38, bodyTilt:5,  leftLeg:-10, rightLeg:6 },
    { cx:50, handX:-5, handY:58, clubAngle:185,  clubLen:38, bodyTilt:5,  leftLeg:-10, rightLeg:8 },
    { cx:50, handX:-12,handY:45, clubAngle:-60,  clubLen:38, bodyTilt:-5, leftLeg:-8, rightLeg:10 },
    { cx:50, handX:-15,handY:32, clubAngle:-25,  clubLen:38, bodyTilt:-15,leftLeg:-6, rightLeg:12 },
  ];

  return (
    <div className="flex items-end justify-center gap-2 w-full" style={{ padding: "20px 16px", background: "linear-gradient(to bottom, var(--bg-3), var(--bg))" }}>
      {poses.map((pose, i) => {
        const rad  = (pose.clubAngle * Math.PI) / 180;
        const tilt = (pose.bodyTilt  * Math.PI) / 180;
        const hx = pose.cx + pose.handX;
        const hy = pose.handY;
        const cx2 = hx + pose.clubLen * Math.sin(rad);
        const cy2 = hy - pose.clubLen * Math.cos(rad);
        const hipX = pose.cx + 6*Math.sin(tilt);
        const c = svgColors[i];
        return (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <svg viewBox="0 0 100 130" style={{ width: "100%", maxWidth: 90 }}>
              <line x1={hx} y1={hy} x2={cx2} y2={cy2} stroke={c} strokeWidth="2.5" strokeLinecap="round" />
              <circle cx={pose.cx} cy={20} r={7} fill="none" stroke={c} strokeWidth="2" />
              <line x1={pose.cx} y1={27} x2={pose.cx} y2={33} stroke={c} strokeWidth="1.5" />
              <line x1={pose.cx} y1={33} x2={hipX} y2={62} stroke={c} strokeWidth="3" strokeLinecap="round" />
              <line x1={pose.cx-10} y1={35} x2={pose.cx+10} y2={35} stroke={c} strokeWidth="1.5" opacity="0.7" />
              <line x1={pose.cx} y1={38} x2={hx} y2={hy} stroke={c} strokeWidth="2" strokeLinecap="round" />
              <line x1={hipX-8} y1={62} x2={hipX+8} y2={62} stroke={c} strokeWidth="1.5" opacity="0.7" />
              <line x1={hipX} y1={62} x2={pose.cx + pose.leftLeg} y2={92} stroke={c} strokeWidth="2" strokeLinecap="round" />
              <line x1={hipX} y1={62} x2={pose.cx + pose.rightLeg} y2={92} stroke={c} strokeWidth="2" strokeLinecap="round" />
              <ellipse cx={pose.cx + pose.leftLeg}  cy={93} rx={5} ry={2} fill={c} opacity="0.5" />
              <ellipse cx={pose.cx + pose.rightLeg} cy={93} rx={5} ry={2} fill={c} opacity="0.5" />
              {(i === 0 || i === 4) && (
                <circle cx={hx + (i===0?0:-8)} cy={93} r={3} fill="white" opacity={i===4?"1":"0.5"} stroke={c} strokeWidth="0.5"/>
              )}
              <line x1={10} y1={95} x2={90} y2={95} stroke={c} strokeWidth="0.5" opacity="0.2" />
            </svg>
            <span style={{ fontSize: 9, fontWeight: 700, color: c, textAlign: "center" }}>
              {i+1}.{labels[i]}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function GuidePage() {
  return (
    <div className="animate-fadein" style={{ maxWidth: 960 }}>
      {/* Topbar */}
      <div className="topbar">
        <div className="crumb">
          <a href="/">대시보드</a>
          <span className="sep">/</span>
          <span className="now">7단계 가이드</span>
        </div>
      </div>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div className="chip accent mono mb-2">🏌️ GOLF SWING GUIDE</div>
        <div className="h1 mb-2">
          골프 스윙 <span className="em">7단계</span>
        </div>
        <p className="text-muted" style={{ maxWidth: 480, margin: "0 auto" }}>
          완벽한 골프 스윙을 위한 7가지 핵심 단계를 이해하고,
          AI 분석으로 자신의 스윙을 개선해 보세요.
        </p>
      </div>

      {/* Strip Illustration */}
      <div className="card overflow-hidden mb-4" style={{ padding: 0 }}>
        <SwingStripIllustration />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", textAlign: "center", padding: "8px 0", background: "var(--bg-2)", borderTop: "1px solid var(--line)" }}>
          {PHASES.map(p => (
            <a key={p.key} href={`#phase-${p.num}`}
              style={{ fontSize: 10, fontWeight: 700, color: svgColors[p.num - 1], cursor: "pointer", opacity: 0.8, transition: "opacity 0.15s" }}
              onMouseEnter={e => (e.currentTarget.style.opacity = "1")}
              onMouseLeave={e => (e.currentTarget.style.opacity = "0.8")}
            >
              {p.num}. {p.name}
            </a>
          ))}
        </div>
      </div>

      {/* Quick Nav */}
      <div className="flex items-center justify-center gap-2 mb-6">
        {PHASES.map((p, i) => (
          <div key={p.key} className="flex items-center gap-2">
            <a href={`#phase-${p.num}`}
              style={{
                width: 32, height: 32,
                borderRadius: "50%",
                display: "grid", placeItems: "center",
                fontSize: 12, fontWeight: 700,
                background: `color-mix(in srgb, ${svgColors[i]} 20%, transparent)`,
                color: svgColors[i],
                border: `1px solid ${svgColors[i]}`,
                opacity: 0.7,
                transition: "all 0.15s",
                textDecoration: "none",
              }}
              onMouseEnter={e => (e.currentTarget.style.opacity = "1")}
              onMouseLeave={e => (e.currentTarget.style.opacity = "0.7")}
            >
              {p.num}
            </a>
            {i < PHASES.length - 1 && (
              <div style={{ width: 16, height: 2, background: "var(--line-2)", borderRadius: 1 }} />
            )}
          </div>
        ))}
      </div>

      {/* Phase Cards */}
      <div className="flex-col gap-4" style={{ display: "flex" }}>
        {PHASES.map((p, idx) => (
          <div key={p.key} id={`phase-${p.num}`}
            className="card overflow-hidden"
            style={{ padding: 0, scrollMarginTop: 20, border: `1px solid color-mix(in srgb, ${svgColors[idx]} 30%, transparent)` }}
          >
            {/* Header bar */}
            <div className="flex items-center gap-3 px-4 py-3"
              style={{ background: `linear-gradient(135deg, color-mix(in srgb, ${svgColors[idx]} 10%, transparent), transparent)` }}>
              <div style={{
                width: 40, height: 40,
                borderRadius: 12,
                display: "grid", placeItems: "center",
                fontSize: 20,
                background: `color-mix(in srgb, ${svgColors[idx]} 15%, transparent)`,
                border: `1px solid ${svgColors[idx]}`,
                flexShrink: 0,
              }}>
                {p.icon}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="chip mono" style={{ fontSize: 9, padding: "2px 8px", background: `color-mix(in srgb, ${svgColors[idx]} 15%, transparent)`, color: svgColors[idx], borderColor: svgColors[idx] }}>
                    STEP {p.num}
                  </span>
                  <span className="text-muted text-xs">{p.en}</span>
                </div>
                <div className="h3 mt-1">{p.name}</div>
              </div>
              <div style={{ marginLeft: "auto", textAlign: "right" }}>
                <div className="text-muted text-xs">체크포인트</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: svgColors[idx] }}>{p.checkpoint}</div>
              </div>
            </div>

            {/* Body */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, padding: "16px 20px 20px" }}>
              <div>
                <p style={{ fontSize: 13, lineHeight: 1.7, color: "var(--text-2)" }}>{p.desc}</p>
              </div>
              <div>
                <div className="card-sub mb-2">핵심 포인트</div>
                <div className="flex-col gap-2" style={{ display: "flex" }}>
                  {p.tips.map((tip, i) => (
                    <div key={i} className="flex items-start gap-2" style={{ fontSize: 12, color: "var(--text-2)" }}>
                      <span style={{
                        width: 18, height: 18,
                        borderRadius: "50%",
                        display: "grid", placeItems: "center",
                        fontSize: 10, fontWeight: 700,
                        background: `color-mix(in srgb, ${svgColors[idx]} 15%, transparent)`,
                        color: svgColors[idx],
                        flexShrink: 0,
                        marginTop: 1,
                      }}>
                        {i + 1}
                      </span>
                      {tip}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* CTA */}
      <div className="card text-center mt-6 mb-4" style={{ padding: 32, background: "linear-gradient(135deg, rgba(212,255,58,0.06), rgba(90,169,255,0.04))", border: "1px solid rgba(212,255,58,0.2)" }}>
        <div className="h2 mb-2">
          내 스윙을 <span className="em">AI로 분석</span>해 보세요
        </div>
        <p className="text-muted mb-4">7단계 동작을 AI가 자동으로 인식하고 교정 피드백을 제공합니다.</p>
        <Link href="/upload" className="btn primary lg">
          스윙 영상 업로드 →
        </Link>
      </div>
    </div>
  );
}
