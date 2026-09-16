// final-pages.jsx — consolidated single-variation pages (with flow for capture, tabs for detail/mresult)

// ---- 01 Home: Action-first (HomeV2) ----
window.FinalHome = () => (
  <>
    <div className="page-title">
      <div><h1>홈 / 대시보드</h1><div className="page-subtitle">액션 우선형 — 새 분석 CTA를 가장 크게. 중급 아마추어의 '지금 뭐할까'에 바로 답하는 허브.</div></div>
      <div className="label-mono">PC / Tablet</div>
    </div>
    <div className="sk-divider"/>
    <div className="var-frame single-frame"><HomeV2/></div>
  </>
);

// ---- 02 Upload: dropzone + guide (UploadV1) ----
window.FinalUpload = () => (
  <>
    <div className="page-title">
      <div><h1>영상 업로드</h1><div className="page-subtitle">드롭존 + 가이드. 현재 구현의 자연스러운 진화. PC는 저장 영상 분석이 메인 경로.</div></div>
      <div className="label-mono">PC / Tablet</div>
    </div>
    <div className="sk-divider"/>
    <div className="var-frame single-frame"><UploadV1/></div>
  </>
);

// ---- 03 Seven: thumbnail + checklist (SevenV1) ----
window.FinalSeven = () => (
  <>
    <div className="page-title">
      <div><h1>7단계 분석</h1><div className="page-subtitle">썸네일 + 체크리스트. 각 단계 패스/페일을 한눈에. 현재 구현의 자연스러운 확장.</div></div>
      <div className="label-mono">PC / Tablet</div>
    </div>
    <div className="sk-divider"/>
    <div className="var-frame single-frame"><SevenV1/></div>
  </>
);

// ---- 04 Detail: Report (default) + AI Coach tab ----
window.FinalDetail = () => {
  const [tab, setTab] = React.useState("report");
  return (
    <>
      <div className="page-title">
        <div><h1>상세 진단 & 코칭</h1><div className="page-subtitle">리포트형을 기본으로, AI 코치 대화 탭을 함께 제공. 데이터 + 스토리텔링 둘 다 커버.</div></div>
        <div className="label-mono">PC / Tablet</div>
      </div>
      <div className="sk-divider"/>
      <div className="tab-subtab">
        <div className={"subtab " + (tab === "report" ? "active" : "")} onClick={() => setTab("report")}>📋 리포트</div>
        <div className={"subtab " + (tab === "coach" ? "active" : "")} onClick={() => setTab("coach")}>💬 AI 코치 대화</div>
      </div>
      <div className={"sub-pane " + (tab === "report" ? "active" : "")}>
        <div className="var-frame single-frame"><DetailV1/></div>
      </div>
      <div className={"sub-pane " + (tab === "coach" ? "active" : "")}>
        <div className="var-frame single-frame"><DetailV2/></div>
      </div>
    </>
  );
};

// ---- 05 History: Before/After (HistoryV3) ----
window.FinalHistory = () => (
  <>
    <div className="page-title">
      <div><h1>진행 기록</h1><div className="page-subtitle">Before/After 비교. 두 스윙 나란히 놓고 지표 변화 강조. 코치 공유/동기부여에 유리.</div></div>
      <div className="label-mono">PC / Tablet</div>
    </div>
    <div className="sk-divider"/>
    <div className="var-frame single-frame"><HistoryV3/></div>
  </>
);

// ---- 06 Capture: 3-step flow (Setup → Viewfinder → Session) ----
window.FinalCapture = () => (
  <>
    <div className="page-title">
      <div><h1>실시간 촬영</h1><div className="page-subtitle">핵심 NEW 기능. 3단계 흐름: 셋업 가이드로 거치 확인 → 자동 감지 뷰파인더 → 세션 모드로 연속 녹화.</div></div>
      <div className="label-mono">Mobile · 3-step flow</div>
    </div>
    <div className="sk-divider"/>
    <div className="flow-strip">
      <div className="flow-step flow-frame">
        <div className="page-step-label">STEP 1</div>
        <div className="var-title" style={{ fontSize: 20 }}>셋업 가이드</div>
        <div className="var-desc">거치/거리/높이를 촬영 전 체크</div>
        <div className="var-frame phone" style={{ position: "relative" }}>
          <div className="final-tag">01</div>
          <CaptureV3/>
        </div>
      </div>
      <div className="flow-arrow">→</div>
      <div className="flow-step flow-frame">
        <div className="page-step-label">STEP 2</div>
        <div className="var-title" style={{ fontSize: 20 }}>자동 감지 뷰파인더</div>
        <div className="var-desc">핸즈프리 — 스윙하면 자동 녹화</div>
        <div className="var-frame phone" style={{ position: "relative" }}>
          <div className="final-tag">02</div>
          <CaptureV1/>
        </div>
      </div>
      <div className="flow-arrow">→</div>
      <div className="flow-step flow-frame">
        <div className="page-step-label">STEP 3</div>
        <div className="var-title" style={{ fontSize: 20 }}>세션 모드</div>
        <div className="var-desc">연속 스윙 후 한번에 리뷰</div>
        <div className="var-frame phone" style={{ position: "relative" }}>
          <div className="final-tag">03</div>
          <CaptureV2/>
        </div>
      </div>
    </div>
  </>
);

// ---- 07 Mobile Result: Swipe cards (default) + AI conversation tab ----
window.FinalMResult = () => {
  const [tab, setTab] = React.useState("swipe");
  return (
    <>
      <div className="page-title">
        <div><h1>간단 분석 결과</h1><div className="page-subtitle">스와이프 단계 카드가 기본. 원하면 AI 대화형으로 전환해 친근하게 들을 수 있음.</div></div>
        <div className="label-mono">Mobile</div>
      </div>
      <div className="sk-divider"/>
      <div className="tab-subtab">
        <div className={"subtab " + (tab === "swipe" ? "active" : "")} onClick={() => setTab("swipe")}>📱 스와이프 카드</div>
        <div className={"subtab " + (tab === "chat" ? "active" : "")} onClick={() => setTab("chat")}>💬 AI 대화형</div>
      </div>
      <div className={"sub-pane " + (tab === "swipe" ? "active" : "")}>
        <div className="var-frame phone" style={{ margin: "0 auto" }}><MResultV2/></div>
      </div>
      <div className={"sub-pane " + (tab === "chat" ? "active" : "")}>
        <div className="var-frame phone" style={{ margin: "0 auto" }}><MResultV3/></div>
      </div>
    </>
  );
};

// ---- 08 Drills: card library (DrillV1) ----
window.FinalDrills = () => (
  <>
    <div className="page-title">
      <div><h1>드릴 / 연습 가이드</h1><div className="page-subtitle">카드 라이브러리. 태그·레벨 필터로 내 이슈에 맞는 드릴을 빠르게.</div></div>
      <div className="label-mono">Common</div>
    </div>
    <div className="sk-divider"/>
    <div className="var-frame single-frame"><DrillV1/></div>
  </>
);

// ---- 09 Onboarding: Welcome → Level (flow) ----
window.FinalOnboard = () => (
  <>
    <div className="page-title">
      <div><h1>온보딩</h1><div className="page-subtitle">Welcome 스플래시 → 레벨 설정. 2단계로 가볍게 시작.</div></div>
      <div className="label-mono">Mobile · 2-step flow</div>
    </div>
    <div className="sk-divider"/>
    <div className="flow-strip">
      <div className="flow-step flow-frame">
        <div className="page-step-label">STEP 1</div>
        <div className="var-title" style={{ fontSize: 20 }}>Welcome 스플래시</div>
        <div className="var-desc">기능 3줄 + 시작 CTA</div>
        <div className="var-frame phone" style={{ position: "relative" }}>
          <div className="final-tag">01</div>
          <OnboardV1/>
        </div>
      </div>
      <div className="flow-arrow">→</div>
      <div className="flow-step flow-frame">
        <div className="page-step-label">STEP 2</div>
        <div className="var-title" style={{ fontSize: 20 }}>레벨 설정</div>
        <div className="var-desc">맞춤 기준치 세팅</div>
        <div className="var-frame phone" style={{ position: "relative" }}>
          <div className="final-tag">02</div>
          <OnboardV2/>
        </div>
      </div>
    </div>
  </>
);

// ---- 10 Profile: profile + settings (ProfileV1) ----
window.FinalProfile = () => (
  <>
    <div className="page-title">
      <div><h1>설정 / 프로필</h1><div className="page-subtitle">프로필 + 골프백 + 앱 설정. 기본 정보 관리 허브.</div></div>
      <div className="label-mono">Common</div>
    </div>
    <div className="sk-divider"/>
    <div className="var-frame single-frame"><ProfileV1/></div>
  </>
);
