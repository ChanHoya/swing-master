// page-seven.jsx — 7-stage analysis result (PC/Tablet) — 3 variations

const STAGES = ["어드레스","테이크백","탑","다운스윙","임팩트","팔로우","피니시"];
const POSES = ["address","takeaway","top","downswing","impact","follow","finish"];

const SevenV1 = () => (
  <>
    <FrameTopbar title="7단계 분석"/>
    <div className="row ac jb mb-12">
      <h3 style={{ fontSize: 22 }}><span className="sk-marker">7단계</span> 스윙 분석</h3>
      <span className="tiny muted">클릭 → 해당 구간 상세</span>
    </div>

    <div className="row gap-6">
      {STAGES.map((s, i) => (
        <div key={i} className="sk-box f1" style={{ padding: 6, cursor: "pointer", minWidth: 0 }}>
          <div className="sk-stick" style={{ height: 110, display: "grid", placeItems: "center" }}>
            <StickFigure pose={POSES[i]} size={75}/>
          </div>
          <div className="tc tiny mt-4" style={{ fontWeight: 700 }}>{i+1}. {s}</div>
          <div style={{ height: 4, marginTop: 4, background: ["var(--green)","var(--green)","var(--highlight)","var(--accent)","var(--accent)","var(--highlight)","var(--green)"][i], borderRadius: 2 }}/>
        </div>
      ))}
    </div>

    <div className="sk-divider"/>

    <div className="label-mono mb-8">단계별 체크리스트</div>
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      {[
        { stage: "어드레스", items: [{ok: true, t: "스탠스 어깨너비"}, {ok: true, t: "그립 중립"}, {ok: false, t: "체중 55/45 (편중)"}]},
        { stage: "탑", items: [{ok: true, t: "왼팔 펴짐"}, {ok: false, t: "오버스윙"}, {ok: true, t: "손목 각도"}]},
        { stage: "임팩트", items: [{ok: false, t: "헤드 1.7cm 이탈"}, {ok: true, t: "체중 전방"}, {ok: false, t: "힙 회전 부족"}]},
        { stage: "피니시", items: [{ok: true, t: "완전한 회전"}, {ok: true, t: "왼발 지지"}, {ok: true, t: "밸런스 유지"}]},
      ].map((b, i) => (
        <div className="sk-box p-10" key={i}>
          <div className="hand" style={{ fontSize: 17 }}>{b.stage}</div>
          <div className="col gap-4 mt-6">
            {b.items.map((it, j) => (
              <div className="row ac gap-6 tiny" key={j}>
                <span style={{ width: 14, display: "grid", placeItems: "center" }}>
                  <SkIcon name={it.ok ? "check" : "alert"} size={13} color={it.ok ? "var(--green)" : "var(--accent)"}/>
                </span>
                <span style={{ textDecoration: it.ok ? "none" : "none", color: it.ok ? "var(--ink)" : "var(--accent)" }}>{it.t}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  </>
);

const SevenV2 = () => (
  <>
    <FrameTopbar title="7단계 · 타임라인"/>
    <div className="label-mono mb-6">영상 스크러버 + 단계 마커</div>
    <div className="sk-stick" style={{ height: 230, position: "relative", marginBottom: 10 }}>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
        <StickFigure pose="impact" size={170}/>
      </div>
      {/* overlay skeleton accents */}
      <svg style={{ position: "absolute", inset: 0, pointerEvents: "none" }} viewBox="0 0 100 100" preserveAspectRatio="none">
        <path d="M46,22 L54,62" stroke="var(--accent)" strokeWidth="0.6" strokeDasharray="1 1"/>
      </svg>
      <div style={{ position: "absolute", right: 10, top: 10 }} className="sk-chip red tiny">5/7 · 임팩트</div>
    </div>

    {/* Timeline scrubber with markers */}
    <div className="sk-box p-10 mb-12" style={{ position: "relative" }}>
      <div style={{ height: 26, position: "relative", background: "var(--paper-tint)", border: "1.5px solid var(--ink)", borderRadius: 4 }}>
        {STAGES.map((s, i) => (
          <div key={i} style={{
            position: "absolute",
            left: `${(i / 6) * 100}%`,
            top: -2, bottom: -2,
            width: 2,
            background: i === 4 ? "var(--accent)" : "var(--ink)",
            transform: "translateX(-1px)",
          }}/>
        ))}
        <div style={{ position: "absolute", left: "66%", top: -6, bottom: -6, width: 3, background: "var(--accent)" }}/>
      </div>
      <div className="row jb" style={{ marginTop: 6 }}>
        {STAGES.map((s, i) => (
          <div key={i} className="tiny" style={{ fontSize: 10, color: i === 4 ? "var(--accent)" : "var(--pencil)", fontWeight: i === 4 ? 700 : 400, textAlign: "center", flex: 1 }}>
            {i+1}<br/>{s}
          </div>
        ))}
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      <div className="sk-box p-10">
        <div className="label-mono">현재 프레임 · 임팩트</div>
        <div className="col gap-4 mt-6 tiny">
          <div className="row jb"><span>척추 각도</span><span className="hand" style={{ fontSize: 15 }}>34.4°</span></div>
          <div className="row jb"><span>헤드 이탈</span><span className="hand" style={{ fontSize: 15, color: "var(--accent)" }}>1.7 cm ↑</span></div>
          <div className="row jb"><span>힙 회전</span><span className="hand" style={{ fontSize: 15 }}>45°</span></div>
          <div className="row jb"><span>체중</span><span className="hand" style={{ fontSize: 15 }}>전 65 / 후 35</span></div>
        </div>
      </div>
      <div className="sk-box tint-red p-10">
        <div className="label-mono">즉시 교정 포인트</div>
        <div className="hand mt-4" style={{ fontSize: 16 }}>헤드 스웨이 ↓</div>
        <div className="tiny mt-4">임팩트 순간 헤드가 공 방향으로 <span className="sk-marker-red">1.7cm 밀림</span>. 척추를 축으로 고정.</div>
      </div>
    </div>
  </>
);

const SevenV3 = () => (
  <>
    <FrameTopbar title="7단계 · 프로 오버레이"/>
    <div className="row ac jb mb-8">
      <h3 style={{ fontSize: 20 }}><span className="sk-marker">Rory McIlroy</span>와 겹쳐보기</h3>
      <div className="row gap-4">
        <span className="sk-chip yellow tiny">● 내 스윙</span>
        <span className="sk-chip blue tiny">◯ 프로</span>
      </div>
    </div>

    <div className="row gap-6">
      {STAGES.map((s, i) => (
        <div key={i} className="sk-box f1" style={{ padding: 4, minWidth: 0 }}>
          <div className="sk-stick" style={{ height: 100, position: "relative" }}>
            {/* Two overlapping stick figures */}
            <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", opacity: 0.4 }}>
              <StickFigure pose={POSES[i]} size={68}/>
            </div>
            <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
              <svg viewBox="0 0 100 100" width="68" height="68" style={{ filter: "url(#sk-rough)" }}>
                <circle cx="50" cy="18" r="7" fill="none" stroke="var(--blue)" strokeWidth="1.4" strokeDasharray="2 1"/>
                <path d="M50,25 L50,65" stroke="var(--blue)" strokeWidth="1.4" strokeDasharray="2 1" fill="none"/>
              </svg>
            </div>
          </div>
          <div className="tc tiny mt-4" style={{ fontWeight: 700 }}>{i+1}. {s}</div>
          <div className="tc tiny" style={{ fontSize: 10, color: ["var(--green)","var(--green)","var(--accent)","var(--accent)","var(--highlight)","var(--green)","var(--green)"][i] }}>
            {["±1°","±2°","-8°","-6°","-3°","±1°","±1°"][i]}
          </div>
        </div>
      ))}
    </div>

    <div className="sk-divider"/>
    <div className="sk-box tint-yellow p-12">
      <div className="label-mono">핵심 격차</div>
      <div className="hand mt-4" style={{ fontSize: 18 }}>탑에서 <span className="sk-marker-red">8° 오버스윙</span> + 다운스윙 <span className="sk-marker-red">6° 일찍 릴리즈</span></div>
      <div className="tiny muted mt-6">두 포인트만 교정해도 비거리 평균 +8야드 예상</div>
      <button className="sk-btn small accent mt-12">교정 드릴 받기 →</button>
    </div>
  </>
);

window.PageSeven = () => (
  <VariationPage
    title="7단계 스윙 분석 화면"
    subtitle="어드레스→피니시 7포즈를 어떻게 보여줄지. 현재 구현된 가로 썸네일을 더 깊이 있게."
    variations={[
      { title: "썸네일 + 체크리스트", desc: "현재 UI의 자연스러운 확장. 각 단계별 패스/페일 체크.", content: <SevenV1/> },
      { title: "타임라인 스크러버", desc: "영상 스크럽에 맞춰 해당 단계와 지표가 동기화.", content: <SevenV2/> },
      { title: "프로 오버레이", desc: "내 포즈 위에 프로 골퍼 포즈 겹치기. 편차를 각도로 표시.", content: <SevenV3/> },
    ]}
  />
);
