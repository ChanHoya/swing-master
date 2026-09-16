# LLM Integration Sub-Agent

## 역할
OpenAI API 연동 & 프롬프트 관리 전담

## 담당 영역

| 영역 | 세부 내용 |
|------|-----------|
| API 클라이언트 | OpenAI 비동기 클라이언트 설정 |
| 프롬프트 빌더 | SwingMetrics → LLM 입력 포맷 변환 |
| 응답 파서 | JSON 응답 검증 & Pydantic 파싱 |
| 재시도 로직 | 파싱 실패 시 exponential backoff 재시도 |
| 비용 추적 | 토큰 사용량 DB 기록 |

## 파일 구조 (예정)

```
backend/
└── llm/
    ├── __init__.py
    ├── client.py              ← OpenAI AsyncClient 설정
    ├── prompt_builder.py      ← 지표 → 프롬프트 변환
    ├── feedback_parser.py     ← 응답 파싱 & 검증
    ├── retry_handler.py       ← 재시도 로직
    └── cost_tracker.py        ← 토큰 비용 기록
```

## 핵심 구현 패턴

### 비동기 호출 + Structured Output

```python
from openai import AsyncOpenAI
from pydantic import BaseModel

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_feedback(metrics: SwingMetrics) -> FeedbackResult:
    prompt = build_prompt(metrics)
    
    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        temperature=0.3,  # 일관성 우선
    )
    
    return FeedbackResult.model_validate_json(
        response.choices[0].message.content
    )
```

### 재시도 로직

```python
MAX_RETRIES = 2
RETRY_DELAY = [1, 3]  # seconds

for attempt in range(MAX_RETRIES + 1):
    try:
        result = await generate_feedback(metrics)
        return result
    except (ValidationError, JSONDecodeError) as e:
        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY[attempt])
        else:
            raise LLMParseError(f"파싱 실패: {e}")
```

## 프롬프트 관리 규칙

1. 모든 프롬프트는 `docs/05_prompts.md`에서 관리
2. 코드 내 프롬프트 하드코딩 금지 → 상수 파일에서 import
3. A/B 테스트 시 `PROMPT_VERSION` 환경변수로 전환

## 비용 관리

| 설정 | 값 |
|------|-----|
| 모델 | `gpt-4o` (기본) / `gpt-4o-mini` (실험) |
| max_tokens | 1,500 |
| temperature | 0.3 |
| 예상 비용/회 | ~$0.06 (입력 500t + 출력 500t) |
| 일 한도 | 익명: 1회, 가입: 5회 |

## 토큰 사용량 추적

```sql
CREATE TABLE llm_usage (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID REFERENCES analyses(id),
    model           VARCHAR(50),
    prompt_tokens   INT,
    completion_tokens INT,
    total_tokens    INT,
    cost_usd        NUMERIC(10, 6),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

## 에러 타입 & 처리

| 에러 | 원인 | 처리 |
|------|------|------|
| `RateLimitError` | API 호출 초과 | 429 반환 + 재시도 후 알림 |
| `ValidationError` | JSON 파싱 실패 | 재시도 2회, 초과 시 실패 처리 |
| `AuthenticationError` | API 키 오류 | 즉시 500 반환 + Sentry 알림 |
| `APITimeoutError` | 응답 30초 초과 | 타임아웃 후 실패 처리 |

## 참고 문서
- `docs/05_prompts.md` — 프롬프트 템플릿 (PROMPT-001, PROMPT-002)
- `docs/06_data_schema.md` — SwingMetrics, AnalysisResult 타입
- `docs/07_risks.md` — R03 (비용), R06 (품질) 리스크 대응
