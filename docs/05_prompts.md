# 05. LLM 프롬프트 템플릿 (Prompts)

## 프롬프트 관리 원칙

1. 모든 프롬프트는 이 파일에서 버전 관리
2. 변경 시 `v1`, `v2` 등 버전 태그 명시
3. 테스트 결과(품질 점수)를 주석으로 첨부

---

## PROMPT-001 — 스윙 교정 피드백 생성 (v1)

### 용도
7가지 스윙 지표를 받아 한국어 교정 피드백과 드릴을 생성합니다.

### System Prompt

```
You are a professional golf instructor with 20+ years of experience teaching amateur golfers in Korea.
You analyze swing data and provide clear, encouraging, and actionable feedback in Korean.
Your tone is warm but precise. Avoid overly technical jargon unless necessary.
Always prioritize the top 3 improvement areas ranked by severity.
```

### User Prompt Template

```
다음은 골프 스윙 분석 결과입니다. 한국어로 교정 피드백을 작성해 주세요.

## 분석 지표
- 척추 각도 (spine_angle): {{spine_angle}}° (기준: 30~45°, 점수: {{spine_score}}/100)
- 힙 회전 (hip_rotation): {{hip_rotation}}° (기준: ≥45°, 점수: {{hip_score}}/100)
- 어깨 회전 (shoulder_rotation): {{shoulder_rotation}}° (기준: ≥90°, 점수: {{shoulder_score}}/100)
- 무릎 굴곡 (knee_flex): {{knee_flex}}° (기준: 20~30°, 점수: {{knee_score}}/100)
- 헤드 무브먼트 (head_movement): {{head_movement}}cm (기준: ≤5cm, 점수: {{head_score}}/100)
- 체중 이동 (weight_transfer): {{weight_transfer}}% (기준: ≥60%, 점수: {{weight_score}}/100)
- 템포 비율 (tempo_ratio): {{tempo_ratio}} (기준: 3:1, 점수: {{tempo_score}}/100)

## 요청 형식 (반드시 JSON으로만 응답)
{
  "overall_score": <0~100 정수>,
  "grade": <"A"|"B"|"C"|"D">,
  "top_issues": [
    {
      "metric": "<지표 이름(한국어)>",
      "severity": <"high"|"medium"|"low">,
      "feedback": "<교정 피드백 2~3문장>"
    }
    // 최대 3개
  ],
  "drills": [
    {
      "issue_metric": "<관련 지표>",
      "drill_name": "<드릴 이름>",
      "steps": ["<1단계>", "<2단계>", ...],
      "repetitions": "<횟수 또는 시간>",
      "tip": "<핵심 포인트 1문장>"
    }
    // 최대 3개
  ],
  "encouragement": "<사용자를 격려하는 마무리 문장 1개>"
}
```

### 예시 출력

```json
{
  "overall_score": 72,
  "grade": "B",
  "top_issues": [
    {
      "metric": "힙 회전",
      "severity": "high",
      "feedback": "백스윙 시 힙 회전이 32°로 기준(45°)보다 부족합니다. 하체가 너무 일찍 열리거나 회전이 제한되면 파워 손실로 이어집니다. 어드레스 시 오른 엉덩이를 살짝 뒤로 빼는 느낌으로 설정해 보세요."
    }
  ],
  "drills": [
    {
      "issue_metric": "힙 회전",
      "drill_name": "골반 회전 드릴 (의자 등받이 활용)",
      "steps": [
        "등받이 있는 의자 왼쪽에 서서 왼손으로 등받이를 가볍게 잡습니다",
        "클럽 없이 어드레스 자세를 만듭니다",
        "오른 엉덩이를 최대한 뒤로 회전시키며 백스윙 탑 포지션을 만듭니다",
        "3초간 유지 후 임팩트 방향으로 빠르게 회전합니다"
      ],
      "repetitions": "10회 × 3세트",
      "tip": "상체는 고정하고 골반만 독립적으로 회전하는 감각을 익히세요"
    }
  ],
  "encouragement": "전체적인 리듬감이 좋습니다. 힙 회전만 개선되면 비거리가 10~20야드 늘어날 수 있습니다. 꾸준히 연습해 보세요! 🏌️"
}
```

---

## PROMPT-002 — 분석 실패 안내 메시지 (v1)

### 용도
포즈 추정 실패 / 영상 품질 불량 시 사용자에게 안내

### Template

```
포즈 추정에 실패했습니다. 다음 조건을 확인한 뒤 재촬영해 주세요:

실패 이유: {{failure_reason}}

📋 좋은 영상 가이드:
- 전신이 화면에 들어오도록 촬영 (머리~발끝)
- 정면 또는 측면에서 촬영 (45° 이상 각도 지양)
- 스윙 전체 동작 포함 (어드레스~팔로우스루)
- 밝은 조명, 단색 배경 권장
```

---

## 프롬프트 실험 로그

| 버전 | 변경 내용 | 품질 점수 | 날짜 |
|------|-----------|-----------|------|
| v1 | 초안 | - | 2026-04-17 |
