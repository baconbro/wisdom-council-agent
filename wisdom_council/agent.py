"""
Wisdom Council Agent - Main Agent Implementation
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional
from pathlib import Path

import yaml
from pydantic import BaseModel

from wisdom_council.council import WisdomCouncil, CouncilDecision
from wisdom_council.executor import Executor
from wisdom_council.memory import MemoryManager
from wisdom_council.checkpoint import Checkpointer, SqliteCheckpointer
from wisdom_council.heads import Architect, Oracle, Guardian, Synthesizer


class TaskRequest(BaseModel):
    """Request model for tasks"""
    task: str
    context: dict = {}
    thread_id: Optional[str] = None


@dataclass
class AgentResult:
    """Result from agent execution"""
    final_output: str
    deliberation: CouncilDecision
    execution_trace: list
    tokens_used: int
    execution_time: float
    thread_id: str
    checkpoints: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "final_output": self.final_output,
            "deliberation": self.deliberation.to_dict(),
            "tokens_used": self.tokens_used,
            "execution_time": self.execution_time,
            "thread_id": self.thread_id
        }


@dataclass
class AgentEvent:
    """Event emitted during streaming execution"""
    type: str  # council_deliberation, execution_step, final_output
    content: str
    head: Optional[str] = None
    step: Optional[int] = None
    metadata: dict = field(default_factory=dict)


class HumanApprovalRequired(Exception):
    """Raised when an action requires human approval"""
    
    def __init__(self, action: str, reason: str, content: str, approval_id: str):
        self.action = action
        self.reason = reason
        self.content = content
        self.approval_id = approval_id
        super().__init__(f"Human approval required for: {action}")
    
    async def approve(self) -> AgentResult:
        """Approve the action and continue"""
        # Implementation would signal approval to the agent
        pass
    
    async def reject(self, feedback: str = None) -> AgentResult:
        """Reject the action with optional feedback"""
        pass


class WisdomCouncilAgent:
    """
    Main Wisdom Council Agent class.
    
    Orchestrates the council deliberation and execution pipeline.
    
    Example:
        >>> agent = WisdomCouncilAgent()
        >>> result = await agent.run("Create a project plan")
        >>> print(result.final_output)
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        council: Optional[WisdomCouncil] = None,
        memory: Optional[MemoryManager] = None,
        checkpointer: Optional[Checkpointer] = None,
        require_human_approval: Optional[list[str]] = None
    ):
        """
        Initialize the Wisdom Council Agent.
        
        Args:
            config_path: Path to YAML configuration file
            council: Custom WisdomCouncil instance
            memory: Custom MemoryManager instance  
            checkpointer: Custom Checkpointer instance
            require_human_approval: List of action types requiring approval
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize council
        if council:
            self.council = council
        else:
            self.council = self._create_default_council()
        
        # Initialize memory
        if memory:
            self.memory = memory
        else:
            self.memory = self._create_default_memory()
        
        # Initialize checkpointer
        if checkpointer:
            self.checkpointer = checkpointer
        elif self.config.get("checkpointing", {}).get("enabled", True):
            self.checkpointer = self._create_default_checkpointer()
        else:
            self.checkpointer = None
        
        # Human approval settings
        self.require_human_approval = require_human_approval or \
            self.config.get("human_approval", {}).get("require_approval", [])
        
        # Initialize executor
        self.executor = Executor(
            config=self.config.get("execution", {}),
            checkpointer=self.checkpointer
        )
        
        # State
        self._pending_approvals = {}
    
    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from YAML file"""
        if config_path is None:
            # Look for default config locations
            default_paths = [
                Path("./config.yaml"),
                Path("./config.yml"),
                Path("~/.wisdom_council/config.yaml").expanduser(),
            ]
            for path in default_paths:
                if path.exists():
                    config_path = str(path)
                    break
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Return default config
        return self._default_config()
    
    def _default_config(self) -> dict:
        """Return default configuration"""
        return {
            "council": {
                "max_debate_rounds": 3,
                "consensus_threshold": 0.8,
                "timeout_seconds": 300
            },
            "heads": {
                "architect": {
                    "model": "qwen3:235b",
                    "temperature": 0.1
                },
                "oracle": {
                    "model": "qwen3:235b", 
                    "temperature": 0.8
                },
                "guardian": {
                    "model": "llama4:maverick",
                    "temperature": 0.3,
                    "veto_power": True
                }
            },
            "checkpointing": {
                "enabled": True,
                "storage": "sqlite",
                "path": "./checkpoints"
            }
        }
    
    def _create_default_council(self) -> WisdomCouncil:
        """Create default council with standard heads"""
        heads_config = self.config.get("heads", {})
        
        heads = [
            Architect(config=heads_config.get("architect", {})),
            Oracle(config=heads_config.get("oracle", {})),
            Guardian(config=heads_config.get("guardian", {})),
        ]
        
        return WisdomCouncil(
            heads=heads,
            synthesizer=Synthesizer(config=heads_config.get("synthesizer", {})),
            max_rounds=self.config.get("council", {}).get("max_debate_rounds", 3),
            consensus_threshold=self.config.get("council", {}).get("consensus_threshold", 0.8)
        )
    
    def _create_default_memory(self) -> MemoryManager:
        """Create default memory manager"""
        memory_config = self.config.get("memory", {})
        return MemoryManager(config=memory_config)
    
    def _create_default_checkpointer(self) -> Checkpointer:
        """Create default checkpointer"""
        checkpoint_config = self.config.get("checkpointing", {})
        return SqliteCheckpointer(
            db_path=checkpoint_config.get("path", "./checkpoints"),
            save_frequency=checkpoint_config.get("frequency", 5)
        )
    
    async def run(
        self,
        task: str,
        context: Optional[dict] = None,
        thread_id: Optional[str] = None
    ) -> AgentResult:
        """
        Run a task through the council and execution pipeline.
        
        Args:
            task: The task description
            context: Additional context dictionary
            thread_id: Unique identifier for checkpointing
            
        Returns:
            AgentResult with final output and metadata
        """
        import time
        start_time = time.time()
        
        # Generate thread ID if not provided
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        
        context = context or {}
        tokens_used = 0
        execution_trace = []
        
        try:
            # 1. Retrieve relevant memories
            memories = await self.memory.retrieve(task, limit=10)
            context["memories"] = memories
            
            # 2. Council deliberates on approach
            decision = await self.council.deliberate(task, context)
            tokens_used += decision.tokens_used
            execution_trace.append({
                "phase": "deliberation",
                "decision": decision.to_dict()
            })
            
            if not decision.approved:
                return AgentResult(
                    final_output=f"Task blocked by council: {decision.dissents}",
                    deliberation=decision,
                    execution_trace=execution_trace,
                    tokens_used=tokens_used,
                    execution_time=time.time() - start_time,
                    thread_id=thread_id
                )
            
            # 3. Execute the plan
            results = await self.executor.execute(
                plan=decision.plan,
                thread_id=thread_id,
                context=context
            )
            tokens_used += results.tokens_used
            execution_trace.append({
                "phase": "execution",
                "results": results.to_dict()
            })
            
            # 4. Council reviews results
            review = await self.council.review(task, decision.plan, results)
            tokens_used += review.tokens_used
            
            if review.needs_revision:
                # Iterate on results
                results = await self.executor.revise(
                    results=results,
                    feedback=review.feedback,
                    thread_id=thread_id
                )
                tokens_used += results.tokens_used
                execution_trace.append({
                    "phase": "revision",
                    "results": results.to_dict()
                })
            
            # 5. Store learnings in memory
            await self.memory.store(
                task=task,
                decision=decision,
                results=results
            )
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                final_output=results.final_output,
                deliberation=decision,
                execution_trace=execution_trace,
                tokens_used=tokens_used,
                execution_time=execution_time,
                thread_id=thread_id
            )
            
        except Exception as e:
            # Save checkpoint on error
            if self.checkpointer:
                await self.checkpointer.save(
                    thread_id=thread_id,
                    state={
                        "task": task,
                        "context": context,
                        "error": str(e),
                        "trace": execution_trace
                    },
                    checkpoint_id=f"error-{uuid.uuid4()}"
                )
            raise
    
    async def stream(
        self,
        task: str,
        context: Optional[dict] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Stream execution events as they occur.
        
        Yields:
            AgentEvent objects for each step
        """
        thread_id = str(uuid.uuid4())
        context = context or {}
        
        # 1. Memory retrieval
        yield AgentEvent(
            type="status",
            content="Retrieving relevant memories..."
        )
        memories = await self.memory.retrieve(task, limit=10)
        context["memories"] = memories
        
        # 2. Council deliberation - stream each head's contribution
        yield AgentEvent(
            type="status", 
            content="Council deliberation starting..."
        )
        
        async for event in self.council.stream_deliberate(task, context):
            yield AgentEvent(
                type="council_deliberation",
                content=event.content,
                head=event.head,
                metadata=event.metadata
            )
        
        # Get final decision
        decision = await self.council.get_decision()
        
        if not decision.approved:
            yield AgentEvent(
                type="final_output",
                content=f"Task blocked: {decision.dissents}"
            )
            return
        
        # 3. Execution - stream each step
        yield AgentEvent(
            type="status",
            content="Executing plan..."
        )
        
        step = 0
        async for event in self.executor.stream_execute(decision.plan, thread_id, context):
            step += 1
            yield AgentEvent(
                type="execution_step",
                content=event.content,
                step=step,
                metadata=event.metadata
            )
        
        # 4. Final output
        results = await self.executor.get_results()
        yield AgentEvent(
            type="final_output",
            content=results.final_output
        )
    
    async def resume(self, thread_id: str) -> AgentResult:
        """
        Resume execution from last checkpoint.
        
        Args:
            thread_id: The thread ID to resume
            
        Returns:
            AgentResult from resumed execution
        """
        if not self.checkpointer:
            raise ValueError("Checkpointing not enabled")
        
        checkpoint = await self.checkpointer.get_latest(thread_id)
        if not checkpoint:
            raise ValueError(f"No checkpoint found for thread {thread_id}")
        
        # Restore state and continue
        return await self.run(
            task=checkpoint.state["task"],
            context=checkpoint.state.get("context", {}),
            thread_id=thread_id
        )
    
    async def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> str:
        """
        Manually save a checkpoint.
        
        Args:
            thread_id: The thread ID
            checkpoint_id: Optional custom checkpoint ID
            
        Returns:
            The checkpoint ID
        """
        if not self.checkpointer:
            raise ValueError("Checkpointing not enabled")
        
        checkpoint_id = checkpoint_id or f"manual-{uuid.uuid4()}"
        await self.checkpointer.save(
            thread_id=thread_id,
            state=self.executor.get_current_state(),
            checkpoint_id=checkpoint_id
        )
        return checkpoint_id
    
    async def restore_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> None:
        """
        Restore to a specific checkpoint.
        
        Args:
            thread_id: The thread ID
            checkpoint_id: The checkpoint to restore to
        """
        if not self.checkpointer:
            raise ValueError("Checkpointing not enabled")
        
        checkpoint = await self.checkpointer.get(thread_id, checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        await self.executor.restore_state(checkpoint.state)
