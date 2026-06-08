import asyncio
import base64
import json
import logging
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic_ai.messages import BinaryContent, ImageUrl, ModelMessage
from sqlalchemy.orm import Session

from app.agents.cooking_qa.planner import cooking_qa_planner
from app.agents.core.conversation_state import ConversationState
from app.agents.core.dependencies import RecipeDeps
from app.agents.core.memory import AgentMemory
from app.agents.core.run_context import AgentRunContext
from app.agents.core.stream_events import stream_event_builder
from app.agents.core.system_prompts import (
    CLARIFY_MESSAGE,
    IDENTITY_MESSAGE,
    OFF_TOPIC_MESSAGE,
    PROFILE_MANAGEMENT_EMPTY_MESSAGE,
)
from app.agents.core.user_context import user_context_builder
from app.agents.intent.answer_router import domain_answer_router
from app.agents.intent.intent_models import (
    AnswerStrategy,
    MainIntentResult,
    PrimaryTask,
    RecipeFindSubIntent,
)
from app.agents.intent.main_intent_classifier import main_intent_classifier
from app.agents.recipe.recipe_agent import cooking_agent, recipe_agent
from app.agents.recipe.search_planner import SearchPlan, recipe_search_planner
from app.api.errors import ApiError
from app.core import config
from app.models.social import Like, Scrap
from app.models.user import UserProfile
from app.services.agent_answer_verifier import answer_verifier
from app.services.agent_context_resolver import agent_context_resolver
from app.services.chat_service import ChatService
from app.services.conversation_state_service import conversation_state_resolver
from app.services.live_research_service import live_research_service
from app.services.profile_update_service import (
    ProfileUpdateAction,
    ProfileUpdateDecision,
    UserProfileService,
    profile_update_analyzer,
)
from app.services.recipe_retrieval_service import recipe_retrieval_service
from app.services.retrieval_orchestrator import RetrievalOrchestrator
from app.services.storage_service import chat_image_storage

logger = logging.getLogger(__name__)

_DATA_URL_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL)


def _to_image_content(image: str) -> BinaryContent | ImageUrl:
    m = _DATA_URL_RE.match(image)
    if m:
        return BinaryContent(data=base64.b64decode(m.group(2)), media_type=m.group(1))
    return ImageUrl(url=image)


@dataclass(frozen=True)
class _StreamExecutionConfig:
    prompt: str
    image: str | None
    history: list[ModelMessage]
    room_id: int | None = None
    user_id: int | None = None
    chat_service: ChatService | None = None
    db: Session | None = None
    persist: bool = False


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
        ingredients = _ingredients_text(recipe)
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


def _ingredients_text(recipe: dict) -> str:
    ingredients = recipe.get("ingredients")
    if not isinstance(ingredients, list):
        return ""

    values: list[str] = []
    for item in ingredients:
        if isinstance(item, dict):
            text = " ".join(
                str(part)
                for part in [item.get("name"), item.get("amount_text")]
                if part
            ).strip()
        else:
            text = str(item).strip()
        if text:
            values.append(text)
    return ", ".join(values)


def _append_evidence_pack_context(prompt: str, evidence_pack: Any | None) -> str:
    if evidence_pack is None:
        return prompt
    context = evidence_pack.to_prompt_context()
    if not context:
        return prompt
    return f"{prompt}\n\n{context}"


def _evidence_event_payload(evidence_pack: Any | None) -> dict[str, Any] | None:
    if evidence_pack is None or evidence_pack.is_empty():
        return None
    return evidence_pack.to_payload()


def _append_cooking_qa_context(prompt: str, context: dict[str, Any]) -> str:
    if not context:
        return prompt
    encoded = json.dumps(context, ensure_ascii=False, default=str)
    return f"{prompt}\n\n[Resolved cooking context]\n{encoded}"


def _append_memory_context(prompt: str, memory: AgentMemory) -> str:
    context = memory.to_prompt_context()
    if not context:
        return prompt
    return f"{prompt}\n\n{context}"


def _append_conversation_state_context(
    prompt: str,
    conversation_state: ConversationState,
) -> str:
    context = conversation_state.to_prompt_context()
    if not context:
        return prompt
    return f"{prompt}\n\n{context}"


def _planning_payload(
    primary_task: str,
    strategy: AnswerStrategy,
    planner: str | None,
    confidence: float,
    sub_intent: Any | None = None,
    selected_agent: str | None = None,
) -> dict[str, Any]:
    return {
        "primary_task": primary_task,
        "answer_strategy": strategy.value,
        "sub_intent": _event_value(sub_intent),
        "planner": planner,
        "selected_agent": selected_agent,
        "confidence": confidence,
    }


def _event_value(value: Any | None) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", str(value))


def _cooking_qa_search_query(plan: Any | None, prompt: str) -> str:
    if plan is None:
        return prompt
    for attr in ("target_dish_name", "rewritten_question"):
        value = getattr(plan, attr, None)
        if value:
            return str(value)
    return prompt


def _fallback_main_intent() -> MainIntentResult:
    return MainIntentResult(
        primary_task=PrimaryTask.RECIPE_FIND,
        confidence=1.0,
        reason="intent 분류 실패 fallback",
    )


def _strategy_for_primary_task(primary_task: PrimaryTask) -> AnswerStrategy:
    if primary_task == PrimaryTask.RECIPE_FIND:
        return AnswerStrategy.RECIPE_RECOMMENDATION
    if primary_task == PrimaryTask.COOKING_QA:
        return AnswerStrategy.GENERAL_COOKING_QA
    if primary_task == PrimaryTask.PROFILE_MANAGEMENT:
        return AnswerStrategy.PROFILE_ACTION
    if primary_task == PrimaryTask.SMALLTALK:
        return AnswerStrategy.SMALLTALK
    return AnswerStrategy.FIXED


def _fixed_message_for_task(primary_task: PrimaryTask) -> str | None:
    if primary_task == PrimaryTask.OFF_TOPIC:
        return OFF_TOPIC_MESSAGE
    if primary_task == PrimaryTask.IDENTITY:
        return IDENTITY_MESSAGE
    return None


def _should_clarify(main_intent: MainIntentResult) -> bool:
    return main_intent.needs_clarification or (
        main_intent.primary_task == PrimaryTask.RECIPE_FIND
        and main_intent.confidence < 0.5
    )


def _recipe_find_plan_needs_clarification(plan: Any | None) -> bool:
    if plan is None:
        return False
    return bool(
        getattr(plan, "clarification_required", False)
        or getattr(plan, "sub_intent", None) == RecipeFindSubIntent.CLARIFICATION
    )


def _cooking_qa_plan_needs_clarification(plan: Any | None) -> bool:
    if plan is None:
        return False
    return bool(getattr(plan, "clarification_required", False))


def _recipe_find_plan_requires_retrieval(plan: Any | None) -> bool:
    if plan is None:
        return True
    return bool(
        getattr(plan, "retrieval_required", True)
        and not _recipe_find_plan_needs_clarification(plan)
    )


def _apply_memory_to_search_plan(
    plan: Any,
    memory: AgentMemory,
    conversation_state: ConversationState | None = None,
) -> None:
    long_term = memory.long_term
    if long_term is not None:
        _extend_unique(plan.allergies, long_term.allergies)
        _extend_unique(plan.avoid_ingredients, long_term.allergies)
        _extend_unique(plan.disliked_ingredients, long_term.disliked_ingredients)
        _extend_unique(plan.preferred_ingredients, long_term.preferred_ingredients)
        _extend_unique(plan.diet_keywords, long_term.dietary_restrictions)
        if plan.cooking_skill is None:
            plan.cooking_skill = long_term.cooking_skill
        if plan.preferred_cooking_time_minutes is None:
            plan.preferred_cooking_time_minutes = (
                long_term.preferred_cooking_time_minutes
            )
        if plan.servings is None and long_term.serving_size is not None:
            plan.servings = int(long_term.serving_size)

    avoid = memory.short_term.current_constraints.get("avoid_ingredients")
    if isinstance(avoid, list):
        _extend_unique(plan.avoid_ingredients, [str(item) for item in avoid])
    _extend_unique(plan.available_ingredients, memory.short_term.recent_ingredients)
    if conversation_state is None:
        return


def _extend_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        text = str(value).strip()
        if text and text not in target:
            target.append(text)


def _filter_recipes_for_memory(recipes: list[dict], memory: AgentMemory) -> list[dict]:
    long_term = memory.long_term
    allergies = long_term.allergies if long_term is not None else []
    if not allergies:
        return recipes
    return [
        recipe
        for recipe in recipes
        if not any(_recipe_payload_contains(recipe, allergy) for allergy in allergies)
    ]


def _recipe_payload_contains(recipe: dict, value: str) -> bool:
    normalized_value = "".join(value.lower().split())
    if not normalized_value:
        return False
    haystacks = [
        str(recipe.get("title") or ""),
        str(recipe.get("description") or ""),
    ]
    ingredients = recipe.get("ingredients")
    if isinstance(ingredients, list):
        haystacks.extend(str(item) for item in ingredients)
    return any(normalized_value in "".join(text.lower().split()) for text in haystacks)


def _search_recipe_payloads(
    search_query: str,
    limit: int,
    plan: Any | None,
    deps: RecipeDeps,
    memory: AgentMemory,
) -> tuple[list[dict], Any]:
    result = RetrievalOrchestrator(recipe_retrieval_service).search(
        search_query,
        limit=limit,
        plan=plan,
        memory=memory,
        liked_ids=deps.liked_ids,
        scrapped_ids=deps.scrapped_ids,
    )
    return result.recipe_payloads, result.evidence_pack


def _profile_update_side_effect_tasks(primary_task: PrimaryTask) -> bool:
    return primary_task in {PrimaryTask.RECIPE_FIND, PrimaryTask.COOKING_QA}


def _apply_profile_update_side_effect(
    db: Session | None,
    user_id: int | None,
    prompt: str,
    primary_task: PrimaryTask,
) -> ProfileUpdateDecision | None:
    if (
        db is None
        or user_id is None
        or not _profile_update_side_effect_tasks(primary_task)
    ):
        return None

    try:
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        decision = profile_update_analyzer.analyze(prompt, profile)
        if decision.action == ProfileUpdateAction.AUTO_SAVE:
            UserProfileService(db).apply_candidates(user_id, decision.candidates)
        if decision.action == ProfileUpdateAction.IGNORE:
            return None
        return decision
    except Exception as exc:
        logger.warning("프로필 side effect 처리 실패: %s", exc)
        return None


def _plan_requests_live_research(plan: Any | None) -> bool:
    if plan is None:
        return False
    return bool(
        getattr(plan, "needs_live_research", False)
        or getattr(plan, "requires_freshness", False)
        or getattr(plan, "requires_external_evidence", False)
    )


def _live_research_prompt(prompt: str, plan: Any | None) -> str:
    if plan is None:
        return prompt
    for attr in ("rewritten_question", "query_text", "target_dish_name"):
        value = getattr(plan, attr, None)
        if value:
            return str(value)
    return prompt


def _run_live_research_if_needed(
    primary_task: PrimaryTask,
    prompt: str,
    plan: Any | None,
    run_context: AgentRunContext,
) -> Any | None:
    research_prompt = _live_research_prompt(prompt, plan)
    try:
        should_research = _plan_requests_live_research(plan) or (
            live_research_service.should_research(primary_task, research_prompt)
        )
        if not should_research:
            return None
        query = live_research_service.build_query(research_prompt, primary_task)
        live_result = live_research_service.research(query)
        run_context.live_research_result = live_result
        return live_result
    except Exception as exc:
        logger.warning("Live research 실패: %s", exc)
        return None


def _cooking_qa_retrieval_plan(plan: Any | None, prompt: str) -> SearchPlan | None:
    if plan is None:
        return None
    query_text = _cooking_qa_search_query(plan, prompt)
    referenced_ingredients = [
        str(item).strip()
        for item in getattr(plan, "referenced_ingredients", [])
        if str(item).strip()
    ]
    target_dish_name = getattr(plan, "target_dish_name", None)
    sub_intent = (
        RecipeFindSubIntent.TARGET_DISH
        if target_dish_name
        else RecipeFindSubIntent.BY_INGREDIENTS
    )
    return SearchPlan(
        query_text=query_text,
        sub_intent=sub_intent,
        target_dish_name=target_dish_name,
        available_ingredients=list(referenced_ingredients),
        main_ingredients=list(referenced_ingredients),
        retrieval_required=True,
        answer_strategy=getattr(
            plan,
            "answer_strategy",
            AnswerStrategy.GENERAL_COOKING_QA,
        ),
    )


class AgentService:
    async def guest_stream(
        self,
        prompt: str,
        image: str | None,
        history: list[ModelMessage],
    ) -> AsyncGenerator[str]:
        return self._execute_stream(
            _StreamExecutionConfig(
                prompt=prompt,
                image=image,
                history=history,
                persist=False,
            )
        )

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
        if image and not chat_image_storage.is_available:
            raise ApiError(
                503,
                "STORAGE_NOT_CONFIGURED",
                "이미지 전송을 위한 스토리지가 설정되지 않았습니다.",
            )
        return self._execute_stream(
            _StreamExecutionConfig(
                prompt=prompt,
                image=image,
                history=history,
                room_id=room_id,
                user_id=user_id,
                chat_service=chat_service,
                db=db,
                persist=True,
            )
        )

    async def _execute_stream(
        self,
        execution: _StreamExecutionConfig,
    ) -> AsyncGenerator[str]:
        prompt = execution.prompt
        image_ref = execution.image
        stored_image_url: str | None = None
        if execution.persist and image_ref and execution.room_id is not None:
            image_ref, stored_image_url = _upload_image(image_ref, execution.room_id)

        try:
            main_intent = await main_intent_classifier.classify(
                prompt,
                execution.history,
                image=image_ref,
            )
        except Exception as exc:
            logger.error("Intent 분류 실패: %s", exc)
            main_intent = _fallback_main_intent()

        primary_task = main_intent.primary_task
        confidence = main_intent.confidence
        conversation_state = self._resolve_conversation_state(execution, prompt)
        memory = conversation_state.memory
        run_context = AgentRunContext(
            prompt=prompt,
            user_id=execution.user_id,
            room_id=execution.room_id,
            main_intent=main_intent,
            answer_strategy=_strategy_for_primary_task(primary_task),
            memory=memory,
            conversation_state=conversation_state,
        )

        fixed_message = _fixed_message_for_task(primary_task)
        if fixed_message is not None or _should_clarify(main_intent):
            yield self._metadata_event(primary_task, None)
            answer_strategy = (
                AnswerStrategy.CLARIFICATION
                if _should_clarify(main_intent)
                else AnswerStrategy.FIXED
            )
            yield stream_event_builder.planning(
                _planning_payload(
                    primary_task.value,
                    answer_strategy,
                    None,
                    confidence,
                )
            )
            message = (
                main_intent.clarification_question
                if answer_strategy == AnswerStrategy.CLARIFICATION
                else fixed_message
            ) or CLARIFY_MESSAGE
            yield stream_event_builder.message(message)
            msg_id = self._save_if_persisted(
                execution,
                message,
                recipe_ids=None,
                image_url=stored_image_url,
            )
            yield stream_event_builder.done(msg_id, [])
            return

        if primary_task == PrimaryTask.PROFILE_MANAGEMENT:
            yield self._metadata_event(primary_task, None)
            yield stream_event_builder.planning(
                _planning_payload(
                    primary_task.value,
                    AnswerStrategy.PROFILE_ACTION,
                    "ProfilePlanner",
                    confidence,
                )
            )
            async for chunk in self._handle_profile_management(
                execution,
                stored_image_url,
            ):
                yield chunk
            return

        profile_update_decision = _apply_profile_update_side_effect(
            execution.db,
            execution.user_id,
            prompt,
            primary_task,
        )
        if (
            profile_update_decision is not None
            and profile_update_decision.action == ProfileUpdateAction.AUTO_SAVE
        ):
            conversation_state = self._resolve_conversation_state(execution, prompt)
            memory = conversation_state.memory
            run_context.memory = memory
            run_context.conversation_state = conversation_state

        answer_strategy = run_context.answer_strategy
        deps = RecipeDeps(
            main_intent=main_intent,
            run_context=run_context,
            memory=memory,
            answer_strategy=answer_strategy,
        )
        self._load_social_sets(execution, deps)

        planner_name = None
        should_retrieve = False
        retrieval_plan: Any | None = None
        search_query = prompt
        resolved_context_payload: dict[str, Any] | None = None

        if primary_task == PrimaryTask.RECIPE_FIND:
            planner_name = "RecipeFindPlanner"
            user_profile_context = (
                user_context_builder.build_profile_context(
                    execution.db,
                    execution.user_id,
                )
                if execution.db is not None and execution.user_id is not None
                else None
            )
            try:
                plan = await recipe_search_planner.plan(
                    prompt,
                    execution.history,
                    user_profile_context=user_profile_context,
                    memory_context=memory.to_prompt_context(),
                    image=image_ref,
                )
                _apply_memory_to_search_plan(plan, memory, conversation_state)
                deps.search_plan = plan
                run_context.domain_plan = plan
                answer_strategy = plan.answer_strategy
                deps.answer_strategy = answer_strategy
                run_context.answer_strategy = answer_strategy
                should_retrieve = _recipe_find_plan_requires_retrieval(plan)
                deps.retrieval_allowed = should_retrieve
                retrieval_plan = plan
                search_query = plan.query_text
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
                should_retrieve = True
                deps.retrieval_allowed = True

            if _recipe_find_plan_needs_clarification(deps.search_plan):
                yield self._metadata_event(primary_task, None)
                if profile_update_decision is not None:
                    yield stream_event_builder.profile_update(
                        profile_update_decision.to_event_payload()
                    )
                answer_strategy = AnswerStrategy.CLARIFICATION
                deps.answer_strategy = answer_strategy
                run_context.answer_strategy = answer_strategy
                yield stream_event_builder.planning(
                    _planning_payload(
                        primary_task.value,
                        answer_strategy,
                        planner_name,
                        confidence,
                        sub_intent=getattr(run_context.domain_plan, "sub_intent", None),
                    )
                )
                message = (
                    getattr(deps.search_plan, "clarification_question", None)
                    or CLARIFY_MESSAGE
                )
                yield stream_event_builder.message(message)
                msg_id = self._save_if_persisted(
                    execution,
                    message,
                    recipe_ids=None,
                    image_url=stored_image_url,
                )
                yield stream_event_builder.done(msg_id, [])
                return

        elif primary_task == PrimaryTask.COOKING_QA:
            planner_name = "CookingQAPlanner"
            try:
                deps.cooking_qa_plan = await cooking_qa_planner.plan(
                    prompt,
                    execution.history,
                    memory_context=memory.to_prompt_context(),
                )
                run_context.domain_plan = deps.cooking_qa_plan
                answer_strategy = deps.cooking_qa_plan.answer_strategy
                deps.answer_strategy = answer_strategy
                run_context.answer_strategy = answer_strategy
            except Exception as exc:
                logger.warning("요리 QA 계획 생성 실패: %s", exc)

            if _cooking_qa_plan_needs_clarification(deps.cooking_qa_plan):
                yield self._metadata_event(primary_task, None)
                if profile_update_decision is not None:
                    yield stream_event_builder.profile_update(
                        profile_update_decision.to_event_payload()
                    )
                answer_strategy = AnswerStrategy.CLARIFICATION
                deps.answer_strategy = answer_strategy
                run_context.answer_strategy = answer_strategy
                yield stream_event_builder.planning(
                    _planning_payload(
                        primary_task.value,
                        answer_strategy,
                        planner_name,
                        confidence,
                        sub_intent=getattr(run_context.domain_plan, "sub_intent", None),
                    )
                )
                message = (
                    getattr(deps.cooking_qa_plan, "clarification_question", None)
                    or CLARIFY_MESSAGE
                )
                yield stream_event_builder.message(message)
                msg_id = self._save_if_persisted(
                    execution,
                    message,
                    recipe_ids=None,
                    image_url=stored_image_url,
                )
                yield stream_event_builder.done(msg_id, [])
                return

            if deps.cooking_qa_plan is not None:
                try:
                    resolved = agent_context_resolver.resolve_cooking_qa(
                        deps.cooking_qa_plan,
                        execution.room_id,
                        execution.chat_service,
                        execution.db,
                        memory=memory,
                    )
                    deps.resolved_recipe_ids = resolved.recipe_ids
                    run_context.resolved_context = resolved.payload
                    resolved_context_payload = resolved.payload or None
                except Exception as exc:
                    logger.warning("요리 QA context 해석 실패: %s", exc)

                if deps.cooking_qa_plan.needs_retrieval:
                    retrieval_plan = _cooking_qa_retrieval_plan(
                        deps.cooking_qa_plan,
                        prompt,
                    )
                    if retrieval_plan is not None:
                        _apply_memory_to_search_plan(
                            retrieval_plan,
                            memory,
                            conversation_state,
                        )
                        deps.search_plan = retrieval_plan
                        search_query = retrieval_plan.query_text
                    else:
                        search_query = _cooking_qa_search_query(
                            deps.cooking_qa_plan,
                            prompt,
                        )
                    should_retrieve = True

        live_result = _run_live_research_if_needed(
            primary_task,
            prompt,
            run_context.domain_plan,
            run_context,
        )
        yield self._metadata_event(primary_task, live_result)
        if profile_update_decision is not None:
            yield stream_event_builder.profile_update(
                profile_update_decision.to_event_payload()
            )

        effective_prompt = _append_live_research_context(
            prompt,
            live_result.answer_context if live_result else None,
        )
        effective_prompt = _append_conversation_state_context(
            effective_prompt,
            conversation_state,
        )

        answer_decision = domain_answer_router.decide(run_context)
        yield stream_event_builder.planning(
            _planning_payload(
                primary_task.value,
                answer_strategy,
                planner_name,
                confidence,
                sub_intent=getattr(run_context.domain_plan, "sub_intent", None),
                selected_agent=answer_decision.selected_agent,
            )
        )

        ai_preface = ""
        if profile_update_decision is not None and profile_update_decision.message:
            ai_preface = f"{profile_update_decision.message}\n"
            yield stream_event_builder.message(ai_preface)

        if resolved_context_payload:
            effective_prompt = _append_cooking_qa_context(
                effective_prompt,
                resolved_context_payload,
            )
            yield stream_event_builder.context(resolved_context_payload)

        if should_retrieve:
            yield stream_event_builder.retrieval({"status": "started"})
            try:
                deps.last_found_recipes, run_context.evidence_pack = (
                    _search_recipe_payloads(
                        search_query,
                        limit=3,
                        plan=retrieval_plan,
                        deps=deps,
                        memory=memory,
                    )
                )
                run_context.retrieved_recipes = deps.last_found_recipes
                effective_prompt = _append_evidence_pack_context(
                    effective_prompt,
                    run_context.evidence_pack,
                )
                effective_prompt = _append_recipe_context(
                    effective_prompt,
                    deps.last_found_recipes,
                )
                logger.info(
                    "RAG 사전 검색 결과: %d개",
                    len(deps.last_found_recipes),
                )
                yield stream_event_builder.retrieval(
                    {
                        "status": "completed",
                        "candidate_count": len(deps.last_found_recipes),
                        "selected_count": len(deps.last_found_recipes),
                    }
                )
                evidence_payload = _evidence_event_payload(run_context.evidence_pack)
                if evidence_payload is not None:
                    yield stream_event_builder.evidence(evidence_payload)
            except Exception as exc:
                logger.warning("RAG 검색 실패: %s", exc)
                yield stream_event_builder.retrieval(
                    {"status": "failed", "message": str(exc)}
                )

        user_prompt: Any = (
            [effective_prompt, _to_image_content(image_ref)]
            if image_ref
            else effective_prompt
        )
        fallback_agent = (
            recipe_agent
            if primary_task == PrimaryTask.RECIPE_FIND
            else cooking_agent
        )
        agent = answer_decision.agent or fallback_agent

        queue: asyncio.Queue = asyncio.Queue()
        agent_task = asyncio.create_task(
            _run_agent_to_queue(queue, agent, user_prompt, execution.history, deps)
        )

        ai_full = ai_preface
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

        unique_recipes = list({r["id"]: r for r in deps.last_found_recipes}.values())
        recipe_ids = [r["id"] for r in unique_recipes] or deps.resolved_recipe_ids

        if error_occurred:
            yield stream_event_builder.done(None, recipe_ids)
            return

        verification = answer_verifier.verify(
            ai_full,
            unique_recipes,
            memory,
            plan=retrieval_plan or run_context.domain_plan,
            answer_strategy=answer_strategy,
            resolved_recipe_ids=deps.resolved_recipe_ids,
        )
        run_context.verification = verification.to_payload()
        if not verification.passed:
            logger.warning("답변 검증 경고: %s", verification.issues)
        if unique_recipes:
            yield stream_event_builder.recipes(unique_recipes)

        msg_id = self._save_if_persisted(
            execution,
            ai_full,
            recipe_ids=recipe_ids or None,
            image_url=stored_image_url,
        )
        yield stream_event_builder.done(msg_id, recipe_ids)

    async def _handle_profile_management(
        self,
        execution: _StreamExecutionConfig,
        stored_image_url: str | None,
    ) -> AsyncGenerator[str]:
        if execution.db is None or execution.user_id is None:
            message = (
                "게스트 채팅에서는 프로필을 저장할 수 없어요. "
                "로그인 후 다시 말씀해 주세요."
            )
            yield stream_event_builder.message(message)
            yield stream_event_builder.done(None, [])
            return

        profile = execution.db.query(UserProfile).filter_by(
            user_id=execution.user_id
        ).first()
        decision = profile_update_analyzer.analyze(execution.prompt, profile)

        if decision.action == ProfileUpdateAction.AUTO_SAVE:
            UserProfileService(execution.db).apply_candidates(
                execution.user_id,
                decision.candidates,
            )

        if decision.action != ProfileUpdateAction.IGNORE:
            yield stream_event_builder.profile_update(decision.to_event_payload())

        message = decision.message or PROFILE_MANAGEMENT_EMPTY_MESSAGE
        yield stream_event_builder.message(message)
        msg_id = self._save_if_persisted(
            execution,
            message,
            recipe_ids=None,
            image_url=stored_image_url,
        )
        yield stream_event_builder.done(msg_id, [])

    def _resolve_conversation_state(
        self,
        execution: _StreamExecutionConfig,
        prompt: str,
    ) -> ConversationState:
        return conversation_state_resolver.resolve(
            db=execution.db,
            user_id=execution.user_id,
            room_id=execution.room_id,
            chat_service=execution.chat_service,
            prompt=prompt,
        )

    def _metadata_event(
        self,
        primary_task: PrimaryTask,
        live_result: Any | None,
    ) -> str:
        return stream_event_builder.metadata(
            primary_task.value,
            config.MODEL_NAME,
            extra={
                "used_live_research": bool(
                    live_result and live_result.used_live_research
                ),
                "source_count": len(live_result.evidence) if live_result else 0,
            },
        )

    def _save_if_persisted(
        self,
        execution: _StreamExecutionConfig,
        ai_content: str,
        recipe_ids: list[int] | None,
        image_url: str | None,
    ) -> int | None:
        if (
            not execution.persist
            or execution.chat_service is None
            or execution.room_id is None
        ):
            return None
        return execution.chat_service.save_messages(
            execution.room_id,
            execution.prompt,
            ai_content,
            recipe_ids,
            image_url=image_url,
        )

    def _load_social_sets(
        self,
        execution: _StreamExecutionConfig,
        deps: RecipeDeps,
    ) -> None:
        if execution.db is None or execution.user_id is None:
            return
        try:
            from sqlalchemy import select

            deps.liked_ids = set(
                execution.db.execute(
                    select(Like.recipe_id).where(Like.user_id == execution.user_id)
                ).scalars()
            )
            deps.scrapped_ids = set(
                execution.db.execute(
                    select(Scrap.recipe_id).where(Scrap.user_id == execution.user_id)
                ).scalars()
            )
        except Exception as exc:
            logger.warning("소셜 세트 조회 실패: %s", exc)
