// page-history.jsx — Progress / History (PC/Tablet) — 3 variations

const HistoryV1 = () => (
  <>
    <FrameTopbar title="진행 기록"/>
    <div className="row ac jb mb-12">
      <h3 style={{ fontSize: 22 }}>성장 추이</h3>
      <div className="row gap-4">
        {["7일","30일","90일","1년"].map((t, i) => (
          <span key={i} className={"sk-chip tiny " + (i === 1 ? "yellow" : "ghost")}>{t}</span>
        ))}
      </div>
    </div>

    <div className="sk-box p-12" style={{ height: 200 }}>
      <div className="label-mono mb-6">종합 점수</div>
      <svg viewBox="0 0 400 130" width="100%" height="130" style={{ filter: "url(#sk-rough)" }}>
        <line x1="0" y1="40" x2="400" y2="40" stroke="var(--pencil)" strokeWidth="0.4" strokeDasharray="2 2"/>
        <line x1="0" y1="80" x2="400" y2="80" stroke="var(--pencil)" strokeWidth="0.4" strokeDasharray="2 2"/>
        <path d="M10,95 L40,88 L70,85 L100,72 L130,78 L160,65 L190,58 L220,55 L250,48 L280,50 L310,38 L340,42 L370,30 L395,28" fill="none" stroke="var(--accent)" strokeWidth="1.8"/>
        <text x="0" y="36" fontSize="9" fontFamily="var(--font-mono)" fill="var(--pencil)">80</text>
        <text x="0" y="76" fontSize="9" fontFamily="var(--font-mono)" fill="var(--pencil)">70</text>
      </svg>
    </div>

    <div className="row gap-10 mt-12">
      {[
        { k: "분석 횟수", v: "27", sub: "30일" },
        { k: "평균 점수", v: "75.4", sub: "+4.2 ↑" },
        { k: "연속 연습", v: "7일", sub: "🔥 최장" },
        { k: "교정된 이슈", v: "3/5", sub: "템포·힙·체중" },
      ].map((s, i) => (
        <div className="sk-box p-10 f1 tc" key={i}>
          <div className="label-mono">{s.k}</div>
          <div className="hand" style={{ fontSize: 26, margin: "4px 0" }}>{s.v}</div>
          <div className="tiny muted">{s.sub}</div>
        </div>
      ))}
    </div>

    <div className="sk-divider"/>
    <div className="label-mono mb-6">클럽별 평균</div>
    <div className="col gap-4">
      {[
        { c: "드라이버", s: 73, n: 9 },
        { c: "7번 아이언", s: 78, n: 12 },
        { c: "샌드웨지", s: 72, n: 6 },
      ].map((r, i) => (
        <div className="row ac gap-10" key={i}>
          <span className="sk-chip tiny" style={{ width: 90 }}>{r.c}</span>
          <div className="f1" style={{ height: 14, background: "var(--paper-tint)", border: "1.5px solid var(--ink)", borderRadius: 2, position: "relative" }}>
            <div style={{ width: r.s + "%", height: "100%", background: "var(--highlight)" }}/>
            <span className="tiny hand" style={{ position: "absolute", right: 6, top: -2, fontSize: 13 }}>{r.s}</span>
          </div>
          <span className="tiny muted" style={{ width: 40 }}>{r.n}회</span>
        </div>
      ))}
    </div>
  </>
);

const HistoryV2 = () => (
  <>
    <FrameTopbar title="캘린더 뷰"/>
    <div className="row ac jb mb-12">
      <h3 style={{ fontSize: 22 }}>2026년 4월</h3>
      <div className="row gap-4">
        <span className="sk-chip green tiny">● 분석</span>
        <span className="sk-chip yellow tiny">● 드릴</span>
        <span className="sk-chip blue tiny">● 라운드</span>
      </div>
    </div>

    <div className="sk-box p-12">
      <div className="row jb tiny muted mb-6" style={{ fontFamily: "var(--font-mono)", fontSize: 10 }}>
        {["일","월","화","수","목","금","토"].map((d, i) => <div key={i} style={{ flex: 1, textAlign: "center" }}>{d}</div>)}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4 }}>
        {Array.from({ length: 30 }).map((_, i) => {
          const d = i + 1;
          const hasAnalysis = [3,6,8,11,13,15,17,18].includes(d);
          const hasDrill = [5,7,9,10,12,14,16].includes(d);
          const hasRound = [21].includes(d);
          const today = d === 18;
          return (
            <div key={i} className="sk-box" style={{
              aspectRatio: "1",
              padding: 4,
              background: today ? "var(--highlight-soft)" : "var(--paper)",
              borderWidth: today ? 2.5 : 1.5,
              display: "flex", flexDirection: "column",
            }}>
              <div className="tiny" style={{ fontWeight: today ? 700 : 400, fontSize: 11 }}>{d}</div>
              <div className="row gap-2 mt-4" style={{ fontSize: 8 }}>
                {hasAnalysis && <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green)" }}/>}
                {hasDrill && <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--highlight)" }}/>}
                {hasRound && <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--blue)" }}/>}
              </div>
            </div>
          );
        })}
      </div>
    </div>

    <div className="sk-divider"/>
    <div className="label-mono mb-8">이번 주 요약</div>
    <div className="row gap-10">
      <div className="sk-box tint-green p-10 f1">
        <div className="tiny muted">분석</div>
        <div className="hand" style={{ fontSize: 24 }}>4회</div>
        <div className="tiny">평균 76점</div>
      </div>
      <div className="sk-box tint-yellow p-10 f1">
        <div className="tiny muted">드릴</div>
        <div className="hand" style={{ fontSize: 24 }}>5세션</div>
        <div className="tiny">총 62분</div>
      </div>
      <div className="sk-box tint-blue p-10 f1">
        <div className="tiny muted">다음</div>
        <div className="hand" style={{ fontSize: 18 }}>4/21<br/>안양CC</div>
      </div>
    </div>
  </>
);

const HistoryV3 = () => (
  <>
    <FrameTopbar title="비교 분석"/>
    <h3 style={{ fontSize: 20, marginBottom: 4 }}>두 스윙 <span className="sk-marker">나란히</span> 비교</h3>
    <div className="tiny muted mb-12">30일 전 vs 오늘</div>

    <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 10 }}>
      <div className="sk-box p-10">
        <div className="row ac jb mb-6">
          <span className="sk-chip tiny">3월 19일</span>
          <span className="hand" style={{ fontSize: 20 }}>72</span>
        </div>
        <div className="sk-stick" style={{ height: 140, display: "grid", placeItems: "center" }}>
          <StickFigure pose="top" size={100}/>
        </div>
        <div className="col gap-4 mt-8 tiny">
          <div className="row jb"><span>템포</span><span>0.7:1</span></div>
          <div className="row jb"><span>헤드</span><span>2.3cm</span></div>
          <div className="row jb"><span>힙회전</span><span>38°</span></div>
        </div>
      </div>

      <div className="col ac jc" style={{ padding: "0 4px" }}>
        <SkIcon name="compare" size={28}/>
        <div className="hand" style={{ fontSize: 13, marginTop: 8, color: "var(--accent)" }}>+6</div>
      </div>

      <div className="sk-box p-10 tint-yellow">
        <div className="row ac jb mb-6">
          <span className="sk-chip tiny">오늘</span>
          <span className="hand" style={{ fontSize: 20 }}>78</span>
        </div>
        <div className="sk-stick" style={{ height: 140, display: "grid", placeItems: "center" }}>
          <StickFigure pose="top" size={100}/>
        </div>
        <div className="col gap-4 mt-8 tiny">
          <div className="row jb"><span>템포</span><span>0.8:1 <span style={{ color: "var(--green)" }}>↑</span></span></div>
          <div className="row jb"><span>헤드</span><span>1.7cm <span style={{ color: "var(--green)" }}>↓</span></span></div>
          <div className="row jb"><span>힙회전</span><span>45° <span style={{ color: "var(--green)" }}>↑</span></span></div>
        </div>
      </div>
    </div>

    <div className="sk-divider"/>
    <div className="sk-box p-12 tint-green">
      <div className="label-mono mb-4">변화 요약</div>
      <div className="hand" style={{ fontSize: 18 }}>헤드 안정성이 <span className="sk-marker">크게 개선</span></div>
      <div className="tiny mt-6">한 달간 집중한 '스웨이 방지 드릴'이 효과. 템포도 소폭 향상. 다음 단계: 힙회전 +10° 목표.</div>
    </div>
  </>
);

window.PageHistory = () => (
  <VariationPage
    title="진행 기록 / 히스토리"
    subtitle="장기적 동기부여 + 코치 공유 핵심. 성장을 한눈에 보여주는 레이아웃."
    variations={[
      { title: "추세 그래프", desc: "시간 축 점수 그래프 + 통계 카드. 상태 모니터링용.", content: <HistoryV1/> },
      { title: "캘린더 뷰", desc: "GitHub 잔디처럼 루틴을 점으로. 연속성 강조.", content: <HistoryV2/> },
      { title: "Before/After 비교", desc: "두 스윙 나란히 놓고 지표 차이 강조. 코치 공유용.", content: <HistoryV3/> },
    ]}
  />
);
