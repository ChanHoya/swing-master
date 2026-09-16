// page-profile.jsx — Settings / profile — 3 variations

const ProfileV1 = () => (
  <>
    <FrameTopbar title="프로필"/>
    <div className="row ac gap-12 mb-12">
      <div className="sk-avatar" style={{ width: 64, height: 64, fontSize: 28 }}>C</div>
      <div className="f1">
        <h3 style={{ fontSize: 22 }}>Chanho Jung</h3>
        <div className="tiny muted">중급 · 가입 30일 · 27회 분석</div>
        <div className="row gap-4 mt-4">
          <span className="sk-chip yellow tiny">HDCP 15</span>
          <span className="sk-chip tiny">우타</span>
        </div>
      </div>
      <button className="sk-btn small">편집</button>
    </div>

    <div className="sk-divider"/>

    <div className="label-mono mb-8">내 골프백</div>
    <div className="row gap-6" style={{ flexWrap: "wrap" }}>
      {["드라이버 1W","3W","5W","유틸 4","5I","6I","7I","8I","9I","PW","SW","퍼터"].map((c, i) => (
        <span key={i} className="sk-chip tiny">{c}</span>
      ))}
      <span className="sk-chip ghost tiny">+ 클럽 추가</span>
    </div>

    <div className="sk-divider"/>

    <div className="label-mono mb-8">설정</div>
    <div className="col gap-6">
      {[
        { t: "음성 코칭", v: "On", c: "green" },
        { t: "단위", v: "미터·cm", c: null },
        { t: "자동 감지 민감도", v: "중간", c: null },
        { t: "데이터 백업", v: "매주", c: null },
        { t: "알림", v: "연습 리마인더", c: null },
      ].map((row, i) => (
        <div key={i} className="sk-box p-10 row ac jb">
          <span style={{ fontSize: 14 }}>{row.t}</span>
          <div className="row ac gap-6">
            <span className="tiny muted">{row.v}</span>
            <SkIcon name="arrow" size={12}/>
          </div>
        </div>
      ))}
    </div>
  </>
);

const ProfileV2 = () => (
  <>
    <FrameTopbar title="내 코치 연결"/>
    <h3 style={{ fontSize: 22 }}>코치와 <span className="sk-marker">공유</span></h3>
    <div className="tiny muted mb-12">리포트와 영상을 코치에게 전송하고 피드백 받기</div>

    <div className="sk-box p-12 tint-blue">
      <div className="row ac gap-10">
        <div className="sk-avatar" style={{ width: 48, height: 48, fontSize: 20, background: "var(--blue-soft)" }}>김</div>
        <div className="f1">
          <div style={{ fontSize: 16, fontWeight: 700 }}>김프로</div>
          <div className="tiny muted">KPGA · 아카데미 Pro</div>
          <div className="tiny mt-4">연결됨 · 레슨 3회</div>
        </div>
        <span className="sk-chip green tiny">활성</span>
      </div>
      <div className="row gap-6 mt-12">
        <button className="sk-btn small f1">리포트 전송</button>
        <button className="sk-btn small f1">메시지</button>
      </div>
    </div>

    <div className="sk-divider"/>

    <div className="label-mono mb-8">피드백 메시지 · 2건</div>
    <div className="col gap-8">
      {[
        { t: "어제 영상 잘 받았어요. 임팩트 순간 헤드 위치가 많이 개선됐네요…", d: "2시간 전", unread: true },
        { t: "이번 주 드릴은 메트로놈 중심으로 가시죠. 주말에 필드에서…", d: "어제", unread: false },
      ].map((m, i) => (
        <div key={i} className={"sk-box p-10 " + (m.unread ? "tint-yellow" : "")}>
          <div className="row ac jb mb-4">
            <span className="tiny" style={{ fontWeight: 700 }}>김프로</span>
            <span className="tiny muted">{m.d}</span>
          </div>
          <div className="tiny" style={{ fontSize: 13 }}>{m.t}</div>
        </div>
      ))}
    </div>

    <button className="sk-btn w-full mt-12" style={{ background: "transparent", border: "1.5px dashed var(--ink)", boxShadow: "none" }}>
      + 다른 코치 초대
    </button>
  </>
);

const ProfileV3 = () => (
  <>
    <FrameTopbar title="배지 & 성취"/>
    <h3 style={{ fontSize: 22 }}>배지 컬렉션</h3>
    <div className="tiny muted mb-12">12 / 30 획득</div>

    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
      {[
        { t: "첫 스윙", ok: true, i: "star" },
        { t: "7일 연속", ok: true, i: "bolt" },
        { t: "80점 돌파", ok: true, i: "target" },
        { t: "드릴 10회", ok: true, i: "drill" },
        { t: "템포 A", ok: false, i: "clock" },
        { t: "30일 연속", ok: false, i: "bolt" },
        { t: "90점", ok: false, i: "target" },
        { t: "코치 연결", ok: true, i: "user" },
      ].map((b, i) => (
        <div key={i} className={"sk-box tc p-10 " + (b.ok ? "tint-yellow" : "")} style={{ opacity: b.ok ? 1 : 0.5 }}>
          <SkIcon name={b.i} size={28} color={b.ok ? "var(--accent)" : "var(--muted)"}/>
          <div className="tiny mt-6" style={{ fontWeight: 700, fontSize: 11 }}>{b.t}</div>
        </div>
      ))}
    </div>

    <div className="sk-divider"/>

    <div className="label-mono mb-8">다음 배지</div>
    <div className="sk-box p-12">
      <div className="row ac gap-10">
        <SkIcon name="clock" size={28} color="var(--accent)"/>
        <div className="f1">
          <div style={{ fontWeight: 700 }}>템포 A등급</div>
          <div className="tiny muted">5회 연속 템포 A 달성 시</div>
          <div style={{ height: 6, background: "var(--paper-tint)", borderRadius: 3, marginTop: 8, border: "1px solid var(--ink)" }}>
            <div style={{ width: "40%", height: "100%", background: "var(--accent)" }}/>
          </div>
          <div className="tiny mt-4">2 / 5</div>
        </div>
      </div>
    </div>
  </>
);

window.PageProfile = () => (
  <VariationPage
    title="설정 / 프로필"
    subtitle="골퍼 정보 + 코치 연결 + 성취. 장기 사용자 리텐션 요소."
    variations={[
      { title: "프로필 + 설정", desc: "기본 정보 + 클럽 세팅 + 앱 설정.", content: <ProfileV1/> },
      { title: "코치 연결 허브", desc: "리포트 공유 + 피드백 메시지 스레드.", content: <ProfileV2/> },
      { title: "배지 컬렉션", desc: "게이미피케이션. 장기 동기부여.", content: <ProfileV3/> },
    ]}
  />
);
