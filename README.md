# 🧊 Naengo AI (냉고 AI)

**냉장고 속 재료로 오늘의 요리를 완성하세요!** 사용자의 남은 식재료를 분석하여 최적의 레시피를 추천해주는 PydanticAI 기반의 FastAPI 서버입니다.

## 🚀 주요 기능

- **AI 레시피 추천**: PydanticAI + 벡터 유사도 검색(pgvector)을 활용한 레시피 추천
- **실시간 스트리밍 대화**: `StreamingResponse`를 통한 끊김 없는 AI 채팅 경험
- **대화 맥락 유지**: 과거 대화 내역(History)을 기억하여 문맥에 맞는 답변 제공
- **레시피 목록 조회**: 최신순/좋아요순 커서 기반 페이지네이션
- **북마크**: 스크랩한 레시피 목록 조회
- **유저 프로필 관리**: 사용자 정보 조회/수정, 취향·알레르기 정보(`user_input`) 관리
- **레시피 제출**: 사용자가 직접 레시피를 작성해 제출, 관리자 검토 후 승인
- **데이터베이스 연동**: 유저별 선호도, 스크랩, 좋아요 및 채팅 로그 관리 (PostgreSQL + pgvector)
- **현대적인 문서화**: Scalar를 활용한 직관적인 API 레퍼런스 제공

## 🛠 기술 스택

- **Backend**: FastAPI, PydanticAI
- **Database**: PostgreSQL (with pgvector for AI Vector Search)
- **Package Manager**: [uv](https://docs.astral.sh/uv/) (Rust 기반의 초고속 파이썬 도구)
- **Infrastructure**: Docker, AWS EC2, AWS RDS
- **CI/CD**: GitHub Actions
- **Linting/Formatting**: Ruff

## 💻 시작하기 (로컬 개발 환경)

### 1. uv 설치

1. **파이썬 설치**: [python.org](https://www.python.org/)에서 Python 3.13 이상을 설치하세요.
2. **uv 설치**:
   ```bash
   pip install uv
   ```
3. 설치 확인:
   ```bash
   uv --version
   ```

### 2. 의존성 설치

```bash
uv sync
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 아래 내용을 입력하세요.

```env
API_KEY=your_api_key                        # MindLogic Gateway API 키
EMBEDDING_API_KEY=your_openai_api_key       # OpenAI API 키 (임베딩용)
EMBEDDING_MODEL=text-embedding-3-small      # 임베딩 모델명
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/naengo_db
BASE_URL=https://factchat-cloud.mindlogic.ai/v1/gateway
MODEL_NAME=gpt-5.3-chat-latest
```

### 4. 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

## 🐳 Docker로 실행 (로컬)

로컬에서 Docker로 실행할 경우 별도의 PostgreSQL + pgvector 환경이 필요합니다.

```bash
# 빌드 및 실행
docker-compose up -d --build

# 실시간 로그 확인
docker-compose logs -f

# 서비스 종료
docker-compose down
```

## 📖 API 문서

서버 실행 후 아래 주소에서 API 문서를 확인할 수 있습니다.

- **Scalar UI**: [http://localhost:8000/docs](http://localhost:8000/docs)

## ☁️ 배포

AWS EC2 + RDS 환경에서 Docker로 운영 중이며, `main` 브랜치에 push하면 GitHub Actions를 통해 EC2에 자동 배포됩니다.

## 📁 프로젝트 구조

```text
naengo-ai/
├── app/
│   ├── agents/              # AI 에이전트, 의존성, 시스템 프롬프트
│   ├── api/v1/
│   │   ├── endpoints/       # chat, recipes, users, pending-recipes
│   │   │   └── admin/       # 관리자 전용 엔드포인트
│   │   ├── docs/            # Scalar UI 문서 (summary, description, examples)
│   │   └── deps.py          # 공통 의존성
│   ├── core/                # 공통 설정 (config)
│   ├── db/                  # 데이터베이스 세션 및 초기화
│   ├── models/              # SQLAlchemy DB 모델
│   ├── schemas/             # Pydantic 데이터 검증 스키마
│   └── services/            # 비즈니스 로직 및 AI 검색 서비스
├── scripts/                 # DB 데이터 삽입 스크립트
├── tests/                   # 테스트 코드
├── .github/workflows/       # GitHub Actions CI/CD
├── architecture.md          # 시스템 아키텍처 문서
├── Dockerfile               # uv 기반 최적화 빌드 설정
├── docker-compose.yml       # API 서버 오케스트레이션
└── pyproject.toml           # 프로젝트 의존성 및 Ruff 설정
```

## 🎨 개발 규칙

- **Linting & Formatting**: `Ruff`로 lint 및 format을 관리합니다. 저장 시 자동 정리되도록 에디터를 설정하세요.
- **Commit**: 기능 단위로 커밋하며, `uv.lock` 파일도 함께 커밋해 주세요.
