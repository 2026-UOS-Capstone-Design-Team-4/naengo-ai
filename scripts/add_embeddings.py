import json
import os
import sys

# 상위 디렉토리를 sys.path에 추가하여 app 패키지를 찾을 수 있게 합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI

from app.core import config
from app.db.session import SessionLocal
from app.models.chat import ChatRoom, SessionLog  # noqa
from app.models.recipe import (
    Recipe,
    RecipeStats,  # noqa
)
from app.models.social import Like, Scrap  # noqa

# SQLAlchemy 관계 설정을 위해 모든 모델을 한 번씩 임포트합니다.
from app.models.user import User  # noqa

# 1. OpenAI 클라이언트 설정
# .env의 EMBEDDING_API_KEY를 사용하며, 기본 OpenAI API 주소를 사용합니다.
client = OpenAI(api_key=config.EMBEDDING_API_KEY)

# 1536 차원의 text-embedding-3-small 모델 사용
EMBEDDING_MODEL = "text-embedding-3-small"


def get_embedding(text: str):
    """텍스트(JSON 문자열)를 벡터로 변환 (OpenAI API 호출)"""
    response = client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
    return response.data[0].embedding


def update_missing_embeddings():
    db = SessionLocal()
    success_count = 0
    fail_count = 0

    try:
        # 2. embedding이 없는 레시피 조회
        recipes_to_update = db.query(Recipe).filter(Recipe.embedding == None).all()

        if not recipes_to_update:
            print("✅ 임베딩이 비어 있는 레시피가 없습니다.")
            return

        print(
            f"🚀 총 {len(recipes_to_update)}개의 레시피 임베딩 작업을 시작합니다 (JSON 방식)..."
        )

        for i, recipe in enumerate(recipes_to_update, 1):
            try:
                # 3. 임베딩할 텍스트 구성 (필드들을 딕셔너리로 묶고 JSON으로 변환)
                recipe_data = {
                    "title": recipe.title,
                    "description": recipe.description or "",
                    "ingredients_raw": recipe.ingredients_raw or "",
                    "ingredients": recipe.ingredients or [],
                    "instructions": recipe.instructions or [],
                }

                # JSON 문자열로 변환 (ensure_ascii=False로 한글 보존)
                json_text = json.dumps(recipe_data, ensure_ascii=False)

                # 4. 임베딩 생성 및 저장
                vector = get_embedding(json_text)
                recipe.embedding = vector

                success_count += 1
                print(
                    f"  - [{i}/{len(recipes_to_update)}] '{recipe.title}' 임베딩 완료"
                )

                # 각 작업 성공 시 실시간 커밋
                db.commit()

            except Exception as inner_e:
                print(f"  - ❌ '{recipe.title}' 임베딩 실패: {inner_e}")
                db.rollback()
                fail_count += 1

        # 5. 최종 결과 출력
        print("\n" + "=" * 30)
        print("✨ 모든 임베딩 업데이트 작업이 끝났습니다!")
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {fail_count}개")
        print("=" * 30)

    except Exception as e:
        print(f"🚨 중대한 에러 발생: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    update_missing_embeddings()
