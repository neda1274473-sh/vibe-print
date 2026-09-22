"""
Agent session context store.

Holds in-flight workflow state, artifacts, and recovery history
for a single agent session.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from vibe_print.generator.requirements import ModelRequirements


class StepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    RECOVERED = "recovered"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_CLARIFICATION = "needs_clarification"


@dataclass
class WorkflowStep:
    """A single step in a workflow plan."""
    name: str
    description: str
    status: StepStatus = StepStatus.PENDING
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    recovery_action: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "recovery_action": self.recovery_action,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class AgentSession:
    """
    In-flight context for an agent workflow session.

    Holds everything the agent needs to know across multiple steps
    and (eventually) multiple user turns.
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str = "default"
    goal: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Plan state
    plan: List[WorkflowStep] = field(default_factory=list)
    current_step_index: int = 0

    # Retry / recovery tracking
    retry_counts: Dict[str, int] = field(default_factory=dict)
    recovery_actions: List[Dict[str, Any]] = field(default_factory=list)

    # Artifacts produced during workflow
    requirements: Optional[ModelRequirements] = None
    model_path: Optional[str] = None
    model_type: Optional[str] = None
    analysis_result: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    slicing_result: Optional[Dict[str, Any]] = None
    iteration_id: Optional[str] = None

    # User-facing messages accumulated during execution
    messages: List[str] = field(default_factory=list)

    # Session lifecycle status
    status: str = "active"  # active, completed, failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "goal": self.goal,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "current_step": self.current_step_index,
            "total_steps": len(self.plan),
            "plan": [s.to_dict() for s in self.plan],
            "retry_counts": self.retry_counts,
            "recovery_actions": self.recovery_actions,
            "model_path": self.model_path,
            "model_type": self.model_type,
            "iteration_id": self.iteration_id,
            "messages": self.messages,
        }

    def current_step(self) -> Optional[WorkflowStep]:
        if 0 <= self.current_step_index < len(self.plan):
            return self.plan[self.current_step_index]
        return None

    def add_message(self, msg: str) -> None:
        self.messages.append(msg)

    def record_recovery(self, step: str, strategy: str, result: str) -> None:
        self.recovery_actions.append({
            "step": step,
            "strategy": strategy,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        })

    def increment_retry(self, step_name: str) -> int:
        self.retry_counts[step_name] = self.retry_counts.get(step_name, 0) + 1
        return self.retry_counts[step_name]

    def get_retry_count(self, step_name: str) -> int:
        return self.retry_counts.get(step_name, 0)
