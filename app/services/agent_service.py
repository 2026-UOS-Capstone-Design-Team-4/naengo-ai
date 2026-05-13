import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from pydantic_ai.messages import ImageUrl, ModelMessage
from sqlalchemy.orm import Session

from app.agents.dependencies import RecipeDeps
from app.agents.intent_classifier import intent_classifier
from app.agents.recipe_agent import cooking_agent, recipe_agent
from app.agents.search_planner import recipe_search_planner
from app.core import config
from app.models.user import UserProfile
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

_OFF_TOPIC_MESSAGE = "저는 요리와 식재료에 관한 질문만 도와드릴 수 있어요. 냉장고 재료나 요리 관련 질문을 해주세요!"
_IDENTITY_MESSAGE = "저는 냉고예요! 냉장고 속 재료로 레시피를 추천해드리는 요리 전문가랍니다. 어떤 재료가 있으신가요?"
_SMALLTALK_MESSAGE = "안녕하세요! 오늘은 어떤 재료로 요리하실 건가요? 재료를 알려주시면 맛있는 레시피를 추천해드릴게요!"
_CLARIFY_MESSAGE = "조금 더 구체적으로 말씀해 주시면 더 잘 도와드릴 수 있어요! 어떤 재료가 있으신가요? 아니면 어떤 종류의 요리를 원하세요?"

_RECIPE_INTENTS = {
    "RECIPE_RECOMMENDATION",
    "DIET_OR_ALLERGY",
    "IMAGE_BASED_RECIPE",
    "PROFILE_UPDATE",
}

_COOKING_INTENTS = {
    "COOKING_TIP",
    "INGREDIENT_SUBSTITUTION",
    "RECIPE_DETAIL_QUESTION",
}

_LOW_CONFIDENCE_THRESHOLD = 0.5


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_user_profile_context(db: Session, user_id: int) -> str | None:
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        return None

    parts = []
    if profile.allergies:
        parts.append(f"알레르기: {', '.join(profile.allergies)}")
    if profile.disliked_ingredients:
        parts.append(f"싫어하는 재료: {', '.join(profile.disliked_ingredients)}")
    if profile.preferred_ingredients:
        parts.append(f"좋아하는 재료: {', '.join(profile.preferred_ingredients)}")
    if profile.dietary_restrictions:
        parts.append(f"식이 제한: {', '.join(profile.dietary_restrictions)}")
    if profile.taste_keywords:
        parts.append(f"선호 맛: {', '.join(profile.taste_keywords)}")
    if profile.cooking_skill:
        skill_map = {"easy": "초급", "normal": "중급", "hard": "고급"}
        parts.append(f"요리 수준: {skill_map.get(profile.cooking_skill, profile.cooking_skill)}")
    if profile.preferred_cooking_time_minutes:
        parts.append(f"선호 조리 시간: {profile.preferred_cooking_time_minutes}분 이내")

    return "\n".join(parts) if parts else None


async def _run_agent_to_queue(
    queue: asyncio.Queue,
    agent: Any,
    user_prompt: Any,
    history: list[ModelMessage],
    deps: RecipeDeps,
) -> None:
    """Run agent.run_stream in an isolated asyncio task to avoid anyio cancel-scope/yield conflicts."""
    try:
        async with agent.run_stream(user_prompt, message_history=history, deps=deps) as result:
            async for chunk in result.stream_text(delta=True):
                await queue.put(("text", chunk))
        await queue.put(("done", None))
    except Exception as exc:
        await queue.put(("error", exc))


class AgentService:
    async def stream(
        self,
        prompt: str,
        image: str | None,
        room_id: int,
        history: list[ModelMessage],
        user_id: int,
        chat_service: ChatService,
        db: Session,
    ) -> AsyncGenerator[str, None]:
        return self._stream(prompt, image, room_id, history, user_id, chat_service, db)

    async def _stream(
        self,
        prompt: str,
        image: str | None,
        room_id: int,
        history: list[ModelMessage],
        user_id: int,
        chat_service: ChatService,
        db: Session,
    ) -> AsyncGenerator[str, None]:
        # 1. Intent 분류
        try:
            intent = await intent_classifier.classify(prompt, history)
        except Exception as exc:
            logger.error("Intent 분류 실패: %s", exc)
            intent_type = "RECIPE_RECOMMENDATION"
            confidence = 1.0
        else:
            intent_type = intent.intent_type
            confidence = intent.confidence

        yield _sse("metadata", {"intent_type": intent_type, "model": config.MODEL_NAME})

        # 2. 단순 라우트 (agent 미호출)
        if intent_type == "OFF_TOPIC":
            yield _sse("message", {"content": _OFF_TOPIC_MESSAGE})
            msg_id = chat_service.save_messages(room_id, prompt, _OFF_TOPIC_MESSAGE)
            yield _sse("done", {"message_id": msg_id, "recipe_ids": []})
            return

        if intent_type == "IDENTITY_OR_HELP":
            yield _sse("message", {"content": _IDENTITY_MESSAGE})
            msg_id = chat_service.save_messages(room_id, prompt, _IDENTITY_MESSAGE)
            yield _sse("done", {"message_id": msg_id, "recipe_ids": []})
            return

        if intent_type == "SMALLTALK":
            yield _sse("message", {"content": _SMALLTALK_MESSAGE})
            msg_id = chat_service.save_messages(room_id, prompt, _SMALLTALK_MESSAGE)
            yield _sse("done", {"message_id": msg_id, "recipe_ids": []})
            return

        # 3. 낮은 confidence → 명확화 질문 (레시피 추천 계열만)
        if intent_type in _RECIPE_INTENTS and confidence < _LOW_CONFIDENCE_THRESHOLD:
            yield _sse("message", {"content": _CLARIFY_MESSAGE})
            msg_id = chat_service.save_messages(room_id, prompt, _CLARIFY_MESSAGE)
            yield _sse("done", {"message_id": msg_id, "recipe_ids": []})
            return

        # 4. 요리 관련 라우트
        deps = RecipeDeps()
        user_prompt: Any = [prompt, ImageUrl(url=image)] if image else prompt

        # 레시피 추천 계열: 유저 프로필 + 검색 계획 생성
        if intent_type in _RECIPE_INTENTS:
            user_profile_context = _build_user_profile_context(db, user_id)
            try:
                plan = await recipe_search_planner.plan(
                    prompt, history, user_profile_context=user_profile_context
                )
                deps.search_plan = plan
                logger.info("검색 계획: %s", plan.query_text)
            except Exception as exc:
                logger.warning("검색 계획 생성 실패: %s", exc)

        # 5. Agent 선택
        agent = cooking_agent if intent_type in _COOKING_INTENTS else recipe_agent

        # 6. 별도 asyncio 태스크에서 agent 스트리밍
        # (anyio CancelScope는 yield 경계를 넘을 수 없으므로 Queue로 분리)
        queue: asyncio.Queue = asyncio.Queue()
        agent_task = asyncio.create_task(
            _run_agent_to_queue(queue, agent, user_prompt, history, deps)
        )

        ai_full = ""
        error_occurred = False
        try:
            while True:
                event_type, data = await queue.get()
                if event_type == "text":
                    ai_full += data
                    yield _sse("message", {"content": data})
                elif event_type == "done":
                    break
                elif event_type == "error":
                    logger.error("Agent 스트리밍 오류: %s", data)
                    yield _sse("error", {"code": "AGENT_ERROR", "message": str(data)})
                    error_occurred = True
                    break
        finally:
            if not agent_task.done():
                agent_task.cancel()

        if error_occurred:
            return

        # 7. 레시피 이벤트
        unique_recipes = list({r["id"]: r for r in deps.last_found_recipes}.values())
        recipe_ids = [r["id"] for r in unique_recipes]
        if unique_recipes:
            yield _sse("recipes", unique_recipes)

        # 8. 저장 → done
        msg_id = chat_service.save_messages(
            room_id, prompt, ai_full, recipe_ids or None
        )
        yield _sse("done", {"message_id": msg_id, "recipe_ids": recipe_ids})
