# Python 3.11 slim 이미지 (최소 용량)
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY server.py file_extractor.py ./

# HTTP 포트 노출
# EXPOSE 8000

# MCP 서버 실행
CMD ["python", "server.py"]
