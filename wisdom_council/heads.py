"""
Wisdom Council - Council Head Implementations

Specific implementations for Architect, Oracle, Guardian, and Synthesizer.
"""

from wisdom_council.council import CouncilHead, HeadType, Proposal, Critique


# Default constitutions
ARCHITECT_CONSTITUTION = [
    "Optimize for efficiency and measurability",
    "Prefer proven methods over experimental ones",
    "Ensure all outputs are actionable and specific",
    "Minimize resource usage while maximizing output",
    "Every plan must have clear success criteria"
]

ORACLE_CONSTITUTION = [
    "Consider the human behind the request",
    "Look beyond stated needs to underlying needs",
    "Value wisdom over mere correctness",
    "Consider long-term consequences",
    "Simplicity often beats complexity"
]

GUARDIAN_CONSTITUTION = [
    "First, do no harm",
    "Protect privacy and confidentiality",
    "Ensure ethical alignment",
    "Flag potential negative consequences",
    "Verify alignment with stated values"
]

SYNTHESIZER_CONSTITUTION = [
    "Honor valid points from all perspectives",
    "Resolve conflicts explicitly, not by ignoring them",
    "Create actionable plans, not compromises",
    "Explain trade-offs transparently",
    "The output must be better than any single input"
]


class Architect(CouncilHead):
    """
    The Architect - Logic, precision, systematic planning.
    
    The Architect focuses on:
    - Feasibility and constraints
    - Optimal resource allocation
    - Clear metrics and milestones
    - Risk quantification
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are the Architect. Your role is to provide rigorous, logical, 
systematic analysis. You focus on:
- Feasibility and constraints
- Optimal resource allocation
- Clear metrics and milestones
- Risk quantification

Challenge vague thinking. Demand specificity.
Your output must always include: steps, timeline, resources, risks."""
    
    def __init__(self, config: dict = None):
        config = config or {}
        super().__init__(
            name="Architect",
            head_type=HeadType.ARCHITECT,
            model=config.get("model", "qwen3:235b"),
            temperature=config.get("temperature", 0.1),
            constitution=config.get("constitution", ARCHITECT_CONSTITUTION),
            system_prompt=config.get("system_prompt", self.DEFAULT_SYSTEM_PROMPT),
            veto_power=False,
            config=config
        )
    
    def _build_propose_prompt(self, task: str, context: dict) -> str:
        """Build the prompt for proposal generation"""
        return f"""
        TASK: {task}

        CONTEXT: {context}

        YOUR CONSTITUTION:
        {self._format_constitution()}

        Provide your proposal for how to approach this task.
        Apply rigorous logical analysis.

        Format your response:
        PROPOSAL: [your recommended approach with specific steps]
        REASONING: [logical justification]
        TIMELINE: [estimated timeline with milestones]
        RESOURCES: [resources required]
        RISKS: [potential risks and mitigations]
        CONCERNS: [what could go wrong]
        QUESTIONS: [what you'd ask other council members]
        CONFIDENCE: [0.0-1.0 confidence score]
        """

    async def propose(self, task: str, context: dict) -> Proposal:
        """Generate systematic, logical proposal"""
        prompt = self._build_propose_prompt(task, context)

        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )

        return self._parse_proposal(response)
    
    async def critique(self, task: str, proposals: dict[str, Proposal]) -> Critique:
        """Critique from efficiency and feasibility perspective"""
        prompt = f"""
        TASK: {task}
        
        OTHER COUNCIL MEMBERS PROPOSED:
        {self._format_other_proposals(proposals)}
        
        YOUR CONSTITUTION:
        {self._format_constitution()}
        
        Critique these proposals from your perspective.
        Focus on: efficiency, feasibility, measurability, risks.
        
        Format:
        AGREEMENTS: [what you support and why]
        CONCERNS: [what worries you from a logical/practical standpoint]
        SUGGESTED_CHANGES: [specific modifications to improve]
        QUESTIONS: [clarifications needed]
        """
        
        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_critique(response)
    
    async def revise(self, proposal: Proposal, critiques: list[Critique]) -> Proposal:
        """Revise proposal addressing valid critiques"""
        prompt = f"""
        YOUR ORIGINAL PROPOSAL:
        {proposal.content}
        
        CRITIQUES RECEIVED:
        {self._format_critiques(critiques)}
        
        Revise your proposal to address valid concerns while
        maintaining logical rigor and feasibility.
        
        Format your response:
        PROPOSAL: [revised approach]
        REASONING: [how you addressed critiques]
        CHANGES_MADE: [what you changed and why]
        MAINTAINED: [what you kept and why]
        CONFIDENCE: [0.0-1.0]
        """
        
        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_proposal(response)
    
    def _format_other_proposals(self, proposals: dict[str, Proposal]) -> str:
        parts = []
        for name, prop in proposals.items():
            parts.append(f"{name}: {prop.content}")
        return "\n".join(parts)
    
    def _format_critiques(self, critiques: list[Critique]) -> str:
        parts = []
        for crit in critiques:
            parts.append(f"{crit.head}: Concerns: {crit.concerns}, Suggestions: {crit.suggested_changes}")
        return "\n".join(parts)
    
    def _parse_proposal(self, response: str) -> Proposal:
        """Parse proposal from LLM response"""
        # Simple parsing - use structured output in production
        content = response
        reasoning = ""
        concerns = []
        questions = []
        confidence = 0.8
        
        if "PROPOSAL:" in response:
            content = response.split("PROPOSAL:")[1].split("REASONING:")[0].strip()
        if "REASONING:" in response:
            reasoning = response.split("REASONING:")[1].split("CONCERNS:")[0].strip()
        if "CONCERNS:" in response:
            concerns_text = response.split("CONCERNS:")[1].split("QUESTIONS:")[0].strip()
            concerns = [c.strip() for c in concerns_text.split("\n") if c.strip()]
        if "QUESTIONS:" in response:
            questions_text = response.split("QUESTIONS:")[1].split("CONFIDENCE:")[0].strip()
            questions = [q.strip() for q in questions_text.split("\n") if q.strip()]
        if "CONFIDENCE:" in response:
            try:
                confidence = float(response.split("CONFIDENCE:")[1].strip()[:4])
            except:
                confidence = 0.8
        
        return Proposal(
            head=self.name,
            content=content,
            reasoning=reasoning,
            concerns=concerns,
            questions=questions,
            confidence=confidence,
            tokens_used=len(response.split()) * 2
        )
    
    def _parse_critique(self, response: str) -> Critique:
        """Parse critique from LLM response"""
        agreements = []
        concerns = []
        suggested_changes = []
        questions = []

        # Make parsing case-insensitive
        response_upper = response.upper()

        if "AGREEMENTS:" in response_upper:
            idx = response_upper.index("AGREEMENTS:")
            text_after = response[idx + len("AGREEMENTS:"):]
            # Find the next section
            for marker in ["CONCERNS:", "SUGGESTED_CHANGES:", "QUESTIONS:", "BLIND_SPOTS:"]:
                if marker in text_after.upper():
                    marker_idx = text_after.upper().index(marker)
                    text_after = text_after[:marker_idx]
                    break
            agreements = [a.strip() for a in text_after.strip().split("\n") if a.strip() and not a.strip().startswith("-") == False]
            agreements = [a.lstrip("- •*").strip() for a in text_after.strip().split("\n") if a.strip()]

        if "CONCERNS:" in response_upper:
            idx = response_upper.index("CONCERNS:")
            text_after = response[idx + len("CONCERNS:"):]
            for marker in ["SUGGESTED_CHANGES:", "QUESTIONS:", "BLIND_SPOTS:", "AGREEMENTS:"]:
                if marker in text_after.upper():
                    marker_idx = text_after.upper().index(marker)
                    text_after = text_after[:marker_idx]
                    break
            concerns = [c.lstrip("- •*").strip() for c in text_after.strip().split("\n") if c.strip()]

        if "SUGGESTED_CHANGES:" in response_upper or "SUGGESTED CHANGES:" in response_upper:
            marker = "SUGGESTED_CHANGES:" if "SUGGESTED_CHANGES:" in response_upper else "SUGGESTED CHANGES:"
            idx = response_upper.index(marker)
            text_after = response[idx + len(marker):]
            for m in ["QUESTIONS:", "CONCERNS:", "AGREEMENTS:"]:
                if m in text_after.upper():
                    marker_idx = text_after.upper().index(m)
                    text_after = text_after[:marker_idx]
                    break
            suggested_changes = [s.lstrip("- •*").strip() for s in text_after.strip().split("\n") if s.strip()]

        if "QUESTIONS:" in response_upper:
            idx = response_upper.index("QUESTIONS:")
            text_after = response[idx + len("QUESTIONS:"):]
            for marker in ["CONCERNS:", "AGREEMENTS:", "SUGGESTED"]:
                if marker in text_after.upper():
                    marker_idx = text_after.upper().index(marker)
                    text_after = text_after[:marker_idx]
                    break
            questions = [q.lstrip("- •*").strip() for q in text_after.strip().split("\n") if q.strip()]

        return Critique(
            head=self.name,
            agreements=agreements,
            concerns=concerns,
            suggested_changes=suggested_changes,
            questions=questions,
            tokens_used=len(response.split()) * 2
        )


class Oracle(CouncilHead):
    """
    The Oracle - Wisdom, intuition, human-centered perspective.
    
    The Oracle focuses on:
    - What does the human REALLY need?
    - What are they not saying?
    - What could go wrong emotionally/politically?
    - Is there a simpler path?
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are the Oracle. Your role is to provide wisdom, intuition, 
and human-centered perspective. You focus on:
- What does the human REALLY need?
- What are they not saying?
- What could go wrong emotionally/politically?
- Is there a simpler path?

Challenge assumptions. Ask "why?" and "for whom?"
Your output must always include: human considerations, 
potential blind spots, alternative framings."""
    
    def __init__(self, config: dict = None):
        config = config or {}
        super().__init__(
            name="Oracle",
            head_type=HeadType.ORACLE,
            model=config.get("model", "qwen3:235b"),
            temperature=config.get("temperature", 0.8),
            constitution=config.get("constitution", ORACLE_CONSTITUTION),
            system_prompt=config.get("system_prompt", self.DEFAULT_SYSTEM_PROMPT),
            veto_power=False,
            config=config
        )
    
    def _build_propose_prompt(self, task: str, context: dict) -> str:
        """Build the prompt for proposal generation"""
        return f"""
        TASK: {task}

        CONTEXT: {context}

        YOUR CONSTITUTION:
        {self._format_constitution()}

        Before proposing, consider:
        - What does the human REALLY need? (not just what they asked)
        - What emotions or politics might be at play?
        - What's the simplest path to genuine value?

        Format your response:
        UNDERLYING_NEED: [what the human actually needs]
        PROPOSAL: [your wisdom-centered approach]
        REASONING: [why this serves the human best]
        HUMAN_FACTORS: [emotional, political, cultural considerations]
        SIMPLER_ALTERNATIVE: [is there a simpler way?]
        CONCERNS: [potential blind spots]
        QUESTIONS: [what we should ask ourselves]
        CONFIDENCE: [0.0-1.0]
        """

    async def propose(self, task: str, context: dict) -> Proposal:
        """Generate wisdom-centered proposal"""
        prompt = self._build_propose_prompt(task, context)

        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )

        return self._parse_proposal(response)
    
    async def critique(self, task: str, proposals: dict[str, Proposal]) -> Critique:
        """Critique from wisdom and human-centered perspective"""
        prompt = f"""
        TASK: {task}
        
        OTHER COUNCIL MEMBERS PROPOSED:
        {self._format_other_proposals(proposals)}
        
        YOUR CONSTITUTION:
        {self._format_constitution()}
        
        Critique these proposals through the lens of wisdom.
        Ask: Does this truly serve the human? What's missing?
        
        Format:
        AGREEMENTS: [what resonates with wisdom]
        CONCERNS: [what might miss the human element]
        BLIND_SPOTS: [what the proposals don't see]
        SUGGESTED_CHANGES: [how to add wisdom]
        QUESTIONS: [deeper questions to consider]
        """
        
        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_critique(response)
    
    async def revise(self, proposal: Proposal, critiques: list[Critique]) -> Proposal:
        """Revise proposal integrating feedback with wisdom"""
        prompt = f"""
        YOUR ORIGINAL PROPOSAL:
        {proposal.content}
        
        CRITIQUES RECEIVED:
        {self._format_critiques(critiques)}
        
        Revise with wisdom. Integrate valid logical concerns while
        keeping the human at the center.
        
        Format:
        PROPOSAL: [revised wisdom-centered approach]
        REASONING: [how you balanced rigor with wisdom]
        WHAT_I_LEARNED: [insights from the critiques]
        CONFIDENCE: [0.0-1.0]
        """
        
        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_proposal(response)
    
    # Reuse parsing methods from Architect with minor variations
    _format_other_proposals = Architect._format_other_proposals
    _format_critiques = Architect._format_critiques
    _parse_proposal = Architect._parse_proposal
    _parse_critique = Architect._parse_critique


class Guardian(CouncilHead):
    """
    The Guardian - Safety, ethics, risk assessment.
    
    The Guardian focuses on:
    - Could this cause harm?
    - Are there privacy/security concerns?
    - Does this align with user's values?
    - What are the worst-case scenarios?
    
    The Guardian has VETO power.
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are the Guardian. Your role is to ensure safety, ethics, 
and alignment. You focus on:
- Could this cause harm?
- Are there privacy/security concerns?
- Does this align with user's values?
- What are the worst-case scenarios?

You have VETO power on any plan that violates your constitution.
Your output must always include: risks identified, ethical review,
recommended safeguards."""
    
    def __init__(self, config: dict = None):
        config = config or {}
        super().__init__(
            name="Guardian",
            head_type=HeadType.GUARDIAN,
            model=config.get("model", "llama4:maverick"),
            temperature=config.get("temperature", 0.3),
            constitution=config.get("constitution", GUARDIAN_CONSTITUTION),
            system_prompt=config.get("system_prompt", self.DEFAULT_SYSTEM_PROMPT),
            veto_power=config.get("veto_power", True),
            config=config
        )
    
    def _build_propose_prompt(self, task: str, context: dict) -> str:
        """Build the prompt for proposal generation"""
        return f"""
        TASK: {task}

        CONTEXT: {context}

        YOUR CONSTITUTION:
        {self._format_constitution()}

        First, assess: What could go wrong? What harm could occur?
        Then propose an approach that minimizes risk.

        Format:
        RISK_ASSESSMENT: [potential harms identified]
        PROPOSAL: [safety-first approach]
        SAFEGUARDS: [protections to include]
        ETHICAL_REVIEW: [ethical considerations]
        WORST_CASE: [worst-case scenarios and mitigations]
        VETO_TRIGGERS: [what would cause you to veto]
        CONCERNS: [remaining concerns]
        QUESTIONS: [questions for other heads]
        CONFIDENCE: [0.0-1.0]
        """

    async def propose(self, task: str, context: dict) -> Proposal:
        """Generate safety-first proposal"""
        prompt = self._build_propose_prompt(task, context)

        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )

        return self._parse_proposal(response)
    
    async def critique(self, task: str, proposals: dict[str, Proposal]) -> Critique:
        """Critique from safety and ethics perspective"""
        prompt = f"""
        TASK: {task}
        
        OTHER COUNCIL MEMBERS PROPOSED:
        {self._format_other_proposals(proposals)}
        
        YOUR CONSTITUTION:
        {self._format_constitution()}
        
        Review these proposals for safety and ethical concerns.
        Flag anything that could cause harm.
        
        Format:
        AGREEMENTS: [safe elements]
        SAFETY_CONCERNS: [potential harms]
        ETHICAL_CONCERNS: [ethical issues]
        VETO_WORTHY: [anything that would trigger veto]
        SUGGESTED_SAFEGUARDS: [protections to add]
        QUESTIONS: [clarifications needed for safety review]
        """
        
        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_guardian_critique(response)
    
    async def revise(self, proposal: Proposal, critiques: list[Critique]) -> Proposal:
        """Revise maintaining safety focus"""
        prompt = f"""
        YOUR ORIGINAL PROPOSAL:
        {proposal.content}
        
        CRITIQUES RECEIVED:
        {self._format_critiques(critiques)}
        
        Revise while maintaining safety as the top priority.
        
        Format:
        PROPOSAL: [revised safe approach]
        SAFEGUARDS_ADDED: [new protections]
        REASONING: [how safety is maintained]
        CONFIDENCE: [0.0-1.0]
        """
        
        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_proposal(response)
    
    def _parse_guardian_critique(self, response: str) -> Critique:
        """Parse Guardian-specific critique"""
        agreements = []
        concerns = []
        suggested_changes = []
        questions = []
        
        if "AGREEMENTS:" in response:
            agreements_text = response.split("AGREEMENTS:")[1].split("SAFETY_CONCERNS:")[0].strip()
            agreements = [a.strip() for a in agreements_text.split("\n") if a.strip()]
        
        # Combine safety and ethical concerns
        if "SAFETY_CONCERNS:" in response:
            safety_text = response.split("SAFETY_CONCERNS:")[1].split("ETHICAL_CONCERNS:")[0].strip()
            concerns.extend([f"[SAFETY] {c.strip()}" for c in safety_text.split("\n") if c.strip()])
        if "ETHICAL_CONCERNS:" in response:
            ethical_text = response.split("ETHICAL_CONCERNS:")[1].split("VETO_WORTHY:")[0].strip()
            concerns.extend([f"[ETHICAL] {c.strip()}" for c in ethical_text.split("\n") if c.strip()])
        if "VETO_WORTHY:" in response:
            veto_text = response.split("VETO_WORTHY:")[1].split("SUGGESTED_SAFEGUARDS:")[0].strip()
            concerns.extend([f"[VETO] {c.strip()}" for c in veto_text.split("\n") if c.strip()])
        
        if "SUGGESTED_SAFEGUARDS:" in response:
            safeguards_text = response.split("SUGGESTED_SAFEGUARDS:")[1].split("QUESTIONS:")[0].strip()
            suggested_changes = [s.strip() for s in safeguards_text.split("\n") if s.strip()]
        if "QUESTIONS:" in response:
            questions_text = response.split("QUESTIONS:")[1].strip()
            questions = [q.strip() for q in questions_text.split("\n") if q.strip()]
        
        return Critique(
            head=self.name,
            agreements=agreements,
            concerns=concerns,
            suggested_changes=suggested_changes,
            questions=questions,
            tokens_used=len(response.split()) * 2
        )
    
    _format_other_proposals = Architect._format_other_proposals
    _format_critiques = Architect._format_critiques
    _parse_proposal = Architect._parse_proposal


class Synthesizer(CouncilHead):
    """
    The Synthesizer - Merges diverse perspectives into balanced action.
    
    The Synthesizer focuses on:
    - What is the best of each perspective?
    - How can apparent conflicts be resolved?
    - What trade-offs are we making and why?
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are the Synthesizer. Your role is to merge diverse perspectives 
into balanced, actionable plans. You focus on:
- What is the best of each perspective?
- How can apparent conflicts be resolved?
- What trade-offs are we making and why?

Never simply average or compromise. Synthesize into something better.
Your output must always include: what was incorporated from each head,
how conflicts were resolved, final reasoning."""
    
    def __init__(self, config: dict = None):
        config = config or {}
        super().__init__(
            name="Synthesizer",
            head_type=HeadType.SYNTHESIZER,
            model=config.get("model", "qwen3:235b"),
            temperature=config.get("temperature", 0.4),
            constitution=config.get("constitution", SYNTHESIZER_CONSTITUTION),
            system_prompt=config.get("system_prompt", self.DEFAULT_SYSTEM_PROMPT),
            veto_power=False,
            config=config
        )
    
    async def propose(self, task: str, context: dict) -> Proposal:
        """Synthesizer doesn't propose - it synthesizes"""
        raise NotImplementedError("Synthesizer synthesizes, doesn't propose")
    
    async def critique(self, task: str, proposals: dict[str, Proposal]) -> Critique:
        """Synthesizer doesn't critique - it synthesizes"""
        raise NotImplementedError("Synthesizer synthesizes, doesn't critique")
    
    async def revise(self, proposal: Proposal, critiques: list[Critique]) -> Proposal:
        """Synthesizer doesn't revise - it synthesizes"""
        raise NotImplementedError("Synthesizer synthesizes, doesn't revise")
    
    async def synthesize(
        self,
        task: str,
        proposals: dict[str, Proposal],
        critiques: dict[str, Critique]
    ) -> dict:
        """
        Create unified synthesis from all perspectives.
        
        This is the Synthesizer's main function.
        """
        prompt = f"""
        TASK: {task}
        
        COUNCIL PERSPECTIVES:
        
        ARCHITECT proposes:
        {proposals.get('Architect', Proposal('', '', '', [], [], 0)).content}
        
        ORACLE proposes:
        {proposals.get('Oracle', Proposal('', '', '', [], [], 0)).content}
        
        GUARDIAN proposes:
        {proposals.get('Guardian', Proposal('', '', '', [], [], 0)).content}
        
        KEY CONCERNS RAISED:
        {self._summarize_concerns(critiques)}
        
        YOUR TASK:
        Create a unified plan that captures the best of each perspective.
        
        RULES:
        1. Never simply compromise - synthesize into something BETTER
        2. Address ALL significant concerns
        3. Make explicit trade-offs transparent
        4. The result must be actionable
        
        Format:
        UNIFIED_PLAN:
        [Detailed plan as structured content]
        
        FROM_ARCHITECT: [what you incorporated]
        FROM_ORACLE: [what you incorporated]
        FROM_GUARDIAN: [what you incorporated]
        
        CONFLICTS_RESOLVED:
        [How you resolved disagreements]
        
        TRADE_OFFS:
        [What trade-offs you made and why]
        
        FINAL_REASONING:
        [Why this synthesis is optimal]
        """
        
        response = await self._llm.invoke(
            system_prompt=self.system_prompt,
            user_prompt=prompt
        )
        
        return self._parse_synthesis(response)
    
    def _summarize_concerns(self, critiques: dict[str, Critique]) -> str:
        """Summarize key concerns from all critiques"""
        all_concerns = []
        for head_name, critique in critiques.items():
            for concern in critique.concerns:
                all_concerns.append(f"- {head_name}: {concern}")
        return "\n".join(all_concerns) if all_concerns else "No major concerns raised."
    
    def _parse_synthesis(self, response: str) -> dict:
        """Parse synthesis response"""
        plan = {}
        from_architect = ""
        from_oracle = ""
        from_guardian = ""
        conflicts = ""
        trade_offs = ""
        reasoning = ""
        
        if "UNIFIED_PLAN:" in response:
            plan_text = response.split("UNIFIED_PLAN:")[1].split("FROM_ARCHITECT:")[0].strip()
            plan = {"content": plan_text}
        
        if "FROM_ARCHITECT:" in response:
            from_architect = response.split("FROM_ARCHITECT:")[1].split("FROM_ORACLE:")[0].strip()
        if "FROM_ORACLE:" in response:
            from_oracle = response.split("FROM_ORACLE:")[1].split("FROM_GUARDIAN:")[0].strip()
        if "FROM_GUARDIAN:" in response:
            from_guardian = response.split("FROM_GUARDIAN:")[1].split("CONFLICTS_RESOLVED:")[0].strip()
        if "CONFLICTS_RESOLVED:" in response:
            conflicts = response.split("CONFLICTS_RESOLVED:")[1].split("TRADE_OFFS:")[0].strip()
        if "TRADE_OFFS:" in response:
            trade_offs = response.split("TRADE_OFFS:")[1].split("FINAL_REASONING:")[0].strip()
        if "FINAL_REASONING:" in response:
            reasoning = response.split("FINAL_REASONING:")[1].strip()
        
        return {
            "plan": plan,
            "incorporated": {
                "architect": from_architect,
                "oracle": from_oracle,
                "guardian": from_guardian
            },
            "conflicts_resolved": conflicts,
            "trade_offs": trade_offs,
            "reasoning": reasoning,
            "tokens_used": len(response.split()) * 2
        }
