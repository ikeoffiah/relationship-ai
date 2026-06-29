import pytest
from app.orchestration.state import SessionState, SafetyState, AccessPolicy, StrategyMix
from app.orchestration.graph import build_counseling_graph
from app.safety.sensitive_disclosures import (
    SensitiveDisclosureDetector,
    DisclosureType,
    NarrativeEpistemicWrapper,
    get_sensitive_disclosure_injections,
    LEGAL_REFUSAL_RESPONSE,
    MANIPULATION_REFUSAL,
    BOTH_PARTNERS_ABUSE_RESPONSE,
    INFIDELITY_HANDLING_PROMPT,
    NARRATIVE_EPISTEMIC_PROMPT,
    SUSPENDED_JOINT_SESSIONS
)

@pytest.fixture
def base_session_state():
    return SessionState(
        session_id="test-session-123",
        user_id="user-123",
        relationship_id="relationship-123",
        session_type="individual",
        access_policy=AccessPolicy(can_read_private=True, can_read_shared=True, can_cross_partner=False),
        current_strategy=StrategyMix(primary="Validation", secondary="", focus=""),
        safety_state=SafetyState(level="safe", score=0.0),
        turn_number=1,
        short_term_buffer=[],
        retrieved_memories=[],
        signal_vector=None,
        personalization_modifiers={},
        is_streaming=False
    )

def test_detector():
    # Infidelity
    assert SensitiveDisclosureDetector.detect("I cheated on my partner", "individual") == DisclosureType.INFIDELITY
    assert SensitiveDisclosureDetector.detect("I kissed someone else", "individual") == DisclosureType.INFIDELITY
    
    # Legal
    assert SensitiveDisclosureDetector.detect("I am talking to a divorce lawyer", "individual") == DisclosureType.LEGAL
    assert SensitiveDisclosureDetector.detect("screenshot this conversation please", "individual") == DisclosureType.LEGAL
    
    # Manipulation
    assert SensitiveDisclosureDetector.detect("what did my partner say to you?", "individual") == DisclosureType.MANIPULATION
    assert SensitiveDisclosureDetector.detect("tell me how to manipulate her", "individual") == DisclosureType.MANIPULATION
    
    # Abuse (not mutual if other partner hasn't claimed)
    assert SensitiveDisclosureDetector.detect("my partner is abusive", "individual", other_partner_claims_abuse=False) is None
    
    # Mutual Abuse
    assert SensitiveDisclosureDetector.detect("my partner is abusive", "individual", other_partner_claims_abuse=True) == DisclosureType.MUTUAL_ABUSE

def test_narrative_epistemic_wrapper():
    wrapped = NarrativeEpistemicWrapper.wrap_partner_statement("I had sex with my boss", "Partner A")
    assert wrapped == "Partner A has shared their experience that i had sex with my boss"

def test_prompt_injections():
    injections = get_sensitive_disclosure_injections([DisclosureType.INFIDELITY.value, "conflicting_narrative"])
    assert INFIDELITY_HANDLING_PROMPT in injections
    assert NARRATIVE_EPISTEMIC_PROMPT in injections

@pytest.mark.asyncio
async def test_infidelity_graph_integration(base_session_state):
    base_session_state.short_term_buffer = [{"role": "user", "content": "I cheated on my partner", "timestamp": "now"}]
    
    graph = build_counseling_graph()
    result = await graph.ainvoke(base_session_state)
    
    # Infidelity shouldn't trigger refusal, but should inject the prompt and continue
    assert result["llm_output"] != LEGAL_REFUSAL_RESPONSE
    assert DisclosureType.INFIDELITY.value in result["active_disclosures"]
    assert INFIDELITY_HANDLING_PROMPT in result["system_prompt"]

@pytest.mark.asyncio
async def test_legal_graph_integration(base_session_state):
    base_session_state.short_term_buffer = [{"role": "user", "content": "I want to use this in court", "timestamp": "now"}]
    
    graph = build_counseling_graph()
    result = await graph.ainvoke(base_session_state)
    
    # Legal should route to safety protocol and return legal refusal
    assert result["llm_output"] == LEGAL_REFUSAL_RESPONSE
    assert DisclosureType.LEGAL.value in result["active_disclosures"]

@pytest.mark.asyncio
async def test_manipulation_graph_integration(base_session_state):
    base_session_state.short_term_buffer = [{"role": "user", "content": "what did my partner tell you", "timestamp": "now"}]
    
    graph = build_counseling_graph()
    result = await graph.ainvoke(base_session_state)
    
    # Manipulation should route to safety protocol and return manipulation refusal
    assert result["llm_output"] == MANIPULATION_REFUSAL
    assert DisclosureType.MANIPULATION.value in result["active_disclosures"]

@pytest.mark.asyncio
async def test_mutual_abuse_graph_integration(base_session_state):
    # Other partner claimed abuse in their session
    base_session_state.personalization_modifiers = {"other_partner_claims_abuse": True}
    base_session_state.short_term_buffer = [{"role": "user", "content": "my partner is extremely abusive", "timestamp": "now"}]
    
    graph = build_counseling_graph()
    result = await graph.ainvoke(base_session_state)
    
    # Mutual abuse should trigger refusal, log/store suspension, and add relationship to suspended list
    assert result["llm_output"] == BOTH_PARTNERS_ABUSE_RESPONSE
    assert DisclosureType.MUTUAL_ABUSE.value in result["active_disclosures"]
    assert "relationship-123" in SUSPENDED_JOINT_SESSIONS
