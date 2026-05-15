from typing import Optional, Literal, List, Dict, Any, TypedDict, Annotated
from dataclasses import dataclass
import operator

class AccessPolicy(TypedDict):
    can_read_private: bool
    can_read_shared: bool
    can_cross_partner: bool

class StrategyMix(TypedDict):
    primary: str
    secondary: str
    focus: str

class SafetyState(TypedDict):
    level: str
    score: float

class Message(TypedDict):
    role: str
    content: str
    timestamp: str

class MemoryRecord(TypedDict):
    memory_id: str
    content: str
    metadata: Dict[str, Any]

class SignalVector(TypedDict):
    signals: Dict[str, float]

@dataclass
class SessionState:
    session_id: str
    user_id: str
    relationship_id: Optional[str]
    session_type: Literal['individual', 'joint', 'async_relay']
    access_policy: AccessPolicy
    current_strategy: StrategyMix
    safety_state: SafetyState
    turn_number: int
    short_term_buffer: Annotated[List[Message], operator.add]
    retrieved_memories: List[MemoryRecord]
    signal_vector: Optional[SignalVector]
    personalization_modifiers: Dict[str, Any]
    is_streaming: bool
    
    # Internal fields for orchestration
    system_prompt: Optional[str] = None
    llm_output: Optional[str] = None
    regeneration_count: int = 0
