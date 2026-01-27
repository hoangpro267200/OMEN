"""Abstract base classes for all OMEN rules.

Rules are the building blocks of OMEN's intelligence.
They must be:
- Deterministic
- Explainable
- Versioned
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

from ..models.common import RulesetVersion
from ..models.explanation import ExplanationStep


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Rule(ABC, Generic[InputT, OutputT]):
    """
    Base class for all OMEN rules.

    Every rule must:
    1. Have a unique name and version
    2. Produce an explanation step
    3. Be deterministic (same input → same output)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique rule identifier."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Rule version for reproducibility."""
        ...

    @property
    def qualified_name(self) -> str:
        """Full name including version."""
        return f"{self.name}@{self.version}"

    @abstractmethod
    def apply(self, input_data: InputT) -> OutputT:
        """Apply the rule to input data."""
        ...

    @abstractmethod
    def explain(
        self,
        input_data: InputT,
        output_data: OutputT,
        processing_time: datetime | None = None,
    ) -> ExplanationStep:
        """Generate explanation for this rule application."""
        ...
