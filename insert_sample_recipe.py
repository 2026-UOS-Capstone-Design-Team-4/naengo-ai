import json
import os

from app.db.session import SessionLocal
from app.models.chat import ChatRoom, SessionLog  # noqa
from app.models.recipe import (
    Recipe,
    RecipeStats,  # noqa
)
from app.models.social import Like, Scrap  # noqa

# SQLAlchemy 관계 설정을 위해 모든 모델을 한 번씩 임포트합니다.
from app.models.user import User  # noqa

# 1. 파일 경로 설정
JSON_FILE_PATH = "recipe.json"


def import_recipes_from_json():
    # 파일 존재 확인
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ {JSON_FILE_PATH} 파일이 존재하지 않습니다.")
        return

    # 2. JSON 파일 읽기
    with open(JSON_FILE_PATH, encoding="utf-8") as f:
        try:
            recipes_list = json.load(f)
            if not isinstance(recipes_list, list):
                print("❌ JSON 파일은 배열([]) 형식이어야 합니다.")
                return
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 에러: {e}")
            return

    # 3. 데이터베이스 세션 생성
    db = SessionLocal()
    success_count = 0
    fail_count = 0

    print(f"🚀 {len(recipes_list)}개의 레시피를 임포트하기 시작합니다...")

    try:
        for data in recipes_list:
            try:
                # 4. Recipe 객체 생성 (기존 필드 매핑)
                # 데이터에 없는 필드는 기본값 None 또는 지정된 값을 사용합니다.
                new_recipe = Recipe(
                    title=data.get("title"),
                    description=data.get("description"),
                    ingredients_raw=data.get("ingredients_raw"),
                    ingredients=data.get("ingredients"),
                    instructions=data.get("instructions"),
                    image_url=data.get("image_url"),
                    video_url=data.get("video_url"),
                    source=data.get("source", "STANDARD"),
                    status=data.get("status", "APPROVED"),
                )

                # 5. DB에 추가
                db.add(new_recipe)
                success_count += 1
                print(f"  - [{success_count}] '{new_recipe.title}' 추가됨")

            except Exception as inner_e:
                print(
                    f"  - ❌ 레시피 추가 실패: {data.get('title', '제목 없음')} ({inner_e})"
                )
                fail_count += 1

        # 6. 최종 커밋
        db.commit()
        print("\n" + "=" * 30)
        print("✨ 임포트 완료!")
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {fail_count}개")
        print("=" * 30)

    except Exception as e:
        db.rollback()
        print(f"🚨 중대한 에러 발생 (롤백함): {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import_recipes_from_json()
