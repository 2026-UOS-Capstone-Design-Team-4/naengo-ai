import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recipe import Recipe

logger = logging.getLogger(__name__)


def search_recipes_by_vector(
    db: Session, query_vector: list[float], limit: int = 5
) -> list[Recipe]:
    """
    벡터 유사도 검색(Cosine Distance)을 통해 유사한 레시피를 찾습니다.
    """
    # pgvector-sqlalchemy는 리스트를 직접 전달받아 처리하는 것이 더 안정적입니다.

    # 코사인 거리가 가장 가까운(유사도가 높은) 레시피 검색
    query = (
        select(Recipe)
        .order_by(Recipe.embedding.cosine_distance(query_vector))
        .limit(limit)
    )

    logger.info(f"🔍 [DB Search] 벡터 유사도 검색 시작 (Limit: {limit})")

    try:
        result = db.execute(query)
        recipes = result.scalars().all()
        logger.info(
            f"✅ [DB Search] 검색 완료: {len(recipes)}개의 레시피를 찾았습니다."
        )
        return recipes
    except Exception as e:
        logger.error(f"❌ [DB Search] 검색 중 에러 발생: {str(e)}")
        raise e
