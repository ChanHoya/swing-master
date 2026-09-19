# 플랫폼과 파이썬 버전을 둘 다 고정한다. 여기서 두 번 깨졌다.
#
# 1) --platform=linux/amd64 — Render 는 linux/amd64 이미지만 받는다(공식 문서).
#    mediapipe 0.10.33 의 리눅스 휠은 manylinux_2_28_x86_64 하나뿐이라
#    arm64 맥에서 그냥 `docker build` 하면 pip 이 1.0.x 밖에 못 봐서
#    "Could not find a version that satisfies mediapipe==0.10.33" 로 깨진다.
#    맥에서는 에뮬레이션이라 느리지만, 깨지는 것보다 낫다.
#
# 2) python:3.12-slim — numpy 1.26.4 는 cp313 휠을 내지 않는다(cp39~cp312 까지).
#    3.13 에서는 pip 이 소스 빌드로 넘어가고 slim 에는 컴파일러가 없어 실패한다.
#    로컬 맥의 .venv 에 3.13+numpy 1.26.4 가 있는 것은 clang 으로 직접
#    컴파일됐기 때문이고, 그 상태를 pip freeze 한 것이 requirements.txt 다.
#    3.12 로 내리면 나머지 핀은 하나도 바꾸지 않고 전부 휠로 설치된다.
FROM --platform=linux/amd64 python:3.12-slim

WORKDIR /app

# OpenCV·MediaPipe 가 요구하는 시스템 라이브러리와 한글 폰트.
#
# fonts-nanum 이 없으면 오버레이의 단계 라벨이 "3.탑" 대신 "3" 으로만 나온다.
# overlay.py 가 폰트를 못 찾을 때 깨진 글자 대신 숫자만 남기도록 해 뒀기 때문이다.
# AGENTS.md 의 "모든 사용자 노출 텍스트는 한국어" 규칙을 지키려면 필요하다.
# libegl1·libgles2 는 MediaPipe 가 요구한다. 없으면 import 는 되지만
# PoseLandmarker.create_from_options() 에서 네이티브 바인딩을 dlopen 할 때
# "libGLESv2.so.2: cannot open shared object file" 로 죽는다. 즉 앱은 정상
# 기동하고 /health 도 통과한 뒤, 첫 분석에서만 실패한다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libegl1 libgles2 libglib2.0-0 libgomp1 fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

# 빌드 컨텍스트는 저장소 루트다(Railway 가 그렇게 넘긴다). 그래서 경로가
# backend/ 로 시작한다. 이 Dockerfile 이 backend/ 안에 있다고 해서 컨텍스트도
# 거기인 것은 아니다 — 그렇게 가정했다가 "requirements.txt: not found" 로 깨졌다.
COPY backend/requirements.txt .

# mediapipe 는 opencv-contrib-python 을 의존성으로 선언한다. 그래서
# requirements.txt 에 headless 만 적어도 contrib 가 함께 깔리고, 둘은 같은
# cv2/ 디렉터리를 공유해 나중에 설치된 쪽이 이긴다. 실측에서 contrib(QT5 GUI
# 링크 빌드)가 이겼고, 분석이 libGLESv2.so.2 를 못 찾아 실패했다.
#
# 서버에는 화면이 없다. 둘 다 지우고 headless 만 다시 깔아 확실히 headless 가
# 남게 한다. mediapipe 의 의존성 메타데이터는 충족되지 않은 것으로 남지만,
# 런타임에 필요한 것은 import 가능한 cv2 뿐이다.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y opencv-contrib-python opencv-python-headless \
    && pip install --no-cache-dir opencv-python-headless==4.11.0.86

COPY backend/ .

# print() 가 컨테이너에서 블록 버퍼링되면 [Vision] 진행 로그가 늦거나
# 유실된다. 배포 후 문제를 진단할 방법이 사라지므로 버퍼링을 끈다.
ENV PYTHONUNBUFFERED=1

# Render 등은 $PORT 를 주입한다. 없으면 8000 을 쓴다.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
