import pytest
from app.orchestration.state import SessionState, SafetyState, AccessPolicy, StrategyMix
from app.orchestration.graph import (
    node_1_safety_prescreen, node_2_consent_gate, node_3_memory_retrieval,
    node_4_strategy_selection, node_5_personalization_injection,
    node_6_system_prompt_assembly, node_7_llm_call, node_8_safety_postscreen,
    node_9_dialogue_manager_format, build_counseling_graph, route_after_prescreen
)

@pytest.fixture
def mock_session_state():
    return SessionState(
        session_id="test-session-123",
        user_id="user-123",
        relationship_id=None,
        session_type="individual",
        access_policy=AccessPolicy(can_read_private=False, can_read_shared=False, can_cross_partner=False),
        current_strategy=StrategyMix(primary="", secondary="", focus=""),
        safety_state=SafetyState(level="safe", score=0.0),
        turn_number=1,
        short_term_buffer=[{"role": "user", "content": "Hello", "timestamp": "now"}],
        retrieved_memories=[],
        signal_vector=None,
        personalization_modifiers={},
        is_streaming=False
    )

@pytest.mark.asyncio
async def test_node_1_safety_prescreen(mock_session_state):
    result = await node_1_safety_prescreen(mock_session_state)
    assert "safety_state" in result
    assert result["safety_state"]["level"] == "safe"
    assert result["safety_state"]["score"] >= 0.0

@pytest.mark.asyncio
async def test_node_2_consent_gate(mock_session_state):
    result = await node_2_consent_gate(mock_session_state)
    assert "access_policy" in result
    assert "can_read_private" in result["access_policy"]

@pytest.mark.asyncio
async def test_node_3_memory_retrieval(mock_session_state):
    result = await node_3_memory_retrieval(mock_session_state)
    assert "retrieved_memories" in result

@pytest.mark.asyncio
async def test_node_4_strategy_selection(mock_session_state):
    result = await node_4_strategy_selection(mock_session_state)
    assert "current_strategy" in result

@pytest.mark.asyncio
async def test_node_5_personalization_injection(mock_session_state):
    result = await node_5_personalization_injection(mock_session_state)
    assert "personalization_modifiers" in result

@pytest.mark.asyncio
async def test_node_6_system_prompt_assembly(mock_session_state):
    result = await node_6_system_prompt_assembly(mock_session_state)
    assert "system_prompt" in result
    assert "User Message: Hello" in result["system_prompt"]

@pytest.mark.asyncio
async def test_node_7_llm_call(mock_session_state):
    result = await node_7_llm_call(mock_session_state)
    assert "llm_output" in result

@pytest.mark.asyncio
async def test_node_8_safety_postscreen(mock_session_state):
    result = await node_8_safety_postscreen(mock_session_state)
    # mock returns False for harmfulness
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_node_9_dialogue_manager_format(mock_session_state):
    result = await node_9_dialogue_manager_format(mock_session_state)
    assert "llm_output" in result

def test_route_after_prescreen(mock_session_state):
    # Test safe
    mock_session_state.safety_state = SafetyState(level="safe", score=0.1)
    route = route_after_prescreen(mock_session_state)
    assert route == "node_2_consent_gate"
    
    # Test critical
    mock_session_state.safety_state = SafetyState(level="critical", score=0.8)
    route = route_after_prescreen(mock_session_state)
    assert route == "SAFETY_PROTOCOL"

def test_graph_compiles():
    graph = build_counseling_graph()
    assert graph is not None
