from dataclasses import dataclass
from enum import StrEnum

from app.agents.core.system_prompts import (
    CLARIFY_MESSAGE,
    IDENTITY_MESSAGE,
    OFF_TOPIC_MESSAGE,
)


class AgentRoute(StrEnum):
    FIXED_RESPONSE = "FIXED_RESPONSE"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    RECIPE_AGENT = "RECIPE_AGENT"
    COOKING_AGENT = "COOKING_AGENT"
    SMALLTALK_AGENT = "SMALLTALK_AGENT"


@dataclass(frozen=True)
class AgentRouteDecision:
    route: AgentRoute
    message: str | None = None
    should_plan_retrieval: bool = False


_RECIPE_INTENTS = {
    "RECIPE_RECOMMENDATION",
    "DIET_OR_ALLERGY",
    "IMAGE_BASED_RECIPE",
}
_COOKING_INTENTS = {
    "COOKING_TIP",
    "INGREDIENT_SUBSTITUTION",
    "RECIPE_DETAIL_QUESTION",
}
_LOW_CONFIDENCE_THRESHOLD = 0.5


class IntentAgentRouter:
    def decide(self, intent_type: str, confidence: float) -> AgentRouteDecision:
        if intent_type == "OFF_TOPIC":
            return AgentRouteDecision(
                route=AgentRoute.FIXED_RESPONSE,
                message=OFF_TOPIC_MESSAGE,
            )
        if intent_type == "IDENTITY":
            return AgentRouteDecision(
                route=AgentRoute.FIXED_RESPONSE,
                message=IDENTITY_MESSAGE,
            )
        if intent_type == "SMALLTALK":
            return AgentRouteDecision(route=AgentRoute.SMALLTALK_AGENT)
        if intent_type == "PROFILE_UPDATE":
            return AgentRouteDecision(route=AgentRoute.PROFILE_UPDATE)
        if intent_type in _RECIPE_INTENTS and confidence < _LOW_CONFIDENCE_THRESHOLD:
            return AgentRouteDecision(
                route=AgentRoute.FIXED_RESPONSE,
                message=CLARIFY_MESSAGE,
            )
        if intent_type in _COOKING_INTENTS:
            return AgentRouteDecision(route=AgentRoute.COOKING_AGENT)
        return AgentRouteDecision(
            route=AgentRoute.RECIPE_AGENT,
            should_plan_retrieval=intent_type in _RECIPE_INTENTS,
        )


intent_agent_router = IntentAgentRouter()
