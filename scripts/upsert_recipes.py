import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI

from app.core import config
from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa
from app.models.recipe import PendingRecipe, Recipe, RecipeStats  # noqa
from app.models.social import Like, Scrap  # noqa
from app.models.user import User, UserProfile  # noqa

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "recipe.json")

client = OpenAI(api_key=config.EMBEDDING_API_KEY)


def build_embedding_text(recipe: dict) -> str:
    difficulty_map = {"easy": "쉬움", "normal": "보통", "hard": "어려움"}

    title = recipe.get("title", "")
    description = recipe.get("description", "")
    ingredients_raw = recipe.get("ingredients_raw", "")
    servings = recipe.get("servings")
    cooking_time = recipe.get("cooking_time")
    difficulty = difficulty_map.get(recipe.get("difficulty", ""), "")
    category = recipe.get("category", [])
    tags = recipe.get("tags", [])
    tips = recipe.get("tips", [])

    parts = []
    if title:
        parts.append(f"{title} 레시피입니다.")
    if category:
        parts.append(f"카테고리: {', '.join(category)}.")
    if description:
        parts.append(description)
    if ingredients_raw:
        parts.append(f"주재료는 {ingredients_raw}입니다.")
    if servings:
        parts.append(f"{servings}인분 요리입니다.")
    if cooking_time:
        parts.append(f"조리 시간은 약 {cooking_time}분입니다.")
    if difficulty:
        parts.append(f"난이도는 {difficulty}입니다.")
    if tags:
        parts.append(f"태그: {', '.join(tags)}.")
    if tips:
        parts.append(f"조리 팁: {' '.join(tips)}")

    print(f"🔍 임베딩 텍스트 생성:\n{' '.join(parts)}\n")
    return " ".join(parts)


def get_embedding(recipe: dict) -> list[float]:
    text = build_embedding_text(recipe)
    response = client.embeddings.create(input=[text], model=config.EMBEDDING_MODEL)
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

    # JSON 내 video_url 중복 체크
    url_counts: dict[str, int] = {}
    for data in recipes_list:
        url = data.get("video_url")
        if url:
            url_counts[url] = url_counts.get(url, 0) + 1
    duplicates = {url: cnt for url, cnt in url_counts.items() if cnt > 1}
    if duplicates:
        print(f"⚠️  JSON 내 중복 video_url {len(duplicates)}개 발견:")
        for url, cnt in duplicates.items():
            print(f"   - {url} ({cnt}회)")

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
                    ingredients=data.get("ingredients"),
                    ingredients_raw=data.get("ingredients_raw"),
                    instructions=data.get("instructions"),
                    servings=data.get("servings"),
                    cooking_time=data.get("cooking_time"),
                    calories=data.get("calories"),
                    difficulty=data.get("difficulty"),
                    category=data.get("category"),
                    tags=data.get("tags", []),
                    tips=data.get("tips", []),
                    content=data.get("content"),
                    video_url=video_url,
                    image_url=data.get("image_url"),
                    author_type="ADMIN",
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
