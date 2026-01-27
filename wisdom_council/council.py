"""
Wisdom Council - Council Implementation

The deliberation body that debates and synthesizes decisions.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional
from enum import Enum


class HeadType(Enum):
    """Types of council heads"""
    ARCHITECT = "architect"
    ORACLE = "oracle"
    GUARDIAN = "guardian"
    SYNTHESIZER = "synthesizer"
    CUSTOM = "custom"


@dataclass
class Proposal:
    """A proposal from a council head"""
    head: str
    content: str
    reasoning: str
    concerns: list[str]
    questions: list[str]
    confidence: float
    tokens_used: int = 0
    
    def to_dict(self) -> dict:
        return {
            "head": self.head,
            "content": self.content,
            "reasoning": self.reasoning,
            "concerns": self.concerns,
            "questions": self.questions,
            "confidence": self.confidence
        }


@dataclass
class Critique:
    """A critique of proposals from a council head"""
    head: str
    agreements: list[str]
    concerns: list[str]
    suggested_changes: list[str]
    questions: list[str]
    tokens_used: int = 0
    
    def to_dict(self) -> dict:
        return {
            "head": self.head,
            "agreements": self.agreements,
            "concerns": self.concerns,
            "suggested_changes": self.suggested_changes,
            "questions": self.questions
        }


@dataclass
class ConstitutionCheck:
    """Result of checking a plan against a head's constitution"""
    head: str
    passed: bool
    violations: list[str]
    warnings: list[str]
    
    def to_dict(self) -> dict:
        return {
            "head": self.head,
            "passed": self.passed,
            "violations": self.violations,
            "warnings": self.warnings
        }


@dataclass
class DeliberationRound:
    """Record of one round of deliberation"""
    number: int
    proposals: dict[str, Proposal]
    critiques: dict[str, Critique]
    has_consensus: bool
    
    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "proposals": {k: v.to_dict() for k, v in self.proposals.items()},
            "critiques": {k: v.to_dict() for k, v in self.critiques.items()},
            "has_consensus": self.has_consensus
        }


@dataclass
class CouncilDecision:
    """Final decision from the council"""
    approved: bool
    plan: dict
    dissents: list[dict]
    synthesis_reasoning: str
    rounds: list[DeliberationRound]
    guardian_review: Optional[ConstitutionCheck] = None
    tokens_used: int = 0
    
    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "plan": self.plan,
            "dissents": self.dissents,
            "synthesis_reasoning": self.synthesis_reasoning,
            "rounds": [r.to_dict() for r in self.rounds],
            "guardian_review": self.guardian_review.to_dict() if self.guardian_review else None,
            "tokens_used": self.tokens_used
        }


@dataclass
class ReviewResult:
    """Result of reviewing execution results"""
    approved: bool
    needs_revision: bool
    feedback: str
    issues: list[str]
    tokens_used: int = 0


@dataclass
class StreamEvent:
    """Event during streaming deliberation"""
    head: str
    content: str
    event_type: str  # proposal, critique, synthesis
    metadata: dict = field(default_factory=dict)


class CouncilHead(ABC):
    """
    Base class for council head implementations.
    
    Each council head has:
    - A name and type
    - A model configuration
    - A constitution (list of principles)
    - A system prompt
    - Optional veto power
    """
    
    def __init__(
        self,
        name: str,
        head_type: HeadType,
        model: str,
        temperature: float,
        constitution: list[str],
        system_prompt: str,
        veto_power: bool = False,
        config: dict = None
    ):
        self.name = name
        self.head_type = head_type
        self.model = model
        self.temperature = temperature
        self.constitution = constitution
        self.system_prompt = system_prompt
        self.veto_power = veto_power
        self.config = config or {}
        
        # Initialize LLM client
        self._llm = self._init_llm()
    
    def _init_llm(self):
        """Initialize the LLM client based on provider"""
        provider = self.config.get("provider", "ollama")
        
        if provider == "ollama":
            from wisdom_council.llm import OllamaClient
            return OllamaClient(
                model=self.model,
                temperature=self.temperature
            )
        elif provider == "openai":
            from wisdom_council.llm import OpenAIClient
            return OpenAIClient(
                model=self.model,
                temperature=self.temperature
            )
        elif provider == "anthropic":
            from wisdom_council.llm import AnthropicClient
            return AnthropicClient(
                model=self.model,
                temperature=self.temperature
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @abstractmethod
    async def propose(self, task: str, context: dict) -> Proposal:
        """Generate initial proposal for a task"""
        pass
    
    @abstractmethod
    async def critique(self, task: str, proposals: dict[str, Proposal]) -> Critique:
        """Critique other heads' proposals"""
        pass
    
    @abstractmethod
    async def revise(self, proposal: Proposal, critiques: list[Critique]) -> Proposal:
        """Revise proposal based on critiques"""
        pass
    
    async def evaluate_constitution(self, plan: dict) -> ConstitutionCheck:
        """Check if plan satisfies this head's constitution"""
        prompt = f"""
        Evaluate this plan against your constitution.
        
        YOUR CONSTITUTION:
        {self._format_constitution()}
        
        PLAN TO EVALUATE:
        {plan}
        
        For each principle in your constitution, determine if the plan:
        - Satisfies it (OK)
        - Violates it (VIOLATION)
        - Partially addresses it (WARNING)
        
        Format your response as:
        PASSED: true/false
        VIOLATIONS: [list any violations]
        WARNINGS: [list any warnings]
        """
        
        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_constitution_check(response)
    
    def _format_constitution(self) -> str:
        """Format constitution as numbered list"""
        return "\n".join(f"{i+1}. {c}" for i, c in enumerate(self.constitution))
    
    def _parse_constitution_check(self, response: str) -> ConstitutionCheck:
        """Parse constitution check response"""
        # Simple parsing - in production, use structured output
        passed = "PASSED: true" in response.lower()
        violations = []
        warnings = []
        
        if "VIOLATIONS:" in response:
            violations_section = response.split("VIOLATIONS:")[1]
            if "WARNINGS:" in violations_section:
                violations_section = violations_section.split("WARNINGS:")[0]
            violations = [v.strip() for v in violations_section.strip().split("\n") if v.strip()]
        
        if "WARNINGS:" in response:
            warnings_section = response.split("WARNINGS:")[1]
            warnings = [w.strip() for w in warnings_section.strip().split("\n") if w.strip()]
        
        return ConstitutionCheck(
            head=self.name,
            passed=passed,
            violations=violations,
            warnings=warnings
        )


class WisdomCouncil:
    """
    The deliberation body that debates and synthesizes decisions.
    
    The council consists of multiple heads (Architect, Oracle, Guardian, etc.)
    that each bring different perspectives. They engage in multi-round debate
    before the Synthesizer creates a unified plan.
    """
    
    def __init__(
        self,
        heads: list[CouncilHead],
        synthesizer: CouncilHead,
        max_rounds: int = 3,
        consensus_threshold: float = 0.8
    ):
        self.heads = heads
        self.synthesizer = synthesizer
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        
        # Find guardian (if any) for veto checks
        self.guardian = next(
            (h for h in heads if h.veto_power),
            None
        )
        
        # State for streaming
        self._current_decision = None
        self._deliberation_rounds = []
    
    async def deliberate(self, task: str, context: dict) -> CouncilDecision:
        """
        Run multi-round deliberation between council heads.
        
        Args:
            task: The task to deliberate on
            context: Additional context (memories, user info, etc.)
            
        Returns:
            CouncilDecision with approved plan and deliberation history
        """
        self._deliberation_rounds = []
        total_tokens = 0
        
        # Round 1: Independent proposals
        proposals = {}
        for head in self.heads:
            proposal = await head.propose(task, context)
            proposals[head.name] = proposal
            total_tokens += proposal.tokens_used
        
        # Rounds 2-N: Dialectic exchange
        for round_num in range(self.max_rounds):
            critiques = {}
            
            # Each head critiques others
            for head in self.heads:
                other_proposals = {k: v for k, v in proposals.items() if k != head.name}
                critique = await head.critique(task, other_proposals)
                critiques[head.name] = critique
                total_tokens += critique.tokens_used
            
            # Record round
            has_consensus = self._check_consensus(critiques)
            self._deliberation_rounds.append(DeliberationRound(
                number=round_num + 1,
                proposals=proposals.copy(),
                critiques=critiques,
                has_consensus=has_consensus
            ))
            
            # Check for early consensus
            if has_consensus:
                break
            
            # Revise proposals based on critiques
            for head in self.heads:
                relevant_critiques = [c for name, c in critiques.items() if name != head.name]
                proposals[head.name] = await head.revise(
                    proposals[head.name],
                    relevant_critiques
                )
                total_tokens += proposals[head.name].tokens_used
        
        # Synthesis
        synthesis = await self._synthesize(task, proposals, critiques)
        total_tokens += synthesis.get("tokens_used", 0)
        
        # Guardian veto check
        guardian_review = None
        if self.guardian:
            guardian_review = await self.guardian.evaluate_constitution(synthesis["plan"])
            total_tokens += 500  # Estimate
            
            if not guardian_review.passed:
                # Attempt to address veto
                synthesis = await self._address_veto(synthesis, guardian_review)
                total_tokens += synthesis.get("tokens_used", 0)
                
                # Re-check
                guardian_review = await self.guardian.evaluate_constitution(synthesis["plan"])
        
        # Collect any remaining dissents
        dissents = self._collect_dissents(critiques)
        
        decision = CouncilDecision(
            approved=guardian_review.passed if guardian_review else True,
            plan=synthesis["plan"],
            dissents=dissents,
            synthesis_reasoning=synthesis["reasoning"],
            rounds=self._deliberation_rounds,
            guardian_review=guardian_review,
            tokens_used=total_tokens
        )
        
        self._current_decision = decision
        return decision
    
    async def stream_deliberate(
        self,
        task: str,
        context: dict
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream deliberation events as they occur.
        
        Yields:
            StreamEvent for each head's contribution
        """
        self._deliberation_rounds = []
        
        # Round 1: Stream proposals
        proposals = {}
        for head in self.heads:
            yield StreamEvent(
                head=head.name,
                content=f"{head.name} is formulating proposal...",
                event_type="status"
            )
            
            proposal = await head.propose(task, context)
            proposals[head.name] = proposal
            
            yield StreamEvent(
                head=head.name,
                content=proposal.content,
                event_type="proposal",
                metadata={"reasoning": proposal.reasoning}
            )
        
        # Rounds 2-N: Stream critiques and revisions
        for round_num in range(self.max_rounds):
            yield StreamEvent(
                head="Council",
                content=f"--- Round {round_num + 1} ---",
                event_type="round_start"
            )
            
            critiques = {}
            for head in self.heads:
                other_proposals = {k: v for k, v in proposals.items() if k != head.name}
                critique = await head.critique(task, other_proposals)
                critiques[head.name] = critique
                
                yield StreamEvent(
                    head=head.name,
                    content=f"Agreements: {critique.agreements}\nConcerns: {critique.concerns}",
                    event_type="critique"
                )
            
            has_consensus = self._check_consensus(critiques)
            self._deliberation_rounds.append(DeliberationRound(
                number=round_num + 1,
                proposals=proposals.copy(),
                critiques=critiques,
                has_consensus=has_consensus
            ))
            
            if has_consensus:
                yield StreamEvent(
                    head="Council",
                    content="Consensus reached!",
                    event_type="consensus"
                )
                break
            
            # Stream revisions
            for head in self.heads:
                relevant_critiques = [c for name, c in critiques.items() if name != head.name]
                proposals[head.name] = await head.revise(proposals[head.name], relevant_critiques)
                
                yield StreamEvent(
                    head=head.name,
                    content=f"Revised: {proposals[head.name].content[:200]}...",
                    event_type="revision"
                )
        
        # Stream synthesis
        yield StreamEvent(
            head="Synthesizer",
            content="Creating unified plan...",
            event_type="status"
        )

        synthesis = await self._synthesize(task, proposals, critiques)
        total_tokens = synthesis.get("tokens_used", 0)

        yield StreamEvent(
            head="Synthesizer",
            content=synthesis["reasoning"],
            event_type="synthesis"
        )

        # Guardian veto check
        guardian_review = None
        if self.guardian:
            yield StreamEvent(
                head="Guardian",
                content="Reviewing plan against constitution...",
                event_type="status"
            )
            guardian_review = await self.guardian.evaluate_constitution(synthesis["plan"])
            total_tokens += 500  # Estimate

            if not guardian_review.passed:
                yield StreamEvent(
                    head="Guardian",
                    content=f"VETO: {guardian_review.violations}",
                    event_type="veto"
                )
                # Attempt to address veto
                synthesis = await self._address_veto(synthesis, guardian_review)
                total_tokens += synthesis.get("tokens_used", 0)
                # Re-check
                guardian_review = await self.guardian.evaluate_constitution(synthesis["plan"])
            else:
                yield StreamEvent(
                    head="Guardian",
                    content="Plan approved by Guardian",
                    event_type="approval"
                )

        # Collect any remaining dissents
        dissents = self._collect_dissents(critiques)

        # Create and store the final decision
        self._current_decision = CouncilDecision(
            approved=guardian_review.passed if guardian_review else True,
            plan=synthesis["plan"],
            dissents=dissents,
            synthesis_reasoning=synthesis["reasoning"],
            rounds=self._deliberation_rounds,
            guardian_review=guardian_review,
            tokens_used=total_tokens
        )

    async def get_decision(self) -> CouncilDecision:
        """Get the final decision after streaming"""
        return self._current_decision
    
    async def review(self, task: str, plan: dict, results: dict) -> ReviewResult:
        """
        Review execution results against original plan.
        
        Args:
            task: Original task
            plan: The plan that was executed
            results: Execution results
            
        Returns:
            ReviewResult with approval status and feedback
        """
        issues = []
        feedback_parts = []
        total_tokens = 0
        
        # Each head reviews from their perspective
        for head in self.heads:
            review = await head.evaluate_constitution({"plan": plan, "results": results})
            total_tokens += 500  # Estimate
            
            if not review.passed:
                issues.extend(review.violations)
            if review.warnings:
                feedback_parts.extend(review.warnings)
        
        needs_revision = len(issues) > 0
        
        return ReviewResult(
            approved=not needs_revision,
            needs_revision=needs_revision,
            feedback="\n".join(feedback_parts),
            issues=issues,
            tokens_used=total_tokens
        )
    
    def _check_consensus(self, critiques: dict[str, Critique]) -> bool:
        """Check if critiques indicate consensus"""
        # Simple heuristic: consensus if no major concerns
        total_concerns = sum(len(c.concerns) for c in critiques.values())
        max_concerns = len(self.heads) * 3  # Allow up to 3 concerns per head
        
        return total_concerns / max_concerns < (1 - self.consensus_threshold)
    
    async def _synthesize(
        self,
        task: str,
        proposals: dict[str, Proposal],
        critiques: dict[str, Critique]
    ) -> dict:
        """Create synthesis from all proposals and critiques"""
        prompt = f"""
        TASK: {task}
        
        COUNCIL PROPOSALS:
        {self._format_proposals(proposals)}
        
        CRITIQUES EXCHANGED:
        {self._format_critiques(critiques)}
        
        As the Synthesizer, create a unified plan that:
        1. Incorporates the best elements from each head
        2. Addresses the concerns raised
        3. Resolves conflicts between perspectives
        4. Results in an actionable, balanced approach
        
        Where heads disagree, explain your resolution.
        
        Format:
        UNIFIED_PLAN: [the merged approach as JSON]
        INCORPORATED_FROM_EACH: [what you took from each head]
        CONFLICT_RESOLUTIONS: [how you resolved disagreements]
        FINAL_REASONING: [why this synthesis is optimal]
        """
        
        response = await self.synthesizer._llm.invoke(
            system_prompt=self.synthesizer.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_synthesis(response)
    
    async def _address_veto(self, synthesis: dict, veto: ConstitutionCheck) -> dict:
        """Attempt to address guardian veto"""
        prompt = f"""
        The Guardian has VETOED the current plan.
        
        VIOLATIONS:
        {veto.violations}
        
        CURRENT PLAN:
        {synthesis['plan']}
        
        Modify the plan to address ALL violations while preserving
        the core intent. If a violation cannot be addressed, explain why.
        
        Format:
        MODIFIED_PLAN: [updated plan as JSON]
        CHANGES_MADE: [what was changed]
        UNRESOLVED: [any violations that couldn't be addressed]
        """
        
        response = await self.synthesizer._llm.invoke(
            system_prompt=self.synthesizer.system_prompt,
            user_prompt=prompt
        )
        
        modified = self._parse_synthesis(response)
        modified["veto_addressed"] = True
        return modified
    
    def _collect_dissents(self, critiques: dict[str, Critique]) -> list[dict]:
        """Collect unresolved concerns as dissents"""
        dissents = []
        for head_name, critique in critiques.items():
            if critique.concerns:
                dissents.append({
                    "head": head_name,
                    "concerns": critique.concerns
                })
        return dissents
    
    def _format_proposals(self, proposals: dict[str, Proposal]) -> str:
        """Format proposals for prompt"""
        parts = []
        for name, prop in proposals.items():
            parts.append(f"""
            {name.upper()}:
            Proposal: {prop.content}
            Reasoning: {prop.reasoning}
            Concerns: {prop.concerns}
            """)
        return "\n".join(parts)
    
    def _format_critiques(self, critiques: dict[str, Critique]) -> str:
        """Format critiques for prompt"""
        parts = []
        for name, crit in critiques.items():
            parts.append(f"""
            {name.upper()} says:
            Agreements: {crit.agreements}
            Concerns: {crit.concerns}
            Suggestions: {crit.suggested_changes}
            """)
        return "\n".join(parts)
    
    def _parse_synthesis(self, response: str) -> dict:
        """Parse synthesis response"""
        # Simple parsing - in production, use structured output
        plan = {}
        reasoning = ""
        
        if "UNIFIED_PLAN:" in response:
            plan_section = response.split("UNIFIED_PLAN:")[1]
            # Try to extract JSON-like content
            # In production, use proper JSON parsing
            plan = {"raw": plan_section.split("INCORPORATED")[0].strip()}
        
        if "FINAL_REASONING:" in response:
            reasoning = response.split("FINAL_REASONING:")[1].strip()
        
        return {
            "plan": plan,
            "reasoning": reasoning,
            "tokens_used": len(response.split()) * 2  # Rough estimate
        }
