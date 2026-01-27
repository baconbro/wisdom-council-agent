#!/usr/bin/env python3
"""
Wisdom Council Agent - Quick Start Example

This example demonstrates basic usage of the Wisdom Council Agent.
"""

import asyncio
from wisdom_council import WisdomCouncilAgent


async def basic_example():
    """Basic usage example with full transparency"""
    print("=" * 60)
    print("WISDOM COUNCIL AGENT - Basic Example")
    print("=" * 60)

    # Initialize agent with default configuration
    agent = WisdomCouncilAgent()

    # Ask user for their task
    print("\nWhat would you like the Wisdom Council to help you with?")
    print("(Enter your question or task description)\n")
    task = input("Your task: ").strip()

    if not task:
        print("No task provided. Using example task.")
        task = "Create a project management framework for a university IT department."

    # Run the task
    print("\n📋 Task:", task)
    print("\n🏛️ Council deliberating...\n")

    result = await agent.run(task)

    # Display results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\n📊 Final Output:\n{result.final_output}")
    print(f"\n⏱️ Execution Time: {result.execution_time:.2f}s")
    print(f"🔢 Tokens Used: {result.tokens_used}")

    # Show MEMORY details
    print("\n" + "=" * 60)
    print("MEMORY DETAILS")
    print("=" * 60)

    for trace in result.execution_trace:
        if trace.get("phase") == "memory_retrieval":
            print(f"\n🧠 RETRIEVED MEMORIES: {trace.get('count', 0)} found")
            memories = trace.get("memories", [])
            if memories:
                for i, mem in enumerate(memories, 1):
                    print(f"   [{i}] {mem['content']}")
                    print(f"       Source: {mem['source']} | Importance: {mem['importance']:.1%} | Time: {mem['timestamp']}")
            else:
                print("   (No relevant memories found)")

        elif trace.get("phase") == "memory_storage":
            print(f"\n💾 STORED TO MEMORY:")
            print(f"   Task: {trace.get('task_summary', 'N/A')}")
            print(f"   Decision approved: {trace.get('decision_approved', 'N/A')}")
            stored_to = trace.get('stored_to', [])
            print(f"   Stored to: {', '.join(stored_to) if stored_to else 'default'}")

    # Show FULL deliberation details
    print("\n" + "=" * 60)
    print("COUNCIL DELIBERATION (FULL DETAILS)")
    print("=" * 60)

    for round_data in result.deliberation.rounds:
        print(f"\n{'─' * 50}")
        print(f"ROUND {round_data.number}")
        print(f"{'─' * 50}")

        # Show FULL proposals
        print("\n📝 PROPOSALS:\n")
        for head, proposal in round_data.proposals.items():
            print(f"  🎭 {head}:")
            print(f"     Proposal: {proposal.content}")
            if proposal.reasoning:
                print(f"     Reasoning: {proposal.reasoning}")
            if proposal.concerns:
                print(f"     Concerns: {proposal.concerns}")
            if proposal.questions:
                print(f"     Questions: {proposal.questions}")
            print(f"     Confidence: {proposal.confidence:.0%}")
            print()

        # Show FULL critiques
        if round_data.critiques:
            print("\n💬 CRITIQUES:\n")
            for head, critique in round_data.critiques.items():
                print(f"  🎭 {head}'s Critique:")
                if critique.agreements:
                    print(f"     ✓ Agrees with: {critique.agreements}")
                if critique.concerns:
                    print(f"     ⚠ Concerns: {critique.concerns}")
                if critique.suggested_changes:
                    print(f"     → Suggestions: {critique.suggested_changes}")
                if critique.questions:
                    print(f"     ? Questions: {critique.questions}")
                print()

        print(f"  📊 Consensus: {'Yes ✓' if round_data.has_consensus else 'No ✗'}")

    # Show synthesis reasoning
    if result.deliberation.synthesis_reasoning:
        print(f"\n{'─' * 50}")
        print("🔮 SYNTHESIS REASONING")
        print(f"{'─' * 50}")
        print(f"  {result.deliberation.synthesis_reasoning}")

    # Guardian review with FULL details
    print(f"\n{'─' * 50}")
    print("🛡️ GUARDIAN REVIEW")
    print(f"{'─' * 50}")

    if result.deliberation.guardian_review:
        review = result.deliberation.guardian_review
        if review.passed:
            print("  ✅ Status: APPROVED")
        else:
            print("  ❌ Status: VETOED")

        # ALWAYS show violations when vetoed - this is the key transparency fix!
        if review.violations:
            print("\n  🚫 CONSTITUTIONAL VIOLATIONS:")
            for violation in review.violations:
                print(f"     ✗ {violation}")

        if review.warnings:
            print("\n  ⚠️ WARNINGS:")
            for warning in review.warnings:
                print(f"     ! {warning}")
    else:
        print("  ℹ️ No Guardian review performed")

    # Show dissents
    if result.deliberation.dissents:
        print(f"\n{'─' * 50}")
        print("📢 REMAINING DISSENTS")
        print(f"{'─' * 50}")
        for dissent in result.deliberation.dissents:
            print(f"  🎭 {dissent['head']}:")
            for concern in dissent['concerns']:
                print(f"     - {concern}")


async def streaming_example():
    """Streaming output example with full transparency"""
    print("\n" + "=" * 60)
    print("WISDOM COUNCIL AGENT - Streaming Example (LIVE)")
    print("=" * 60)

    agent = WisdomCouncilAgent()

    # Ask user for their task
    print("\nWhat would you like the Wisdom Council to help you with?")
    task = input("Your task: ").strip()

    if not task:
        print("No task provided. Using example task.")
        task = "Design a risk assessment methodology for IT projects"

    print(f"\n📋 Task: {task}")
    print("\n🔴 LIVE DELIBERATION - Watch the council think in real-time:\n")
    print("─" * 60)

    async for event in agent.stream(task):
        if event.type == "council_deliberation":
            head = event.head or "Council"
            # Show FULL content, not truncated
            print(f"\n🎭 [{head}]")
            print(f"   {event.content}")

            # Show metadata if available (reasoning, concerns, etc.)
            if event.metadata:
                if "reasoning" in event.metadata and event.metadata["reasoning"]:
                    print(f"   💭 Reasoning: {event.metadata['reasoning']}")
                if "concerns" in event.metadata and event.metadata["concerns"]:
                    print(f"   ⚠️ Concerns: {event.metadata['concerns']}")

        elif event.type == "memory_retrieved":
            # Show memory retrieval details
            print(f"\n🧠 MEMORY RETRIEVED: {event.content}")
            if event.metadata and event.metadata.get("memories"):
                for i, mem in enumerate(event.metadata["memories"], 1):
                    print(f"   [{i}] {mem['content']}")
                    print(f"       Source: {mem['source']} | Importance: {mem['importance']:.1%} | Time: {mem['timestamp']}")
            else:
                print("   (No relevant memories found)")

        elif event.type == "memory_stored":
            # Show memory storage details
            print(f"\n💾 MEMORY STORED: {event.content}")
            if event.metadata:
                print(f"   Task: {event.metadata.get('task_summary', 'N/A')}")
                print(f"   Decision approved: {event.metadata.get('decision_approved', 'N/A')}")
                stored_to = event.metadata.get('stored_to', [])
                print(f"   Stored to: {', '.join(stored_to) if stored_to else 'default'}")

        elif event.type == "status":
            print(f"\n📌 {event.content}")

        elif event.type == "execution_step":
            step = event.step or "?"
            print(f"\n⚙️ [Step {step}]")
            print(f"   {event.content}")

        elif event.type == "final_output":
            print("\n" + "=" * 60)
            print("✅ FINAL RESULT")
            print("=" * 60)
            print(f"\n{event.content}")


async def custom_council_example():
    """Custom council configuration example"""
    print("\n" + "=" * 60)
    print("WISDOM COUNCIL AGENT - Custom Council Example")
    print("=" * 60)
    
    from wisdom_council import WisdomCouncil, Architect, Oracle, Guardian, Synthesizer
    from wisdom_council.council import CouncilHead, HeadType
    
    # Create a custom "Innovator" head
    class Innovator(CouncilHead):
        def __init__(self):
            super().__init__(
                name="Innovator",
                head_type=HeadType.CUSTOM,
                model="qwen3:235b",
                temperature=0.9,  # High temperature for creativity
                constitution=[
                    "Challenge conventional thinking",
                    "Propose 10x solutions, not 10% improvements",
                    "Embrace calculated risks",
                    "Look for paradigm shifts"
                ],
                system_prompt="""You are the Innovator. Challenge assumptions.
                Propose breakthrough approaches. Ask 'what if we did the opposite?'"""
            )
        
        async def propose(self, task, context):
            # Implementation...
            pass
        
        async def critique(self, task, proposals):
            # Implementation...
            pass
        
        async def revise(self, proposal, critiques):
            # Implementation...
            pass
    
    # Create custom council with 4 heads
    custom_council = WisdomCouncil(
        heads=[
            Architect({"temperature": 0.1}),
            Oracle({"temperature": 0.8}),
            Guardian({"veto_power": True}),
            # Innovator(),  # Add custom head
        ],
        synthesizer=Synthesizer(),
        max_rounds=4,  # More debate rounds
        consensus_threshold=0.7  # Lower threshold
    )
    
    # Create agent with custom council
    agent = WisdomCouncilAgent(council=custom_council)

    # Ask user for their task
    print("\nWhat would you like the Wisdom Council to help you with?")
    task = input("Your task: ").strip()

    if not task:
        print("No task provided. Using example task.")
        task = "Design an AI governance framework for enterprise deployment"

    print(f"\n📋 Task: {task}\n")

    result = await agent.run(task)
    
    print(f"\n✅ Result: {result.final_output[:500]}...")


async def plan_example():
    """Plan creation and approval example"""
    print("\n" + "=" * 60)
    print("WISDOM COUNCIL AGENT - Plan Example")
    print("=" * 60)

    from wisdom_council import (
        WisdomCouncilAgent,
        PlanManager,
        PlanApprovalRequired,
        PlanStatus
    )

    # Initialize agent with plan support
    agent = WisdomCouncilAgent(require_plan_approval=True)

    task = """
    Deploy a new microservice to production:
    1. Run unit tests
    2. Build Docker image
    3. Push to container registry
    4. Update Kubernetes deployment
    5. Verify health checks
    """

    print(f"\n📋 Task: {task}")
    print("\n🏛️ Creating plan through council deliberation...\n")

    try:
        # Create and display a plan (will require approval)
        plan = await agent.create_plan(task)

        # Display the plan for user visibility
        print(await agent.show_plan())

        # Simulate user approval
        print("\n👤 User reviewing plan...")
        print(">>> Approving plan...\n")
        await agent.approve_plan(comment="Looks good, proceed!")

        # Execute the approved plan
        print("🚀 Executing approved plan...\n")
        result = await agent.execute_plan()

        print("=" * 60)
        print("EXECUTION COMPLETE")
        print("=" * 60)
        print(f"\n{result.final_output}")
        print(f"\n⏱️ Execution Time: {result.execution_time:.2f}s")

    except PlanApprovalRequired as e:
        print("\n⚠️ Plan requires approval before execution!")
        print(e.display)
        print("\nCall agent.approve_plan() to approve, or agent.reject_plan() to reject.")


async def plan_with_dependencies_example():
    """Plan with dependencies example"""
    print("\n" + "=" * 60)
    print("WISDOM COUNCIL AGENT - Plan Dependencies Example")
    print("=" * 60)

    from wisdom_council import PlanManager, PlanStatus

    # Create a plan manager directly for fine-grained control
    manager = PlanManager(plans_dir="./plans")

    # Create a plan with explicit dependencies
    plan = await manager.create_plan(
        name="Database Migration",
        description="Migrate database schema with zero downtime",
        auto_submit=False,  # Don't auto-submit for approval
        items=[
            {
                "title": "Backup current database",
                "description": "Create full backup of production database",
                "temp_id": "backup",
                "priority": 1
            },
            {
                "title": "Create new schema version",
                "description": "Apply migration scripts to create new tables",
                "temp_id": "schema",
                "dependencies": ["backup"],  # Must complete backup first
                "priority": 2
            },
            {
                "title": "Migrate data",
                "description": "Copy data from old tables to new schema",
                "temp_id": "migrate",
                "dependencies": ["schema"],  # Must create schema first
                "priority": 2
            },
            {
                "title": "Update application config",
                "description": "Point application to new schema",
                "temp_id": "config",
                "dependencies": ["migrate"],
                "priority": 3
            },
            {
                "title": "Verify migration",
                "description": "Run integrity checks on migrated data",
                "temp_id": "verify",
                "dependencies": ["config"],
                "priority": 3
            },
            {
                "title": "Remove old schema",
                "description": "Drop old tables after verification",
                "temp_id": "cleanup",
                "dependencies": ["verify"],
                "priority": 4
            }
        ]
    )

    # Display the plan
    print("\n" + plan.display(show_details=True))

    # Submit for approval
    await manager.submit_for_approval(plan.id)
    print("\n>>> Plan submitted for approval!")

    # Simulate approval
    await manager.approve(plan.id, comment="Migration plan approved")
    print(">>> Plan approved!\n")

    # Show ready items (items with no pending dependencies)
    plan = await manager.get_plan(plan.id)
    ready = plan.get_ready_items()
    print(f"Items ready to execute: {[item.title for item in ready]}")

    # Simulate executing items
    print("\n🚀 Simulating execution...\n")

    while True:
        next_item = await manager.get_next_item(plan.id)
        if not next_item:
            break

        print(f"  Starting: {next_item.title}")
        await manager.start_item(plan.id, next_item.id)

        # Simulate work...
        await asyncio.sleep(0.5)

        await manager.complete_item(
            plan.id, next_item.id,
            result=f"Completed {next_item.title}"
        )
        print(f"  Completed: {next_item.title}")

    # Final status
    plan = await manager.get_plan(plan.id)
    print("\n" + plan.display(show_details=False))


async def resume_example():
    """Checkpoint and resume example"""
    print("\n" + "=" * 60)
    print("WISDOM COUNCIL AGENT - Resume Example")
    print("=" * 60)
    
    from wisdom_council.checkpoint import SqliteCheckpointer
    
    # Create checkpointer
    checkpointer = SqliteCheckpointer(db_path="./checkpoints")

    agent = WisdomCouncilAgent(checkpointer=checkpointer)

    # Ask user for their task
    print("\nWhat would you like the Wisdom Council to help you with?")
    task = input("Your task: ").strip()

    if not task:
        print("No task provided. Using example task.")
        task = "Analyze portfolio of 25 projects and create health dashboard"

    thread_id = "demo-thread-001"

    print(f"\n📋 Task: {task}")
    print(f"🧵 Thread ID: {thread_id}")
    
    try:
        # Start the task
        result = await agent.run(task, thread_id=thread_id)
        print(f"\n✅ Completed: {result.final_output[:200]}...")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("🔄 Attempting to resume from checkpoint...")
        
        # Resume from last checkpoint
        result = await agent.resume(thread_id)
        print(f"\n✅ Resumed and completed: {result.final_output[:200]}...")


async def main():
    """Run examples with full transparency"""
    print("\n" + "🏛️ " * 20)
    print("\n   WISDOM COUNCIL AGENT\n")
    print("🏛️ " * 20 + "\n")

    print("Choose how to run:")
    print("  1. Basic (shows full deliberation after completion)")
    print("  2. Streaming (watch deliberation in real-time) [RECOMMENDED]")
    print("  3. Plan example (with approval workflow)")
    print()
    choice = input("Enter choice (1-3) [default: 2]: ").strip() or "2"

    if choice == "1":
        await basic_example()
    elif choice == "2":
        await streaming_example()
    elif choice == "3":
        await plan_example()
    else:
        print(f"Invalid choice: {choice}")
        return

    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)
    print("\nTIP: For the full CLI with more options, install and run:")
    print("     pip install -e .")
    print("     wisdom-council --help")


if __name__ == "__main__":
    asyncio.run(main())
