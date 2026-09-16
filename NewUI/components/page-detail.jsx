// page-detail.jsx — Detailed diagnosis & coaching (PC/Tablet) — 3 variations

const DetailV1 = () => (
  <>
    <FrameTopbar title="상세 진단"/>
    <div className="row ac jb mb-12">
      <h3 style={{ fontSize: 22 }}>진단 리포트</h3>
      <div className="row gap-6">
        <button className="sk-btn small"><SkIcon name="share" size={12}/> 코치에게</button>
        <button className="sk-btn small">PDF</button>
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      <div className="sk-box p-12 tc">
        <div className="label-mono">종합 점수</div>
        <div className="hand" style={{ fontSize: 56, lineHeight: 1 }}>78</div>
        <div className="sk-chip yellow" style={{ fontSize: 12 }}>B등급 · 양호</div>
        <div className="tiny muted mt-8">지난 분석 대비 <span style={{ color: "var(--green)", fontWeight: 700 }}>+3</span></div>
      </div>
      <div className="sk-box p-12">
        <div className="label-mono mb-6">스윙 지표 레이더</div>
        <svg viewBox="0 0 160 140" width="100%" height="110" style={{ filter: "url(#sk-rough)" }}>
          <polygon points="80,20 130,50 120,110 40,110 30,50" fill="none" stroke="var(--pencil)" strokeWidth="0.8" strokeDasharray="2 2"/>
          <polygon points="80,40 115,60 108,95 52,95 45,60" fill="var(--highlight-soft)" stroke="var(--accent)" strokeWidth="1.6" opacity="0.85"/>
          <text x="80" y="14" textAnchor="middle" fontSize="9" fontFamily="var(--font-mono)">척추</text>
          <text x="138" y="50" fontSize="9" fontFamily="var(--font-mono)">템포</text>
          <text x="125" y="122" fontSize="9" fontFamily="var(--font-mono)">체중</text>
          <text x="10" y="122" fontSize="9" fontFamily="var(--font-mono)">회전</text>
          <text x="5" y="50" fontSize="9" fontFamily="var(--font-mono)">헤드</text>
        </svg>
      </div>
    </div>

    <div className="sk-divider"/>

    <div className="label-mono mb-8">주요 교정 포인트 · 3건</div>
    <div className="col gap-8">
      {[
        { level: "심각", color: "red", title: "템포 비율 0.8:1", desc: "백스윙↔다운스윙 리듬 불균형. 3:1 비율 목표.", drill: "메트로놈 드릴" },
        { level: "심각", color: "red", title: "힙 회전 부족", desc: "백스윙 시 힙이 45°만 돌아감. 파워 축적 부족.", drill: "의자 힙턴" },
        { level: "중간", color: "yellow", title: "체중 이동", desc: "다운스윙 시 전방 이동 지연.", drill: "발 들고 피니시" },
      ].map((it, i) => (
        <div className="sk-box p-12 row ac gap-10" key={i}>
          <div style={{ width: 6, alignSelf: "stretch", background: it.color === "red" ? "var(--accent)" : "var(--highlight)", borderRadius: 3 }}/>
          <div className="f1">
            <div className="row ac gap-6 mb-4">
              <span className={"sk-chip tiny " + it.color}>심각도 {it.level}</span>
              <span style={{ fontSize: 15, fontWeight: 700 }}>{it.title}</span>
            </div>
            <div className="tiny muted">{it.desc}</div>
          </div>
          <button className="sk-btn small highlight">{it.drill} →</button>
        </div>
      ))}
    </div>
  </>
);

const DetailV2 = () => (
  <>
    <FrameTopbar title="AI 코치 피드백"/>
    <div className="row ac gap-10 mb-12">
      <div style={{ width: 48, height: 48, borderRadius: "50%", border: "2px solid var(--ink)", background: "var(--accent-soft)", display: "grid", placeItems: "center", filter: "url(#sk-rough)" }}>
        <span className="hand" style={{ fontSize: 22 }}>AI</span>
      </div>
      <div>
        <div className="hand" style={{ fontSize: 20 }}>Coach GPT</div>
        <div className="tiny muted">분석 완료 · 방금 전</div>
      </div>
      <div className="f1"/>
      <button className="sk-btn small"><SkIcon name="mic" size={12}/> 음성 듣기</button>
    </div>

    {/* Chat-like coaching */}
    <div className="col gap-10">
      <div className="sk-box p-12 tint-blue" style={{ maxWidth: "85%" }}>
        <div className="tiny">오늘 스윙 먼저 <b>잘한 점</b>부터 볼게요 👍</div>
        <ul className="tiny" style={{ margin: "6px 0 0", paddingLeft: 16 }}>
          <li>피니시 자세가 안정적 · 밸런스 A등급</li>
          <li>그립과 스탠스가 정석</li>
        </ul>
      </div>

      <div className="sk-box p-12 tint-red" style={{ maxWidth: "85%" }}>
        <div className="tiny">가장 <b>큰 이슈</b>는 임팩트 때 헤드가 <span className="sk-marker-red">1.7cm 밀리는 현상</span>이에요.</div>
        <div className="sk-stick mt-8" style={{ height: 100, display: "grid", placeItems: "center" }}>
          <StickFigure pose="impact" size={80}/>
        </div>
        <div className="tiny mt-6">→ 척추가 축이 아니라 전체가 이동. 스웨이 드릴 필요.</div>
      </div>

      <div className="sk-box p-12" style={{ maxWidth: "85%" }}>
        <div className="tiny"><b>이번 주 연습 순서</b> 제안드려요:</div>
        <div className="col gap-6 mt-8">
          {["① 메트로놈 드릴 · 월/수/금 10분","② 의자 힙턴 드릴 · 화/목 15분","③ 발 들고 피니시 · 매일 5회"].map((s, i) => (
            <div key={i} className="row ac gap-8 tiny" style={{ padding: "4px 8px", background: "var(--paper-tint)", borderRadius: 4 }}>
              <span>{s}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="sk-box p-10 tint-yellow row ac gap-8" style={{ maxWidth: "85%" }}>
        <SkIcon name="bolt" size={16}/>
        <span className="tiny">예상 효과: 2주 후 템포 B→A, 비거리 평균 +8y</span>
      </div>
    </div>

    <div className="row gap-6 mt-12">
      <button className="sk-btn small">👍 도움됨</button>
      <button className="sk-btn small">👎 별로</button>
      <button className="sk-btn small">더 물어보기…</button>
    </div>
  </>
);

const DetailV3 = () => (
  <>
    <FrameTopbar title="지표 딥다이브"/>
    <div className="label-mono mb-8">프레임별 지표 차트</div>

    <div className="sk-box p-12 mb-12" style={{ height: 160 }}>
      <div className="row ac jb mb-6">
        <div className="hand" style={{ fontSize: 17 }}>헤드 무브먼트 (cm)</div>
        <div className="row gap-4">
          <span className="sk-chip tiny">측정치</span>
          <span className="sk-chip blue tiny">기준선</span>
        </div>
      </div>
      <svg viewBox="0 0 300 90" width="100%" height="90" style={{ filter: "url(#sk-rough)" }}>
        <path d="M0,70 L300,70" stroke="var(--pencil)" strokeWidth="0.5" strokeDasharray="2 2"/>
        <path d="M0,55 L300,55" stroke="var(--blue)" strokeWidth="1" strokeDasharray="3 2"/>
        <path d="M5,70 L40,68 L80,60 L120,52 L160,30 L200,45 L240,60 L280,68 L295,70" fill="none" stroke="var(--accent)" strokeWidth="1.8"/>
        {/* stage markers */}
        {[0.14,0.28,0.42,0.57,0.71,0.85].map((x, i) => (
          <line key={i} x1={x*300} x2={x*300} y1="5" y2="85" stroke="var(--ink)" strokeWidth="0.4" strokeDasharray="1 2"/>
        ))}
        <text x="160" y="25" fontSize="9" fontFamily="var(--font-mono)" fill="var(--accent)">peak 1.7cm ↑</text>
      </svg>
      <div className="row jb tiny muted" style={{ fontSize: 9, marginTop: 4 }}>
        {STAGES.map((s, i) => <span key={i}>{s}</span>)}
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
      {[
        { k: "척추 각도", v: "34.4°", sub: "기준 32~36°", color: "green" },
        { k: "템포 비율", v: "0.8:1", sub: "목표 3:1", color: "red" },
        { k: "헤드 이탈", v: "1.7 cm", sub: "기준 < 1.0", color: "red" },
        { k: "힙 회전", v: "45°", sub: "목표 55°", color: "yellow" },
        { k: "어깨 회전", v: "88°", sub: "기준 85~95°", color: "green" },
        { k: "체중 전환", v: "62%", sub: "목표 80%", color: "yellow" },
      ].map((m, i) => (
        <div className="sk-box p-10" key={i}>
          <div className="row ac jb">
            <div className="label-mono">{m.k}</div>
            <span className={"sk-chip tiny " + m.color} style={{ padding: "1px 6px" }}>{m.color === "green" ? "OK" : m.color === "yellow" ? "주의" : "교정"}</span>
          </div>
          <div className="hand" style={{ fontSize: 22, marginTop: 2 }}>{m.v}</div>
          <div className="tiny muted">{m.sub}</div>
        </div>
      ))}
    </div>
  </>
);

window.PageDetail = () => (
  <VariationPage
    title="상세 진단 & 코칭 피드백"
    subtitle="7단계 요약을 넘어 '왜 그런지'와 '어떻게 고칠지'를 풀어내는 핵심 화면."
    variations={[
      { title: "리포트형", desc: "체계적 리포트 포맷. 점수 + 레이더 + 교정 포인트 3건.", content: <DetailV1/> },
      { title: "AI 코치 대화", desc: "스토리텔링형. 칭찬 + 이슈 + 주간 플랜 순서로.", content: <DetailV2/> },
      { title: "지표 딥다이브", desc: "상급자/데이터 애호가용. 프레임별 수치 그래프.", content: <DetailV3/> },
    ]}
  />
);
