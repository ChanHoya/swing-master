// page-home.jsx — Home / Dashboard (PC/Tablet) — 3 variations

const HomeV1 = () => (
  <>
    <FrameTopbar title="대시보드" actions={<button className="sk-btn small primary">+ 새 분석</button>} />

    <div className="row ac jb mb-12">
      <div>
        <h3 style={{ fontSize: 22 }}>안녕하세요, Chanho 👋</h3>
        <div className="tiny muted">이번 주 <span className="sk-marker">3회 분석</span> · 평균 점수 <b>78</b></div>
      </div>
      <div className="row gap-6">
        <span className="sk-chip blue">드라이버</span>
        <span className="sk-chip ghost">아이언</span>
        <span className="sk-chip ghost">웨지</span>
      </div>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 12 }}>
      <div className="sk-box p-12">
        <div className="label-mono mb-8">최근 스윙 · 4월 17일</div>
        <div style={{ display: "grid", gridTemplateColumns: "110px 1fr", gap: 10 }}>
          <div className="sk-stick" style={{ height: 130 }}>
            <div style={{ padding: 8 }}><StickFigure pose="impact" size={90} /></div>
          </div>
          <div className="col gap-6">
            <div className="row ac gap-8">
              <h2 style={{ fontSize: 34 }}>78</h2>
              <span className="sk-chip green">+3</span>
              <span className="tiny muted">vs 이전 스윙</span>
            </div>
            <div className="tiny">주요 이슈: <span className="sk-marker-red">템포 비율 0.8:1</span></div>
            <div className="tiny muted">척추 각도 34° · 힙 회전 45° · 헤드무브 1.7cm</div>
            <button className="sk-btn small" style={{ alignSelf: "flex-start", marginTop: 4 }}>상세 리포트 →</button>
          </div>
        </div>
      </div>

      <div className="sk-box p-12 tint-yellow">
        <div className="label-mono mb-8">이번 주 목표</div>
        <div className="hand" style={{ fontSize: 20, lineHeight: 1.2 }}>3:1 템포<br/>일관성 잡기</div>
        <div className="row ac gap-6 mt-12">
          <div style={{ flex: 1, height: 8, background: "var(--paper)", border: "1.5px solid var(--ink)", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ width: "60%", height: "100%", background: "var(--accent)" }}/>
          </div>
          <span className="tiny">3/5회</span>
        </div>
        <div className="tiny muted mt-8">드릴: 메트로놈 60–70 BPM</div>
      </div>
    </div>

    <div className="sk-divider"/>

    <div className="label-mono mb-8">성장 추이 · 30일</div>
    <div className="sk-box p-12" style={{ height: 110 }}>
      <svg viewBox="0 0 300 70" width="100%" height="100%" style={{ filter: "url(#sk-rough)" }}>
        <path d="M5,55 L30,48 L55,50 L80,40 L105,42 L130,35 L155,38 L180,28 L205,32 L230,22 L255,25 L280,18 L295,20" fill="none" stroke="var(--accent)" strokeWidth="1.8"/>
        <path d="M5,55 L295,20" stroke="var(--pencil)" strokeWidth="0.6" strokeDasharray="2 2" fill="none"/>
      </svg>
    </div>

    <div className="row gap-10 mt-12">
      <div className="sk-box tint-blue p-10 f1">
        <div className="label-mono">드릴 추천</div>
        <div className="hand" style={{ fontSize: 17, marginTop: 4 }}>메트로놈 스윙</div>
        <div className="tiny muted mt-4">10–15분 · 3세트</div>
      </div>
      <div className="sk-box tint-green p-10 f1">
        <div className="label-mono">코치 피드백</div>
        <div className="hand" style={{ fontSize: 17, marginTop: 4 }}>김프로 · 2건</div>
        <div className="tiny muted mt-4">어제 · 읽지 않음</div>
      </div>
    </div>
  </>
);

const HomeV2 = () => (
  <>
    <FrameTopbar title="홈"/>
    <div className="row ac jb mb-12">
      <h2 style={{ fontSize: 28 }}>오늘의 <span className="sk-marker">라운드 체크</span></h2>
      <span className="tiny muted">4월 18일 · 금</span>
    </div>

    {/* Split hero: big CTA card + quick stats */}
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      <div className="sk-box sk-bold p-14 tint-red" style={{ minHeight: 160 }}>
        <div className="label-mono mb-8">PRIMARY ACTION</div>
        <div className="hand" style={{ fontSize: 28, lineHeight: 1.1 }}>새 스윙<br/>분석하기</div>
        <div className="row gap-8 mt-12">
          <button className="sk-btn primary">
            <SkIcon name="upload" size={14}/> 영상 업로드
          </button>
          <button className="sk-btn">
            <SkIcon name="camera" size={14}/> 폰에서 촬영
          </button>
        </div>
        <div className="tiny muted mt-8">· 분석 ~30초 · 클럽/각도 자동 인식</div>
      </div>

      <div className="col gap-10">
        <div className="sk-box p-12 row ac gap-10">
          <div style={{ width: 44, height: 44, borderRadius: "50%", border: "2px solid var(--ink)", display: "grid", placeItems: "center", filter: "url(#sk-rough)", background: "var(--highlight-soft)" }}>
            <span className="hand" style={{ fontWeight: 700 }}>78</span>
          </div>
          <div className="f1">
            <div className="tiny muted">평균 점수</div>
            <div className="row ac gap-4"><span style={{ fontSize: 17, fontWeight: 700 }}>B등급</span><span className="sk-chip green tiny">↑ +5</span></div>
          </div>
        </div>
        <div className="sk-box p-12 row ac gap-10">
          <SkIcon name="bolt" size={28} color="var(--accent)"/>
          <div className="f1">
            <div className="tiny muted">연속 연습</div>
            <div style={{ fontSize: 17, fontWeight: 700 }}>7일째 🔥</div>
          </div>
        </div>
        <div className="sk-box p-12 row ac gap-10">
          <SkIcon name="clock" size={28}/>
          <div className="f1">
            <div className="tiny muted">다음 라운드</div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>4월 21일 · 안양CC</div>
          </div>
        </div>
      </div>
    </div>

    <div className="sk-divider"/>

    <div className="label-mono mb-8">체크업 위젯</div>
    <div className="row gap-10">
      {["템포", "힙회전", "척추각", "체중이동"].map((k, i) => (
        <div className="sk-box p-10 f1" key={i} style={{ textAlign: "center" }}>
          <div className="tiny muted">{k}</div>
          <div className="hand" style={{ fontSize: 22 }}>{["B", "C", "A", "B"][i]}</div>
          <div style={{ height: 4, background: "var(--paper-tint)", borderRadius: 2, marginTop: 4 }}>
            <div style={{ width: ["70%","55%","85%","68%"][i], height: "100%", background: "var(--accent)" }}/>
          </div>
        </div>
      ))}
    </div>
  </>
);

const HomeV3 = () => (
  <>
    <FrameTopbar title="연습 저널"/>
    <div className="label-mono mb-8">TIMELINE · 최근 활동</div>

    <div className="col gap-10">
      {[
        { date: "오늘", title: "드라이버 스윙 분석", score: 78, tag: "템포↑", color: "green" },
        { date: "어제", title: "아이언 연습 세션", score: 72, tag: "힙회전↓", color: "red" },
        { date: "4월 15일", title: "코치 피드백 받음", score: null, tag: "읽지 않음", color: "yellow" },
        { date: "4월 13일", title: "드라이버 스윙 분석", score: 75, tag: "체중이동↑", color: "green" },
      ].map((item, i) => (
        <div className="row ac gap-12" key={i}>
          <div style={{ width: 70, textAlign: "right" }}>
            <div className="tiny muted">{item.date}</div>
          </div>
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "var(--ink)", border: "1.5px solid var(--paper)", outline: "1.5px solid var(--ink)" }}/>
          <div className="sk-box p-10 f1 row ac jb">
            <div>
              <div style={{ fontWeight: 700 }}>{item.title}</div>
              <div className="tiny muted mt-4">
                {item.score !== null && <>점수 <b>{item.score}</b> · </>}
                <span className={"sk-chip " + item.color + " tiny"}>{item.tag}</span>
              </div>
            </div>
            <button className="sk-btn small">열기 →</button>
          </div>
        </div>
      ))}
    </div>

    <div className="sk-divider"/>

    <div className="row gap-10">
      <div className="sk-box p-12 f1 tint-yellow">
        <div className="label-mono">오늘의 미션</div>
        <div className="hand" style={{ fontSize: 18, marginTop: 4 }}>메트로놈 드릴 · 10분</div>
        <div className="tiny muted mt-4">완료 시 배지 획득</div>
        <button className="sk-btn small mt-8">시작하기</button>
      </div>
      <div className="sk-box p-12 f1">
        <div className="label-mono">프로 스윙 비교</div>
        <div className="row gap-6 mt-4">
          <span className="sk-chip">Rory</span>
          <span className="sk-chip">Tiger</span>
          <span className="sk-chip">Scottie</span>
        </div>
        <div className="tiny muted mt-8">당신의 스윙 위에 오버레이</div>
      </div>
    </div>
  </>
);

window.PageHome = () => (
  <VariationPage
    title="홈 / 대시보드"
    subtitle="로그인 후 첫 화면. 중급 아마추어가 매일 열어볼 동기부여 + 다음 액션 허브. PC/태블릿 1200px 기준."
    variations={[
      { title: "데이터 카드형", desc: "최근 스윙 + 성장 그래프 + 주요 위젯. 현재 다크 버전에서 가장 큰 진화.", content: <HomeV1/> },
      { title: "액션 우선형", desc: "CTA를 크게 띄운 라운드 전용 대시보드. '다음에 뭐할지' 명확.", content: <HomeV2/> },
      { title: "타임라인 저널", desc: "연습/분석/피드백을 시간순으로. 코치와 공유에 유리.", content: <HomeV3/> },
    ]}
  />
);
