from enum import Enum


class Resolution(Enum):
    CURRENT = "current"
    INCOMING = "incoming"
    BOTH_CURRENT_FIRST = "both_current_first"
    BOTH_INCOMING_FIRST = "both_incoming_first"
    MANUAL = "manual"
