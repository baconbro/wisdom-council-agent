#!/usr/bin/env python3
"""
Wisdom Council Agent - Quick Start Example

This example demonstrates basic usage of the Wisdom Council Agent.
"""

import asyncio
from wisdom_council import WisdomCouncilAgent


async def basic_example():
    """Basic usage example"""
    print("=" * 60)
    print("WISDOM COUNCIL AGENT - Basic Example")
    print("=" * 60)
    
    # Initialize agent with default configuration
    agent = WisdomCouncilAgent()
    
    # Define a task
    task = """
    Create a project management framework for a university IT department
    that needs to manage 25 concurrent projects across 6 domains:
    Finance, HR, Student Systems, Research, Infrastructure, and Data Analytics.
    """
    
    # Run the task
    print("\n📋 Task:", task.strip())
    print("\n🏛️ Council deliberating...\n")
    
    result = await agent.run(task)
    
    # Display results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\n📊 Final Output:\n{result.final_output}")
    print(f"\n⏱️ Execution Time: {result.execution_time:.2f}s")
    print(f"🔢 Tokens Used: {result.tokens_used}")
    
    # Show deliberation summary
    print("\n" + "=" * 60)
    print("COUNCIL DELIBERATION SUMMARY")
    print("=" * 60)
    
    for round in result.deliberation.rounds:
        print(f"\n--- Round {round.number} ---")
        for head, proposal in round.proposals.items():
            print(f"  {head}: {proposal.content[:100]}...")
        print(f"  Consensus: {'Yes' if round.has_consensus else 'No'}")
    
    print(f"\n🔒 Guardian Review: {'Approved' if result.deliberation.guardian_review.passed else 'VETOED'}")
    
    if result.deliberation.dissents:
        print("\n⚠️ Dissents:")
        for dissent in result.deliberation.dissents:
            print(f"  - {dissent['head']}: {dissent['concerns']}")


async def streaming_example():
    """Streaming output example"""
    print("\n" + "=" * 60)
    print("WISDOM COUNCIL AGENT - Streaming Example")
    print("=" * 60)
    
    agent = WisdomCouncilAgent()
    
    task = "Design a risk assessment methodology for IT projects"
    print(f"\n📋 Task: {task}\n")
    
    async for event in agent.stream(task):
        if event.type == "council_deliberation":
            print(f"🗣️ [{event.head}]: {event.content[:150]}...")
        elif event.type == "status":
            print(f"📌 {event.content}")
        elif event.type == "execution_step":
            print(f"⚙️ Step {event.step}: {event.content[:100]}...")
        elif event.type == "final_output":
            print(f"\n✅ Result: {event.content[:500]}...")


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
    
    result = await agent.run(
        "Design an AI governance framework for enterprise deployment"
    )
    
    print(f"\n✅ Result: {result.final_output[:500]}...")


async def resume_example():
    """Checkpoint and resume example"""
    print("\n" + "=" * 60)
    print("WISDOM COUNCIL AGENT - Resume Example")
    print("=" * 60)
    
    from wisdom_council.checkpoint import SqliteCheckpointer
    
    # Create checkpointer
    checkpointer = SqliteCheckpointer(db_path="./checkpoints")
    
    agent = WisdomCouncilAgent(checkpointer=checkpointer)
    
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
    """Run all examples"""
    print("\n" + "🏛️ " * 20)
    print("\n   WISDOM COUNCIL AGENT - EXAMPLES\n")
    print("🏛️ " * 20 + "\n")
    
    # Run basic example
    await basic_example()
    
    # Uncomment to run other examples:
    # await streaming_example()
    # await custom_council_example()
    # await resume_example()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
