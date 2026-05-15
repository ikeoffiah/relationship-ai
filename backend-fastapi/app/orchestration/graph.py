from langgraph.graph import StateGraph, END
from app.orchestration.state import SessionState, SafetyState, AccessPolicy, StrategyMix
import asyncio

# --- Mocks for Services ---
class SafetyPreScreener:
    @staticmethod
    def screen(message: str, session_context: dict) -> float:
        # Mock score
        return 0.1

class SafetyPostScreener:
    @staticmethod
    def screen(text: str, session_context: dict) -> bool:
        # Return True if harmful
        return False

class CounselingStrategyEngine:
    @staticmethod
    def select(signal_vector, session_history) -> StrategyMix:
        return StrategyMix(primary="Validation", secondary="Exploration", focus="Current Emotion")

class ConsentService:
    @staticmethod
    def get_access_policy(session_id: str) -> AccessPolicy:
        return AccessPolicy(can_read_private=True, can_read_shared=True, can_cross_partner=False)

class VectorRetrieval:
    @staticmethod
    async def retrieve(policy: AccessPolicy, query: str):
        # Mock retrieval <40ms p50
        return []

class LLMService:
    @staticmethod
    async def generate(prompt: str) -> str:
        return "This is a mocked LLM response."

# --- Node Implementations ---

async def node_1_safety_prescreen(state: SessionState):
    latest_msg = state.short_term_buffer[-1]["content"] if state.short_term_buffer else ""
    score = SafetyPreScreener.screen(latest_msg, {"session_id": state.session_id})
    
    level = "safe"
    if score > 0.7:
        level = "critical"
    elif score >= 0.3:
        level = "elevated"
        
    return {"safety_state": SafetyState(level=level, score=score)}


async def node_2_consent_gate(state: SessionState):
    policy = ConsentService.get_access_policy(state.session_id)
    return {"access_policy": policy}


async def node_3_memory_retrieval(state: SessionState):
    latest_msg = state.short_term_buffer[-1]["content"] if state.short_term_buffer else ""
    memories = await VectorRetrieval.retrieve(state.access_policy, latest_msg)
    return {"retrieved_memories": memories}


async def node_4_strategy_selection(state: SessionState):
    strategy = CounselingStrategyEngine.select(state.signal_vector, state.short_term_buffer)
    return {"current_strategy": strategy}


async def node_5_personalization_injection(state: SessionState):
    # Mock reading UserProfile
    modifiers = {
        "communication_style": "direct",
        "attachment_style": "secure",
        "cultural_context": "Western"
    }
    return {"personalization_modifiers": modifiers}


async def node_6_system_prompt_assembly(state: SessionState):
    core = "[Core therapeutic identity + ethical guardrails]"
    strat = f"[Active strategy: {state.current_strategy.get('primary')}, {state.current_strategy.get('secondary')}, focus: {state.current_strategy.get('focus')}]"
    prof = f"[User profile: comm_style={state.personalization_modifiers.get('communication_style')}, attachment={state.personalization_modifiers.get('attachment_style')}]"
    mems = f"[Retrieved memories: {state.retrieved_memories}]"
    cons = f"[Consent summary: {state.access_policy}]"
    safe = f"[Safety state: {state.safety_state.get('level')}]"
    
    prompt = f"{core}\n{strat}\n{prof}\n{mems}\n{cons}\n{safe}\n\nUser Message: {state.short_term_buffer[-1]['content'] if state.short_term_buffer else ''}"
    return {"system_prompt": prompt}


async def node_7_llm_call(state: SessionState):
    # In a real impl, we'd stream via a callback, here we just await the mock
    output = await LLMService.generate(state.system_prompt or "")
    return {"llm_output": output}


async def node_8_safety_postscreen(state: SessionState):
    output = state.llm_output or ""
    is_harmful = SafetyPostScreener.screen(output, {"session_id": state.session_id})
    
    if is_harmful and state.regeneration_count < 2:
        return {"regeneration_count": state.regeneration_count + 1}
    elif is_harmful:
        return {"llm_output": "I'm sorry, I cannot fulfill that request."}
    
    return {}


async def node_9_dialogue_manager_format(state: SessionState):
    # NVC alignment, pacing, etc.
    final_text = state.llm_output or ""
    # Mock modifications
    formatted = f"{final_text}\n[Pacing: Relaxed]"
    return {"llm_output": formatted}


# --- Routing Functions ---

def route_after_prescreen(state: SessionState) -> str:
    if state.safety_state["score"] > 0.7:
        return "SAFETY_PROTOCOL"
    return "node_2_consent_gate"

def route_after_postscreen(state: SessionState) -> str:
    # If regeneration counter incremented but we don't have safe output yet
    # We check if it is still harmful (the node handles the logic of rewriting llm_output on fail max)
    # If llm_output was rewritten to the refusal, it's safe to proceed.
    if state.llm_output == "I'm sorry, I cannot fulfill that request.":
        return "node_9_dialogue_manager_format"
    
    # We need to re-run LLM if harmful and retries < 2, but we didn't track "is_harmful" in state natively easily without a field
    # Let's say if regeneration_count > 0 and llm_output hasn't changed (in real we'd inject constraint)
    # For now, simplistic routing:
    return "node_9_dialogue_manager_format"


# --- Graph Construction ---

def build_counseling_graph():
    graph = StateGraph(SessionState)
    
    graph.add_node("node_1_safety_prescreen", node_1_safety_prescreen)
    graph.add_node("node_2_consent_gate", node_2_consent_gate)
    graph.add_node("node_3_memory_retrieval", node_3_memory_retrieval)
    graph.add_node("node_4_strategy_selection", node_4_strategy_selection)
    graph.add_node("node_5_personalization_injection", node_5_personalization_injection)
    graph.add_node("node_6_system_prompt_assembly", node_6_system_prompt_assembly)
    graph.add_node("node_7_llm_call", node_7_llm_call)
    graph.add_node("node_8_safety_postscreen", node_8_safety_postscreen)
    graph.add_node("node_9_dialogue_manager_format", node_9_dialogue_manager_format)
    
    # Safety exit node
    graph.add_node("SAFETY_PROTOCOL", lambda state: {"llm_output": "Safety protocol triggered. Session paused."})

    graph.set_entry_point("node_1_safety_prescreen")
    
    graph.add_conditional_edges(
        "node_1_safety_prescreen",
        route_after_prescreen,
        {
            "SAFETY_PROTOCOL": "SAFETY_PROTOCOL",
            "node_2_consent_gate": "node_2_consent_gate"
        }
    )
    
    graph.add_edge("node_2_consent_gate", "node_3_memory_retrieval")
    graph.add_edge("node_3_memory_retrieval", "node_4_strategy_selection")
    graph.add_edge("node_4_strategy_selection", "node_5_personalization_injection")
    graph.add_edge("node_5_personalization_injection", "node_6_system_prompt_assembly")
    graph.add_edge("node_6_system_prompt_assembly", "node_7_llm_call")
    graph.add_edge("node_7_llm_call", "node_8_safety_postscreen")
    
    # For simplicity, postscreen goes to dialogue manager
    # In a full retry loop, it would route back to node_6 or node_7
    graph.add_edge("node_8_safety_postscreen", "node_9_dialogue_manager_format")
    
    graph.add_edge("node_9_dialogue_manager_format", END)
    graph.add_edge("SAFETY_PROTOCOL", END)
    
    return graph.compile()
