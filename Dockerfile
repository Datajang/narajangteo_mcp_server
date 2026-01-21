# Python 3.11 slim 이미지
FROM python:3.11-slim

# Python 출력 버퍼링 해제 (로그 즉시 출력)
ENV PYTHONUNBUFFERED=1

# 한글/UTF-8 강제 설정 (필수)
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (lxml 등 의존성)
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY server.py file_extractor.py ./

# MCP 서버 실행
CMD ["python", "server.py"]