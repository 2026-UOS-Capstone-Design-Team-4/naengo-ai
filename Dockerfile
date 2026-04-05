# 1. Base Image: 파이썬 3.13 슬림 버전 사용
FROM python:3.13-slim

# 2. 환경 변수 설정
# 바이트코드 생성을 억제하고 로그 출력을 즉시 터미널로 보냅니다.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 시스템 의존성 설치 (psycopg2 등을 위해 필요한 빌드 도구)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. uv 설치 (가장 빠르고 현대적인 파이썬 패키지 관리자)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 6. 의존성 파일 복사 및 설치
# 소스 코드가 바뀌어도 라이브러리 설치 단계는 캐시되어 매우 빠릅니다.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 7. 소스 코드 복사 및 프로젝트 설치
COPY . .
RUN uv sync --frozen --no-dev

# 8. 포트 개방
EXPOSE 8000

# 9. 애플리케이션 실행 (uv run을 통해 정확한 환경에서 실행)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
