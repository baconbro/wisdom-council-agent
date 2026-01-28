"""
Wisdom Council Agent
====================

A multi-head AI agent architecture inspired by The Matrix's 
Architect and Oracle dynamic.

Example:
    >>> from wisdom_council import WisdomCouncilAgent
    >>> agent = WisdomCouncilAgent()
    >>> result = await agent.run("Create a project plan")
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from wisdom_council.agent import WisdomCouncilAgent
from wisdom_council.council import WisdomCouncil, CouncilHead, CouncilDecision, StreamEvent
from wisdom_council.heads import Architect, Oracle, Guardian, Synthesizer
from wisdom_council.executor import Executor, SubAgent
from wisdom_council.memory import MemoryManager
from wisdom_council.checkpoint import Checkpointer
from wisdom_council.llm import BaseLLMClient, OllamaClient, StreamChunk
from wisdom_council.plan import (
    Plan,
    PlanItem,
    PlanStatus,
    PlanItemStatus,
    PlanManager,
    PlanStorage,
    FilePlanStorage,
    PlanApprovalRequired,
)

__all__ = [
    # Agent
    "WisdomCouncilAgent",
    # Council
    "WisdomCouncil",
    "CouncilHead",
    "CouncilDecision",
    "StreamEvent",
    # Heads
    "Architect",
    "Oracle",
    "Guardian",
    "Synthesizer",
    # Execution
    "Executor",
    "SubAgent",
    # Memory
    "MemoryManager",
    # Checkpointing
    "Checkpointer",
    # LLM Clients
    "BaseLLMClient",
    "OllamaClient",
    "StreamChunk",
    # Plan Management
    "Plan",
    "PlanItem",
    "PlanStatus",
    "PlanItemStatus",
    "PlanManager",
    "PlanStorage",
    "FilePlanStorage",
    "PlanApprovalRequired",
]
