"""Clinical extraction provider interface.

Turns a raw transcript into a structured, entity-tagged clinical note:
an ordered list of lines, each optionally carrying zero or more tagged
entities (medication/procedure/diagnostic/symptom/allergy spans).
"""
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from app.models.clinical_note import EntityType
from app.models.preference import DoctorPreference
from app.models.template import NoteTemplate


class ExtractedEntity(BaseModel):
    entity_type: EntityType
    text: str
    start_offset: int | None = None
    end_offset: int | None = None
    confidence: float | None = None


class ExtractedLine(BaseModel):
    text: str
    entities: list[ExtractedEntity] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    lines: list[ExtractedLine]

    @property
    def rendered_content(self) -> str:
        return "\n".join(line.text for line in self.lines)


class TaggedLine(BaseModel):
    """Entities found on one existing transcript line, referenced by
    line_index rather than carrying the line's text — tagging never rewrites
    the transcript, it only points at spans within it."""

    line_index: int
    entities: list[ExtractedEntity] = Field(default_factory=list)


class TaggingResult(BaseModel):
    lines: list[TaggedLine] = Field(default_factory=list)


class ClinicalExtractionProvider(ABC):
    @abstractmethod
    async def extract(
        self,
        transcript_text: str,
        preferences: list[DoctorPreference],
        template: NoteTemplate | None,
    ) -> ExtractionResult:
        raise NotImplementedError

    @abstractmethod
    async def tag_lines(self, lines: list[str]) -> TaggingResult:
        """Tags clinically relevant entity spans on an already-final list of
        transcript lines, without altering their wording."""
        raise NotImplementedError
