"""
Base classes for methodology documentation.

Every calculation in OMEN must have documented formula, cited source(s),
assumptions, limitations, validation status, and version history.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional


class ValidationStatus(Enum):
    """Validation status of a methodology."""

    DRAFT = "draft"
    INTERNAL_REVIEW = "internal"
    EXPERT_REVIEW = "expert"
    BACKTESTED = "backtested"
    PRODUCTION = "production"


@dataclass
class SourceCitation:
    """Citation for an evidence source."""

    title: str
    author: str
    publication: str
    date: date
    url: Optional[str] = None
    page_or_section: Optional[str] = None
    accessed_date: Optional[date] = None
    doi: Optional[str] = None

    def to_string(self) -> str:
        """Format as citation string."""
        parts = [self.author, f'"{self.title}"', self.publication]
        if self.date:
            parts.append(self.date.strftime("%B %Y"))
        if self.page_or_section:
            parts.append(self.page_or_section)
        return ", ".join(str(p) for p in parts)

    def to_dict(self) -> dict:
        out = {
            "title": self.title,
            "author": self.author,
            "publication": self.publication,
            "date": self.date.isoformat() if self.date else None,
            "url": self.url,
            "page_or_section": self.page_or_section,
            "formatted": self.to_string(),
        }
        return out


@dataclass
class Methodology:
    """
    Complete documentation for a calculation methodology.

    Every rule, formula, or parameter in OMEN should have one.
    """

    name: str
    version: str
    description: str

    formula: str
    formula_latex: Optional[str] = None

    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    parameters: dict[str, tuple[Any, str]] = field(default_factory=dict)

    primary_source: Optional[SourceCitation] = None
    supporting_sources: list[SourceCitation] = field(default_factory=list)

    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    validation_status: ValidationStatus = ValidationStatus.DRAFT
    validated_by: Optional[str] = None
    validation_date: Optional[date] = None
    validation_notes: Optional[str] = None

    created_date: date = field(default_factory=date.today)
    last_updated: date = field(default_factory=date.today)
    changelog: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "formula": self.formula,
            "formula_latex": self.formula_latex,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "parameters": {
                k: {"value": v[0], "rationale": v[1]}
                for k, v in self.parameters.items()
            },
            "primary_source": self.primary_source.to_dict() if self.primary_source else None,
            "supporting_sources": [s.to_dict() for s in self.supporting_sources],
            "assumptions": self.assumptions,
            "limitations": self.limitations,
            "validation": {
                "status": self.validation_status.value,
                "validated_by": self.validated_by,
                "validation_date": (
                    self.validation_date.isoformat() if self.validation_date else None
                ),
                "notes": self.validation_notes,
            },
            "version_info": {
                "created": self.created_date.isoformat(),
                "last_updated": self.last_updated.isoformat(),
                "changelog": self.changelog,
            },
        }
