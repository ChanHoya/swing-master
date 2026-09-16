// page-mresult.jsx — Mobile quick result — 3 variations

const MResultV1 = () => (
  <>
    <PhoneStatus/>
    <div className="row ac jb mb-8" style={{ padding: "0 12px" }}>
      <SkIcon name="back" size={18}/>
      <span className="tiny muted">결과</span>
      <SkIcon name="share" size={16}/>
    </div>

    <div className="tc mt-12">
      <div className="label-mono">종합 점수</div>
      <div style={{ position: "relative", width: 140, height: 140, margin: "8px auto" }}>
        <svg viewBox="0 0 100 100" width="140" height="140" style={{ filter: "url(#sk-rough)" }}>
          <circle cx="50" cy="50" r="40" fill="none" stroke="var(--paper-tint)" strokeWidth="8"/>
          <circle cx="50" cy="50" r="40" fill="none" stroke="var(--accent)" strokeWidth="8" strokeDasharray="196 251" strokeLinecap="round" transform="rotate(-90 50 50)"/>
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
          <div className="tc">
            <div className="hand" style={{ fontSize: 42, lineHeight: 1 }}>78</div>
            <div className="tiny muted">/100</div>
          </div>
        </div>
      </div>
      <span className="sk-chip yellow">B등급 · 양호</span>
    </div>

    <div className="sk-divider"/>

    <div style={{ padding: "0 8px" }}>
      <div className="label-mono mb-6">한눈에 보는 진단</div>
      <div className="col gap-6">
        <div className="sk-box tint-green p-10 row ac gap-8">
          <SkIcon name="check" size={16} color="var(--green)"/>
          <div className="tiny f1"><b>잘한 것</b> — 피니시 안정</div>
        </div>
        <div className="sk-box tint-red p-10 row ac gap-8">
          <SkIcon name="alert" size={16} color="var(--accent)"/>
          <div className="tiny f1"><b>고칠 것</b> — 템포 불균형</div>
        </div>
        <div className="sk-box tint-yellow p-10 row ac gap-8">
          <SkIcon name="bolt" size={16}/>
          <div className="tiny f1"><b>추천</b> — 메트로놈 드릴 10분</div>
        </div>
      </div>
    </div>

    <div className="row gap-6 mt-16" style={{ padding: "0 8px" }}>
      <button className="sk-btn f1 small">7단계 보기</button>
      <button className="sk-btn f1 small primary">드릴 시작 →</button>
    </div>
  </>
);

const MResultV2 = () => (
  <>
    <PhoneStatus/>
    {/* Swipeable stage cards */}
    <div className="tc mb-8">
      <div className="label-mono">5 / 7 · 임팩트</div>
    </div>

    <div className="sk-box p-10" style={{ position: "relative" }}>
      <div className="sk-stick" style={{ height: 260, display: "grid", placeItems: "center", position: "relative" }}>
        <StickFigure pose="impact" size={150}/>
        {/* callout */}
        <div style={{ position: "absolute", top: 18, right: 10 }} className="sk-chip red tiny">헤드 +1.7cm</div>
      </div>

      <div className="col gap-4 mt-8 tiny">
        <div className="row jb"><span className="muted">척추 각도</span><span className="hand" style={{ fontSize: 15 }}>34.4°</span></div>
        <div className="row jb"><span className="muted">힙 회전</span><span className="hand" style={{ fontSize: 15 }}>45°</span></div>
        <div className="row jb"><span className="muted">체중 이동</span><span className="hand" style={{ fontSize: 15, color: "var(--green)" }}>전 65%</span></div>
      </div>

      <div className="sk-box tint-red p-8 mt-8">
        <div className="tiny"><b>이 단계 이슈</b>: 척추가 공 방향으로 밀림</div>
      </div>
    </div>

    {/* dots */}
    <div className="row ac jc gap-4 mt-12">
      {[0,1,2,3,4,5,6].map(i => (
        <div key={i} style={{ width: i === 4 ? 14 : 6, height: 6, borderRadius: 3, background: i === 4 ? "var(--accent)" : "var(--paper-tint)", border: "1px solid var(--ink)" }}/>
      ))}
    </div>
    <div className="tc tiny muted mt-4">좌우 스와이프로 단계 이동</div>

    <button className="sk-btn w-full mt-12">전체 리포트 열기</button>
  </>
);

const MResultV3 = () => (
  <>
    <PhoneStatus/>
    {/* Conversational AI coach */}
    <div className="row ac gap-8 mb-8" style={{ padding: "0 8px" }}>
      <div className="sk-avatar" style={{ width: 28, height: 28 }}>AI</div>
      <div className="f1">
        <div className="hand" style={{ fontSize: 15 }}>Coach</div>
        <div className="tiny muted">방금 분석 완료</div>
      </div>
      <SkIcon name="mic" size={16}/>
    </div>

    <div className="col gap-8" style={{ padding: "0 8px" }}>
      <div className="sk-box tint-blue p-10">
        <div className="tiny hand" style={{ fontSize: 15 }}>78점! <span className="sk-marker">지난번보다 +3</span> 잘 하고 있어요 👏</div>
      </div>
      <div className="sk-box p-10" style={{ alignSelf: "flex-start" }}>
        <div className="tiny">가장 큰 이슈는 <b>템포 불균형</b>이에요.</div>
        <div className="sk-stick mt-6" style={{ height: 80, display: "grid", placeItems: "center" }}>
          <StickFigure pose="top" size={60}/>
        </div>
      </div>
      <div className="sk-box tint-yellow p-10">
        <div className="tiny hand">📢 오늘 10분만 <span className="sk-marker">메트로놈 드릴</span> 해볼까요?</div>
        <div className="row gap-4 mt-8">
          <button className="sk-btn small primary">시작 →</button>
          <button className="sk-btn small">나중에</button>
        </div>
      </div>
    </div>

    <div className="mt-16" style={{ padding: "0 8px" }}>
      <div className="sk-box sk-dashed p-8 row ac gap-6">
        <SkIcon name="mic" size={14}/>
        <span className="tiny muted">"자세히 설명해줘"라고 말해보세요</span>
      </div>
    </div>
  </>
);

window.PageMResult = () => (
  <VariationPage
    title="간단 분석 결과 (모바일)"
    subtitle="폰에서는 핵심만 빠르게. 상세는 PC에서 확인하는 전제. 스와이프 + 음성 UX 중심."
    variations={[
      { title: "점수 · 한줄 요약", desc: "가장 단순. 핵심 3개 (잘한것/고칠것/추천)만.", content: <MResultV1/>, frame: "phone" },
      { title: "스와이프 단계 카드", desc: "7단계를 좌우 스와이프로. 모바일에 최적화.", content: <MResultV2/>, frame: "phone" },
      { title: "AI 대화형", desc: "채팅 메시지처럼 친근하게. 음성 명령 지원.", content: <MResultV3/>, frame: "phone" },
    ]}
  />
);
