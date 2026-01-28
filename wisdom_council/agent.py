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
from wisdom_council.plan import (
    Plan, PlanItem, PlanStatus, PlanItemStatus,
    PlanManager, PlanApprovalRequired
)


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
        plan_manager: Optional[PlanManager] = None,
        require_human_approval: Optional[list[str]] = None,
        require_plan_approval: bool = True
    ):
        """
        Initialize the Wisdom Council Agent.

        Args:
            config_path: Path to YAML configuration file
            council: Custom WisdomCouncil instance
            memory: Custom MemoryManager instance
            checkpointer: Custom Checkpointer instance
            plan_manager: Custom PlanManager for persistent plans
            require_human_approval: List of action types requiring approval
            require_plan_approval: Whether plans require user approval before execution
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

        # Initialize plan manager for persistent, visible plans
        if plan_manager:
            self.plan_manager = plan_manager
        else:
            self.plan_manager = self._create_default_plan_manager()

        # Human approval settings
        self.require_human_approval = require_human_approval or \
            self.config.get("human_approval", {}).get("require_approval", [])
        self.require_plan_approval = require_plan_approval or \
            self.config.get("plan", {}).get("require_approval", True)

        # Initialize executor
        self.executor = Executor(
            config=self.config.get("execution", {}),
            checkpointer=self.checkpointer
        )

        # State
        self._pending_approvals = {}
        self._current_plan_id = None
    
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

    def _create_default_plan_manager(self) -> PlanManager:
        """Create default plan manager for persistent plans"""
        plan_config = self.config.get("plan", {})
        return PlanManager(
            plans_dir=plan_config.get("path", "./plans"),
            on_approval_requested=self._on_plan_approval_requested,
            on_plan_updated=self._on_plan_updated
        )

    async def _on_plan_approval_requested(self, plan: Plan) -> None:
        """Callback when a plan needs approval"""
        # Display the plan for user visibility
        print("\n" + plan.display() + "\n")

    async def _on_plan_updated(self, plan: Plan) -> None:
        """Callback when a plan is updated"""
        pass
    
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
            execution_trace.append({
                "phase": "memory_retrieval",
                "count": len(memories),
                "memories": [
                    {
                        "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                        "importance": m.importance,
                        "source": m.source,
                        "timestamp": m.timestamp
                    }
                    for m in memories
                ]
            })

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
            execution_trace.append({
                "phase": "memory_storage",
                "task_summary": task[:200] + "..." if len(task) > 200 else task,
                "decision_approved": decision.approved,
                "stored_to": ["short_term", "long_term"] if self.memory.config.get("long_term") else ["short_term"]
            })

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
        context: Optional[dict] = None,
        enable_thinking: bool = False
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Stream execution events as they occur.

        Args:
            task: The task description
            context: Additional context
            enable_thinking: If True, stream thinking/reasoning tokens in real-time

        Yields:
            AgentEvent objects for each step, including thinking tokens when enabled
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

        # Emit memory retrieval details
        yield AgentEvent(
            type="memory_retrieved",
            content=f"Retrieved {len(memories)} memories",
            metadata={
                "count": len(memories),
                "memories": [
                    {
                        "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                        "importance": m.importance,
                        "source": m.source,
                        "timestamp": m.timestamp
                    }
                    for m in memories
                ]
            }
        )
        
        # 2. Council deliberation - stream each head's contribution
        yield AgentEvent(
            type="status",
            content="Council deliberation starting..."
        )

        async for event in self.council.stream_deliberate(task, context, enable_thinking=enable_thinking):
            if event.event_type == "thinking":
                # Stream thinking/reasoning tokens in real-time
                yield AgentEvent(
                    type="thinking",
                    content=event.content,
                    head=event.head,
                    metadata={"is_thinking": True}
                )
            elif event.event_type == "token":
                # Stream content tokens in real-time
                yield AgentEvent(
                    type="token",
                    content=event.content,
                    head=event.head,
                    metadata={"is_token": True}
                )
            else:
                # Other event types (proposal, critique, status, etc.)
                yield AgentEvent(
                    type="council_deliberation",
                    content=event.content,
                    head=event.head,
                    metadata=event.metadata
                )
        
        # Get final decision
        decision = await self.council.get_decision()

        if decision is None:
            yield AgentEvent(
                type="final_output",
                content="Error: Council deliberation did not produce a decision"
            )
            return

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

        # 5. Store learnings in memory
        yield AgentEvent(
            type="status",
            content="Storing learnings to memory..."
        )
        await self.memory.store(
            task=task,
            decision=decision,
            results=results
        )

        # Emit memory storage details
        yield AgentEvent(
            type="memory_stored",
            content="Stored task learnings to memory",
            metadata={
                "task_summary": task[:200] + "..." if len(task) > 200 else task,
                "decision_approved": decision.approved,
                "has_results": results is not None,
                "stored_to": ["short_term", "long_term"] if self.memory.config.get("long_term") else ["short_term"]
            }
        )

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

    # =========================================================================
    # Plan Management Methods
    # =========================================================================

    async def create_plan(
        self,
        task: str,
        context: Optional[dict] = None,
        auto_submit: bool = True
    ) -> Plan:
        """
        Create a plan for a task through council deliberation.

        The plan is stored persistently and made visible for user approval.

        Args:
            task: The task description
            context: Additional context
            auto_submit: Automatically submit for user approval

        Returns:
            The created Plan (awaiting approval)
        """
        context = context or {}

        # 1. Retrieve relevant memories
        memories = await self.memory.retrieve(task, limit=10)
        context["memories"] = memories

        # 2. Council deliberates and creates plan
        decision = await self.council.deliberate(task, context)

        if not decision.approved:
            raise ValueError(f"Council rejected task: {decision.dissents}")

        # 3. Parse the plan into structured items
        plan_items = self._parse_plan_to_items(decision.plan)

        # 4. Create persistent plan
        plan = await self.plan_manager.create_plan(
            name=f"Plan: {task[:50]}...",
            description=task,
            items=plan_items,
            created_by="council",
            auto_submit=auto_submit,
            context={
                "task": task,
                "original_context": context,
                "deliberation": decision.to_dict()
            }
        )

        self._current_plan_id = plan.id
        return plan

    def _parse_plan_to_items(self, plan: dict) -> list[dict]:
        """Parse a council plan into structured plan items"""
        items = []
        content = plan.get("content", plan.get("raw", str(plan)))

        # Simple heuristic parsing - split by numbered items or bullets
        lines = content.split("\n")
        current_item = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for numbered items (1., 2., etc.) or bullets (-, *, etc.)
            is_item_start = (
                (len(line) > 2 and line[0].isdigit() and line[1] in '.)')
                or line.startswith('- ')
                or line.startswith('* ')
                or line.startswith('• ')
            )

            if is_item_start:
                if current_item:
                    items.append(current_item)

                # Clean up the line
                if line[0].isdigit():
                    title = line[2:].strip() if len(line) > 2 else line
                else:
                    title = line[2:].strip()

                current_item = {
                    "title": title[:100],  # Truncate long titles
                    "description": title,
                    "temp_id": f"item-{len(items) + 1}"
                }
            elif current_item:
                # Append to current item description
                current_item["description"] += f" {line}"

        if current_item:
            items.append(current_item)

        # If no items found, create a single item from the whole content
        if not items:
            items.append({
                "title": "Execute plan",
                "description": content[:500],
                "temp_id": "item-1"
            })

        return items

    async def show_plan(self, plan_id: Optional[str] = None) -> str:
        """
        Display a plan for user visibility.

        Args:
            plan_id: The plan ID (uses current plan if not provided)

        Returns:
            Formatted plan display string
        """
        plan_id = plan_id or self._current_plan_id
        if not plan_id:
            return "No active plan. Use create_plan() first."

        return await self.plan_manager.display_plan(plan_id)

    async def show_all_plans(self, status: Optional[PlanStatus] = None) -> str:
        """Display all plans"""
        return await self.plan_manager.display_all_plans(status)

    async def approve_plan(
        self,
        plan_id: Optional[str] = None,
        comment: str = None
    ) -> Plan:
        """
        Approve a plan for execution.

        Args:
            plan_id: The plan ID (uses current plan if not provided)
            comment: Optional approval comment

        Returns:
            The approved Plan
        """
        plan_id = plan_id or self._current_plan_id
        if not plan_id:
            raise ValueError("No plan specified and no current plan")

        return await self.plan_manager.approve(plan_id, comment=comment)

    async def reject_plan(
        self,
        plan_id: Optional[str] = None,
        reason: str = "User rejected"
    ) -> Plan:
        """
        Reject a plan.

        Args:
            plan_id: The plan ID (uses current plan if not provided)
            reason: Reason for rejection

        Returns:
            The rejected Plan
        """
        plan_id = plan_id or self._current_plan_id
        if not plan_id:
            raise ValueError("No plan specified and no current plan")

        return await self.plan_manager.reject(plan_id, reason=reason)

    async def execute_plan(
        self,
        plan_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> AgentResult:
        """
        Execute an approved plan.

        The plan must be approved before execution.

        Args:
            plan_id: The plan ID (uses current plan if not provided)
            thread_id: Thread ID for checkpointing

        Returns:
            AgentResult with execution results
        """
        import time
        start_time = time.time()

        plan_id = plan_id or self._current_plan_id
        if not plan_id:
            raise ValueError("No plan specified and no current plan")

        plan = await self.plan_manager.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if plan.status == PlanStatus.AWAITING_APPROVAL:
            raise PlanApprovalRequired(plan)

        if plan.status == PlanStatus.REJECTED:
            raise ValueError(f"Plan was rejected: {plan.rejection_reason}")

        if plan.status not in (PlanStatus.APPROVED, PlanStatus.IN_PROGRESS):
            raise ValueError(f"Plan cannot be executed (status: {plan.status})")

        # Generate thread ID if not provided
        thread_id = thread_id or str(uuid.uuid4())
        tokens_used = 0
        execution_trace = []

        # Mark plan as in progress
        if plan.status == PlanStatus.APPROVED:
            plan.start_execution()
            await self.plan_manager.update_plan(plan)

        # Execute each plan item
        while True:
            # Get next ready item
            item = await self.plan_manager.get_next_item(plan_id)
            if not item:
                break

            # Mark item as in progress
            await self.plan_manager.start_item(plan_id, item.id)

            # Execute the item
            try:
                result = await self.executor.execute(
                    plan={"content": item.description},
                    thread_id=thread_id,
                    context=plan.context
                )
                tokens_used += result.tokens_used

                # Mark item as completed
                await self.plan_manager.complete_item(
                    plan_id, item.id,
                    result=result.final_output
                )

                execution_trace.append({
                    "item_id": item.id,
                    "item_title": item.title,
                    "status": "completed",
                    "result": result.to_dict()
                })

            except Exception as e:
                # Mark item as failed
                await self.plan_manager.fail_item(plan_id, item.id, str(e))
                execution_trace.append({
                    "item_id": item.id,
                    "item_title": item.title,
                    "status": "failed",
                    "error": str(e)
                })
                # Continue with other items that don't depend on this one

        # Reload plan to get final state
        plan = await self.plan_manager.get_plan(plan_id)

        execution_time = time.time() - start_time

        # Create a summary from execution trace
        final_output = self._summarize_plan_execution(plan, execution_trace)

        return AgentResult(
            final_output=final_output,
            deliberation=plan.context.get("deliberation", {}),
            execution_trace=execution_trace,
            tokens_used=tokens_used,
            execution_time=execution_time,
            thread_id=thread_id
        )

    def _summarize_plan_execution(self, plan: Plan, trace: list) -> str:
        """Create a summary of plan execution"""
        progress = plan.get_progress()
        lines = [
            f"Plan '{plan.name}' execution complete.",
            f"Progress: {progress['completed']}/{progress['total']} items ({progress['percentage']}%)",
            ""
        ]

        for item in trace:
            status = "DONE" if item["status"] == "completed" else "FAILED"
            lines.append(f"[{status}] {item['item_title']}")

        if progress['failed'] > 0:
            lines.append(f"\nWarning: {progress['failed']} items failed.")

        return "\n".join(lines)

    async def run_with_plan(
        self,
        task: str,
        context: Optional[dict] = None,
        thread_id: Optional[str] = None,
        wait_for_approval: bool = True
    ) -> AgentResult:
        """
        Run a task with a visible, persistent plan that requires user approval.

        This is the recommended way to run complex tasks:
        1. Creates a plan from council deliberation
        2. Displays the plan for user visibility
        3. Waits for user approval (or raises PlanApprovalRequired)
        4. Executes the approved plan

        Args:
            task: The task description
            context: Additional context
            thread_id: Thread ID for checkpointing
            wait_for_approval: If False, raises PlanApprovalRequired instead of waiting

        Returns:
            AgentResult with execution results

        Raises:
            PlanApprovalRequired: If plan needs approval and wait_for_approval=False
        """
        # Create the plan
        plan = await self.create_plan(task, context, auto_submit=True)

        # Display the plan
        print(await self.show_plan(plan.id))

        if self.require_plan_approval and plan.status == PlanStatus.AWAITING_APPROVAL:
            if not wait_for_approval:
                raise PlanApprovalRequired(plan)

            # In a real implementation, this would wait for user input
            # For now, we raise the exception to let the caller handle approval
            raise PlanApprovalRequired(plan)

        # Execute the approved plan
        return await self.execute_plan(plan.id, thread_id)
