from pgvector.psycopg2 import register_vector
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.core import config


def _on_connect(dbapi_conn, _connection_record):
    register_vector(dbapi_conn)


# 1. 엔진 생성
engine = create_engine(config.DATABASE_URL)
event.listen(engine, "connect", _on_connect)

# 2. 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 3. DB 세션 가져오기 (Dependency)
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# 4. 초기화 함수 (pgvector 확장 활성화 등)
def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
