import asyncio
import base64
import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from pydantic_ai.messages import ImageUrl, ModelMessage
from sqlalchemy.orm import Session

from app.agents.core.dependencies import RecipeDeps
from app.agents.core.stream_events import stream_event_builder
from app.agents.core.system_prompts import PROFILE_UPDATE_EMPTY_MESSAGE
from app.agents.core.user_context import user_context_builder
from app.agents.intent.intent_agent_router import AgentRoute, intent_agent_router
from app.agents.intent.intent_classifier import intent_classifier
from app.agents.recipe.recipe_agent import cooking_agent, recipe_agent
from app.agents.recipe.search_planner import recipe_search_planner
from app.agents.responders.smalltalk import smalltalk_responder
from app.core import config
from app.models.user import UserProfile
from app.services.chat_service import ChatService
from app.services.live_research_service import live_research_service
from app.services.profile_update_service import (
    ProfileUpdateAction,
    UserProfileService,
    profile_update_extractor,
    profile_update_policy,
)
from app.services.recipe_retrieval_service import recipe_retrieval_service
from app.services.storage_service import chat_image_storage

logger = logging.getLogger(__name__)

_DATA_URL_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL)


def _upload_image(image: str, room_id: int) -> tuple[str, str | None]:
    """Return (image_ref_for_llm, stored_url_or_none).

    Tries to upload the base64 data URL to persistent storage. Falls back to
    passing the original data URL if upload fails or storage is passthrough.
    """
    m = _DATA_URL_RE.match(image)
    if not m:
        return image, None

    content_type = m.group(1)
    raw = base64.b64decode(m.group(2))
    ext = content_type.split("/")[-1].split("+")[0]
    key = f"chat/{room_id}/{uuid4()}.{ext}"

    try:
        stored_url = chat_image_storage.upload_bytes(raw, key, content_type)
    except Exception as exc:
        logger.warning("채팅 이미지 업로드 실패: %s", exc)
        stored_url = None

    return image, stored_url


async def _run_agent_to_queue(
    queue: asyncio.Queue,
    agent: Any,
    user_prompt: Any,
    history: list[ModelMessage],
    deps: RecipeDeps,
) -> None:
    """Run agent streaming in a task to avoid anyio cancel-scope/yield conflicts."""
    try:
        async with agent.run_stream(
            user_prompt,
            message_history=history,
            deps=deps,
        ) as result:
            async for chunk in result.stream_text(delta=True):
                await queue.put(("text", chunk))
        await queue.put(("done", None))
    except Exception as exc:
        await queue.put(("error", exc))


def _append_live_research_context(prompt: str, answer_context: str | None) -> str:
    if not answer_context:
        return prompt
    return f"{prompt}\n\n[{answer_context}]"


def _append_recipe_context(prompt: str, recipes: list[dict]) -> str:
    if not recipes:
        return prompt
    lines = ["RAG recipe candidates:"]
    for index, recipe in enumerate(recipes, start=1):
        title = recipe.get("title") or "제목 없음"
        description = recipe.get("description") or ""
        ingredients = recipe.get("ingredients_raw") or ""
        cooking_time = recipe.get("cooking_time_minutes")
        difficulty = recipe.get("difficulty")
        categories = ", ".join(recipe.get("category") or [])
        lines.append(
            "\n".join(
                part
                for part in [
                    f"{index}. {title}",
                    f"   description: {description}" if description else "",
                    f"   ingredients: {ingredients}" if ingredients else "",
                    f"   time: {cooking_time} minutes" if cooking_time else "",
                    f"   difficulty: {difficulty}" if difficulty else "",
                    f"   categories: {categories}" if categories else "",
                ]
                if part
            )
        )
    return f"{prompt}\n\n[{chr(10).join(lines)}]"


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
    ) -> AsyncGenerator[str]:
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
    ) -> AsyncGenerator[str]:
        # 0. 이미지 업로드 (있을 경우)
        image_ref = image
        stored_image_url: str | None = None
        if image:
            image_ref, stored_image_url = _upload_image(image, room_id)

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

        live_result = None
        if live_research_service.should_research(intent_type, prompt):
            try:
                query = live_research_service.build_query(prompt, intent_type)
                live_result = live_research_service.research(query)
            except Exception as exc:
                logger.warning("Live research 실패: %s", exc)

        yield stream_event_builder.metadata(
            intent_type,
            config.MODEL_NAME,
            extra={
                "used_live_research": bool(
                    live_result and live_result.used_live_research
                ),
                "source_count": len(live_result.evidence) if live_result else 0,
            },
        )

        # 2. 단순 라우트(agent 미호출)
        route_decision = intent_agent_router.decide(intent_type, confidence)
        if route_decision.route == AgentRoute.FIXED_RESPONSE:
            message = (
                smalltalk_responder.respond(prompt)
                if route_decision.use_smalltalk_responder
                else route_decision.message or ""
            )
            yield stream_event_builder.message(message)
            msg_id = chat_service.save_messages(
                room_id, prompt, message, image_url=stored_image_url
            )
            yield stream_event_builder.done(msg_id, [])
            return

        if route_decision.route == AgentRoute.PROFILE_UPDATE:
            profile = db.query(UserProfile).filter_by(user_id=user_id).first()
            candidates = profile_update_extractor.extract(prompt)
            decision = profile_update_policy.decide(candidates, profile)

            if decision.action == ProfileUpdateAction.AUTO_SAVE:
                UserProfileService(db).apply_candidates(user_id, decision.candidates)

            if decision.action != ProfileUpdateAction.IGNORE:
                yield stream_event_builder.profile_update(decision.to_event_payload())

            message = decision.message or PROFILE_UPDATE_EMPTY_MESSAGE
            yield stream_event_builder.message(message)
            msg_id = chat_service.save_messages(
                room_id, prompt, message, image_url=stored_image_url
            )
            yield stream_event_builder.done(msg_id, [])
            return

        # 4. 요리 관련 라우트
        deps = RecipeDeps()
        effective_prompt = _append_live_research_context(
            prompt,
            live_result.answer_context if live_result else None,
        )
        user_prompt: Any = (
            [effective_prompt, ImageUrl(url=image_ref)]
            if image_ref
            else effective_prompt
        )

        # 레시피 추천 계열: 사용자 프로필과 검색 계획을 함께 사용한다.
        if route_decision.should_plan_retrieval:
            user_profile_context = user_context_builder.build_profile_context(
                db,
                user_id,
            )
            try:
                plan = await recipe_search_planner.plan(
                    prompt, history, user_profile_context=user_profile_context
                )
                deps.search_plan = plan
                logger.info(
                    "검색 계획: %s",
                    json.dumps(
                        plan.model_dump(),
                        ensure_ascii=False,
                        default=str,
                    ),
                )
            except Exception as exc:
                logger.warning("검색 계획 생성 실패: %s", exc)

            search_query = deps.search_plan.query_text if deps.search_plan else prompt
            try:
                recipes = recipe_retrieval_service.search_recipes(
                    search_query,
                    limit=3,
                    plan=deps.search_plan,
                )
                deps.last_found_recipes = [
                    recipe_retrieval_service.recipe_to_payload(recipe)
                    for recipe in recipes
                ]
                effective_prompt = _append_recipe_context(
                    effective_prompt,
                    deps.last_found_recipes,
                )
                user_prompt = (
                    [effective_prompt, ImageUrl(url=image_ref)]
                    if image_ref
                    else effective_prompt
                )
                logger.info("RAG 사전 검색 결과: %d개", len(deps.last_found_recipes))
            except Exception as exc:
                logger.warning("RAG 사전 검색 실패: %s", exc)

        # 5. Agent 선택
        agent = (
            cooking_agent
            if route_decision.route == AgentRoute.COOKING_AGENT
            else recipe_agent
        )

        # 6. 별도 asyncio 태스크에서 agent 스트리밍
        # anyio CancelScope는 yield 경계를 넘을 수 없으므로 Queue로 분리한다.
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
                    yield stream_event_builder.message(data)
                elif event_type == "done":
                    break
                elif event_type == "error":
                    logger.error("Agent 스트리밍 오류: %s", data)
                    yield stream_event_builder.error("AGENT_ERROR", str(data))
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
            yield stream_event_builder.recipes(unique_recipes)

        # 8. 저장 후 done 이벤트
        msg_id = chat_service.save_messages(
            room_id, prompt, ai_full, recipe_ids or None, image_url=stored_image_url
        )
        yield stream_event_builder.done(msg_id, recipe_ids)
