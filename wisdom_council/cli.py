#!/usr/bin/env python3
"""
Wisdom Council Agent - CLI with Full Transparency

A proper CLI that shows what's happening in real-time, including:
- Full proposals from each council head
- Complete reasoning and concerns
- Guardian veto reasons (violations and warnings)
- Real-time streaming of deliberation
"""

import asyncio
import argparse
import sys
from enum import Enum
from typing import Optional

from wisdom_council import WisdomCouncilAgent
from wisdom_council.council import CouncilDecision, Proposal, Critique, ConstitutionCheck


class VerbosityLevel(Enum):
    """Verbosity levels for output"""
    QUIET = 0      # Minimal output
    NORMAL = 1     # Default - summary output
    VERBOSE = 2    # Full details
    DEBUG = 3      # Everything including internal state


class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Head colors
    ARCHITECT = "\033[94m"  # Blue
    ORACLE = "\033[95m"     # Magenta
    GUARDIAN = "\033[91m"   # Red
    SYNTHESIZER = "\033[92m"  # Green

    # Status colors
    SUCCESS = "\033[92m"
    WARNING = "\033[93m"
    ERROR = "\033[91m"
    INFO = "\033[96m"

    @classmethod
    def head_color(cls, head_name: str) -> str:
        colors = {
            "Architect": cls.ARCHITECT,
            "Oracle": cls.ORACLE,
            "Guardian": cls.GUARDIAN,
            "Synthesizer": cls.SYNTHESIZER,
        }
        return colors.get(head_name, cls.RESET)


def print_header(text: str, char: str = "="):
    """Print a header line"""
    width = 70
    print(f"\n{char * width}")
    print(f" {text}")
    print(f"{char * width}\n")


def print_subheader(text: str):
    """Print a subheader"""
    print(f"\n{Colors.BOLD}--- {text} ---{Colors.RESET}\n")


def format_proposal(head: str, proposal: Proposal, verbosity: VerbosityLevel) -> str:
    """Format a proposal for display"""
    color = Colors.head_color(head)
    lines = []

    if verbosity == VerbosityLevel.QUIET:
        return f"{color}{head}{Colors.RESET}: {proposal.content[:100]}..."

    lines.append(f"{color}{Colors.BOLD}{head}{Colors.RESET}")
    lines.append(f"{Colors.DIM}{'─' * 40}{Colors.RESET}")

    if verbosity.value >= VerbosityLevel.NORMAL.value:
        lines.append(f"{Colors.BOLD}Proposal:{Colors.RESET}")
        lines.append(f"  {proposal.content}")

    if verbosity.value >= VerbosityLevel.VERBOSE.value:
        lines.append(f"\n{Colors.BOLD}Reasoning:{Colors.RESET}")
        lines.append(f"  {proposal.reasoning}")

        if proposal.concerns:
            lines.append(f"\n{Colors.WARNING}Concerns:{Colors.RESET}")
            for concern in proposal.concerns:
                lines.append(f"  - {concern}")

        if proposal.questions:
            lines.append(f"\n{Colors.INFO}Questions:{Colors.RESET}")
            for question in proposal.questions:
                lines.append(f"  ? {question}")

        lines.append(f"\n{Colors.DIM}Confidence: {proposal.confidence:.0%}{Colors.RESET}")

    return "\n".join(lines)


def format_critique(head: str, critique: Critique, verbosity: VerbosityLevel) -> str:
    """Format a critique for display"""
    color = Colors.head_color(head)
    lines = []

    if verbosity == VerbosityLevel.QUIET:
        return ""

    lines.append(f"{color}{head}'s Critique:{Colors.RESET}")

    if verbosity.value >= VerbosityLevel.NORMAL.value:
        if critique.agreements:
            lines.append(f"  {Colors.SUCCESS}Agrees with:{Colors.RESET}")
            for agreement in critique.agreements[:3]:  # Limit in normal mode
                lines.append(f"    + {agreement}")

        if critique.concerns:
            lines.append(f"  {Colors.WARNING}Concerns:{Colors.RESET}")
            for concern in critique.concerns:
                lines.append(f"    ! {concern}")

    if verbosity.value >= VerbosityLevel.VERBOSE.value:
        if critique.suggested_changes:
            lines.append(f"  {Colors.INFO}Suggested Changes:{Colors.RESET}")
            for change in critique.suggested_changes:
                lines.append(f"    -> {change}")

        if critique.questions:
            lines.append(f"  Questions:")
            for question in critique.questions:
                lines.append(f"    ? {question}")

    return "\n".join(lines)


def format_guardian_review(review: ConstitutionCheck, verbosity: VerbosityLevel) -> str:
    """Format Guardian's constitutional review"""
    lines = []

    if review.passed:
        lines.append(f"{Colors.SUCCESS}{Colors.BOLD}GUARDIAN REVIEW: APPROVED{Colors.RESET}")
    else:
        lines.append(f"{Colors.ERROR}{Colors.BOLD}GUARDIAN REVIEW: VETOED{Colors.RESET}")

    # Always show violations when vetoed
    if not review.passed or verbosity.value >= VerbosityLevel.VERBOSE.value:
        if review.violations:
            lines.append(f"\n{Colors.ERROR}Constitutional Violations:{Colors.RESET}")
            for violation in review.violations:
                lines.append(f"  {Colors.ERROR}X{Colors.RESET} {violation}")

    # Show warnings
    if review.warnings and verbosity.value >= VerbosityLevel.NORMAL.value:
        lines.append(f"\n{Colors.WARNING}Warnings:{Colors.RESET}")
        for warning in review.warnings:
            lines.append(f"  {Colors.WARNING}!{Colors.RESET} {warning}")

    return "\n".join(lines)


def display_deliberation(decision: CouncilDecision, verbosity: VerbosityLevel):
    """Display the full deliberation process"""

    print_header("COUNCIL DELIBERATION")

    for round_data in decision.rounds:
        print_subheader(f"Round {round_data.number}")

        # Show proposals
        print(f"{Colors.BOLD}Proposals:{Colors.RESET}\n")
        for head, proposal in round_data.proposals.items():
            print(format_proposal(head, proposal, verbosity))
            print()

        # Show critiques
        if verbosity.value >= VerbosityLevel.NORMAL.value and round_data.critiques:
            print(f"\n{Colors.BOLD}Critiques:{Colors.RESET}\n")
            for head, critique in round_data.critiques.items():
                formatted = format_critique(head, critique, verbosity)
                if formatted:
                    print(formatted)
                    print()

        # Consensus check
        if round_data.has_consensus:
            print(f"{Colors.SUCCESS}>>> Consensus reached! <<<{Colors.RESET}\n")

    # Synthesis reasoning
    if verbosity.value >= VerbosityLevel.VERBOSE.value:
        print_subheader("Synthesis")
        print(f"{Colors.BOLD}Synthesizer's Reasoning:{Colors.RESET}")
        print(f"  {decision.synthesis_reasoning}")

    # Guardian review - ALWAYS show details when vetoed
    if decision.guardian_review:
        print()
        print(format_guardian_review(decision.guardian_review, verbosity))

    # Dissents
    if decision.dissents and verbosity.value >= VerbosityLevel.NORMAL.value:
        print_subheader("Remaining Dissents")
        for dissent in decision.dissents:
            print(f"  {Colors.head_color(dissent['head'])}{dissent['head']}{Colors.RESET}:")
            for concern in dissent['concerns']:
                print(f"    - {concern}")


async def run_streaming(agent: WisdomCouncilAgent, task: str, verbosity: VerbosityLevel):
    """Run with streaming output showing real-time deliberation"""

    print_header("COUNCIL DELIBERATION (Live)")
    print(f"{Colors.DIM}Watching council deliberate in real-time...{Colors.RESET}\n")

    current_round = 0

    async for event in agent.stream(task):
        if event.type == "memory_retrieval":
            # Show what memories were retrieved
            memories = event.metadata.get("memories", [])
            count = event.metadata.get("count", 0)
            print(f"\n{Colors.INFO}🧠 MEMORY RETRIEVAL:{Colors.RESET}")
            if count == 0:
                print(f"   {Colors.DIM}(No relevant memories found - fresh context){Colors.RESET}")
            else:
                print(f"   Found {count} relevant memories:")
                for i, mem in enumerate(memories, 1):
                    content_preview = mem['content'][:80] + "..." if len(mem['content']) > 80 else mem['content']
                    print(f"   {i}. [{Colors.BOLD}{mem['source']}{Colors.RESET}] {content_preview}")
                    print(f"      {Colors.DIM}Importance: {mem['importance']:.0%} | {mem['timestamp']}{Colors.RESET}")
            print()

        elif event.type == "status":
            print(f"{Colors.INFO}[STATUS]{Colors.RESET} {event.content}")

        elif event.type == "council_deliberation":
            head = event.head or "Council"
            color = Colors.head_color(head)

            # Check for round markers
            if "Round" in event.content:
                current_round += 1
                print(f"\n{Colors.BOLD}{'─' * 50}{Colors.RESET}")
                print(f"{Colors.BOLD}Round {current_round}{Colors.RESET}")
                print(f"{Colors.BOLD}{'─' * 50}{Colors.RESET}\n")
            elif event.content == "Consensus reached!":
                print(f"\n{Colors.SUCCESS}>>> {event.content} <<<{Colors.RESET}\n")
            else:
                # Regular deliberation content
                print(f"{color}[{head}]{Colors.RESET}")

                # Show full content in verbose mode
                if verbosity.value >= VerbosityLevel.VERBOSE.value:
                    print(f"  {event.content}")
                    if event.metadata:
                        if "reasoning" in event.metadata:
                            print(f"  {Colors.DIM}Reasoning: {event.metadata['reasoning']}{Colors.RESET}")
                else:
                    # Truncate in normal mode
                    content = event.content[:200] + "..." if len(event.content) > 200 else event.content
                    print(f"  {content}")
                print()

        elif event.type == "execution_step":
            step = event.step or "?"
            print(f"{Colors.INFO}[Step {step}]{Colors.RESET} {event.content}")

        elif event.type == "final_output":
            print_header("RESULT")
            print(event.content)


async def run_standard(agent: WisdomCouncilAgent, task: str, verbosity: VerbosityLevel):
    """Run with standard (non-streaming) output"""

    print(f"\n{Colors.INFO}Council deliberating...{Colors.RESET}")
    print(f"{Colors.DIM}(Use --stream for real-time updates){Colors.RESET}\n")

    result = await agent.run(task)

    # Display deliberation
    display_deliberation(result.deliberation, verbosity)

    # Display result
    print_header("RESULT")
    print(result.final_output)

    # Metrics
    print(f"\n{Colors.DIM}{'─' * 50}{Colors.RESET}")
    print(f"{Colors.DIM}Execution Time: {result.execution_time:.2f}s{Colors.RESET}")
    print(f"{Colors.DIM}Tokens Used: {result.tokens_used:,}{Colors.RESET}")


async def main():
    parser = argparse.ArgumentParser(
        description="Wisdom Council Agent - Multi-head AI deliberation system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wisdom-council "Design a database schema for an e-commerce site"
  wisdom-council --verbose "Create a security audit plan"
  wisdom-council --stream "Analyze this code for bugs"
  wisdom-council --debug "Complex multi-step task"

Verbosity Levels:
  (default)   Summary output with key decisions
  --verbose   Full proposals, reasoning, and concerns
  --debug     Everything including internal state
  --quiet     Minimal output, just the result
        """
    )

    parser.add_argument(
        "task",
        nargs="?",
        help="The task for the council to deliberate on"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show full deliberation details"
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Show debug-level output"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output"
    )

    parser.add_argument(
        "-s", "--stream",
        action="store_true",
        help="Stream deliberation in real-time"
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )

    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    # Disable colors if requested
    if args.no_color:
        for attr in dir(Colors):
            if not attr.startswith("_") and attr != "head_color":
                setattr(Colors, attr, "")

    # Determine verbosity
    if args.debug:
        verbosity = VerbosityLevel.DEBUG
    elif args.verbose:
        verbosity = VerbosityLevel.VERBOSE
    elif args.quiet:
        verbosity = VerbosityLevel.QUIET
    else:
        verbosity = VerbosityLevel.NORMAL

    # Get task
    task = args.task
    if not task:
        print_header("WISDOM COUNCIL AGENT")
        print("What would you like the council to help you with?\n")
        task = input("Your task: ").strip()

        if not task:
            print(f"{Colors.ERROR}No task provided. Exiting.{Colors.RESET}")
            sys.exit(1)

    print_header("WISDOM COUNCIL AGENT")
    print(f"{Colors.BOLD}Task:{Colors.RESET} {task}\n")

    # Initialize agent
    agent = WisdomCouncilAgent(config_path=args.config)

    # Run
    try:
        if args.stream:
            await run_streaming(agent, task, verbosity)
        else:
            await run_standard(agent, task, verbosity)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Interrupted by user.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.ERROR}Error: {e}{Colors.RESET}")
        if verbosity == VerbosityLevel.DEBUG:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def cli():
    """Entry point for the CLI"""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
