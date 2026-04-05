# 🧊 Naengo AI (냉고 AI)

**냉장고 파먹기의 종결자!** 사용자의 남은 식재료를 분석하여 최적의 레시피를 추천해주는 PydanticAI 기반의 FastAPI 서버입니다.

## 🚀 주요 기능

- **AI 레시피 추천**: PydanticAI를 활용한 지능형 레시피 생성 및 추천
- **실시간 스트리밍 대화**: `StreamingResponse`를 통한 끊김 없는 AI 채팅 경험
- **대화 맥락 유지**: 과거 대화 내역(History)을 기억하여 문맥에 맞는 답변 제공
- **데이터베이스 연동**: 유저별 선호도, 스크랩, 좋아요 및 채팅 로그 관리 (PostgreSQL + pgvector)
- **현대적인 문서화**: Scalar를 활용한 현대적이고 직관적인 API 레퍼런스 제공

## 🛠 기술 스택

- **Backend**: FastAPI, PydanticAI
- **Database**: PostgreSQL (with pgvector for AI Vector Search)
- **Package Manager**: [uv](https://docs.astral.sh/uv/) (Rust 기반의 초고속 파이썬 도구)
- **Infrastructure**: Docker, Docker Compose
- **Linting/Formatting**: Ruff

## 💻 시작하기 (로컬 개발 환경)

이 프로젝트는 `uv`를 사용합니다. 먼저 `uv`가 설치되어 있어야 합니다.

### 1. uv 설치

이 프로젝트는 `uv`를 사용합니다. 먼저 파이썬이 설치되어 있어야 합니다.

1. **파이썬 설치**: [python.org](https://www.python.org/)에서 최신 버전(3.13 이상 권장)을 설치하세요.
2. **uv 설치**: 터미널(또는 PowerShell)에서 다음 명령어를 입력하세요.
   ```bash
   pip install uv
   ```

설치 후 `uv --version` 명령어로 설치가 잘 되었는지 확인하세요.

### 2. 의존성 설치
```bash
# 가상환경 생성 및 라이브러리 설치 (1초 만에 완료!)
uv sync
```

### 2. 환경 변수 설정
`.env` 파일을 생성하고 필요한 API 키를 입력하세요.
```bash
OPENAI_API_KEY=your_api_key_here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recipe_db
```

### 3. 서버 실행 (Docker 권장 🐳)
DB 서버와 API 서버를 한 번에 실행하려면 Docker Compose를 사용하세요.
```bash
# DB + API 서버 동시 실행
docker-compose up -d

# 실시간 로그 확인
docker-compose logs -f
```

### 4. 서버 실행 (로컬 - 선택 사항)
로컬 DB가 실행 중인 경우 uvicorn을 직접 실행할 수 있습니다.
```bash
uv run uvicorn app.main:app --reload
```

## 📖 API 문서 확인

서버가 실행되면 다음 주소에서 인터랙티브한 API 문서를 확인할 수 있습니다.
- **Scalar UI**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📁 프로젝트 구조

```text
naengo-ai/
├── app/
│   ├── agents/          # AI 에이전트 및 프롬프트 로직
│   ├── api/             # API 엔드포인트 (v1)
│   ├── core/            # 공통 설정 (config)
│   ├── db/              # 데이터베이스 세션 및 초기화
│   ├── models/          # SQLAlchemy DB 모델
│   └── schemas/         # Pydantic 데이터 검증 스키마
├── tests/               # 테스트 코드
├── Dockerfile           # uv 기반 최적화 빌드 설정
├── docker-compose.yml   # DB + API 오케스트레이션
└── pyproject.toml       # 프로젝트 의존성 및 Ruff 설정
```

## 🎨 개발 규칙

- **Linting & Formatting**: 파일을 저장할 때마다 `Ruff`가 자동으로 코드를 정리합니다.
- **Commit**: 가급적 기능 단위로 커밋하며, `uv.lock` 파일도 함께 커밋해 주세요.
