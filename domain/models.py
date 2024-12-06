from dataclasses import dataclass
from typing import Optional, List, Any

@dataclass
class Doctor:
    username: str
    data: Optional[str] = None

@dataclass
class Conversation:
    messages: List[Any]
    last_access: float