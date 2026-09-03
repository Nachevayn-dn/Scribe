"""Prompt construction for the clinical extraction step."""
from app.models.preference import DoctorPreference
from app.models.template import NoteTemplate

SYSTEM_PROMPT = """You are a clinical scribe assistant for a dental/medical practice. \
You are given a raw transcript of a patient-provider conversation and must turn it into \
a structured clinical note.

Rules:
- Write the note as a sequence of short lines (like a real chart note), not one big paragraph.
- Section headers (e.g. "Chief Complaint", "Diagnostics", "Next Steps") are their own lines \
with no tagged entities.
- Within clinical content lines, identify clinically relevant spans and tag each with exactly \
one entity type: MEDICATION, PROCEDURE, DIAGNOSTIC, SYMPTOM, or ALLERGY. Only tag spans that \
are genuinely one of these — most words in a line are untagged.
- start_offset/end_offset are character offsets of the tagged span within that line's text \
(0-indexed, end exclusive). Get these exactly right so highlighting lines up with the text.
- Do not invent clinical facts that are not supported by the transcript. If the provider \
gave an explicit instruction (see "Doctor preferences" below) that applies to something \
mentioned in the transcript, follow it — e.g. proactively suggest a specific next step.
- Keep the tone professional and concise, as in a real chart note.
"""


def build_user_prompt(
    transcript_text: str,
    preferences: list[DoctorPreference],
    template: NoteTemplate | None,
) -> str:
    parts = [f"Transcript:\n\"\"\"\n{transcript_text}\n\"\"\""]

    if template is not None and template.structure:
        sections = ", ".join(str(s) for s in template.structure)
        parts.append(
            f"Organize the note using these sections, in order, as section-header lines: "
            f"{sections}."
        )

    if preferences:
        pref_lines = "\n".join(
            f'- If the transcript mentions "{p.trigger_phrase}": {p.instruction}'
            for p in preferences
        )
        parts.append(f"Doctor preferences to apply when relevant:\n{pref_lines}")

    parts.append(
        "Call the record_clinical_note tool exactly once with the full structured note."
    )
    return "\n\n".join(parts)


TAGGING_SYSTEM_PROMPT = """You are a clinical scribe assistant. You are given a transcript of a \
patient-provider conversation, already split into numbered lines. Tag clinically relevant spans \
in each line — do not rewrite, summarize, or reorder anything, just identify spans.

Rules:
- For each line that contains one, tag every clinically relevant span with exactly one entity \
type: MEDICATION, PROCEDURE, DIAGNOSTIC, SYMPTOM, or ALLERGY. Most lines have zero or a few \
tagged spans — don't force it.
- start_offset/end_offset are character offsets of the tagged span within that line's text \
(0-indexed, end exclusive), measured against the exact line text given below. Get these exactly \
right so highlighting lines up with the text.
- Only include lines that have at least one tagged entity in your response — omit lines with none.
- Never alter, translate, or paraphrase the wording; you are only pointing at spans within the \
text you were given.
"""


def build_tagging_user_prompt(lines: list[str]) -> str:
    numbered = "\n".join(f"{idx}: {line}" for idx, line in enumerate(lines))
    return (
        f"Transcript lines (format is \"<line_index>: <text>\"):\n{numbered}\n\n"
        "Call the tag_transcript_entities tool exactly once with the tagged entities."
    )


TAGGING_TOOL = {
    "name": "tag_transcript_entities",
    "description": "Tags clinically relevant entity spans within the given transcript lines, referenced by line_index.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "line_index": {"type": "integer"},
                        "entities": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "entity_type": {
                                        "type": "string",
                                        "enum": [
                                            "MEDICATION",
                                            "PROCEDURE",
                                            "DIAGNOSTIC",
                                            "SYMPTOM",
                                            "ALLERGY",
                                        ],
                                    },
                                    "text": {"type": "string"},
                                    "start_offset": {"type": "integer"},
                                    "end_offset": {"type": "integer"},
                                },
                                "required": ["entity_type", "text", "start_offset", "end_offset"],
                            },
                        },
                    },
                    "required": ["line_index", "entities"],
                },
            }
        },
        "required": ["lines"],
    },
}


ASK_AI_SYSTEM_PROMPT = """You are helping a doctor with their clinical note, in one of two ways:

1. REWORK — the doctor wants the note itself changed: made shorter or longer, \
rephrased, translated, restructured, given specific detail added or removed. \
Call record_revision with the complete revised note text (same line-based \
format as the input — one clinical statement per line). Never invent clinical \
facts that weren't already in the note or the doctor's instruction.

2. LOOKUP — the doctor is asking a question or wants you to check something \
external (current guidelines, a drug interaction, a coding reference, general \
medical information). Use the web_search tool if it would help, then call \
record_answer with a concise answer and the sources you used. Never edit the \
note for a lookup — that's a separate, deliberate step the doctor takes \
themselves if they want to incorporate what you found.

Decide which of these two the doctor's instruction calls for, then call \
exactly one of record_revision or record_answer to finish — always end by \
calling one of them, never just plain text.
"""


def build_ask_ai_user_prompt(current_content: str, instruction: str) -> str:
    return (
        f"Current note:\n\"\"\"\n{current_content}\n\"\"\"\n\n"
        f"Doctor's instruction: {instruction}"
    )


ASK_AI_TOOLS = [
    {
        "type": "web_search_20260209",
        "name": "web_search",
        "max_uses": 3,
    },
    {
        "name": "record_revision",
        "description": "Records a fully revised version of the clinical note.",
        "input_schema": {
            "type": "object",
            "properties": {
                "revised_content": {
                    "type": "string",
                    "description": "The complete revised note text, same line-based format as the original.",
                }
            },
            "required": ["revised_content"],
        },
    },
    {
        "name": "record_answer",
        "description": "Records a direct answer to the doctor's question or research request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                        },
                        "required": ["title", "url"],
                    },
                },
            },
            "required": ["answer"],
        },
    },
]


EXTRACTION_TOOL = {
    "name": "record_clinical_note",
    "description": "Records the structured, entity-tagged clinical note extracted from the transcript.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "entities": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "entity_type": {
                                        "type": "string",
                                        "enum": [
                                            "MEDICATION",
                                            "PROCEDURE",
                                            "DIAGNOSTIC",
                                            "SYMPTOM",
                                            "ALLERGY",
                                        ],
                                    },
                                    "text": {"type": "string"},
                                    "start_offset": {"type": "integer"},
                                    "end_offset": {"type": "integer"},
                                },
                                "required": ["entity_type", "text"],
                            },
                        },
                    },
                    "required": ["text", "entities"],
                },
            }
        },
        "required": ["lines"],
    },
}
