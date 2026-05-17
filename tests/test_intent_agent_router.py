from app.agents.intent.intent_agent_router import AgentRoute, IntentAgentRouter


def test_off_topic_routes_to_fixed_response():
    decision = IntentAgentRouter().decide("OFF_TOPIC", confidence=1.0)

    assert decision.route == AgentRoute.FIXED_RESPONSE
    assert decision.message is not None
    assert decision.should_plan_retrieval is False


def test_profile_update_routes_to_profile_update_flow():
    decision = IntentAgentRouter().decide("PROFILE_UPDATE", confidence=1.0)

    assert decision.route == AgentRoute.PROFILE_UPDATE
    assert decision.message is None


def test_low_confidence_recipe_intent_routes_to_fixed_clarification():
    decision = IntentAgentRouter().decide("RECIPE_RECOMMENDATION", confidence=0.4)

    assert decision.route == AgentRoute.FIXED_RESPONSE
    assert "구체적으로" in decision.message


def test_recipe_recommendation_routes_to_recipe_agent_with_planning():
    decision = IntentAgentRouter().decide("RECIPE_RECOMMENDATION", confidence=0.9)

    assert decision.route == AgentRoute.RECIPE_AGENT
    assert decision.should_plan_retrieval is True


def test_cooking_tip_routes_to_cooking_agent():
    decision = IntentAgentRouter().decide("COOKING_TIP", confidence=0.9)

    assert decision.route == AgentRoute.COOKING_AGENT
    assert decision.should_plan_retrieval is False


def test_smalltalk_uses_smalltalk_responder():
    decision = IntentAgentRouter().decide("SMALLTALK", confidence=0.95)

    assert decision.route == AgentRoute.FIXED_RESPONSE
    assert decision.message is None
    assert decision.use_smalltalk_responder is True

