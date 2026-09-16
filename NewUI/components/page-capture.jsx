// page-capture.jsx — Mobile real-time capture — 3 variations (NEW flagship)

const CaptureV1 = () => (
  <>
    <PhoneStatus/>
    {/* Camera viewport */}
    <div className="sk-stick" style={{ height: 420, position: "relative", borderRadius: 12 }}>
      {/* ghost body silhouette guide */}
      <svg viewBox="0 0 100 140" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" style={{ filter: "url(#sk-rough)", opacity: 0.5 }}>
        <path d="M50,15 a7,7 0 1,0 0,14 a7,7 0 1,0 0,-14 M50,29 L50,70 M50,40 L30,55 M50,40 L70,55 M50,70 L42,110 M50,70 L58,110" fill="none" stroke="var(--pencil)" strokeWidth="0.8" strokeDasharray="2 2"/>
      </svg>
      {/* corner guides */}
      {[[0,0],[1,0],[0,1],[1,1]].map(([x,y], i) => (
        <div key={i} style={{
          position: "absolute",
          [x?"right":"left"]: 8, [y?"bottom":"top"]: 8,
          width: 22, height: 22,
          borderTop: y ? "none" : "2px solid var(--accent)",
          borderBottom: y ? "2px solid var(--accent)" : "none",
          borderLeft: x ? "none" : "2px solid var(--accent)",
          borderRight: x ? "2px solid var(--accent)" : "none",
          filter: "url(#sk-rough)",
        }}/>
      ))}
      {/* top status */}
      <div style={{ position: "absolute", top: 10, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <span className="sk-chip green tiny" style={{ background: "var(--paper)" }}>● 자세 OK · 거리 적정</span>
      </div>
      {/* tripod hint */}
      <div style={{ position: "absolute", bottom: 60, left: "50%", transform: "translateX(-50%)", textAlign: "center" }}>
        <div className="hand" style={{ fontSize: 16 }}>스윙하시면</div>
        <div className="hand" style={{ fontSize: 16, color: "var(--accent)" }}>자동 감지 📸</div>
      </div>
    </div>

    {/* bottom controls */}
    <div className="row ac jb mt-12" style={{ padding: "0 12px" }}>
      <div className="col ac">
        <div style={{ width: 36, height: 36, border: "1.8px solid var(--ink)", borderRadius: 8, display: "grid", placeItems: "center", filter: "url(#sk-rough)" }}>
          <SkIcon name="video" size={18}/>
        </div>
        <div className="tiny muted mt-4">갤러리</div>
      </div>
      {/* Auto-detect indicator (big circle) */}
      <div className="col ac">
        <div style={{ width: 66, height: 66, borderRadius: "50%", border: "3px solid var(--ink)", display: "grid", placeItems: "center", background: "var(--paper)", position: "relative", filter: "url(#sk-rough)" }}>
          <div style={{ width: 46, height: 46, borderRadius: "50%", background: "var(--accent)", border: "2px solid var(--ink)" }}/>
          {/* pulsing ring */}
          <div style={{ position: "absolute", inset: -4, borderRadius: "50%", border: "2px dashed var(--accent)" }}/>
        </div>
        <div className="tiny hand mt-4" style={{ color: "var(--accent)" }}>AUTO</div>
      </div>
      <div className="col ac">
        <div style={{ width: 36, height: 36, border: "1.8px solid var(--ink)", borderRadius: 8, display: "grid", placeItems: "center", filter: "url(#sk-rough)" }}>
          <SkIcon name="gear" size={18}/>
        </div>
        <div className="tiny muted mt-4">설정</div>
      </div>
    </div>

    {/* club & angle */}
    <div className="row ac jc gap-4 mt-12" style={{ padding: "0 12px" }}>
      <span className="sk-chip yellow tiny">7I</span>
      <span className="sk-chip blue tiny">DTL</span>
    </div>

    {/* Annotation */}
    <div className="sk-note" style={{ top: 40, right: -10 }}>
      카메라 거치 OK<br/>→ 스윙만!
    </div>
  </>
);

const CaptureV2 = () => (
  <>
    <PhoneStatus/>
    <div className="tc mb-8">
      <div className="label-mono">READY · 3회차</div>
      <div className="hand" style={{ fontSize: 22 }}>세션 촬영 중</div>
    </div>

    <div className="sk-stick" style={{ height: 320, position: "relative", borderRadius: 10 }}>
      {/* live detection overlay */}
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
        <StickFigure pose="takeaway" size={160}/>
      </div>
      {/* capture countdown */}
      <div style={{ position: "absolute", top: 10, right: 10 }} className="sk-chip red tiny">● REC · 0:03</div>
      <div style={{ position: "absolute", bottom: 10, left: 10, right: 10 }}>
        <div className="sk-box p-8" style={{ background: "var(--paper)", opacity: 0.95 }}>
          <div className="tiny hand">스윙 감지됨 — 3, 2, 1…</div>
          <div style={{ height: 4, background: "var(--paper-tint)", borderRadius: 2, marginTop: 4 }}>
            <div style={{ width: "70%", height: "100%", background: "var(--accent)" }}/>
          </div>
        </div>
      </div>
    </div>

    {/* Session shots gallery */}
    <div className="label-mono mt-12 mb-6">이번 세션 · 2회 녹화됨</div>
    <div className="row gap-6">
      {[{ s: 74, c: "green" }, { s: 77, c: "green" }, { t: "촬영 중", c: "yellow" }, { t: "+", c: "ghost" }].map((it, i) => (
        <div key={i} className="sk-box f1" style={{ aspectRatio: "9/16", display: "grid", placeItems: "center", position: "relative", background: it.c === "green" ? "var(--paper)" : "var(--paper-tint)" }}>
          {it.s ? <><div className="hand" style={{ fontSize: 22 }}>{it.s}</div><span className="sk-chip tiny" style={{ position: "absolute", bottom: 4, fontSize: 9 }}>#{i+1}</span></> : <div className="tiny hand">{it.t}</div>}
        </div>
      ))}
    </div>

    {/* Voice command hint */}
    <div className="sk-box tint-yellow p-8 mt-12 row ac gap-8">
      <SkIcon name="mic" size={18}/>
      <div className="tiny f1">"다음", "그만" 음성 명령 가능</div>
      <div className="sk-chip tiny" style={{ fontSize: 9 }}>ON</div>
    </div>

    <button className="sk-btn primary w-full mt-12">세션 종료 · 전체 리뷰 →</button>
  </>
);

const CaptureV3 = () => (
  <>
    <PhoneStatus/>
    {/* Pre-capture setup coaching */}
    <div className="tc">
      <div className="label-mono mb-4">촬영 전 체크 · 2/3</div>
      <h3 style={{ fontSize: 18 }}>카메라를 <span className="sk-marker">허리 높이</span>에</h3>
    </div>

    <div className="sk-stick mt-12" style={{ height: 260, position: "relative", borderRadius: 10 }}>
      {/* tripod + phone illustration */}
      <div style={{ position: "absolute", left: "20%", bottom: 12, textAlign: "center" }}>
        <SkIcon name="tripod" size={90}/>
        <div className="tiny hand mt-4">📱</div>
      </div>
      {/* golfer */}
      <div style={{ position: "absolute", right: 20, bottom: 12 }}>
        <StickFigure pose="address" size={110}/>
      </div>
      {/* distance line */}
      <svg style={{ position: "absolute", inset: 0, pointerEvents: "none" }} viewBox="0 0 100 100" preserveAspectRatio="none">
        <path d="M30,72 L72,72" stroke="var(--accent)" strokeWidth="0.5" strokeDasharray="1.5 1"/>
        <text x="50" y="68" textAnchor="middle" fontSize="4" fontFamily="var(--font-mono)" fill="var(--accent)">2.5m</text>
      </svg>
    </div>

    <div className="col gap-6 mt-12">
      {[
        { ok: true, t: "거치대 설치" },
        { ok: true, t: "거리 2~3m" },
        { ok: false, t: "허리 높이 맞추기" },
      ].map((r, i) => (
        <div className="sk-box p-10 row ac gap-8" key={i}>
          <SkIcon name="check" size={16} color={r.ok ? "var(--green)" : "var(--muted)"}/>
          <span className="tiny f1" style={{ color: r.ok ? "var(--ink)" : "var(--pencil)" }}>{r.t}</span>
          {r.ok && <span className="sk-chip green tiny" style={{ fontSize: 9 }}>OK</span>}
        </div>
      ))}
    </div>

    <button className="sk-btn primary w-full mt-16">카메라 시작 →</button>
    <div className="tc tiny muted mt-8">AR 가이드로 자동 정렬 지원</div>
  </>
);

window.PageCapture = () => (
  <VariationPage
    title="실시간 촬영 (모바일 · NEW)"
    subtitle="스마트폰을 거치하고 자동으로 스윙 감지 → 캡처 → 분석. 이 앱의 핵심 신규 기능."
    variations={[
      { title: "자동 감지 뷰파인더", desc: "카메라 화면 + 자세 가이드 + 자동 녹화 모드. 핸즈프리.", content: <CaptureV1/>, frame: "phone" },
      { title: "세션 모드", desc: "연속 스윙 녹화 → 세션 끝나면 한번에 리뷰. 음성 명령 포함.", content: <CaptureV2/>, frame: "phone" },
      { title: "셋업 가이드", desc: "촬영 전 거치/거리/높이를 AR로 코칭. 입문자 친화.", content: <CaptureV3/>, frame: "phone" },
    ]}
  />
);
