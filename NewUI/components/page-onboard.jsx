// page-onboard.jsx — Onboarding flow — 3 variations

const OnboardV1 = () => (
  <>
    <div className="tc mt-20">
      <div style={{ width: 80, height: 80, borderRadius: 20, background: "var(--highlight)", border: "2.5px solid var(--ink)", display: "grid", placeItems: "center", margin: "0 auto 16px", filter: "url(#sk-rough)" }}>
        <SkIcon name="golf" size={40}/>
      </div>
      <h1 style={{ fontSize: 40, lineHeight: 1 }}>Swing<span style={{ color: "var(--accent)" }}>Master</span></h1>
      <div className="tiny muted mt-8" style={{ padding: "0 24px" }}>영상 하나로, 프로 수준의<br/><span className="sk-marker">스윙 진단 + 교정</span></div>

      <div className="col gap-6 mt-20" style={{ padding: "0 20px" }}>
        {[
          { icon: "target", t: "7단계 자세 분석" },
          { icon: "camera", t: "실시간 자동 촬영" },
          { icon: "bolt", t: "AI 맞춤 드릴 추천" },
        ].map((f, i) => (
          <div className="sk-box p-10 row ac gap-10" key={i}>
            <SkIcon name={f.icon} size={20} color="var(--accent)"/>
            <span className="tiny f1" style={{ fontSize: 14 }}>{f.t}</span>
            <SkIcon name="check" size={14} color="var(--green)"/>
          </div>
        ))}
      </div>

      <div className="mt-20" style={{ padding: "0 20px" }}>
        <button className="sk-btn primary w-full">시작하기 →</button>
        <button className="sk-btn w-full mt-8" style={{ background: "transparent", border: "1.5px dashed var(--ink)" }}>로그인</button>
      </div>
    </div>
  </>
);

const OnboardV2 = () => (
  <>
    <div className="row ac jb mb-12">
      <div className="row gap-4">
        {[1,2,3,4].map(i => (
          <div key={i} style={{ width: i === 2 ? 24 : 8, height: 8, borderRadius: 4, background: i <= 2 ? "var(--accent)" : "var(--paper-tint)", border: "1px solid var(--ink)" }}/>
        ))}
      </div>
      <span className="tiny muted">2/4</span>
    </div>

    <h2 style={{ fontSize: 26, marginBottom: 8 }}>어떤 골퍼세요?</h2>
    <div className="tiny muted mb-12">맞춤 진단 기준을 설정해드려요</div>

    <div className="col gap-8">
      {[
        { t: "입문자", sub: "1년 미만 · 기본기 위주", sel: false },
        { t: "중급", sub: "스코어 90–100대 · 일관성 개선", sel: true },
        { t: "상급", sub: "스코어 80대 이하 · 세부 교정", sel: false },
        { t: "프로/코치", sub: "레슨 도구로 사용", sel: false },
      ].map((l, i) => (
        <div key={i} className={"sk-box p-12 row ac gap-10 " + (l.sel ? "tint-yellow sk-bold" : "")}>
          <div style={{ width: 18, height: 18, borderRadius: "50%", border: "1.8px solid var(--ink)", display: "grid", placeItems: "center" }}>
            {l.sel && <div style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--accent)" }}/>}
          </div>
          <div className="f1">
            <div style={{ fontSize: 15, fontWeight: 700 }}>{l.t}</div>
            <div className="tiny muted">{l.sub}</div>
          </div>
        </div>
      ))}
    </div>

    <div className="row gap-6 mt-20">
      <button className="sk-btn">← 이전</button>
      <button className="sk-btn primary f1">다음 →</button>
    </div>
  </>
);

const OnboardV3 = () => (
  <>
    <div className="label-mono mb-8">4/4 · 마지막</div>
    <h2 style={{ fontSize: 24 }}>첫 스윙 <span className="sk-marker">기준치</span> 만들기</h2>
    <div className="tiny muted mb-12">30초 영상 1개로 당신의 베이스라인 측정</div>

    <div className="sk-box sk-dashed p-16 tc" style={{ minHeight: 160 }}>
      <SkIcon name="camera" size={32}/>
      <div className="hand" style={{ fontSize: 18, marginTop: 8 }}>지금 촬영</div>
      <div className="tiny muted mt-4">또는</div>
      <div className="hand" style={{ fontSize: 16, marginTop: 4 }}>기존 영상 업로드</div>
    </div>

    <div className="sk-box tint-blue p-10 mt-12">
      <div className="label-mono mb-4">팁</div>
      <div className="tiny">· 7번 아이언 권장 (표준)<br/>· 정면 또는 후면 각도<br/>· 전신 프레임</div>
    </div>

    <div className="sk-divider"/>
    <div className="tc">
      <button className="sk-btn small" style={{ background: "transparent", border: "1.5px dashed var(--ink)", boxShadow: "none" }}>나중에 할게요</button>
    </div>
  </>
);

window.PageOnboard = () => (
  <VariationPage
    title="온보딩 흐름"
    subtitle="첫 설치 경험. 스윙 마스터를 쓰는 이유 + 레벨 설정 + 기준 스윙 촬영."
    variations={[
      { title: "Welcome 스플래시", desc: "기능 3줄 + 시작 CTA. 홈 화면 첫 진입.", content: <OnboardV1/>, frame: "phone" },
      { title: "레벨 설정 단계", desc: "4단계 중 2번째. 진행 바 + 라디오 선택.", content: <OnboardV2/>, frame: "phone" },
      { title: "기준 스윙 촬영", desc: "베이스라인 측정. 나중에 미루기 옵션.", content: <OnboardV3/>, frame: "phone" },
    ]}
  />
);
