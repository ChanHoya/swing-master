// page-drills.jsx — Drill / practice guide — 3 variations

const DrillV1 = () => (
  <>
    <FrameTopbar title="드릴 라이브러리"/>
    <div className="row ac jb mb-12">
      <h3 style={{ fontSize: 22 }}>맞춤 <span className="sk-marker">연습 과제</span></h3>
      <div className="row gap-4">
        <span className="sk-chip yellow tiny">내 이슈</span>
        <span className="sk-chip ghost tiny">전체</span>
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      {[
        { t: "메트로놈 스윙", m: "10–15분", tag: "템포", c: "red", lv: "초급" },
        { t: "의자 힙턴", m: "15회 × 3세트", tag: "힙회전", c: "red", lv: "초급" },
        { t: "발 들고 피니시", m: "10회 × 3세트", tag: "체중이동", c: "yellow", lv: "중급" },
        { t: "슬로우 모션 스윙", m: "20분", tag: "전반적", c: "green", lv: "중급" },
      ].map((d, i) => (
        <div className="sk-box p-12" key={i}>
          <div className="row ac jb mb-6">
            <span className={"sk-chip tiny " + d.c}>{d.tag}</span>
            <span className="tiny muted">{d.lv}</span>
          </div>
          <div className="hand" style={{ fontSize: 20 }}>{d.t}</div>
          <div className="tiny muted mt-4">⏱ {d.m}</div>
          <div className="sk-stick mt-8" style={{ height: 90, display: "grid", placeItems: "center" }}>
            <StickFigure pose={["top","downswing","finish","follow"][i]} size={65}/>
          </div>
          <button className="sk-btn small w-full mt-8">시작</button>
        </div>
      ))}
    </div>
  </>
);

const DrillV2 = () => (
  <>
    <FrameTopbar title="주간 플랜"/>
    <h3 style={{ fontSize: 22 }}>이번 주 <span className="sk-marker">드릴 플랜</span></h3>
    <div className="tiny muted mb-12">AI 코치가 당신의 이슈를 바탕으로 짠 7일 커리큘럼</div>

    <div className="col gap-6">
      {[
        { d: "월", drill: "메트로놈 · 10분", status: "완료", c: "green" },
        { d: "화", drill: "의자 힙턴 · 15분", status: "완료", c: "green" },
        { d: "수", drill: "메트로놈 · 10분", status: "오늘", c: "yellow" },
        { d: "목", drill: "발 들고 피니시 · 10분", status: "예정", c: "ghost" },
        { d: "금", drill: "메트로놈 · 10분", status: "예정", c: "ghost" },
        { d: "토", drill: "필드 점검 스윙", status: "예정", c: "ghost" },
        { d: "일", drill: "휴식", status: "—", c: "ghost" },
      ].map((r, i) => (
        <div key={i} className="sk-box p-10 row ac gap-10">
          <div className="hand" style={{ fontSize: 20, width: 30, textAlign: "center" }}>{r.d}</div>
          <div className="f1">
            <div style={{ fontSize: 14 }}>{r.drill}</div>
          </div>
          <span className={"sk-chip tiny " + r.c}>{r.status}</span>
        </div>
      ))}
    </div>

    <div className="sk-divider"/>
    <div className="sk-box tint-yellow p-10 row ac gap-8">
      <SkIcon name="bolt" size={18}/>
      <div className="tiny f1">다음 라운드 전까지 <b>2주 플랜</b>으로 확장 가능</div>
      <button className="sk-btn small">보기</button>
    </div>
  </>
);

const DrillV3 = () => (
  <>
    <FrameTopbar title="드릴 상세"/>
    <div className="row ac jb mb-8">
      <SkIcon name="back" size={16}/>
      <span className="tiny muted">메트로놈 스윙 연습</span>
      <SkIcon name="share" size={14}/>
    </div>

    <h2 style={{ fontSize: 28 }}>메트로놈 <span className="sk-marker">3:1 템포</span></h2>
    <div className="row gap-6 mt-4 mb-12">
      <span className="sk-chip tiny">초급</span>
      <span className="sk-chip red tiny">템포 이슈</span>
      <span className="tiny muted">· 10~15분 · 실내 가능</span>
    </div>

    <div className="sk-stick" style={{ height: 200, display: "grid", placeItems: "center", marginBottom: 10 }}>
      <div className="tc">
        <StickFigure pose="top" size={120}/>
        <div className="tiny muted mt-4">영상 가이드 자리</div>
      </div>
    </div>

    <div className="label-mono mb-6">단계별 가이드</div>
    <div className="col gap-8">
      {[
        "메트로놈을 60–70 BPM으로 설정",
        "백스윙(1) → 전환(2) → 다운스윙(3) 3박자",
        "3:1 비율을 느끼며 천천히 스윙",
        "점차 스윙 속도를 올려 실제 템포까지",
      ].map((s, i) => (
        <div key={i} className="row gap-8">
          <div style={{ width: 24, height: 24, borderRadius: "50%", border: "1.8px solid var(--ink)", display: "grid", placeItems: "center", flexShrink: 0, background: "var(--highlight-soft)", filter: "url(#sk-rough)" }}>
            <span className="hand" style={{ fontSize: 13 }}>{i+1}</span>
          </div>
          <div className="tiny f1" style={{ paddingTop: 4 }}>{s}</div>
        </div>
      ))}
    </div>

    <div className="sk-box tint-yellow p-10 mt-12 row ac gap-8">
      <SkIcon name="bolt" size={16}/>
      <div className="tiny f1">탑에서 잠시 멈추는 느낌으로 전환 동작 여유 있게</div>
    </div>

    <div className="row gap-6 mt-12">
      <button className="sk-btn f1">메트로놈 열기 ♪</button>
      <button className="sk-btn primary f1">완료 기록 →</button>
    </div>
  </>
);

window.PageDrills = () => (
  <VariationPage
    title="드릴 / 연습 가이드"
    subtitle="진단에서 교정으로 이어지는 액션. 내 이슈 기반 맞춤 추천."
    variations={[
      { title: "카드 라이브러리", desc: "태그/레벨로 필터. 이슈별로 빠르게 탐색.", content: <DrillV1/> },
      { title: "주간 플랜 뷰", desc: "7일 커리큘럼. 오늘 할 일 하나만 집중.", content: <DrillV2/> },
      { title: "드릴 상세", desc: "단계별 가이드 + 영상 + 완료 기록.", content: <DrillV3/> },
    ]}
  />
);
