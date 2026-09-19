# Render + Vercel 배포 설계 (2026-09-19)

맥북 로컬에서만 돌던 Swing Master 를 폰에서 쓸 수 있게 만든다.
백엔드는 Render(무료), 프론트엔드는 Vercel 에 올린다.

## 배경 — 지난 시도가 멈춘 이유

커밋 `03e8504` 가 Railway 배포를 시도하다 이렇게 적고 중단했다.

> 아직 배포는 못 한다. mediapipe==0.10.33 이 Linux 휠로 존재하지 않는다
> (리눅스에는 1.0.0/1.0.1 만 있다). 버전 상향의 영향은 별도로 검증한다.

**이 진단은 틀렸다.** PyPI 를 직접 확인했다.

```
mediapipe-0.10.33-py3-none-manylinux_2_28_x86_64.whl
```

`py3-none` 태그라 파이썬 버전을 가리지 않고, `manylinux_2_28` 은 glibc 2.28 이상을
요구하는데 `python:3.13-slim`(Debian, glibc 2.36+)이 이를 충족한다. **버전을 올리지
않고 0.10.33 그대로 리눅스에 설치된다.** 남겨 둔 "버전 상향 영향 검증" 숙제는
불필요했다.

대신 검증되지 않은 위험을 하나 새로 찾았다. mediapipe 0.10.33 의 의존성 목록에
`opencv-contrib-python` 이 들어 있다. `03e8504` 가 `requirements.txt` 에서 contrib 를
지웠지만 mediapipe 가 스스로 끌어오므로 리눅스 빌드에서 되살아나 `cv2` 를 덮어쓸 수
있다. Phase 0 에서 실제 빌드로 확인한다.

## 사용자 결정

| 항목 | 결정 |
|---|---|
| Render 요금제 | **무료**. 512MB / 0.1 CPU / 15분 무활동 시 스핀다운 |
| 무료 티어에 안 들어갈 경우 | **미리 정하지 않는다.** 실측 숫자를 보고 유료 전환 또는 품질·속도 조절을 그때 결정 |
| 접근 통제 | **로그인한 사람만 업로드 + 초대 코드로 가입 잠금** |
| 모바일 범위 | 배포 + 실제 폰 화면 손보기. **PWA 는 범위 밖** |
| 진행 순서 | 로컬 Docker 로 먼저 실측한 뒤 배포 (A안) |

## 바뀌는 것과 바뀌지 않는 것

**바뀌지 않는다.** DB(Supabase, `ap-south-1` pooler)와 스토리지(Cloudflare R2)는 이미
클라우드에 있고 주소도 그대로 쓴다. 마이그레이션 없음. 분석 알고리즘·규칙 엔진·LLM
윤문도 손대지 않는다. `BackgroundTasks` 로 같은 프로세스에서 분석하는 구조도
유지한다 — Render 무료 티어에는 Background Worker 가 없으므로 선택지가 아니다.

**바뀐다.** ① 백엔드 실행 위치, ② 업로드 인증과 가입 잠금, ③ CORS·환경변수 배선,
④ 폰 화면에서 깨지는 곳.

---

## Phase 0 — 로컬에서 무료 티어를 재현해 실측

공개 노출 없이, Render 에서 겪을 일을 먼저 겪는다.

```bash
docker build -t swing-api -f backend/Dockerfile .        # 컨텍스트는 저장소 루트
docker run --memory=512m --cpus=0.1 --env-file backend/.env -p 8000:8000 swing-api
```

`--memory=512m` 은 실제 cgroup 제한이라 넘치면 컨테이너가 진짜로 OOM kill 된다.
입력은 `~/Downloads/골프스윙호야1.mp4`(2.0MB) 등 실제 스윙 영상을 쓴다. 저장소에는
영상이 없지만 로컬에 있다.

| 측정 | 방법 | 판단 |
|---|---|---|
| 빌드 성공 | `docker build` | 1순위 용의자는 `opencv-contrib-python` 재설치로 인한 `cv2` 덮어쓰기 |
| 최대 메모리 | 분석 중 `docker stats` | 512MB 근처면 위험, OOM kill 이면 불가 |
| 소요 시간 | `[Vision] 완료` 로그 | 로컬 9.5초 대비 배수 |

**판정이 "불가" 면 여기서 멈추고 요금제를 사용자에게 묻는다.** 그 전제 위에 쌓는
작업을 먼저 하지 않는다.

경량화가 필요해질 때의 첫 카드는 확인해 두었다. 백엔드가 실제로 import 하는
서드파티는 `fastapi, sqlalchemy, boto3, httpx, jose, bcrypt, pydantic, cv2,
mediapipe, numpy, supervision, PIL` 뿐인데 `requirements.txt` 에 **`openai` 와
`google-genai` 가 들어 있고 어디에서도 쓰이지 않는다** (`feedback/llm.py` 는 httpx 로
Gemini 를 직접 호출한다). 반면 `matplotlib`·`sounddevice` 는 mediapipe 가 의존성으로
요구하므로 지워도 pip 가 되살린다.

## Phase 1 — 접근 통제

공개 URL 에 올리는 순간 성격이 달라진다. `NEXT_PUBLIC_API_URL` 은 프론트 번들에
박히므로 백엔드 주소를 숨길 방법이 없고, 0.1 CPU 인스턴스는 낯선 사람이 100MB 영상
두어 개만 올려도 막힌다. R2 용량과 Gemini 할당량도 같이 나간다.

현재 상태를 확인했다. `ANON_DAILY_LIMIT` / `AUTH_DAILY_LIMIT` 은 **설정에만 있고
어디에서도 강제되지 않으며**, `POST /auth/register` 는 누구나 열려 있고, GitHub
저장소는 공개다.

**백엔드**

1. `POST /upload` — `get_optional_user_id` → `get_current_user_id`. 토큰 없으면 401.
   이 변경으로 `get_optional_user_id` 는 유일한 사용처를 잃으므로 함께 제거한다.
2. `POST /auth/register` — 본문에 `invite_code` 추가. `settings.INVITE_CODE` 와 다르면 403.
3. `config.py` — `INVITE_CODE: str = ""` 추가.

`INVITE_CODE` 가 비어 있으면 **가입을 여는 게 아니라 막는다.** 환경변수를 깜빡하고
배포했을 때 문이 열려 있으면 안 된다. 로컬 개발은 `.env` 에 아무 값이나 넣는다.

**프론트엔드**

4. `AuthContext.register(email, password, inviteCode)` — 인자 추가.
5. `AuthModal` — 가입 모드에서 초대 코드 입력 칸.
6. `upload/page.tsx` — 로그인 상태가 아니면 업로드 UI 대신 로그인 안내. 지금은 인증을
   전혀 보지 않아, 그대로 두면 폰에서 영상을 다 고르고 업로드한 뒤에야 401 을 맞는다.

**테스트**

7. `tests/test_auth_helpers.py:66` 은 `"""비로그인 업로드를 막으면 안 된다"""` 를
   단언한다. 전제가 뒤집혔으므로 삭제가 아니라 **새 계약으로 교체** — 비로그인
   업로드는 401.
8. 초대 코드 테스트 추가: 일치 → 성공, 불일치 → 403, `INVITE_CODE` 미설정 → 403.

**하지 않는 것.** 일일 횟수 제한은 구현하지 않는다. 가입이 초대 코드로 잠기면 쓸 수
있는 사람이 이미 한정되고, 그 위에 IP 당 카운터를 만드는 건 안 쓰일 기계를 미리 짓는
일이다. 대신 쓰이지 않는 두 설정값이 "구현된 보호장치"로 보이지 않도록 주석으로
미구현임을 명시한다.

**문서.** `AGENTS.md` 의 해당 항목과 `core/auth.py` 독스트링이 "업로드는 로그인 없이도
되어야 한다"를 전제로 쓰여 있다. 둘 다 갱신한다.

## Phase 2 — Render 배포

저장소 루트에 `render.yaml` 을 신설한다.

```yaml
services:
  - type: web
    runtime: docker
    name: swing-master-api
    plan: free
    region: singapore
    dockerfilePath: ./backend/Dockerfile
    dockerContext: .
    healthCheckPath: /health
    envVars:
      - key: ENV
        value: production
      - key: SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        sync: false
      # R2_*, GEMINI_API_KEY, INVITE_CODE, CORS_ORIGINS 도 sync: false
```

`dockerfilePath` · `dockerContext` · `plan: free` 는 Render 블루프린트 문서에서 확인한
실재 필드다. 컨텍스트를 루트로 두는 것은 `03e8504` 가 고친 전제와 같다.

리전은 **싱가포르**. Supabase 가 `ap-south-1`(뭄바이)라 오리건보다 가깝고 한국에서의
업로드 경로도 짧다.

`SECRET_KEY` 는 `generateValue: true` 로 Render 가 만든다. 현재 `.env` 값은 문자 그대로
`CHANGE_ME_IN_PRODUCTION...` 이라 JWT 서명에 쓰면 안 된다. 키가 바뀌면 기존 토큰은
무효화되지만 사용자가 본인뿐이라 문제되지 않는다.

### CORS — 지금 설정은 배포하면 반드시 깨진다

Starlette 1.0.0 의 `CORSMiddleware.is_allowed_origin` 을 직접 읽어 확인했다.

```python
return origin in self.allow_origins   # 정확한 문자열 비교
```

따라서 현재 기본값의 `"https://*.vercel.app"` 는 **아무것도 매칭하지 않는다.** 패턴은
`allow_origin_regex` 로만 동작한다. 두 가지를 한다.

1. `CORS_ORIGINS` 를 Render 환경변수로 실제 Vercel 도메인을 정확히 지정한다
   (pydantic 이 JSON 배열로 파싱). `http://localhost:3000` 은 남겨 로컬 개발을 유지한다.
2. `CORS_ORIGIN_REGEX` 설정을 새로 추가해 `main.py` 의 `allow_origin_regex` 에 연결한다.
   프리뷰 배포용이며 `https://.*\.vercel\.app` 처럼 전부 여는 대신 **프로젝트 슬러그로
   좁힌** 패턴을 쓴다. 기본값은 빈 문자열. 실제 패턴 값은 Vercel 프로젝트 이름이
   정해지는 Phase 3 에서 확정한다 (예: `https://swing-master-[a-z0-9-]+\.vercel\.app`).

## Phase 3 — Vercel 배포와 keep-alive

### 설정 파일이 두 개라 먼저 정리한다

루트와 `frontend/` 에 `vercel.json` 이 각각 있고 내용이 다르다. 특히
`frontend/vercel.json` 의

```json
"env": { "NEXT_PUBLIC_API_URL": "@api-url" }
```

이 `@` 문법은 폐지된 Vercel Secrets 참조라, 이대로 두면 빌드가 실패한다.

정리 방침: Vercel 프로젝트의 **Root Directory 를 `frontend` 로 지정**, 루트
`vercel.json` 은 삭제, `frontend/vercel.json` 은 **보안 헤더만 남긴다**(빌드 명령은
Next.js 자동 감지에 맡긴다). `NEXT_PUBLIC_API_URL` 은 대시보드 환경변수로 넣는다.

**이 값은 빌드 시점에 번들로 박히므로 Render 주소가 정해진 뒤에 넣고 재배포해야
한다. 순서가 중요하다 — Render 먼저, Vercel 나중.**

### keep-alive

Supabase 무료 프로젝트는 7일 무활동 시 일시정지된다. 공식 문서는 이렇게 말한다.

> You can prevent a pending pause by visiting the project via the Supabase Dashboard
> or by generating sufficient API or application traffic to the database. Once paused,
> projects can be restored through the Supabase Dashboard for up to one year.
> Restoring a project returns it to its previous state, including all data and
> configurations.

복구하면 데이터와 설정이 그대로 돌아오고 계속 쓸 수 있다. 문제는 **복구 경로가
대시보드뿐**이라는 점이다. Render 인스턴스는 요청이 오면 스스로 깨어나지만 Supabase 는
그렇지 않다. 폰에서 앱을 열어도 살아나지 않고 맥북으로 대시보드에 들어가야 하므로,
"맥북 없이 폰으로 쓴다"는 이번 목적과 정면으로 부딪힌다.

그래서 애초에 멈추지 않게 한다. **GitHub Actions 스케줄 워크플로로 3일마다 `/health`
를 호출한다.** `/health` 는 `SELECT 1` 을 실제로 DB 에 날리므로 그대로 DB 트래픽이
되고, 덤으로 Render 인스턴스도 깨어난다. 비용은 월 1시간 남짓으로 무료 한도(월 750
인스턴스 시간)에 비해 미미하다.

한계도 적어 둔다. GitHub Actions 스케줄 워크플로는 저장소에 60일간 활동이 없으면 자동
비활성화되므로, 프로젝트를 오래 방치하면 이 안전장치도 함께 멈춘다. 그리고 Supabase
복구는 1년까지만 가능하다.

### 운영상 알아둘 것

- `ENV=production` 이면 `main.py` 가 기동 시 `create_all` 을 건너뛴다. Supabase 에는
  개발 중 테이블이 이미 만들어져 있어 문제없지만, **스키마를 바꾸면 alembic 을 직접
  돌려야 한다.** 자동으로 따라오지 않는다.
- 무료 플랜은 자동 일일 백업이 없다. 분석 이력이 쌓이면 가끔 직접 내보낸다.

## Phase 4 — 모바일 화면

무엇을 고칠지 미리 못 박지 않는다. 폰에서 무엇이 깨지는지는 띄워 봐야 안다.

위험 지점은 예상된다. `analysis/[id]/page.tsx` 가 934줄에 레이더 차트(SVG), 7단계 카드,
배속 버튼 5개, 궤적 토글, 전체영상 토글을 모두 담고 있어 **좁은 폭에서 컨트롤이 넘칠
가능성**이 가장 크다. 손 궤적은 `containRect()` 로 레터박스를 계산해 캔버스에 그리므로
세로 화면에서 **궤적이 어긋나는지** 확인해야 한다. `Sidebar.tsx`(166줄)도 좁은 화면
동작을 봐야 한다.

`NewUI/mobile.html` 에 모바일 와이어프레임이 이미 있어 레이아웃 판단의 기준으로 쓴다.

Chrome DevTools 로 모바일 뷰포트를 에뮬레이션해 1차로 거르고 **실제 폰에서 최종
확인**한다. 에뮬레이터는 터치 타깃 크기나 iOS Safari 의 비디오 동작을 그대로
재현하지 못한다.

---

## 검증

| 단계 | 통과 기준 |
|---|---|
| Phase 0 | 512MB 컨테이너에서 분석 완주, 최대 메모리와 소요 시간 기록 |
| Phase 1 | 백엔드 테스트 전부 통과. 현재 141개에서 `test_auth_helpers.py` 의 비로그인 업로드 테스트 1개가 새 계약으로 교체되고, 초대 코드 3종 + 업로드 401 이 추가된다 |
| 프론트 변경 | `npx tsc --noEmit` — AGENTS.md 가 정한 필수 검증 |
| Phase 2~3 | 배포된 `/health` 가 `status: ok` 반환 |
| Phase 4 | 폰에서 로그인 → 촬영 → 업로드 → 분석 완료 → 결과 표시까지 한 번에 |

`pytest` 출력을 `tail`/`head`/`grep` 으로 파이프하지 않는다. 종료 코드가 가려진다.
(`HANDOFF-2026-09-17.md` 에 그로 인해 깨진 커밋이 기록돼 있다.)

## 범위 밖

- PWA(홈 화면 아이콘, 전체화면)
- 일일 업로드 횟수 제한
- 커스텀 도메인 — Render/Vercel 기본 도메인을 쓴다
- 분석 알고리즘 정확도 개선 (`detect_swing_window` 실패 3/11 등은 별건)

---

## 개정 (2026-09-19, Phase 0 실측 이후)

실측이 이 문서의 전제 두 개를 무너뜨렸다. 아래가 우선한다.
상세는 `docs/superpowers/plans/2026-09-19-phase0-measurement.md`.

### 1. "DB 는 이미 Supabase 라 마이그레이션 없음" — 틀렸다

`config.py` 는 `env_file=".env"` 를 프로세스 작업 디렉터리 기준으로 읽는다.
백엔드는 `backend/` 에서 실행하므로 `backend/.env` 를 읽고, 그 값은
`localhost:5432` 다. 루트 `.env` 의 Supabase 주소는 쓰이지 않으며, 그 프로젝트는
이미 소멸했다(`tenant/user ... not found`).

**원격 DB 를 새로 만들어야 한다. Neon 으로 결정했다.** 근거는 유휴 후 복귀 방식이다.

| | 유휴 시 | 깨우는 방법 | 만료 |
|---|---|---|---|
| Neon free | 5분 후 컴퓨트 정지 | **연결하면 자동 재개** (수백 ms) | 없음 |
| Supabase free | 7일 후 일시정지 | 대시보드에서 수동 | 1년 내 복구 |
| Render Postgres free | — | — | 30일 후 만료 → 삭제 |

Supabase 의 수동 복구는 "맥 없이 폰으로 쓴다"는 이 작업의 목적과 정면으로 부딪힌다.

**따라 오는 변경 두 가지.**
- `database.py` 에 `pool_pre_ping=True` 를 더한다. Neon 이 유휴 연결을 끊으므로
  풀에 죽은 커넥션이 남는다.
- 로컬 Postgres 의 사용자 1명·업로드 25건·분석 25건을 Neon 으로 옮긴다.
  이들이 참조하는 R2 객체는 살아 있어, 옮기면 히스토리가 그대로 보인다.

### 2. keep-alive 워크플로 — 불필요해졌다

Supabase 의 7일 일시정지를 막으려던 장치다. Neon 과 Render 모두 요청이 오면
스스로 깨어나므로 **사람 손도 크론도 필요 없다.** 해당 태스크를 삭제한다.

### 3. 이미지가 리눅스에서 돌지 않던 문제 네 가지를 고쳤다

커밋 `063a14e`. `FROM --platform=linux/amd64`, 베이스 `python:3.12-slim`,
`libegl1 libgles2` 추가, opencv 를 headless 하나로 정리.
`mediapipe` 버전 상향은 필요 없었다 — 필요한 것은 플랫폼을 맞추는 일이었다.

### 4. 실측 결과 — 메모리 통과, 속도는 Render 에서 재확인

512MB/0.1CPU 컨테이너에서 분석이 완주했다. 최대 메모리 **355MB/512MB(69%)**,
OOM 없음. 에뮬레이션 오버헤드가 포함된 상한이므로 네이티브에서는 더 낮다.

소요 시간 470초는 QEMU 에뮬레이션 값이라 Render 예상치로 쓸 수 없다. 다만
0.1 CPU 제약 자체가 지배적일 가능성이 크다. **무료로 배포해 실제 값을 받은 뒤
요금제를 결정한다**(사용자 결정).
