# requirements.txt 는 Python 3.13 환경에서 고정했다. 베이스 이미지가 다르면
# numpy·scipy 핀이 설치되지 않거나 다른 휠을 끌어오므로 버전을 맞춘다.
FROM python:3.13-slim

WORKDIR /app

# OpenCV·MediaPipe 가 요구하는 시스템 라이브러리와 한글 폰트.
#
# fonts-nanum 이 없으면 오버레이의 단계 라벨이 "3.탑" 대신 "3" 으로만 나온다.
# overlay.py 가 폰트를 못 찾을 때 깨진 글자 대신 숫자만 남기도록 해 뒀기 때문이다.
# AGENTS.md 의 "모든 사용자 노출 텍스트는 한국어" 규칙을 지키려면 필요하다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# 빌드 컨텍스트는 저장소 루트다(Railway 가 그렇게 넘긴다). 그래서 경로가
# backend/ 로 시작한다. 이 Dockerfile 이 backend/ 안에 있다고 해서 컨텍스트도
# 거기인 것은 아니다 — 그렇게 가정했다가 "requirements.txt: not found" 로 깨졌다.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Railway 등은 $PORT 를 주입한다. 없으면 8000 을 쓴다.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
