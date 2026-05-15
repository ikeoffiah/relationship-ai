from enum import Enum

class JointSessionState(Enum):
    PENDING_A    = "PENDING_A"    # Partner A has opened the joint session; awaiting B
    PENDING_B    = "PENDING_B"    # Partner A confirmed; awaiting B's independent confirmation
    ACTIVE       = "ACTIVE"       # Both confirmed; joint session live
    EXITED       = "EXITED"       # One or both partners have exited to individual mode
    TERMINATED   = "TERMINATED"   # Session forcibly ended (dissolution, safety escalation, timeout)

VALID_TRANSITIONS = {
    JointSessionState.PENDING_A:  [JointSessionState.PENDING_B, JointSessionState.TERMINATED],
    JointSessionState.PENDING_B:  [JointSessionState.ACTIVE, JointSessionState.EXITED, JointSessionState.TERMINATED],
    JointSessionState.ACTIVE:     [JointSessionState.EXITED, JointSessionState.TERMINATED],
    JointSessionState.EXITED:     [],   # terminal
    JointSessionState.TERMINATED: [],   # terminal
}
