import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI

from app.core import config
from app.db.session import SessionLocal
from app.models.chat import ChatRoom, SessionLog  # noqa
from app.models.recipe import Recipe, RecipeStats  # noqa
from app.models.social import Like, Scrap  # noqa
from app.models.user import User  # noqa

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "recipe.json")

client = OpenAI(api_key=config.EMBEDDING_API_KEY)


def get_embedding(recipe: dict) -> list[float]:
    recipe_data = {
        "title": recipe.get("title", ""),
        "description": recipe.get("description", ""),
        "ingredients_raw": recipe.get("ingredients_raw", ""),
        "ingredients": recipe.get("ingredients", []),
        "instructions": recipe.get("instructions", []),
    }
    json_text = json.dumps(recipe_data, ensure_ascii=False)
    response = client.embeddings.create(input=[json_text], model=config.EMBEDDING_MODEL)
    return response.data[0].embedding


def upsert_recipes():
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ {JSON_FILE_PATH} 파일이 존재하지 않습니다.")
        return

    with open(JSON_FILE_PATH, encoding="utf-8") as f:
        try:
            recipes_list = json.load(f)
            if not isinstance(recipes_list, list):
                print("❌ JSON 파일은 배열([]) 형식이어야 합니다.")
                return
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 에러: {e}")
            return

    db = SessionLocal()
    insert_count = 0
    skip_count = 0
    fail_count = 0

    print(f"🚀 {len(recipes_list)}개의 레시피 처리를 시작합니다...")

    try:
        # DB의 video_url을 한 번에 조회해서 set으로 만들기
        existing_urls: set[str] = {
            row[0] for row in db.query(Recipe.video_url).all() if row[0]
        }
        print(f"  📦 DB에 기존 레시피 {len(existing_urls)}개 확인됨")

        for data in recipes_list:
            video_url = data.get("video_url")
            title = data.get("title", "제목 없음")

            try:
                # video_url 중복 체크
                if video_url in existing_urls:
                    skip_count += 1
                    continue

                # 임베딩 생성
                print(f"  - 🔄 임베딩 생성 중: '{title}'")
                embedding = get_embedding(data)

                # DB 삽입
                new_recipe = Recipe(
                    title=title,
                    description=data.get("description"),
                    ingredients_raw=data.get("ingredients_raw"),
                    ingredients=data.get("ingredients"),
                    instructions=data.get("instructions"),
                    image_url=data.get("image_url"),
                    video_url=video_url,
                    source=data.get("source", "STANDARD"),
                    status=data.get("status", "APPROVED"),
                    embedding=embedding,
                )
                db.add(new_recipe)
                db.commit()
                existing_urls.add(video_url)

                insert_count += 1
                print(f"  - ✅ 추가 완료: '{title}'")

            except Exception as e:
                db.rollback()
                print(f"  - ❌ 실패: '{title}' ({e})")
                fail_count += 1

    except Exception as e:
        print(f"🚨 중대한 에러 발생: {e}")
    finally:
        db.close()

    print("\n" + "=" * 30)
    print("✨ 완료!")
    print(f"✅ 추가: {insert_count}개")
    print(f"⏭️  스킵: {skip_count}개")
    print(f"❌ 실패: {fail_count}개")
    print("=" * 30)


if __name__ == "__main__":
    upsert_recipes()
