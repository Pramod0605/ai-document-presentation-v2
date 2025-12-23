"""
Analytics module for tracking LLM pipeline cost and time metrics.
Version 1.2 - Supports 3-pass architecture with per-phase tracking.
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


# Model pricing per 1M tokens (as of Dec 2024)
MODEL_PRICING = {
    "google/gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "google/gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "anthropic/claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


@dataclass
class PhaseMetrics:
    """Metrics for a single pipeline phase."""
    phase_name: str
    model: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineAnalytics:
    """Complete analytics for a pipeline run."""
    job_id: str
    pipeline_version: str = "1.2"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    phases: List[PhaseMetrics] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result["phases"] = [asdict(p) for p in self.phases]
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class AnalyticsTracker:
    """Tracks analytics for a pipeline run."""

    def __init__(self, job_id: str):
        self.analytics = PipelineAnalytics(job_id=job_id)
        self._phase_start_times: Dict[str, float] = {}

    def start_pipeline(self) -> None:
        """Mark pipeline start."""
        self.analytics.started_at = datetime.utcnow().isoformat()
        self.analytics.status = "running"

    def end_pipeline(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Mark pipeline end and calculate totals."""
        self.analytics.completed_at = datetime.utcnow().isoformat()
        self.analytics.status = status
        self.analytics.error = error

        # Calculate totals
        if self.analytics.started_at:
            start = datetime.fromisoformat(self.analytics.started_at)
            end = datetime.fromisoformat(self.analytics.completed_at)
            self.analytics.total_duration_seconds = (end - start).total_seconds()

        self.analytics.total_cost_usd = sum(p.cost_usd for p in self.analytics.phases)
        self.analytics.total_input_tokens = sum(p.input_tokens for p in self.analytics.phases)
        self.analytics.total_output_tokens = sum(p.output_tokens for p in self.analytics.phases)

    def start_phase(self, phase_name: str, model: str, metadata: Optional[Dict] = None) -> PhaseMetrics:
        """Start tracking a new phase."""
        phase = PhaseMetrics(
            phase_name=phase_name,
            model=model,
            started_at=datetime.utcnow().isoformat(),
            status="running",
            metadata=metadata or {}
        )
        self._phase_start_times[phase_name] = time.time()
        self.analytics.phases.append(phase)
        return phase

    def end_phase(
        self,
        phase_name: str,
        input_tokens: int,
        output_tokens: int,
        status: str = "completed",
        error: Optional[str] = None
    ) -> Optional[PhaseMetrics]:
        """End tracking for a phase and calculate metrics."""
        phase = self._find_phase(phase_name)
        if not phase:
            return None

        phase.completed_at = datetime.utcnow().isoformat()
        phase.status = status
        phase.error = error
        phase.input_tokens = input_tokens
        phase.output_tokens = output_tokens
        phase.total_tokens = input_tokens + output_tokens

        # Calculate duration
        if phase_name in self._phase_start_times:
            phase.duration_seconds = time.time() - self._phase_start_times[phase_name]

        # Calculate cost
        phase.cost_usd = self._calculate_cost(phase.model, input_tokens, output_tokens)

        return phase

    def add_llm_call(
        self,
        phase: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> PhaseMetrics:
        """Add a completed LLM call as a phase (convenience method for V1.5 agents)."""
        phase_obj = PhaseMetrics(
            phase_name=phase,
            model=model,
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            status="completed",
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            duration_seconds=0.0,
            cost_usd=self._calculate_cost(model, prompt_tokens, completion_tokens)
        )
        self.analytics.phases.append(phase_obj)
        return phase_obj

    def _find_phase(self, phase_name: str) -> Optional[PhaseMetrics]:
        """Find a phase by name."""
        for phase in self.analytics.phases:
            if phase.phase_name == phase_name:
                return phase
        return None

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage."""
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            # Try partial match
            for model_key, prices in MODEL_PRICING.items():
                if model_key in model or model in model_key:
                    pricing = prices
                    break

        if not pricing:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the pipeline analytics."""
        return {
            "job_id": self.analytics.job_id,
            "status": self.analytics.status,
            "total_duration_seconds": round(self.analytics.total_duration_seconds, 2),
            "total_cost_usd": round(self.analytics.total_cost_usd, 4),
            "total_tokens": self.analytics.total_input_tokens + self.analytics.total_output_tokens,
            "phases_completed": len([p for p in self.analytics.phases if p.status == "completed"]),
            "phases_failed": len([p for p in self.analytics.phases if p.status == "failed"]),
            "cost_breakdown": {
                p.phase_name: {
                    "cost_usd": round(p.cost_usd, 4),
                    "duration_seconds": round(p.duration_seconds, 2),
                    "tokens": p.total_tokens
                }
                for p in self.analytics.phases
            }
        }

    def save_to_file(self, filepath: str) -> None:
        """Save analytics to a JSON file."""
        with open(filepath, "w") as f:
            f.write(self.analytics.to_json())

    def print_summary(self) -> None:
        """Print a formatted summary to console."""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print(f"PIPELINE ANALYTICS - Job {summary['job_id']}")
        print("=" * 60)
        print(f"Status: {summary['status']}")
        print(f"Total Duration: {summary['total_duration_seconds']:.2f}s")
        print(f"Total Cost: ${summary['total_cost_usd']:.4f}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"Phases: {summary['phases_completed']} completed, {summary['phases_failed']} failed")
        print("-" * 60)
        print("PHASE BREAKDOWN:")
        for phase_name, data in summary["cost_breakdown"].items():
            print(f"  {phase_name}:")
            print(f"    Duration: {data['duration_seconds']:.2f}s")
            print(f"    Cost: ${data['cost_usd']:.4f}")
            print(f"    Tokens: {data['tokens']:,}")
        print("=" * 60 + "\n")


# Convenience functions for integration
def create_tracker(job_id: str) -> AnalyticsTracker:
    """Create a new analytics tracker for a job."""
    return AnalyticsTracker(job_id)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a single LLM call."""
    tracker = AnalyticsTracker("estimate")
    return tracker._calculate_cost(model, input_tokens, output_tokens)
