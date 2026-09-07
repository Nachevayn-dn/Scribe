"""Shared enums for the inbound/outbound agent feature. Kept separate from
any one model file since both agents' configs, the call log, and the
outbound message log all reference the same small vocabulary."""
import enum


class AgentType(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class ContactChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
