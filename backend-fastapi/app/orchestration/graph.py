from langgraph.graph import StateGraph, END
from app.orchestration.state import SessionState, SafetyState, AccessPolicy, StrategyMix
from app.safety.sensitive_disclosures import (
    SensitiveDisclosureDetector,
    DisclosureType,
    LEGAL_REFUSAL_RESPONSE,
    MANIPULATION_REFUSAL,
    BOTH_PARTNERS_ABUSE_RESPONSE,
    get_sensitive_disclosure_injections
)

from app.safety.layer1_rules import screen_layer1, SignalCategory
from app.safety.layer2_semantic import screen_layer2
from app.safety.layer3_contextual import screen_layer3
from app.orchestration.llm_provider import generate_reply

POST_SCREEN_REFUSAL = (
    "I'm sorry — I can't help with that. If you or someone else may be in danger, "
    "please reach out to a local emergency line or the resources in the app."
)

# Output the model must never emit. If a generated reply trips these Layer-1
# categories, we refuse rather than deliver it.
_HARMFUL_OUTPUT_CATEGORIES = {
    SignalCategory.SUICIDAL_IDEATION,
    SignalCategory.SELF_HARM,
    SignalCategory.PHYSICAL_ABUSE,
    SignalCategory.COERCIVE_CONTROL,
    SignalCategory.PERPETRATOR_LANGUAGE,
    SignalCategory.MANIPULATION_ATTEMPT,
}


# --- Services ---
class SafetyPreScreener:
    @staticmethod
    async def screen(message: str, session_context: dict) -> float:
        # Layer 1 Rule-based check
        res1 = screen_layer1(message)
        if res1.score >= 0.8:
            return res1.score

        # Ambiguous check: route to Layer 2 and Layer 3 if needed
        if 0.3 <= res1.score < 0.8:
            res2 = await screen_layer2(message)
            if res2.score >= 0.8:
                return res2.score
            res3 = await screen_layer3(message, [])
            return res3.score

        return res1.score


class SafetyPostScreener:
    """Screen the model's own output through the Layer-1 rules so a generated
    reply that itself contains crisis/abusive content is caught before delivery."""

    @staticmethod
    def screen(text: str, session_context: dict) -> bool:
        # Return True if harmful
        res = screen_layer1(text or "")
        return res.category in _HARMFUL_OUTPUT_CATEGORIES and res.score >= 0.8


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
        # Memory retrieval is a separate subsystem (app/memory); not yet wired in.
        return []


# --- System prompt assembly ---

_CORE_IDENTITY = (
    "You are a warm, evidence-based relationship counselor inside the Bliss app, "
    "drawing on Emotionally Focused Therapy, the Gottman method, and Nonviolent "
    "Communication.\n"
    "Your role and limits:\n"
    "- You support one person at a time. You are not a replacement for professional "
    "therapy or emergency services, and you never diagnose.\n"
    "- You never take sides or assume a partner's intent. Help this person understand "
    "their own feelings, needs, and patterns, and express them without blame.\n"
    "- Validate feelings before offering any reframe or suggestion. Never lecture.\n"
    "- Keep replies short and human — usually 2 to 4 sentences — and ask at most one "
    "gentle, open question when it helps."
)

_ATTACHMENT_GUIDANCE = {
    "anxious-preoccupied": "They lean anxious in attachment: brief, explicit reassurance "
    "helps, and silence can read as rejection to them.",
    "dismissive-avoidant": "They lean avoidant: give space, keep intensity low, and don't "
    "push them to open up faster than they're ready.",
    "fearful-avoidant": "They hold both wanting closeness and fearing it: be steady and "
    "patient, and normalize the mixed feelings.",
    "secure": "They lean secure: you can be direct and collaborative.",
}


def build_system_prompt(
    strategy: dict, modifiers: dict, safety_state: dict, disclosures: list, memories: list = None
) -> str:
    strategy = strategy or {}
    modifiers = modifiers or {}
    parts = [_CORE_IDENTITY]

    memory_lines = [f"- {m.get('note')}" for m in (memories or []) if m.get("note")]
    if memory_lines:
        parts.append(
            "What you remember about them from past sessions (use gently and only "
            "when relevant — reference it naturally, never recite it back):\n"
            + "\n".join(memory_lines[:5])
        )

    primary = strategy.get("primary")
    if primary:
        focus = strategy.get("focus") or "the current feeling"
        parts.append(f"Lead with a {primary.lower()} stance this turn, focused on {focus.lower()}.")

    style = (modifiers.get("attachment_style") or "").strip().lower()
    if style in _ATTACHMENT_GUIDANCE:
        parts.append(_ATTACHMENT_GUIDANCE[style])
    comm = (modifiers.get("communication_style") or "").strip().lower()
    if comm:
        parts.append(f"They describe their own communication style as {comm}; meet it.")

    if (safety_state or {}).get("level") == "elevated":
        parts.append(
            "There are signs of distress in this conversation. Slow down, prioritize "
            "emotional safety, and gently check in on how they're really doing."
        )

    injections = get_sensitive_disclosure_injections(disclosures or [])
    parts.extend(injections)

    return "\n\n".join(p for p in parts if p)


# --- Node Implementations ---

async def node_1_safety_prescreen(state: SessionState):
    latest_msg = state.short_term_buffer[-1]["content"] if state.short_term_buffer else ""

    # Check if this is an abuse claim
    is_abuse_claim = "abuse" in latest_msg.lower() or "abusive" in latest_msg.lower() or "violence" in latest_msg.lower()
    other_partner_claims_abuse = state.personalization_modifiers.get("other_partner_claims_abuse", False)

    dt = SensitiveDisclosureDetector.detect(
        latest_msg,
        state.session_type,
        other_partner_claims_abuse=other_partner_claims_abuse
    )

    active_disclosures = list(state.active_disclosures)
    llm_output = state.llm_output
    abuse_claim_by_user = state.abuse_claim_by_user

    if is_abuse_claim:
        abuse_claim_by_user = True

    if dt == DisclosureType.LEGAL:
        llm_output = LEGAL_REFUSAL_RESPONSE
        if DisclosureType.LEGAL.value not in active_disclosures:
            active_disclosures.append(DisclosureType.LEGAL.value)
    elif dt == DisclosureType.MANIPULATION:
        print(f"[AUDIT] manipulation_attempt detected in session {state.session_id}")
        llm_output = MANIPULATION_REFUSAL
        if DisclosureType.MANIPULATION.value not in active_disclosures:
            active_disclosures.append(DisclosureType.MANIPULATION.value)
    elif dt == DisclosureType.MUTUAL_ABUSE:
        llm_output = BOTH_PARTNERS_ABUSE_RESPONSE
        if DisclosureType.MUTUAL_ABUSE.value not in active_disclosures:
            active_disclosures.append(DisclosureType.MUTUAL_ABUSE.value)
        # Suspend joint session capability
        from app.safety.sensitive_disclosures import SUSPENDED_JOINT_SESSIONS
        if state.relationship_id:
            SUSPENDED_JOINT_SESSIONS.add(state.relationship_id)
    elif dt == DisclosureType.INFIDELITY:
        if DisclosureType.INFIDELITY.value not in active_disclosures:
            active_disclosures.append(DisclosureType.INFIDELITY.value)

    score = await SafetyPreScreener.screen(latest_msg, {"session_id": state.session_id})

    level = "safe"
    if score > 0.7 or dt in [DisclosureType.LEGAL, DisclosureType.MANIPULATION, DisclosureType.MUTUAL_ABUSE]:
        level = "critical"
    elif score >= 0.3:
        level = "elevated"

    return {
        "safety_state": SafetyState(level=level, score=score),
        "active_disclosures": active_disclosures,
        "llm_output": llm_output,
        "abuse_claim_by_user": abuse_claim_by_user
    }


async def node_2_consent_gate(state: SessionState):
    policy = ConsentService.get_access_policy(state.session_id)
    return {"access_policy": policy}


async def node_3_memory_retrieval(state: SessionState):
    # Memories are retrieved by the caller (chat_router) and placed on the state;
    # pass them through unchanged.
    return {"retrieved_memories": state.retrieved_memories or []}


async def node_4_strategy_selection(state: SessionState):
    strategy = CounselingStrategyEngine.select(state.signal_vector, state.short_term_buffer)
    return {"current_strategy": strategy}


async def node_5_personalization_injection(state: SessionState):
    # Personalization is populated onto the state by the caller (chat_router
    # reads the user's profile). Pass it through unchanged.
    return {"personalization_modifiers": state.personalization_modifiers or {}}


async def node_6_system_prompt_assembly(state: SessionState):
    prompt = build_system_prompt(
        state.current_strategy,
        state.personalization_modifiers,
        state.safety_state,
        state.active_disclosures,
        state.retrieved_memories,
    )
    return {"system_prompt": prompt}


async def node_7_llm_call(state: SessionState):
    # The conversation is passed as messages; the system prompt carries the
    # therapeutic identity, strategy, personalization, and safety context.
    messages = [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in state.short_term_buffer
        if m.get("content")
    ]
    if not messages:
        messages = [{"role": "user", "content": ""}]
    output = await generate_reply(state.system_prompt or "", messages)
    return {"llm_output": output}


async def node_8_safety_postscreen(state: SessionState):
    output = state.llm_output or ""
    is_harmful = SafetyPostScreener.screen(output, {"session_id": state.session_id})

    if is_harmful and state.regeneration_count < 2:
        return {"regeneration_count": state.regeneration_count + 1, "llm_output": POST_SCREEN_REFUSAL}
    elif is_harmful:
        return {"llm_output": POST_SCREEN_REFUSAL}

    return {}


async def node_9_dialogue_manager_format(state: SessionState):
    # Light final pass: trim whitespace. The model already returns well-formed,
    # appropriately paced text, so no synthetic formatting is added.
    final_text = (state.llm_output or "").strip()
    return {"llm_output": final_text}


# --- Routing Functions ---

def route_after_prescreen(state: SessionState) -> str:
    if state.safety_state["score"] > 0.7 or state.llm_output in [LEGAL_REFUSAL_RESPONSE, MANIPULATION_REFUSAL, BOTH_PARTNERS_ABUSE_RESPONSE]:
        return "SAFETY_PROTOCOL"
    return "node_2_consent_gate"


def route_after_postscreen(state: SessionState) -> str:
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
    graph.add_node("SAFETY_PROTOCOL", lambda state: {"llm_output": state.llm_output or "Safety protocol triggered. Session paused."})

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
    graph.add_edge("node_8_safety_postscreen", "node_9_dialogue_manager_format")
    graph.add_edge("node_9_dialogue_manager_format", END)
    graph.add_edge("SAFETY_PROTOCOL", END)

    return graph.compile()
