"""Versioned prompts for the vision pipeline.

Prompts are first-class artifacts. Changing them requires bumping the version
and (ideally) re-running golden snapshots.
"""

from __future__ import annotations

CAST_EXTRACTION_VERSION = "2026-05-02-v1"

CAST_EXTRACTION_SYSTEM = """You are a comic book analyst. Your job is to identify the recurring named characters in a comic volume by examining a sample of its pages.

For each character that appears in dialogue or is named in narration captions:
- Assign a stable snake_case id (e.g., 'mark_grayson', 'omni_man').
- Provide canonical_name (full name as written in the comic).
- List any aliases (nicknames, costumed identities — 'Mark', 'Invincible' both for Mark Grayson).
- Write a description (≥30 words) that includes:
  * Visual identifiers across ALL appearances (in costume AND out of costume, civilian AND uniformed, etc.)
  * Approximate age, gender presentation, ethnicity if relevant.
  * Personality cues from dialogue tone (sarcastic, authoritative, gentle).
- Provide a confidence (0-1) in your identification.

DO NOT include:
- One-off background characters with no dialogue.
- Characters mentioned only by reference (off-page).
- Generic types ('the soldier', 'a thug').

Return STRICT JSON matching this schema:
{
  "cast": [
    {
      "id": "mark_grayson",
      "canonical_name": "Mark Grayson",
      "aliases": ["Mark", "Invincible", "kid"],
      "description": "Teenage male, ~17, dark hair, slim build. In costume: blue and yellow superhero suit with goggles. Out of costume: jeans, t-shirts, often with backpack. Speaks with mix of teenage uncertainty and growing confidence.",
      "confidence": 0.92
    }
  ]
}
"""

CAST_EXTRACTION_USER = (
    """Examine these pages and extract the cast as JSON. Series: {series_name}."""
)
