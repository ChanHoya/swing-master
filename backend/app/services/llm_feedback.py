import json
import logging
import os
import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# backend/.env (uvicorn 실행 위치) → 루트 .env 순서로 로드
_backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))
if os.path.exists(_backend_env):
    load_dotenv(dotenv_path=_backend_env, override=True)
if os.path.exists(_root_env):
    load_dotenv(dotenv_path=_root_env, override=False)  # backend/.env 우선

SYSTEM_PROMPT = """
You are a professional golf instructor with 20+ years of experience teaching amateur golfers in Korea.
You analyze swing data and provide clear, encouraging, and actionable feedback in Korean.
Your tone is warm but precise. Avoid overly technical jargon unless necessary.
Always prioritize the top 3 improvement areas ranked by severity.
"""

USER_PROMPT_TEMPLATE = """
다음은 골프 스윙 분석 결과입니다. 한국어로 교정 피드백을 작성해 주세요.

## 분석 지표
- 척추 각도 (spine_angle): {spine_angle}° (기준: 30~45°, 점수: {spine_score}/100)
- 힙 회전 (hip_rotation): {hip_rotation}° (기준: ≥45°, 점수: {hip_score}/100)
- 어깨 회전 (shoulder_rotation): {shoulder_rotation}° (기준: ≥90°, 점수: {shoulder_score}/100)
- 무릎 굴곡 (knee_flex): {knee_flex}° (기준: 20~30°, 점수: {knee_score}/100)
- 헤드 무브먼트 (head_movement): {head_movement}cm (기준: ≤5cm, 점수: {head_score}/100)
- 체중 이동 (weight_transfer): {weight_transfer}% (기준: ≥60%, 점수: {weight_score}/100)
- 템포 비율 (tempo_ratio): {tempo_ratio} (기준: 3:1, 점수: {tempo_score}/100)

## 요청 형식 (반드시 유효한 JSON 문자열로만 응답)
{{
  "overall_score": <0~100 정수>,
  "grade": <"A"|"B"|"C"|"D">,
  "top_issues": [
    {{
      "metric": "<지표 이름>",
      "severity": <"high"|"medium"|"low">,
      "feedback": "<교정 피드백 2~3문장>"
    }}
  ],
  "drills": [
    {{
      "issue_metric": "<관련 지표>",
      "drill_name": "<드릴 이름>",
      "steps": ["<1단계>", "<2단계>"],
      "repetitions": "<횟수 또는 시간>",
      "tip": "<핵심 포인트 1문장>"
    }}
  ],
  "encouragement": "<격려 한마디>"
}}
"""

def _calculate_score(value: float, target: float, is_ratio=False) -> int:
    """오차율 기반 스코어 계산"""
    if is_ratio:
        diff = abs(value - target) / target
    else:
        diff = abs(value - target) / (target if target > 0 else 1)
    
    score = 100 - (diff * 100)
    return max(0, min(100, int(score)))

async def generate_feedback(metrics: dict) -> dict:
    """
    Day 3에서 추출한 지표를 받아 순수 HTTPX를 통해 Gemini(REST API)로 드릴(Drill)과 피드백 생성
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.error("환경변수에 GEMINI_API_KEY가 없습니다!")
        # Fallback response for missing key
        return {
            "overall_score": 75,
            "grade": "C",
            "top_issues": [{"metric": "시스템", "severity": "low", "feedback": "API Key 누락으로 피드백 생성 불가"}],
            "drills": [],
            "encouragement": "서버의 .env에 GEMINI_API_KEY가 등록되지 않았습니다."
        }

    spine_angle = metrics.get("spine_angle", 35.0)
    hip_rotation = metrics.get("hip_rotation", 32.0)
    shoulder_rotation = metrics.get("shoulder_rotation", 88.0)
    knee_flex = metrics.get("knee_flex", 22.0)
    head_movement = metrics.get("head_movement", 1.5)
    weight_transfer = metrics.get("weight_transfer", 55.0)
    tempo_ratio = metrics.get("tempo_ratio", 2.8)

    prompt = USER_PROMPT_TEMPLATE.format(
        spine_angle=spine_angle, spine_score=_calculate_score(spine_angle, 40),
        hip_rotation=hip_rotation, hip_score=_calculate_score(hip_rotation, 50),
        shoulder_rotation=shoulder_rotation, shoulder_score=_calculate_score(shoulder_rotation, 90),
        knee_flex=knee_flex, knee_score=_calculate_score(knee_flex, 25),
        head_movement=head_movement, head_score=_calculate_score(head_movement, 2.0),
        weight_transfer=weight_transfer, weight_score=_calculate_score(weight_transfer, 70),
        tempo_ratio=tempo_ratio, tempo_score=_calculate_score(tempo_ratio, 3.0, is_ratio=True),
    )

    # 모델 우선순위 Fallback 체인
    MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash-lite",
    ]
    url_base = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "system_instruction": { "parts": [{"text": SYSTEM_PROMPT}] },
        "contents": [{ "parts": [{"text": prompt}] }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7
        }
    }
    headers = {
        "x-goog-api-key": gemini_key,
        "Content-Type": "application/json"
    }

    last_error = None
    for model in MODELS:
        try:
            import asyncio as _asyncio
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    url_base.format(model=model), json=payload, headers=headers
                )
                if response.status_code in (429, 503) and model != MODELS[-1]:
                    logger.warning(f"모델 {model} 과부하({response.status_code}), 다음 모델로 전환...")
                    await _asyncio.sleep(1)
                    continue
                response.raise_for_status()
                data = response.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(content)
                logger.info(f"Gemini 피드백 성공 (모델: {model})")
                return result
        except Exception as e:
            logger.warning(f"모델 {model} 실패: {e}")
            last_error = e
            continue

    # 모든 모델 실패 시 fallback
    logger.error(f"Gemini 모든 모델 실패: {last_error}")
    return {
        "overall_score": 75,
        "grade": "C",
        "top_issues": [],
        "drills": [],
        "encouragement": f"AI 피드백 서버가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요."
    }
