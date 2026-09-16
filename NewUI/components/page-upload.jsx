// page-upload.jsx — Video upload (PC/Tablet) — 3 variations

const UploadV1 = () => (
  <>
    <FrameTopbar title="영상 업로드"/>
    <h3 style={{ fontSize: 22, marginBottom: 4 }}>스윙 영상 <span className="sk-marker">업로드</span></h3>
    <div className="tiny muted mb-12">MP4 / MOV · 최대 100MB · 5~30초</div>

    <div className="sk-box sk-dashed p-14" style={{ minHeight: 200, display: "grid", placeItems: "center" }}>
      <div className="tc">
        <div style={{ width: 56, height: 56, border: "2px solid var(--ink)", borderRadius: 12, display: "grid", placeItems: "center", margin: "0 auto 10px", filter: "url(#sk-rough)", background: "var(--highlight-soft)" }}>
          <SkIcon name="upload" size={28}/>
        </div>
        <div className="hand" style={{ fontSize: 22 }}>여기에 드래그</div>
        <div className="tiny muted mt-4">또는 클릭해서 파일 선택</div>
        <div className="row ac jc gap-6 mt-12">
          <span className="sk-chip tiny">MP4</span>
          <span className="sk-chip tiny">MOV</span>
          <span className="tiny muted">· 최대 100MB</span>
        </div>
      </div>
    </div>

    <div className="sk-divider"/>

    <div className="row gap-10">
      <div className="sk-box p-10 f1">
        <div className="label-mono mb-4">1. 클럽 선택</div>
        <div className="row gap-4 mt-4" style={{ flexWrap: "wrap" }}>
          {["드라이버","3W","유틸","5I","7I","9I","PW","SW"].map((c, i) => (
            <span key={i} className={"sk-chip tiny " + (i === 0 ? "yellow" : "")}>{c}</span>
          ))}
        </div>
      </div>
      <div className="sk-box p-10 f1">
        <div className="label-mono mb-4">2. 촬영 각도</div>
        <div className="row gap-6 mt-4">
          <span className="sk-chip blue tiny">정면 (DTL)</span>
          <span className="sk-chip tiny">측면 (FO)</span>
          <span className="sk-chip ghost tiny">45°</span>
        </div>
      </div>
    </div>

    <div className="sk-box tint-green p-10 mt-12">
      <div className="row ac gap-8">
        <SkIcon name="check" size={18} color="var(--green)"/>
        <div className="hand" style={{ fontSize: 16 }}>잘 찍히는 영상 팁</div>
      </div>
      <div className="tiny mt-6" style={{ paddingLeft: 26 }}>
        · 전신이 화면에 들어오도록 (머리~발끝)<br/>
        · 45° 이상 비스듬한 각도 피하기<br/>
        · 어드레스~피니시 전체 동작 포함
      </div>
    </div>
  </>
);

const UploadV2 = () => (
  <>
    <FrameTopbar title="업로드 · 파일 선택됨"/>
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      {/* Left: preview */}
      <div>
        <div className="label-mono mb-6">미리보기</div>
        <div className="sk-stick" style={{ height: 260, position: "relative" }}>
          <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
            <StickFigure pose="top" size={140}/>
          </div>
          <div style={{ position: "absolute", left: 8, top: 8 }} className="sk-chip red tiny">● REC</div>
          <div style={{ position: "absolute", right: 8, bottom: 8 }} className="sk-chip tiny">0:06 / 0:12</div>
          {/* scrub line */}
          <div style={{ position: "absolute", left: 10, right: 10, bottom: 28, height: 3, background: "var(--paper)", border: "1px solid var(--ink)", borderRadius: 2 }}>
            <div style={{ width: "50%", height: "100%", background: "var(--accent)" }}/>
          </div>
        </div>
        <div className="row ac jb mt-8">
          <div className="tiny">드라이버스윙2(후면).mp4</div>
          <div className="tiny muted">3.8 MB</div>
        </div>
      </div>

      {/* Right: form */}
      <div className="col gap-10">
        <div className="sk-box p-10">
          <div className="label-mono mb-4">스윙 구간 선택</div>
          <div className="tiny muted">어드레스 시작 ~ 피니시 끝</div>
          <div style={{ height: 32, position: "relative", margin: "8px 0 4px", background: "var(--paper-tint)", border: "1.5px solid var(--ink)", borderRadius: 4 }}>
            <div style={{ position: "absolute", left: "15%", right: "10%", top: 2, bottom: 2, background: "var(--highlight-soft)", border: "1.5px solid var(--accent)" }}/>
          </div>
          <div className="row jb tiny muted"><span>0:00</span><span>0:12</span></div>
        </div>

        <div className="sk-box p-10">
          <div className="label-mono mb-6">메타데이터</div>
          <div className="col gap-6">
            <div className="row ac jb"><span className="tiny">클럽</span><span className="sk-chip yellow tiny">7번 아이언</span></div>
            <div className="row ac jb"><span className="tiny">각도</span><span className="sk-chip blue tiny">DTL (후면)</span></div>
            <div className="row ac jb"><span className="tiny">목표 거리</span><span className="tiny hand">130y</span></div>
            <div className="row ac jb"><span className="tiny">탄도/결과</span><span className="sk-chip tiny">스트레이트</span></div>
          </div>
        </div>

        <button className="sk-btn primary big">
          분석 시작 <SkIcon name="arrow" size={14} color="var(--paper)"/>
        </button>
        <div className="tiny muted tc">예상 소요 시간 약 30초</div>
      </div>
    </div>
  </>
);

const UploadV3 = () => (
  <>
    <FrameTopbar title="배치 업로드"/>
    <h3 style={{ fontSize: 20 }}>여러 영상 한번에 <span className="sk-marker">비교 분석</span></h3>
    <div className="tiny muted mb-12">최대 5개 영상을 올려 시간순/클럽별 비교</div>

    <div className="sk-box sk-dashed p-12 tc" style={{ marginBottom: 10 }}>
      <div className="row ac jc gap-8">
        <SkIcon name="upload" size={20}/>
        <span className="hand" style={{ fontSize: 17 }}>여기에 드래그 (여러 파일 가능)</span>
      </div>
    </div>

    <div className="label-mono mb-6">큐 · 3개 영상</div>
    <div className="col gap-6">
      {[
        { name: "드라이버_0418.mp4", size: "4.1MB", status: "분석 대기", color: "ghost" },
        { name: "7I_0418_a.mp4", size: "3.2MB", status: "업로드 중 · 68%", color: "yellow" },
        { name: "SW_0417.mp4", size: "2.8MB", status: "완료 · 결과 보기", color: "green" },
      ].map((f, i) => (
        <div className="sk-box p-10 row ac gap-10" key={i}>
          <SkIcon name="video" size={22}/>
          <div className="f1">
            <div style={{ fontSize: 14, fontWeight: 700 }}>{f.name}</div>
            <div className="tiny muted">{f.size}</div>
          </div>
          <span className={"sk-chip tiny " + f.color}>{f.status}</span>
          <button className="sk-btn small" style={{ filter: "none", boxShadow: "none" }}>×</button>
        </div>
      ))}
    </div>

    <div className="sk-divider"/>
    <div className="row ac jb">
      <div className="tiny muted">총 10.1MB · 예상 분석 시간 ~90초</div>
      <button className="sk-btn primary">모두 분석 →</button>
    </div>
  </>
);

window.PageUpload = () => (
  <VariationPage
    title="영상 업로드 (PC/태블릿)"
    subtitle="PC는 저장된 영상을 상세 분석하는 메인 경로. 드롭존 UX + 메타데이터 입력 + 구간 트리밍."
    variations={[
      { title: "드롭존 + 가이드", desc: "단순 드래그&드롭. 현재 구현의 자연스러운 진화.", content: <UploadV1/> },
      { title: "미리보기 + 메타", desc: "업로드 후 구간 트리밍과 클럽/각도 입력을 같은 화면에서.", content: <UploadV2/> },
      { title: "배치 큐", desc: "여러 스윙을 한번에 올려 비교 분석. 상급자/코치 워크플로우.", content: <UploadV3/> },
    ]}
  />
);
