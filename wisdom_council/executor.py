"""
Wisdom Council - Execution Layer

Manages sub-agents that perform the actual work.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable, Optional


@dataclass
class Tool:
    """A tool that sub-agents can use"""
    name: str
    function: Callable
    description: str = ""
    
    async def execute(self, **kwargs) -> dict:
        """Execute the tool"""
        return await self.function(**kwargs)


@dataclass
class ExecutionStep:
    """A single execution step"""
    agent: str
    task: str
    result: dict
    tokens_used: int
    duration: float


@dataclass
class ExecutionResult:
    """Results from plan execution"""
    final_output: str
    steps: list[ExecutionStep]
    tokens_used: int
    success: bool
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "final_output": self.final_output,
            "steps": [
                {
                    "agent": s.agent,
                    "task": s.task,
                    "result": s.result,
                    "duration": s.duration
                }
                for s in self.steps
            ],
            "tokens_used": self.tokens_used,
            "success": self.success,
            "errors": self.errors
        }


@dataclass
class StreamEvent:
    """Event during streaming execution"""
    content: str
    agent: str
    step: int
    metadata: dict = field(default_factory=dict)


class SubAgent(ABC):
    """
    Base class for sub-agents that perform specific tasks.
    
    Sub-agents are specialized workers that the Executor delegates to.
    """
    
    def __init__(
        self,
        name: str,
        model: str,
        tools: list[Tool],
        system_prompt: str,
        config: dict = None
    ):
        self.name = name
        self.model = model
        self.tools = {t.name: t for t in tools}
        self.system_prompt = system_prompt
        self.config = config or {}
    
    @abstractmethod
    async def execute(self, task: str, context: dict = None) -> dict:
        """Execute a task"""
        pass
    
    async def use_tool(self, tool_name: str, **kwargs) -> dict:
        """Use a specific tool"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return await self.tools[tool_name].execute(**kwargs)


class ResearchAgent(SubAgent):
    """Agent specialized in research and information gathering"""
    
    def __init__(self, config: dict = None):
        super().__init__(
            name="Research Agent",
            model=config.get("model", "qwen3:72b") if config else "qwen3:72b",
            tools=[
                Tool("web_search", self._web_search, "Search the web"),
                Tool("document_reader", self._read_document, "Read documents"),
                Tool("database_query", self._query_database, "Query databases"),
            ],
            system_prompt="""You are a Research Agent. Your job is to:
            - Gather comprehensive information
            - Verify facts from multiple sources
            - Structure findings clearly""",
            config=config
        )
    
    async def execute(self, task: str, context: dict = None) -> dict:
        """Execute research task"""
        # Implementation would use LLM + tools
        return {
            "findings": [],
            "sources": [],
            "confidence": 0.0
        }
    
    async def _web_search(self, query: str) -> dict:
        """Search the web"""
        # Implementation
        return {"results": []}
    
    async def _read_document(self, path: str) -> dict:
        """Read a document"""
        # Implementation
        return {"content": ""}
    
    async def _query_database(self, query: str) -> dict:
        """Query a database"""
        # Implementation
        return {"rows": []}


class AnalystAgent(SubAgent):
    """Agent specialized in analysis and calculations"""
    
    def __init__(self, config: dict = None):
        super().__init__(
            name="Analyst Agent",
            model=config.get("model", "qwen3:72b") if config else "qwen3:72b",
            tools=[
                Tool("python_repl", self._execute_python, "Execute Python code"),
                Tool("calculator", self._calculate, "Perform calculations"),
                Tool("chart_generator", self._create_chart, "Generate charts"),
            ],
            system_prompt="""You are an Analyst Agent. Your job is to:
            - Perform quantitative analysis
            - Calculate metrics and scores
            - Identify patterns and risks""",
            config=config
        )
    
    async def execute(self, task: str, context: dict = None) -> dict:
        """Execute analysis task"""
        return {
            "analysis": {},
            "metrics": {},
            "visualizations": []
        }
    
    async def _execute_python(self, code: str) -> dict:
        """Execute Python code"""
        # Implementation with sandboxing
        return {"output": "", "error": None}
    
    async def _calculate(self, expression: str) -> dict:
        """Perform calculation"""
        return {"result": 0}
    
    async def _create_chart(self, data: dict, chart_type: str) -> dict:
        """Create a chart"""
        return {"chart_path": ""}


class CoderAgent(SubAgent):
    """Agent specialized in code generation"""
    
    def __init__(self, config: dict = None):
        super().__init__(
            name="Coder Agent",
            model=config.get("model", "deepseek-coder-v2") if config else "deepseek-coder-v2",
            tools=[
                Tool("file_writer", self._write_file, "Write files"),
                Tool("code_executor", self._execute_code, "Execute code"),
                Tool("test_runner", self._run_tests, "Run tests"),
                Tool("linter", self._lint_code, "Lint code"),
            ],
            system_prompt="""You are a Coder Agent. Your job is to:
            - Write clean, tested code
            - Follow best practices
            - Document your code""",
            config=config
        )
    
    async def execute(self, task: str, context: dict = None) -> dict:
        """Execute coding task"""
        return {
            "files_created": [],
            "test_results": {},
            "warnings": []
        }
    
    async def _write_file(self, path: str, content: str) -> dict:
        """Write a file"""
        return {"success": True}
    
    async def _execute_code(self, code: str, language: str) -> dict:
        """Execute code"""
        return {"output": "", "error": None}
    
    async def _run_tests(self, test_path: str) -> dict:
        """Run tests"""
        return {"passed": 0, "failed": 0, "errors": []}
    
    async def _lint_code(self, code: str, language: str) -> dict:
        """Lint code"""
        return {"issues": []}


class Executor:
    """
    Coordinates sub-agents to execute plans.
    
    Takes a plan from the Council and orchestrates the sub-agents
    to complete it.
    """
    
    def __init__(self, config: dict = None, checkpointer=None):
        self.config = config or {}
        self.checkpointer = checkpointer
        
        # Initialize sub-agents
        self.agents = {
            "research": ResearchAgent(config.get("sub_agents", {}).get("research")),
            "analyst": AnalystAgent(config.get("sub_agents", {}).get("analyst")),
            "coder": CoderAgent(config.get("sub_agents", {}).get("coder")),
        }
        
        # Current state
        self._current_state = {}
        self._results = None
    
    async def execute(
        self,
        plan: dict,
        thread_id: str,
        context: dict = None
    ) -> ExecutionResult:
        """
        Execute a plan using sub-agents.
        
        Args:
            plan: The plan from the Council
            thread_id: Thread ID for checkpointing
            context: Additional context
            
        Returns:
            ExecutionResult with outputs and metadata
        """
        steps = []
        total_tokens = 0
        errors = []
        
        # Parse plan steps
        plan_steps = self._parse_plan(plan)
        
        for i, step in enumerate(plan_steps):
            try:
                # Get appropriate agent
                agent = self.agents.get(step["agent_type"])
                if not agent:
                    raise ValueError(f"Unknown agent type: {step['agent_type']}")
                
                # Execute step
                import time
                start_time = time.time()
                
                result = await agent.execute(step["task"], context)
                
                duration = time.time() - start_time
                tokens = result.get("tokens_used", 500)
                total_tokens += tokens
                
                steps.append(ExecutionStep(
                    agent=agent.name,
                    task=step["task"],
                    result=result,
                    tokens_used=tokens,
                    duration=duration
                ))
                
                # Update context with result
                context = context or {}
                context[f"step_{i}_result"] = result
                
                # Checkpoint
                if self.checkpointer and (i + 1) % 5 == 0:
                    await self.checkpointer.save(
                        thread_id=thread_id,
                        state={
                            "step": i + 1,
                            "progress": (i + 1) / len(plan_steps),
                            "context": context
                        },
                        checkpoint_id=f"step-{i+1}"
                    )
                
            except Exception as e:
                errors.append(f"Step {i+1} failed: {str(e)}")
        
        # Compile final output
        final_output = self._compile_output(steps)
        
        self._results = ExecutionResult(
            final_output=final_output,
            steps=steps,
            tokens_used=total_tokens,
            success=len(errors) == 0,
            errors=errors
        )
        
        return self._results
    
    async def stream_execute(
        self,
        plan: dict,
        thread_id: str,
        context: dict = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream execution events"""
        plan_steps = self._parse_plan(plan)
        
        for i, step in enumerate(plan_steps):
            yield StreamEvent(
                content=f"Starting: {step['task'][:100]}...",
                agent=step["agent_type"],
                step=i + 1
            )
            
            agent = self.agents.get(step["agent_type"])
            if agent:
                result = await agent.execute(step["task"], context)
                
                yield StreamEvent(
                    content=f"Completed: {str(result)[:200]}...",
                    agent=step["agent_type"],
                    step=i + 1,
                    metadata={"result": result}
                )
    
    async def get_results(self) -> ExecutionResult:
        """Get execution results after streaming"""
        return self._results
    
    async def revise(
        self,
        results: ExecutionResult,
        feedback: str,
        thread_id: str
    ) -> ExecutionResult:
        """Revise results based on feedback"""
        # Implementation would re-run relevant steps with feedback
        return results
    
    def get_current_state(self) -> dict:
        """Get current execution state"""
        return self._current_state
    
    async def restore_state(self, state: dict) -> None:
        """Restore execution state"""
        self._current_state = state
    
    def _parse_plan(self, plan: dict) -> list[dict]:
        """Parse plan into executable steps"""
        # Simple parsing - in production, use more sophisticated logic
        steps = []
        
        if isinstance(plan, dict):
            content = plan.get("content", plan.get("raw", ""))
            
            # Extract steps from content
            # This is a simple heuristic - real implementation would be smarter
            if "research" in content.lower():
                steps.append({"agent_type": "research", "task": "Gather information"})
            if "analyz" in content.lower():
                steps.append({"agent_type": "analyst", "task": "Analyze data"})
            if "code" in content.lower() or "build" in content.lower():
                steps.append({"agent_type": "coder", "task": "Write code"})
        
        # Default step if none parsed
        if not steps:
            steps.append({"agent_type": "research", "task": "Execute plan"})
        
        return steps
    
    def _compile_output(self, steps: list[ExecutionStep]) -> str:
        """Compile steps into final output"""
        parts = []
        for step in steps:
            parts.append(f"## {step.agent}\n{step.result}")
        return "\n\n".join(parts)
