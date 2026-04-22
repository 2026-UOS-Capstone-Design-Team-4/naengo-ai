import json
import os
import sys

# 상위 디렉토리를 sys.path에 추가하여 app 패키지를 찾을 수 있게 합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.chat import ChatRoom, SessionLog  # noqa
from app.models.recipe import Recipe, RecipeStats  # noqa
from app.models.social import Like, Scrap  # noqa
from app.models.user import User  # noqa

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEW_JSON_PATH = os.path.join(BASE_DIR, "new_recipe.json")
RECIPE_JSON_PATH = os.path.join(BASE_DIR, "recipe.json")


def insert_new_recipes():
    # 1. new_recipe.json 읽기
    if not os.path.exists(NEW_JSON_PATH):
        print(f"❌ {NEW_JSON_PATH} 파일이 존재하지 않습니다.")
        return

    with open(NEW_JSON_PATH, encoding="utf-8") as f:
        try:
            new_recipes = json.load(f)
            if not isinstance(new_recipes, list):
                print("❌ JSON 파일은 배열([]) 형식이어야 합니다.")
                return
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 에러: {e}")
            return

    if not new_recipes:
        print("⚠️  new_recipe.json에 레시피가 없습니다.")
        return

    print(f"🚀 {len(new_recipes)}개의 레시피를 임포트하기 시작합니다...")

    # 2. DB 세션 생성
    db = SessionLocal()
    success_count = 0
    skip_count = 0
    fail_count = 0
    inserted_recipes = []

    try:
        # 3. 기존 video_url 목록 조회
        existing_video_urls = {
            row[0]
            for row in db.query(Recipe.video_url).filter(Recipe.video_url.isnot(None)).all()
        }

        for data in new_recipes:
            try:
                video_url = data.get("video_url")

                # 4. video_url 중복 체크
                if video_url and video_url in existing_video_urls:
                    print(f"  - ⏭️  중복 건너뜀: '{data.get('title', '제목 없음')}' (video_url 이미 존재)")
                    skip_count += 1
                    continue

                new_recipe = Recipe(
                    title=data.get("title"),
                    description=data.get("description"),
                    ingredients_raw=data.get("ingredients_raw"),
                    ingredients=data.get("ingredients"),
                    instructions=data.get("instructions"),
                    image_url=data.get("image_url"),
                    video_url=video_url,
                    source=data.get("source", "STANDARD"),
                    status=data.get("status", "APPROVED"),
                )

                db.add(new_recipe)
                inserted_recipes.append(data)
                if video_url:
                    existing_video_urls.add(video_url)

                success_count += 1
                print(f"  - [{success_count}] '{new_recipe.title}' 추가됨")

            except Exception as inner_e:
                print(f"  - ❌ 레시피 추가 실패: {data.get('title', '제목 없음')} ({inner_e})")
                fail_count += 1

        db.commit()

        print("\n" + "=" * 30)
        print("✨ DB 임포트 완료!")
        print(f"✅ 성공: {success_count}개")
        print(f"⏭️  중복 스킵: {skip_count}개")
        print(f"❌ 실패: {fail_count}개")
        print("=" * 30)

    except Exception as e:
        db.rollback()
        print(f"🚨 중대한 에러 발생 (롤백함): {e}")
        return
    finally:
        db.close()

    # 5. 성공한 레시피를 recipe.json에 append
    if not inserted_recipes:
        print("\n⚠️  recipe.json에 추가할 레시피가 없습니다.")
        return

    with open(RECIPE_JSON_PATH, encoding="utf-8") as f:
        existing_recipes = json.load(f)

    existing_recipes.extend(inserted_recipes)

    with open(RECIPE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_recipes, f, ensure_ascii=False, indent=2)

    print(f"\n📄 recipe.json에 {len(inserted_recipes)}개 레시피 추가 완료!")
    print(f"   (총 {len(existing_recipes)}개 레시피)")

    # 6. new_recipe.json에서 삽입 성공한 레시피 제거
    remaining = [r for r in new_recipes if r not in inserted_recipes]
    with open(NEW_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(remaining, f, ensure_ascii=False, indent=2)

    print(f"🗑️  new_recipe.json에서 {len(inserted_recipes)}개 레시피 제거 완료!")
    print(f"   (남은 레시피: {len(remaining)}개)")


if __name__ == "__main__":
    insert_new_recipes()
