"""
Wisdom Council - Plan System

Persistent, file-based planning with user visibility and approval workflow.
Plans are stored in the file system, support dependencies, and enable
multiple sessions or sub-agents to collaborate on the same work.

This is project management for AI.
"""

import json
import os
import uuid
import fcntl
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Awaitable


class PlanItemStatus(Enum):
    """Status of a plan item"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStatus(Enum):
    """Overall plan status"""
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PlanItem:
    """
    A single item in a plan.

    Attributes:
        id: Unique identifier for this item
        title: Short title for display
        description: Detailed description of what needs to be done
        status: Current status of the item
        dependencies: List of item IDs that must complete before this item
        assigned_to: Optional agent or session assigned to this item
        priority: Priority level (1=highest, 5=lowest)
        estimated_tokens: Estimated token cost for this item
        result: Result/output from execution
        error: Error message if failed
        created_at: Timestamp when created
        updated_at: Timestamp when last updated
        started_at: Timestamp when execution started
        completed_at: Timestamp when completed
        metadata: Additional metadata
    """
    id: str
    title: str
    description: str
    status: PlanItemStatus = PlanItemStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    priority: int = 3
    estimated_tokens: int = 0
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "estimated_tokens": self.estimated_tokens,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlanItem":
        """Create from dictionary"""
        data = data.copy()
        data["status"] = PlanItemStatus(data.get("status", "pending"))
        return cls(**data)

    def is_ready(self) -> bool:
        """Check if this item is ready to execute (all dependencies completed)"""
        return self.status == PlanItemStatus.PENDING

    def mark_in_progress(self) -> None:
        """Mark item as in progress"""
        self.status = PlanItemStatus.IN_PROGRESS
        self.started_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def mark_completed(self, result: str = None) -> None:
        """Mark item as completed"""
        self.status = PlanItemStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def mark_failed(self, error: str) -> None:
        """Mark item as failed"""
        self.status = PlanItemStatus.FAILED
        self.error = error
        self.updated_at = datetime.utcnow().isoformat()

    def mark_blocked(self) -> None:
        """Mark item as blocked"""
        self.status = PlanItemStatus.BLOCKED
        self.updated_at = datetime.utcnow().isoformat()


@dataclass
class Plan:
    """
    A complete plan with multiple items.

    Plans persist to the file system and can be shared across sessions.

    Attributes:
        id: Unique identifier for this plan
        name: Human-readable name for the plan
        description: Detailed description of what the plan accomplishes
        status: Overall plan status
        items: List of plan items
        created_by: Agent/session that created the plan
        approved_by: User/agent that approved the plan
        approval_comment: Comment from approver
        created_at: Timestamp when created
        updated_at: Timestamp when last updated
        approved_at: Timestamp when approved
        completed_at: Timestamp when all items completed
        context: Additional context for the plan
        metadata: Additional metadata
    """
    id: str
    name: str
    description: str
    status: PlanStatus = PlanStatus.DRAFT
    items: list[PlanItem] = field(default_factory=list)
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approval_comment: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_at: Optional[str] = None
    completed_at: Optional[str] = None
    context: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "items": [item.to_dict() for item in self.items],
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "approval_comment": self.approval_comment,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_at": self.approved_at,
            "completed_at": self.completed_at,
            "context": self.context,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        """Create from dictionary"""
        data = data.copy()
        data["status"] = PlanStatus(data.get("status", "draft"))
        data["items"] = [PlanItem.from_dict(item) for item in data.get("items", [])]
        return cls(**data)

    def add_item(
        self,
        title: str,
        description: str,
        dependencies: list[str] = None,
        priority: int = 3,
        **kwargs
    ) -> PlanItem:
        """Add a new item to the plan"""
        item = PlanItem(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            dependencies=dependencies or [],
            priority=priority,
            **kwargs
        )
        self.items.append(item)
        self.updated_at = datetime.utcnow().isoformat()
        return item

    def get_item(self, item_id: str) -> Optional[PlanItem]:
        """Get an item by ID"""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def get_ready_items(self) -> list[PlanItem]:
        """Get all items that are ready to execute (dependencies satisfied)"""
        completed_ids = {
            item.id for item in self.items
            if item.status == PlanItemStatus.COMPLETED
        }
        ready = []
        for item in self.items:
            if item.status != PlanItemStatus.PENDING:
                continue
            if all(dep_id in completed_ids for dep_id in item.dependencies):
                ready.append(item)
        return sorted(ready, key=lambda x: x.priority)

    def get_blocked_items(self) -> list[PlanItem]:
        """Get all items that are blocked"""
        failed_ids = {
            item.id for item in self.items
            if item.status == PlanItemStatus.FAILED
        }
        blocked = []
        for item in self.items:
            if item.status == PlanItemStatus.PENDING:
                if any(dep_id in failed_ids for dep_id in item.dependencies):
                    blocked.append(item)
        return blocked

    def get_progress(self) -> dict:
        """Get progress statistics"""
        total = len(self.items)
        if total == 0:
            return {"total": 0, "completed": 0, "percentage": 0.0}

        completed = sum(1 for item in self.items if item.status == PlanItemStatus.COMPLETED)
        in_progress = sum(1 for item in self.items if item.status == PlanItemStatus.IN_PROGRESS)
        failed = sum(1 for item in self.items if item.status == PlanItemStatus.FAILED)
        pending = sum(1 for item in self.items if item.status == PlanItemStatus.PENDING)

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "pending": pending,
            "percentage": round((completed / total) * 100, 1)
        }

    def is_complete(self) -> bool:
        """Check if all items are completed"""
        return all(
            item.status in (PlanItemStatus.COMPLETED, PlanItemStatus.SKIPPED)
            for item in self.items
        )

    def submit_for_approval(self) -> None:
        """Submit the plan for user approval"""
        self.status = PlanStatus.AWAITING_APPROVAL
        self.updated_at = datetime.utcnow().isoformat()

    def approve(self, approved_by: str = "user", comment: str = None) -> None:
        """Approve the plan"""
        self.status = PlanStatus.APPROVED
        self.approved_by = approved_by
        self.approval_comment = comment
        self.approved_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def reject(self, reason: str, rejected_by: str = "user") -> None:
        """Reject the plan"""
        self.status = PlanStatus.REJECTED
        self.rejection_reason = reason
        self.approved_by = rejected_by
        self.updated_at = datetime.utcnow().isoformat()

    def start_execution(self) -> None:
        """Mark plan as in progress"""
        if self.status != PlanStatus.APPROVED:
            raise ValueError("Plan must be approved before execution")
        self.status = PlanStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow().isoformat()

    def mark_completed(self) -> None:
        """Mark plan as completed"""
        self.status = PlanStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def display(self, show_details: bool = True) -> str:
        """
        Generate a formatted display of the plan for user visibility.

        Returns a string that can be printed to show the plan status.
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"PLAN: {self.name}")
        lines.append("=" * 60)
        lines.append(f"ID: {self.id}")
        lines.append(f"Status: {self._format_status(self.status)}")
        lines.append(f"Description: {self.description}")
        lines.append("")

        # Progress bar
        progress = self.get_progress()
        bar_width = 30
        filled = int(bar_width * progress["percentage"] / 100)
        bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
        lines.append(f"Progress: {bar} {progress['percentage']}%")
        lines.append(f"         {progress['completed']}/{progress['total']} items completed")
        lines.append("")

        # Items table
        lines.append("-" * 60)
        lines.append("PLAN ITEMS:")
        lines.append("-" * 60)

        for i, item in enumerate(self.items, 1):
            status_icon = self._get_status_icon(item.status)
            deps = ""
            if item.dependencies:
                deps = f" [depends on: {', '.join(item.dependencies)}]"

            lines.append(f"{i}. {status_icon} [{item.id}] {item.title}{deps}")

            if show_details:
                lines.append(f"   {item.description}")
                if item.assigned_to:
                    lines.append(f"   Assigned to: {item.assigned_to}")
                if item.result:
                    lines.append(f"   Result: {item.result[:100]}...")
                if item.error:
                    lines.append(f"   Error: {item.error}")
                lines.append("")

        lines.append("-" * 60)

        # Approval section
        if self.status == PlanStatus.AWAITING_APPROVAL:
            lines.append("")
            lines.append(">>> AWAITING YOUR APPROVAL <<<")
            lines.append("Use plan_manager.approve(plan_id) to approve")
            lines.append("Use plan_manager.reject(plan_id, reason) to reject")
        elif self.status == PlanStatus.APPROVED:
            lines.append(f"Approved by: {self.approved_by} at {self.approved_at}")
            if self.approval_comment:
                lines.append(f"Comment: {self.approval_comment}")
        elif self.status == PlanStatus.REJECTED:
            lines.append(f"Rejected by: {self.approved_by}")
            lines.append(f"Reason: {self.rejection_reason}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _format_status(self, status: PlanStatus) -> str:
        """Format status with visual indicator"""
        indicators = {
            PlanStatus.DRAFT: "[DRAFT]",
            PlanStatus.AWAITING_APPROVAL: "[AWAITING APPROVAL]",
            PlanStatus.APPROVED: "[APPROVED]",
            PlanStatus.REJECTED: "[REJECTED]",
            PlanStatus.IN_PROGRESS: "[IN PROGRESS]",
            PlanStatus.COMPLETED: "[COMPLETED]",
            PlanStatus.FAILED: "[FAILED]"
        }
        return indicators.get(status, str(status.value))

    def _get_status_icon(self, status: PlanItemStatus) -> str:
        """Get icon for item status"""
        icons = {
            PlanItemStatus.PENDING: "[ ]",
            PlanItemStatus.IN_PROGRESS: "[~]",
            PlanItemStatus.COMPLETED: "[x]",
            PlanItemStatus.BLOCKED: "[!]",
            PlanItemStatus.FAILED: "[X]",
            PlanItemStatus.SKIPPED: "[-]"
        }
        return icons.get(status, "[ ]")


class PlanStorage(ABC):
    """Abstract base class for plan storage backends"""

    @abstractmethod
    async def save(self, plan: Plan) -> None:
        """Save a plan"""
        pass

    @abstractmethod
    async def load(self, plan_id: str) -> Optional[Plan]:
        """Load a plan by ID"""
        pass

    @abstractmethod
    async def delete(self, plan_id: str) -> None:
        """Delete a plan"""
        pass

    @abstractmethod
    async def list_all(self) -> list[Plan]:
        """List all plans"""
        pass

    @abstractmethod
    async def list_by_status(self, status: PlanStatus) -> list[Plan]:
        """List plans by status"""
        pass


class FilePlanStorage(PlanStorage):
    """
    File-based plan storage.

    Plans are stored as JSON files in a directory, enabling:
    - Persistence between sessions
    - Cross-session synchronization
    - Easy inspection and debugging
    """

    def __init__(self, plans_dir: str = "./plans"):
        self.plans_dir = Path(plans_dir)
        self.plans_dir.mkdir(parents=True, exist_ok=True)

    def _get_plan_path(self, plan_id: str) -> Path:
        """Get the file path for a plan"""
        return self.plans_dir / f"{plan_id}.json"

    async def save(self, plan: Plan) -> None:
        """Save a plan to a JSON file with file locking for concurrency"""
        path = self._get_plan_path(plan.id)
        plan.updated_at = datetime.utcnow().isoformat()

        # Use file locking for safe concurrent access
        with open(path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(plan.to_dict(), f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    async def load(self, plan_id: str) -> Optional[Plan]:
        """Load a plan from a JSON file"""
        path = self._get_plan_path(plan_id)
        if not path.exists():
            return None

        with open(path, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                data = json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return Plan.from_dict(data)

    async def delete(self, plan_id: str) -> None:
        """Delete a plan file"""
        path = self._get_plan_path(plan_id)
        if path.exists():
            path.unlink()

    async def list_all(self) -> list[Plan]:
        """List all plans in the directory"""
        plans = []
        for path in self.plans_dir.glob("*.json"):
            plan = await self.load(path.stem)
            if plan:
                plans.append(plan)
        return sorted(plans, key=lambda p: p.updated_at, reverse=True)

    async def list_by_status(self, status: PlanStatus) -> list[Plan]:
        """List plans filtered by status"""
        all_plans = await self.list_all()
        return [p for p in all_plans if p.status == status]


class PlanManager:
    """
    High-level plan management with user visibility and approval workflow.

    This is the main interface for creating, viewing, and managing plans.

    Example:
        >>> manager = PlanManager()
        >>> plan = await manager.create_plan(
        ...     name="Deploy Application",
        ...     description="Deploy the application to production",
        ...     items=[
        ...         {"title": "Run tests", "description": "Execute test suite"},
        ...         {"title": "Build image", "description": "Build Docker image", "dependencies": ["item-1"]},
        ...         {"title": "Deploy", "description": "Deploy to production", "dependencies": ["item-2"]}
        ...     ]
        ... )
        >>> print(plan.display())  # Show plan to user
        >>> await manager.submit_for_approval(plan.id)  # Request approval
        >>> await manager.approve(plan.id)  # User approves
    """

    def __init__(
        self,
        storage: Optional[PlanStorage] = None,
        plans_dir: str = "./plans",
        on_approval_requested: Optional[Callable[[Plan], Awaitable[None]]] = None,
        on_plan_updated: Optional[Callable[[Plan], Awaitable[None]]] = None
    ):
        """
        Initialize the plan manager.

        Args:
            storage: Custom storage backend (defaults to FilePlanStorage)
            plans_dir: Directory for file storage
            on_approval_requested: Callback when approval is requested
            on_plan_updated: Callback when plan is updated
        """
        self.storage = storage or FilePlanStorage(plans_dir)
        self.on_approval_requested = on_approval_requested
        self.on_plan_updated = on_plan_updated

    async def create_plan(
        self,
        name: str,
        description: str,
        items: list[dict] = None,
        created_by: str = None,
        auto_submit: bool = True,
        context: dict = None,
        **kwargs
    ) -> Plan:
        """
        Create a new plan.

        Args:
            name: Human-readable name for the plan
            description: Detailed description
            items: List of item dicts with title, description, dependencies, etc.
            created_by: Agent/session creating the plan
            auto_submit: Automatically submit for approval after creation
            context: Additional context

        Returns:
            The created Plan
        """
        plan = Plan(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            created_by=created_by,
            context=context or {},
            **kwargs
        )

        # Add items
        if items:
            item_id_map = {}  # Map temporary IDs to actual IDs
            for i, item_data in enumerate(items):
                temp_id = item_data.pop("temp_id", f"temp-{i}")

                # Resolve dependency references
                deps = item_data.pop("dependencies", [])
                resolved_deps = [
                    item_id_map.get(dep, dep) for dep in deps
                ]

                item = plan.add_item(
                    dependencies=resolved_deps,
                    **item_data
                )
                item_id_map[temp_id] = item.id

        # Save the plan
        await self.storage.save(plan)

        # Auto-submit for approval if requested
        if auto_submit:
            await self.submit_for_approval(plan.id)

        return plan

    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID"""
        return await self.storage.load(plan_id)

    async def update_plan(self, plan: Plan) -> None:
        """Update a plan"""
        await self.storage.save(plan)
        if self.on_plan_updated:
            await self.on_plan_updated(plan)

    async def delete_plan(self, plan_id: str) -> None:
        """Delete a plan"""
        await self.storage.delete(plan_id)

    async def list_plans(self, status: Optional[PlanStatus] = None) -> list[Plan]:
        """List all plans, optionally filtered by status"""
        if status:
            return await self.storage.list_by_status(status)
        return await self.storage.list_all()

    async def submit_for_approval(self, plan_id: str) -> Plan:
        """
        Submit a plan for user approval.

        This makes the plan visible to the user and requests their approval.
        """
        plan = await self.storage.load(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        plan.submit_for_approval()
        await self.storage.save(plan)

        # Trigger callback
        if self.on_approval_requested:
            await self.on_approval_requested(plan)

        return plan

    async def approve(
        self,
        plan_id: str,
        approved_by: str = "user",
        comment: str = None
    ) -> Plan:
        """
        Approve a plan.

        Args:
            plan_id: The plan ID to approve
            approved_by: Who is approving
            comment: Optional approval comment

        Returns:
            The approved Plan
        """
        plan = await self.storage.load(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        if plan.status != PlanStatus.AWAITING_APPROVAL:
            raise ValueError(f"Plan is not awaiting approval (status: {plan.status})")

        plan.approve(approved_by=approved_by, comment=comment)
        await self.storage.save(plan)

        if self.on_plan_updated:
            await self.on_plan_updated(plan)

        return plan

    async def reject(
        self,
        plan_id: str,
        reason: str,
        rejected_by: str = "user"
    ) -> Plan:
        """
        Reject a plan.

        Args:
            plan_id: The plan ID to reject
            reason: Reason for rejection
            rejected_by: Who is rejecting

        Returns:
            The rejected Plan
        """
        plan = await self.storage.load(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        plan.reject(reason=reason, rejected_by=rejected_by)
        await self.storage.save(plan)

        if self.on_plan_updated:
            await self.on_plan_updated(plan)

        return plan

    async def start_item(self, plan_id: str, item_id: str) -> PlanItem:
        """Mark a plan item as in progress"""
        plan = await self.storage.load(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        item = plan.get_item(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found in plan")

        item.mark_in_progress()
        await self.storage.save(plan)

        return item

    async def complete_item(
        self,
        plan_id: str,
        item_id: str,
        result: str = None
    ) -> PlanItem:
        """Mark a plan item as completed"""
        plan = await self.storage.load(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        item = plan.get_item(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found in plan")

        item.mark_completed(result=result)

        # Check if plan is complete
        if plan.is_complete():
            plan.mark_completed()

        await self.storage.save(plan)

        return item

    async def fail_item(
        self,
        plan_id: str,
        item_id: str,
        error: str
    ) -> PlanItem:
        """Mark a plan item as failed"""
        plan = await self.storage.load(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        item = plan.get_item(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found in plan")

        item.mark_failed(error=error)

        # Mark dependent items as blocked
        for blocked_item in plan.get_blocked_items():
            blocked_item.mark_blocked()

        await self.storage.save(plan)

        return item

    async def get_next_item(self, plan_id: str) -> Optional[PlanItem]:
        """Get the next item ready to execute"""
        plan = await self.storage.load(plan_id)
        if not plan:
            return None

        ready_items = plan.get_ready_items()
        return ready_items[0] if ready_items else None

    async def display_plan(self, plan_id: str, show_details: bool = True) -> str:
        """
        Get a formatted display of the plan for user visibility.

        This is the main method for showing plans to users.
        """
        plan = await self.storage.load(plan_id)
        if not plan:
            return f"Plan {plan_id} not found"

        return plan.display(show_details=show_details)

    async def display_all_plans(self, status: Optional[PlanStatus] = None) -> str:
        """Display a summary of all plans"""
        plans = await self.list_plans(status=status)

        if not plans:
            return "No plans found."

        lines = []
        lines.append("=" * 60)
        lines.append("ALL PLANS")
        lines.append("=" * 60)

        for plan in plans:
            progress = plan.get_progress()
            status_str = plan._format_status(plan.status)
            lines.append(f"[{plan.id}] {plan.name}")
            lines.append(f"    Status: {status_str}")
            lines.append(f"    Progress: {progress['completed']}/{progress['total']} ({progress['percentage']}%)")
            lines.append(f"    Updated: {plan.updated_at}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


class PlanApprovalRequired(Exception):
    """Raised when a plan requires user approval before proceeding"""

    def __init__(self, plan: Plan):
        self.plan = plan
        self.plan_id = plan.id
        self.display = plan.display()
        super().__init__(f"Plan '{plan.name}' requires approval. ID: {plan.id}")
