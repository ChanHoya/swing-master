# Render + Vercel 배포 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 맥북 로컬에서만 돌던 Swing Master 를 폰에서 쓸 수 있게, 백엔드를 Render(무료)에 프론트를 Vercel 에 올린다.

**Architecture:** DB(Supabase)와 스토리지(R2)는 이미 클라우드에 있어 그대로 쓴다. 백엔드는 기존 `backend/Dockerfile` 로 Render 웹 서비스 하나에 올리고, 분석은 지금처럼 `BackgroundTasks` 로 같은 프로세스에서 돈다(무료 티어에 Worker 가 없다). 공개 URL 이 되므로 업로드에 로그인을 요구하고 가입을 초대 코드로 잠근다.

**Tech Stack:** FastAPI 0.136 / Python 3.13(Docker) / Next.js 16 / Render(Docker, free) / Vercel / Supabase / Cloudflare R2 / GitHub Actions

**Spec:** `docs/superpowers/specs/2026-09-19-render-vercel-deployment-design.md`

## Global Constraints

- **TypeScript strict 모드. `any` 금지** — `unknown` + 타입 가드를 쓴다.
- **모든 사용자 노출 텍스트는 한국어.** 코드 주석은 영어/한국어 모두 허용.
- **백엔드 도구는 `backend/.venv/bin/<도구>` 를 직접 호출한다.** 가상환경을 활성화하지 않는 것이 이 저장소의 관례다.
- **프론트 패키지 매니저는 npm 이다** (`package-lock.json`). AGENTS.md 의 `pnpm` 표기는 낡았다. 타입 검증은 `npx tsc --noEmit`.
- **`pytest` 출력을 `tail`/`head`/`grep` 으로 파이프하지 않는다.** 종료 코드가 가려져 실패를 통과로 착각한다. 줄여 봐야 하면:
  `\.venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"`
- **커밋 규칙:** `feat:` / `fix:` / `docs:` / `refactor:` / `chore:`. 모든 커밋 메시지 끝에
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` 를 붙인다.
- **측정하지 못한 값에 가짜 기본값을 채우지 않는다** — 이 저장소의 제1 불변식. 이번 작업에서 지표 코드를 건드릴 일은 없지만, Task 1 의 측정 기록에도 같은 원칙을 적용한다(못 잰 값은 "못 쟀다"고 적는다).
- **비밀값을 저장소에 커밋하지 않는다.** `.env` 는 `.gitignore` 와 `.dockerignore` 양쪽에서 제외돼 있다. Render/Vercel 값은 각 대시보드에만 넣는다.

---

## Task 1: Phase 0 — 무료 티어를 로컬에서 재현해 실측

이 태스크만 TDD 가 아니다. **코드를 바꾸지 않고 사실을 알아내는 것**이 산출물이다.
여기 결과가 "불가" 면 **뒤 태스크로 넘어가지 말고 사용자에게 요금제를 묻는다.**

**Files:**
- Create: `docs/superpowers/plans/2026-09-19-phase0-measurement.md` (측정 기록)

**Interfaces:**
- Consumes: 없음
- Produces: 측정 기록 문서. 뒤 태스크는 이 문서의 판정(가능/불가)에만 의존한다.

**사전 조건:** Docker Desktop 이 떠 있어야 한다. `docker info --format '{{.ServerVersion}}'` 이 버전을 출력하면 준비된 것이다.

- [ ] **Step 1: 이미지를 빌드한다**

```bash
cd /Users/chanhojung/swing-master
docker build -t swing-api -f backend/Dockerfile . 2>&1 | tail -30
```

컨텍스트는 **저장소 루트**(마지막 인자 `.`)다. `backend/` 가 아니다 — 커밋 `03e8504` 가 고친 전제이고, 틀리면 `requirements.txt: not found` 로 깨진다.

- [ ] **Step 2: cv2 가 어느 패키지에서 왔는지 확인한다**

설계 문서가 지목한 미검증 위험이다. mediapipe 0.10.33 이 `opencv-contrib-python` 을 의존성으로 선언하므로, `requirements.txt` 에서 지웠어도 되살아나 `cv2` 를 덮어쓸 수 있다.

```bash
docker run --rm swing-api sh -c "pip list 2>/dev/null | grep -i opencv; python -c 'import cv2; print(cv2.__version__, cv2.__file__)'"
```

기록할 것: 설치된 opencv 패키지 **목록 전체**와 `cv2` 버전. `opencv-contrib-python` 과 `opencv-python-headless` 가 **둘 다** 나오면 중복이 되살아난 것이다.

- [ ] **Step 3: 512MB / 0.1 CPU 제한으로 컨테이너를 띄운다**

```bash
docker run -d --name swing-probe \
  --memory=512m --cpus=0.1 \
  --env-file backend/.env \
  -e ENV=production \
  -p 8000:8000 swing-api
sleep 20 && curl -s localhost:8000/health
```

`--memory=512m` 은 실제 cgroup 제한이라 넘치면 컨테이너가 진짜로 OOM kill 된다.
`/health` 가 `{"status":"ok",...}` 를 돌려주면 DB 연결까지 산 것이다.

`ENV=production` 으로 덮어쓰는 이유는 운영과 같은 조건에서 재기 위해서다.
`development` 면 SQLAlchemy 가 모든 SQL 을 찍어(`echo=True`) 로그와 메모리에
노이즈가 섞인다. 테이블은 Supabase 에 이미 있으므로 `create_all` 을 건너뛰어도
문제없다.

**함정 하나.** `docker --env-file` 은 값의 따옴표를 벗기지 않고 문자 그대로
넘긴다. `backend/.env` 의 `GEMINI_API_KEY="AQ.Ab8..."` 는 따옴표까지 포함된
키로 전달돼 Gemini 호출이 실패한다. 하지만 `polish()` 는 실패하면 규칙 엔진
결과를 그대로 돌려주므로 **분석은 끝까지 완주하고 측정은 유효하다.** 로그에
`LLM 윤문 실패` 가 보여도 버그가 아니니 그렇게 읽지 말 것.

- [ ] **Step 4: 메모리를 관찰하면서 실제 영상을 분석시킨다**

터미널 두 개가 필요하다. 하나는 관찰:

```bash
while true; do docker stats --no-stream --format '{{.MemUsage}} {{.CPUPerc}}' swing-probe; sleep 2; done | tee /tmp/swing-mem.txt
```

다른 하나는 업로드(이 시점에는 아직 익명 업로드가 열려 있다 — Task 2 에서 닫는다):

```bash
curl -s -X POST localhost:8000/upload \
  -F "file=@/Users/chanhojung/Downloads/골프스윙호야1.mp4;type=video/mp4"
```

돌려받은 `upload_id` 로 상태를 폴링한다:

```bash
curl -s "localhost:8000/analysis/<upload_id>/status"
```

- [ ] **Step 5: 결과를 판정한다**

```bash
docker logs swing-probe 2>&1 | grep -E "\[Vision\]|Killed|MemoryError"
docker inspect swing-probe --format '{{.State.OOMKilled}} {{.State.ExitCode}}'
```

| 관찰 | 판정 |
|---|---|
| `[Vision] 완료 \| 총 N초` 가 찍히고 `OOMKilled=false` | **가능.** N 초를 기록하고 Task 2 로 |
| `OOMKilled=true` 또는 로그가 중간에 끊김 | **불가.** 여기서 멈추고 사용자에게 요금제를 묻는다 |
| 최대 메모리가 480MB 이상 | **위태로움.** 가능으로 보되 기록에 경고를 남긴다 |

- [ ] **Step 6: 측정 기록을 쓴다**

`docs/superpowers/plans/2026-09-19-phase0-measurement.md` 에 아래를 채운다. **못 잰 항목은 추정치를 적지 말고 "못 쟀음"과 그 이유를 적는다.**

```markdown
# Phase 0 측정 기록 (2026-09-19)

| 항목 | 값 |
|---|---|
| 빌드 성공 | |
| 이미지 크기 | (`docker images swing-api --format '{{.Size}}'`) |
| 설치된 opencv 패키지 | |
| cv2 버전/경로 | |
| 분석 소요 시간 (512m/0.1cpu) | |
| 최대 메모리 | |
| OOMKilled | |
| 판정 | 가능 / 위태로움 / 불가 |
```

**참고 — 경량화에 대한 정직한 정정.** 설계 문서는 쓰이지 않는 `openai`·`google-genai` 제거를 "경량화 첫 카드"로 적었다. 이 둘은 **어디에서도 import 되지 않으므로 런타임 메모리(RSS)를 차지하지 않는다.** 제거는 이미지 크기와 빌드 시간을 줄일 뿐 OOM 을 해결하지 못한다. 메모리가 문제라면 실제 레버는 프레임 수(`skip`)와 처리 해상도(`proc_width`)다. 판정이 "불가" 로 나왔을 때 이 구분을 사용자에게 정확히 전달한다.

- [ ] **Step 7: 커밋**

```bash
docker rm -f swing-probe
git add docs/superpowers/plans/2026-09-19-phase0-measurement.md
git commit -m "$(cat <<'EOF'
docs: record Phase 0 free-tier measurement

512MB/0.1CPU 컨테이너에서 실제 스윙 영상으로 분석을 돌려
메모리·소요 시간·opencv 중복 여부를 실측했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 백엔드 접근 통제

**Files:**
- Modify: `backend/app/core/config.py` (INVITE_CODE 추가)
- Modify: `backend/app/core/auth.py` (verify_invite_code 추가, get_optional_user_id 제거, 독스트링 갱신)
- Modify: `backend/app/api/endpoints/auth.py` (register 에 초대 코드 검증)
- Modify: `backend/app/api/endpoints/upload.py:26` (선택 인증 → 필수 인증)
- Modify: `backend/tests/test_auth_helpers.py` (get_optional_user_id 테스트 3개 제거, 모듈 독스트링 갱신)
- Create: `backend/tests/test_invite_code.py`

**Interfaces:**
- Consumes: Task 1 의 판정이 "불가" 가 아닐 것
- Produces:
  - `app.core.auth.verify_invite_code(provided: str | None) -> None` — 불일치/미설정 시 `HTTPException(403)`
  - `app.core.config.Settings.INVITE_CODE: str` (기본값 `""`)
  - `RegisterRequest.invite_code: str` — Task 4 의 프론트가 이 필드명을 보낸다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_invite_code.py` 를 새로 만든다.

```python
"""
초대 코드 검증 테스트.

공개 URL 에 올리면 누구나 가입할 수 있으므로 가입을 초대 코드로 잠근다.
INVITE_CODE 가 설정되지 않았을 때 '열림'이 아니라 '닫힘'이어야 한다 —
환경변수를 깜빡하고 배포했을 때 문이 열려 있으면 안 된다.
"""
import pytest
from fastapi import HTTPException

from app.core.auth import verify_invite_code
from app.core.config import settings


def test_accepts_matching_code(monkeypatch):
    monkeypatch.setattr(settings, "INVITE_CODE", "let-me-in")
    verify_invite_code("let-me-in")  # 예외가 없으면 통과


def test_rejects_wrong_code(monkeypatch):
    monkeypatch.setattr(settings, "INVITE_CODE", "let-me-in")
    with pytest.raises(HTTPException) as exc:
        verify_invite_code("guess")
    assert exc.value.status_code == 403
    assert "초대 코드" in exc.value.detail


def test_rejects_missing_code(monkeypatch):
    monkeypatch.setattr(settings, "INVITE_CODE", "let-me-in")
    with pytest.raises(HTTPException) as exc:
        verify_invite_code(None)
    assert exc.value.status_code == 403


def test_registration_is_closed_when_code_not_configured(monkeypatch):
    """설정이 비어 있으면 가입을 여는 게 아니라 막는다."""
    monkeypatch.setattr(settings, "INVITE_CODE", "")
    with pytest.raises(HTTPException) as exc:
        verify_invite_code("anything")
    assert exc.value.status_code == 403
    assert "닫혀" in exc.value.detail
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && .venv/bin/pytest tests/test_invite_code.py -q
```
기대: `ImportError: cannot import name 'verify_invite_code'` 로 수집 단계에서 실패.

- [ ] **Step 3: 설정과 검증 함수를 구현한다**

`backend/app/core/config.py` 의 `# ── Rate Limiting ──` 블록을 통째로 아래로 교체한다.

```python
    # ── 가입 잠금 ────────────────────────────────────────────────────────────
    # 공개 URL 에 올리면 누구나 가입할 수 있다. 초대 코드를 아는 사람만 막는다.
    # 비어 있으면 가입이 '열리는' 게 아니라 '닫힌다'. 환경변수를 깜빡하고
    # 배포했을 때 문이 열려 있으면 안 되기 때문이다.
    INVITE_CODE: str = ""

    # ── Rate Limiting ────────────────────────────────────────────────────────
    # 주의: 아래 두 값은 선언만 돼 있고 어디에서도 강제되지 않는다(미구현).
    # 가입이 INVITE_CODE 로 잠겨 있어 당장은 필요하지 않다.
    ANON_DAILY_LIMIT: int = 1
    AUTH_DAILY_LIMIT: int = 5
```

`backend/app/core/auth.py` 상단 import 에 `secrets` 를 더하고, 파일 끝에 함수를 추가한다.

```python
def verify_invite_code(provided: str | None) -> None:
    """초대 코드가 맞지 않으면 403.

    설정이 비어 있으면 가입을 닫는다. 기본값이 '열림'이면 환경변수를
    빠뜨린 배포가 곧바로 공개 가입이 되므로, 안전한 쪽으로 기울여 둔다.
    비교는 compare_digest 로 한다 — 비밀값 비교의 표준 관행이다.
    """
    expected = settings.INVITE_CODE
    if not expected:
        raise HTTPException(status_code=403, detail="현재 회원가입이 닫혀 있습니다.")
    if provided is None or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="초대 코드가 올바르지 않습니다.")
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd backend && .venv/bin/pytest tests/test_invite_code.py -q
```
기대: 4 passed.

- [ ] **Step 5: register 엔드포인트에 연결한다**

`backend/app/api/endpoints/auth.py` 에서 import 에 `from app.core.auth import verify_invite_code` 를 더하고, `RegisterRequest` 와 `register` 를 고친다.

```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    invite_code: str


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    verify_invite_code(body.invite_code)

    # 중복 이메일 체크
    stmt = select(User).where(User.email == body.email)
    ...
```

`verify_invite_code` 를 **가장 먼저** 부른다. 코드가 틀린 요청에 대해 이메일 존재 여부를 알려 주지 않기 위해서다.

- [ ] **Step 6: 업로드를 인증 필수로 바꾼다**

`backend/app/api/endpoints/upload.py` 에서 import 와 의존성을 고친다.

```python
from app.core.auth import get_current_user_id          # was: get_optional_user_id
...
    user_id: str = Depends(get_current_user_id),        # was: str | None = Depends(get_optional_user_id)
```

그리고 본문의 소유자 계산을 단순화한다(이제 항상 로그인 상태다).

```python
    # 업로드는 로그인한 사용자에게만 허용한다. 공개 URL 에서 익명 업로드를
    # 열어 두면 R2 용량과 Gemini 할당량이 모르는 사람에게 나간다.
    owner = uuid.UUID(user_id)
```

- [ ] **Step 7: 죽은 코드와 낡은 테스트를 걷어낸다**

`get_optional_user_id` 는 유일한 사용처를 잃었다. `backend/app/core/auth.py` 에서 함수를 제거하고 모듈 독스트링을 갱신한다.

```python
"""
core/auth.py — JWT 에서 사용자를 꺼내는 공용 의존성과 가입 잠금.

업로드는 한때 비로그인으로도 가능했다. 공개 URL 에 올리면서 그 설계를
접었다 — 주소를 숨길 수 없고(NEXT_PUBLIC_API_URL 은 번들에 박힌다),
무료 인스턴스는 낯선 사람의 업로드 몇 건으로 막힌다.
"""
```

`backend/tests/test_auth_helpers.py` 에서 `get_optional_user_id` import 와 그것을 쓰는 테스트 **3개**(`test_optional_returns_user_id_when_logged_in`, `test_optional_returns_none_when_anonymous`, `test_optional_returns_none_for_invalid_token_without_raising`)를 제거하고, 모듈 독스트링을 갱신한다.

```python
"""
app/core/auth.py 의 인증 헬퍼 테스트.

업로드에는 로그인이 필요하다. 로그인한 사용자에게 귀속되어야
나중에 히스토리에서 찾을 수 있다.
"""
```

- [ ] **Step 8: 전체 테스트를 돌린다**

```bash
cd backend && .venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"
```
기대: `EXIT=0`. 개수는 141 − 3(제거) + 4(신규) = **142**.

- [ ] **Step 9: 문서를 맞춘다**

`AGENTS.md` 의 "TODO — 사람이 결정해야 할 것" 첫 항목("업로드에 사용자가 붙지 않는다")은 커밋 `6a09269` 에서 이미 해소됐고 이번 변경으로 전제 자체가 바뀌었다. 해당 항목을 지우고 "해소된 설계 쟁점" 에 한 줄을 더한다.

```markdown
- **업로드는 로그인 필수, 가입은 초대 코드로 잠금 (2026-09-19).** 공개 URL 에
  올리면서 익명 업로드 설계를 접었다. `ANON_DAILY_LIMIT`/`AUTH_DAILY_LIMIT` 은
  선언만 남고 미구현이다 — 가입이 잠겨 있어 당장 필요하지 않다.
```

`backend/.env.example` 에도 항목을 더한다.

```
# ── 가입 잠금 ─────────────────────────────────────────────────────────────────
# 비어 있으면 회원가입이 닫힌다. 로컬 개발에서는 아무 값이나 넣으면 된다.
INVITE_CODE=
```

- [ ] **Step 10: 커밋**

```bash
cd /Users/chanhojung/swing-master
git add backend/app backend/tests backend/.env.example AGENTS.md
git commit -m "$(cat <<'EOF'
feat(auth): require login to upload and lock registration behind an invite code

공개 URL 에 올리기 위한 준비다. NEXT_PUBLIC_API_URL 이 프론트 번들에
박히므로 백엔드 주소를 숨길 수 없고, 무료 인스턴스는 낯선 사람의 업로드
몇 건으로 막힌다.

INVITE_CODE 가 비어 있으면 가입을 연다가 아니라 닫는다. 환경변수를
빠뜨린 배포가 곧바로 공개 가입이 되면 안 된다.

업로드가 인증 필수가 되면서 get_optional_user_id 는 사용처를 잃어
함께 제거했다. 비로그인 업로드를 전제하던 테스트 3개도 같이 정리했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: CORS 를 실제로 동작하게 고친다

현재 기본값의 `"https://*.vercel.app"` 는 **아무것도 매칭하지 않는다.** Starlette 1.0.0 의
`CORSMiddleware.is_allowed_origin` 은 마지막 줄이 `return origin in self.allow_origins`
— 정확한 문자열 비교다. 패턴은 `allow_origin_regex` 로만 동작한다.

**Files:**
- Modify: `backend/app/core/config.py` (CORS_ORIGINS 기본값 수정, CORS_ORIGIN_REGEX 추가)
- Modify: `backend/app/main.py:40-46` (allow_origin_regex 연결)
- Create: `backend/tests/test_cors_config.py`

**Interfaces:**
- Consumes: 없음
- Produces: `app.core.config.Settings.CORS_ORIGIN_REGEX: str` (기본값 `""`). Task 6 에서 Render 환경변수로 실제 패턴을 넣는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_cors_config.py`:

```python
"""
CORS 설정 테스트.

Starlette 의 allow_origins 는 정확한 문자열 비교다(is_allowed_origin 의
마지막 줄이 `return origin in self.allow_origins`). 그래서
"https://*.vercel.app" 같은 와일드카드는 에러도 내지 않고 조용히
아무것도 매칭하지 않는다. 배포 후에야 CORS 차단으로 드러나므로
설정값 자체를 테스트로 묶어 둔다.
"""
import re

from app.core.config import settings


def test_allow_origins_contains_no_wildcard():
    """와일드카드는 조용히 실패한다. 정확한 오리진만 넣어야 한다."""
    for origin in settings.CORS_ORIGINS:
        assert "*" not in origin, (
            f"{origin!r} 은 아무것도 매칭하지 않는다. "
            "패턴이 필요하면 CORS_ORIGIN_REGEX 를 쓸 것."
        )


def test_origin_regex_is_empty_by_default():
    """기본값은 닫혀 있어야 한다. 패턴은 배포 환경에서 명시적으로 준다."""
    assert settings.CORS_ORIGIN_REGEX == ""


def test_origin_regex_matches_only_the_intended_project():
    """프로젝트로 좁힌 패턴이 남의 vercel.app 을 통과시키면 안 된다."""
    pattern = r"https://swing-master-[a-z0-9-]+\.vercel\.app"
    assert re.fullmatch(pattern, "https://swing-master-abc123.vercel.app")
    assert not re.fullmatch(pattern, "https://evil.vercel.app")
    assert not re.fullmatch(pattern, "https://swing-master-abc.vercel.app.evil.com")
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && .venv/bin/pytest tests/test_cors_config.py -q
```
기대: `test_allow_origins_contains_no_wildcard` 가 `https://*.vercel.app` 때문에 FAIL,
`test_origin_regex_is_empty_by_default` 가 `AttributeError` 로 FAIL.

- [ ] **Step 3: 설정을 고친다**

`backend/app/core/config.py` 의 CORS 블록을 교체한다.

```python
    # ── CORS ─────────────────────────────────────────────────────────────────
    # 같은 와이파이의 폰에서 접속하려면 맥의 LAN 주소도 허용해야 한다.
    # .local 이름은 IP 가 바뀌어도 그대로라 고정 주소로 쓸 수 있다.
    #
    # 여기에는 정확한 오리진만 넣는다. Starlette 은 문자열을 그대로 비교하므로
    # "https://*.vercel.app" 같은 와일드카드는 조용히 아무것도 매칭하지 않는다.
    # 패턴이 필요하면 아래 CORS_ORIGIN_REGEX 를 쓴다.
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://MacBook-Air.local:3000",
    ]

    # Vercel 프리뷰 배포처럼 주소가 매번 바뀌는 경우에만 쓴다.
    # 전부 여는 대신 프로젝트로 좁힌 패턴을 넣는다.
    # 예: https://swing-master-[a-z0-9-]+\.vercel\.app
    CORS_ORIGIN_REGEX: str = ""
```

- [ ] **Step 4: main.py 에 연결한다**

`backend/app/main.py` 의 `add_middleware` 호출을 고친다.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # 빈 문자열을 그대로 넘기면 모든 오리진에 대해 fullmatch 가 시도된다.
    # 설정하지 않았다는 뜻이므로 None 으로 바꿔 끈다.
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 5: 통과를 확인한다**

```bash
cd backend && .venv/bin/pytest tests/ -q > /tmp/pt.txt 2>&1; EXIT=$?; tail -5 /tmp/pt.txt; echo "EXIT=$EXIT"
```
기대: `EXIT=0`, 145 passed.

- [ ] **Step 6: 커밋**

```bash
cd /Users/chanhojung/swing-master
git add backend/app/core/config.py backend/app/main.py backend/tests/test_cors_config.py
git commit -m "$(cat <<'EOF'
fix(cors): wildcards in allow_origins never matched anything

Starlette 의 is_allowed_origin 은 `return origin in self.allow_origins`
로 끝난다 — 정확한 문자열 비교다. 기본값에 있던 "https://*.vercel.app" 은
에러도 내지 않고 조용히 아무것도 매칭하지 않았다. 배포한 뒤에야 CORS
차단으로 드러났을 것이다.

와일드카드를 걷어내고, 패턴이 필요한 경우를 위해 CORS_ORIGIN_REGEX 를
따로 뒀다. 기본값은 비어 있고, allow_origin_regex 에는 None 으로 넘긴다.
설정값이 다시 망가지지 않도록 테스트로 묶었다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 프론트엔드 접근 통제

**Files:**
- Modify: `frontend/src/context/AuthContext.tsx:15,38-44` (register 시그니처)
- Modify: `frontend/src/components/auth/AuthModal.tsx` (초대 코드 입력 칸)
- Modify: `frontend/src/app/upload/page.tsx` (로그인 게이트)

**Interfaces:**
- Consumes: Task 2 의 `RegisterRequest.invite_code`
- Produces: `useAuth().register(email: string, password: string, inviteCode: string) => Promise<void>`

- [ ] **Step 1: AuthContext 의 register 에 초대 코드를 더한다**

`frontend/src/context/AuthContext.tsx` 에서 타입과 구현을 고친다.

```typescript
interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode: string) => Promise<void>;
  logout: () => void;
}
```

```typescript
  const register = async (email: string, password: string, inviteCode: string) => {
    const res = await apiClient.post("/auth/register", {
      email,
      password,
      invite_code: inviteCode,
    });
    const u: User = res.data;
    setUser(u);
    localStorage.setItem("swingmaster_user", JSON.stringify(u));
    apiClient.defaults.headers.common["Authorization"] = `Bearer ${u.access_token}`;
  };
```

필드명은 백엔드 `RegisterRequest` 와 같은 `invite_code`(스네이크) 여야 한다.

- [ ] **Step 2: 타입 에러로 깨지는 것을 확인한다**

```bash
cd frontend && npx tsc --noEmit
```
기대: `AuthModal.tsx` 에서 `register(email, password)` 인자 개수가 맞지 않는다는 에러.
**이것이 이 태스크의 "실패하는 테스트" 다** — 타입 검사기가 호출부를 찾아 준다.

- [ ] **Step 3: AuthModal 에 입력 칸을 더한다**

상태를 추가한다.

```typescript
  const [inviteCode, setInviteCode] = useState("");
```

제출부를 고친다.

```typescript
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, inviteCode);
      }
```

비밀번호 `<div>` 바로 뒤에, 가입 모드에서만 보이는 칸을 넣는다.

```tsx
          {mode === "register" && (
            <div>
              <label style={{ display: "block", fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>초대 코드</label>
              <input
                type="text"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                required
                placeholder="초대받은 코드를 입력하세요"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: 10,
                  fontSize: 13,
                  color: "var(--text)",
                  outline: "none",
                  background: "var(--bg-3)",
                  border: "1px solid var(--line)",
                  transition: "border-color 0.15s",
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--line)")}
              />
            </div>
          )}
```

- [ ] **Step 4: 업로드 페이지에 로그인 게이트를 단다**

`frontend/src/app/upload/page.tsx` 상단 import 에 더한다.

```typescript
import { useAuth } from "@/context/AuthContext";
import AuthModal from "@/components/auth/AuthModal";
```

컴포넌트 안 상태 선언부에 더한다.

```typescript
  const { user } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
```

그리고 **훅을 모두 선언한 뒤**(조건부 훅 호출은 React 규칙 위반이다) 반환문 맨 앞에서 갈라낸다.

```tsx
  // 업로드는 로그인이 필요하다. 영상을 다 고르고 업로드한 뒤에 401 을
  // 맞으면 폰에서 특히 나쁜 경험이라 앞에서 막는다.
  if (!user) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
          로그인이 필요합니다
        </h2>
        <p style={{ fontSize: 13, color: "var(--text-3)", marginBottom: 20 }}>
          스윙 영상을 분석하려면 먼저 로그인해 주세요.
        </p>
        <button
          onClick={() => setShowAuth(true)}
          style={{
            padding: "12px 24px",
            borderRadius: 10,
            border: "none",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            background: "var(--accent)",
            color: "#0a0c10",
          }}
        >
          로그인 / 회원가입
        </button>
        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </div>
    );
  }
```

- [ ] **Step 5: 타입 검증을 통과시킨다**

```bash
cd frontend && npx tsc --noEmit
```
기대: 출력 없음(성공).

- [ ] **Step 6: 커밋**

```bash
cd /Users/chanhojung/swing-master
git add frontend/src
git commit -m "$(cat <<'EOF'
feat(auth): ask for an invite code on sign-up and gate the upload page

백엔드가 업로드에 인증을 요구하게 됐으므로 화면도 맞춘다.

업로드 페이지는 로그인 상태를 먼저 본다. 그러지 않으면 폰에서 영상을
고르고 업로드까지 마친 뒤에야 401 을 맞는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: render.yaml 과 Vercel 설정 정리

**Files:**
- Create: `render.yaml`
- Delete: `vercel.json` (루트)
- Modify: `frontend/vercel.json` (보안 헤더만 남김)
- Delete: `railway.toml` (대체됨)

**Interfaces:**
- Consumes: Task 3 의 `CORS_ORIGIN_REGEX`
- Produces: Task 6 의 사람이 따라갈 배포 설정

- [ ] **Step 1: render.yaml 을 만든다**

```yaml
# Render 배포 설정 (Blueprint).
#
# nixpacks 류 추론에 맡기지 않고 backend/Dockerfile 을 쓴다. 이 백엔드는
# OpenCV·MediaPipe 용 libgl1·libglib2.0-0·libgomp1 과 한글 폰트(fonts-nanum)가
# 필요하고 requirements.txt 가 Python 3.13 에 고정돼 있다.
services:
  - type: web
    runtime: docker
    name: swing-master-api
    plan: free
    region: singapore          # Supabase 가 ap-south-1 이라 오리건보다 가깝다
    dockerfilePath: ./backend/Dockerfile
    dockerContext: .           # 컨텍스트는 저장소 루트다. backend/ 가 아니다.
    healthCheckPath: /health
    envVars:
      - key: ENV
        value: production
      # 현재 .env 의 값은 문자 그대로 CHANGE_ME_IN_PRODUCTION 이라 쓸 수 없다.
      # Render 가 256비트 값을 생성하게 한다.
      - key: SECRET_KEY
        generateValue: true
      # 아래는 모두 대시보드에서 입력한다. 저장소에 들어가지 않는다.
      - key: DATABASE_URL
        sync: false
      - key: R2_ACCOUNT_ID
        sync: false
      - key: R2_ACCESS_KEY_ID
        sync: false
      - key: R2_SECRET_ACCESS_KEY
        sync: false
      - key: R2_BUCKET_NAME
        sync: false
      - key: R2_PUBLIC_URL
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: INVITE_CODE
        sync: false
      - key: CORS_ORIGINS
        sync: false
      - key: CORS_ORIGIN_REGEX
        sync: false
```

- [ ] **Step 2: Vercel 설정의 지뢰를 제거한다**

`frontend/vercel.json` 의 `"env": { "NEXT_PUBLIC_API_URL": "@api-url" }` 는 폐지된
Vercel Secrets 참조 문법이다. 그대로 두면 빌드가 *"Secret does not exist"* 로 실패한다.

루트 `vercel.json` 을 지우고(Vercel 프로젝트의 Root Directory 를 `frontend` 로 잡는다),
`frontend/vercel.json` 을 보안 헤더만 남기도록 통째로 교체한다.

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "SAMEORIGIN" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

빌드 명령·출력 경로는 적지 않는다. Next.js 는 Vercel 이 자동 감지한다.
`NEXT_PUBLIC_API_URL` 은 대시보드 환경변수로 넣는다(Task 6).

```bash
git rm vercel.json railway.toml
```

`railway.toml` 은 Render 로 갈아타면서 쓰이지 않는다. 두 개의 배포 설정이 남아 있으면
다음 사람이 어느 쪽이 사실인지 알 수 없다.

- [ ] **Step 3: 프론트 빌드가 실제로 되는지 확인한다**

```bash
cd frontend && npm run build 2>&1 | tail -20
```
기대: `Compiled successfully` 와 라우트 목록. Vercel 에 올리기 전에 로컬에서 먼저 깨 본다.

- [ ] **Step 4: 커밋**

```bash
cd /Users/chanhojung/swing-master
git add render.yaml frontend/vercel.json
git commit -m "$(cat <<'EOF'
chore(deploy): switch deployment config from Railway to Render

render.yaml 을 추가하고 railway.toml 을 지웠다. 빌드 컨텍스트는 저장소
루트이고 Dockerfile 경로는 backend/Dockerfile 이다 — 03e8504 에서 고친
전제와 같다. 리전은 Supabase(ap-south-1)에 가까운 싱가포르로 잡았다.

frontend/vercel.json 의 "@api-url" 은 폐지된 Vercel Secrets 참조라
그대로 두면 빌드가 실패한다. 보안 헤더만 남기고 걷어냈다. 빌드 명령은
Next.js 자동 감지에 맡긴다. 루트 vercel.json 은 Root Directory 를
frontend 로 잡으면서 불필요해져 삭제했다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: 배포 실행 (사람이 대시보드에서 하는 단계)

이 태스크는 코드가 아니라 **외부 서비스 조작**이다. 에이전트가 대신할 수 없으므로
사용자에게 아래 순서를 그대로 안내하고, 각 단계의 결과값을 받아 적는다.

**Files:** 없음 (산출물은 두 개의 URL)

**Interfaces:**
- Consumes: Task 5 의 `render.yaml`, `frontend/vercel.json`
- Produces: `RENDER_URL`(예: `https://swing-master-api.onrender.com`), `VERCEL_URL`. Task 7·8 이 둘 다 쓴다.

- [ ] **Step 1: 변경사항을 푸시한다**

```bash
git push origin main
```
Render 와 Vercel 모두 GitHub 저장소에서 읽어 간다.

- [ ] **Step 2: Render 에 Blueprint 로 올린다**

1. https://dashboard.render.com → **New** → **Blueprint**
2. `ChanHoya/swing-master` 저장소 연결 → `render.yaml` 자동 인식
3. `sync: false` 로 표시된 환경변수를 입력한다. 값은 로컬 `backend/.env` 에 있다:
   `DATABASE_URL`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   `R2_BUCKET_NAME`, `R2_PUBLIC_URL`, `GEMINI_API_KEY`
4. `INVITE_CODE` 는 **새로 정해서** 넣는다 (`openssl rand -hex 8` 로 만들어도 된다).
5. `CORS_ORIGINS` 는 일단 `["http://localhost:3000"]` 로 두고 Step 4 에서 고친다.
   Vercel 주소가 아직 없다. **JSON 배열 형식이어야 한다** — pydantic 이 그렇게 파싱한다.
6. `CORS_ORIGIN_REGEX` 는 비워 둔다.

빌드는 10~20분 걸릴 수 있다(MediaPipe 와 OpenCV 휠이 크다).

- [ ] **Step 3: 백엔드가 살았는지 확인한다**

```bash
curl -s https://<RENDER_URL>/health
```
기대: `{"status":"ok","db":"ok",...}`. `db` 가 `error` 면 `DATABASE_URL` 을 다시 본다.
**첫 요청은 콜드스타트라 1분 가까이 걸릴 수 있다.**

`ENV=production` 이면 기동 시 `Base.metadata.create_all` 을 건너뛴다. 지금은
Supabase 에 개발 중 만들어진 테이블이 이미 있어 문제없지만, **앞으로 스키마를
바꾸면 `alembic upgrade head` 를 직접 돌려야 한다.** 배포가 자동으로 해 주지
않는다.

- [ ] **Step 4: Vercel 에 올린다**

1. https://vercel.com/new → 같은 저장소 import
2. **Root Directory 를 `frontend` 로 지정한다** (기본값 아님 — 반드시 바꾼다)
3. 환경변수 `NEXT_PUBLIC_API_URL` = Step 3 의 Render 주소 (끝에 `/` 없이)
4. Deploy

- [ ] **Step 5: CORS 를 실제 주소로 갱신하고 재배포한다**

Render 대시보드에서 `CORS_ORIGINS` 를 고친다.

```json
["http://localhost:3000","https://<VERCEL_URL>"]
```

프리뷰 배포도 쓸 생각이면 `CORS_ORIGIN_REGEX` 에 프로젝트로 좁힌 패턴을 넣는다.

```
https://swing-master-[a-z0-9-]+\.vercel\.app
```

Render 는 환경변수를 바꾸면 자동으로 재시작한다.

- [ ] **Step 6: 계정을 만들고 끝까지 돌려 본다**

브라우저에서 `https://<VERCEL_URL>` → 회원가입(초대 코드 입력) → 업로드 → 분석 완료 →
결과 표시까지 **한 번에** 되는지 본다. 실패하면 Render 로그(`[Vision]` 줄)를 본다.

---

## Task 7: keep-alive 워크플로

Supabase 무료 프로젝트는 7일 무활동 시 일시정지되고, **복구 경로는 대시보드뿐이다.**
Render 인스턴스처럼 요청이 오면 저절로 깨어나지 않는다. 폰만 들고 있을 때 이걸 당하면
손쓸 방법이 없으므로 애초에 멈추지 않게 한다.

**Files:**
- Create: `.github/workflows/keepalive.yml`

**Interfaces:**
- Consumes: Task 6 의 `RENDER_URL`
- Produces: 없음

- [ ] **Step 1: 워크플로를 만든다**

`.github/workflows/keepalive.yml`:

```yaml
# Supabase 무료 프로젝트는 7일 무활동 시 일시정지되고, 복구는 대시보드에서만
# 된다(요청이 와도 저절로 깨어나지 않는다). 공식 문서가 "충분한 API 또는
# 애플리케이션 트래픽"도 일시정지를 막는다고 하므로 주기적으로 찔러 둔다.
#
# /health 는 SELECT 1 을 실제로 DB 에 날리므로 그대로 DB 트래픽이 되고,
# 덤으로 Render 인스턴스도 깨어난다.
#
# 한계: GitHub Actions 스케줄 워크플로는 저장소에 60일간 활동이 없으면
# 자동 비활성화된다. 프로젝트를 오래 방치하면 이 안전장치도 함께 멈춘다.
name: keep-alive

on:
  schedule:
    - cron: "0 3 */3 * *"   # 3일마다 03:00 UTC
  workflow_dispatch:         # 수동 실행도 가능하게

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping health endpoint
        run: |
          # 콜드스타트가 1분 가까이 걸릴 수 있으므로 넉넉히 기다린다.
          RESPONSE=$(curl -sS --max-time 120 --retry 3 --retry-delay 30 \
            "${{ secrets.RENDER_HEALTH_URL }}")
          echo "$RESPONSE"
          echo "$RESPONSE" | grep -q '"db":"ok"' || {
            echo "DB 가 응답하지 않는다. Supabase 가 일시정지됐을 수 있다."
            exit 1
          }
```

URL 을 저장소에 박지 않고 `secrets.RENDER_HEALTH_URL` 로 받는다. 공개 저장소라
주소를 굳이 눈에 띄게 둘 이유가 없다.

- [ ] **Step 2: 시크릿을 등록한다 (사람이 한다)**

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret
- Name: `RENDER_HEALTH_URL`
- Value: `https://<RENDER_URL>/health`

- [ ] **Step 3: 수동으로 한 번 돌려 확인한다**

GitHub → Actions → keep-alive → **Run workflow**.
기대: 초록색, 로그에 `{"status":"ok","db":"ok",...}`.

- [ ] **Step 4: 커밋**

```bash
git add .github/workflows/keepalive.yml
git commit -m "$(cat <<'EOF'
chore(ci): ping /health every three days to keep Supabase awake

Supabase 무료 프로젝트는 7일 무활동 시 일시정지되고 복구는 대시보드에서만
된다 — Render 인스턴스와 달리 요청이 와도 깨어나지 않는다. 폰만 들고
있을 때 이걸 당하면 손쓸 방법이 없다.

/health 가 SELECT 1 을 실제로 DB 에 날리므로 그대로 DB 트래픽이 되고
Render 인스턴스도 함께 깨어난다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 모바일 화면 점검과 수정

**무엇을 고칠지 미리 못 박지 않는다.** 폰에서 무엇이 깨지는지는 띄워 봐야 안다.
이 태스크는 "점검 → 발견한 것만 고친다" 이고, 발견이 없으면 고치지 않는 것이 정답이다.

**Files:**
- Modify: 점검 결과에 따라 `frontend/src/app/analysis/[id]/page.tsx`,
  `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/app/upload/page.tsx` 등
- Modify: `docs/04_roadmap_7days.md` (체크박스 갱신)

**Interfaces:**
- Consumes: Task 6 의 `VERCEL_URL`
- Produces: 없음

- [ ] **Step 1: 뷰포트 메타태그부터 확인한다**

```bash
grep -n "viewport" frontend/src/app/layout.tsx
```

없으면 Next.js 가 기본값을 넣어 주지만, 명시돼 있는지 먼저 본다. 없다면 추가한다.

```typescript
export const viewport = {
  width: "device-width",
  initialScale: 1,
};
```

- [ ] **Step 2: 모바일 뷰포트로 1차 점검한다**

Chrome DevTools MCP 로 `https://<VERCEL_URL>` 을 열고 iPhone 폭(390×844)으로 리사이즈해
아래 화면을 순서대로 본다.

| 화면 | 보는 것 |
|---|---|
| `/upload` | 로그인 게이트 버튼이 터치하기 충분한가, 파일 선택이 동작하는가 |
| `/analysis/<id>` | 배속 버튼 5개 + 궤적/전체영상 토글이 **가로로 넘치지 않는가** |
| `/analysis/<id>` | 레이더 차트(SVG)가 잘리지 않는가 |
| `/analysis/<id>` | 손 궤적이 영상 위에 **정확히 겹치는가** (`containRect()` 가 세로 화면에서도 맞는가) |
| 사이드바 | 좁은 폭에서 본문을 덮거나 밀어내지 않는가 |

기준이 필요하면 `NewUI/mobile.html` 의 모바일 와이어프레임을 참고한다.

- [ ] **Step 3: 발견한 것을 고친다**

발견된 문제마다 고치고 `npx tsc --noEmit` 로 검증한다. 레이아웃만 건드리고
**분석 로직이나 궤적 계산에는 손대지 않는다** — 이번 태스크의 범위가 아니다.

- [ ] **Step 4: 실제 폰에서 최종 확인한다**

에뮬레이터는 터치 타깃 크기와 iOS Safari 의 비디오 동작(인라인 재생, 자동재생 정책)을
그대로 재현하지 못한다. 실제 폰에서 **로그인 → 촬영 → 업로드 → 분석 완료 → 결과 표시**
까지 한 번에 되는지 본다.

- [ ] **Step 5: 로드맵 체크박스를 갱신한다**

`docs/04_roadmap_7days.md` 의 "배포 준비" 항목을 고친다. `Railway` 를 언급한 줄은
Render 로 바꾼다.

```markdown
- [x] Vercel GitHub 연동 + 환경변수 등록
- [x] Render 백엔드 배포 + 환경변수 등록 (Railway 에서 변경)
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src docs/04_roadmap_7days.md
git commit -m "$(cat <<'EOF'
fix(ui): [deploy] repair what broke on a real phone screen

배포한 화면을 실제 폰에서 돌려보고 발견한 것만 고쳤다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## 되돌리는 법

배포가 잘못돼도 로컬 개발은 계속 된다 — `CORS_ORIGINS` 기본값에 `localhost:3000` 을
남겨 뒀다. Render 서비스는 대시보드에서 Suspend 하면 요금·트래픽이 멈추고, Vercel 은
이전 배포로 즉시 롤백할 수 있다. 코드 수준에서 문제가 생기면 Task 단위로 커밋돼 있으므로
해당 커밋만 `git revert` 한다.
