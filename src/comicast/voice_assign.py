"""Voice assignment workflow.

Two paths:
1. LLM-driven: build a search query from the description, get candidates, user picks.
2. Direct ID: user pastes an ElevenLabs voice_id they already know.

Phase 1 implements both as CLI prompts. Voice archetype library entries can be
appended during assignment (no removal/edit; conflict-on-overwrite is silent —
see VOICE-04 backlog).
"""

from __future__ import annotations

import re

from elevenlabs.core import ApiError
from rich.console import Console
from rich.prompt import Prompt

from comicast.elevenlabs_client import ElevenLabsClient
from comicast.logging_setup import get_logger
from comicast.schemas import CastEntry, SeriesProfile

log = get_logger("comicast.voice_assign")
console = Console()


def cast_members_needing_voice(profile: SeriesProfile) -> list[CastEntry]:
    return [c for c in profile.cast if not c.voice_id]


# Order matters: more-specific labels first; first match wins. Python 3.7+ dict
# preserves insertion order, so "teen" is tried before "young adult" (both share
# the keyword "young"); changing this dict's key order changes label selection.
_AGE_KEYWORDS = {
    "teen": ("teen", "young"),
    "child": ("child",),
    "young adult": ("young", "20s"),
    "adult": ("adult",),
    "middle-aged": ("middle-aged", "40s", "50s"),
    "elderly": ("elderly", "old"),
}
_GENDER_KEYWORDS = ["male", "female", "boy", "girl", "man", "woman"]


def suggest_query_from_description(description: str) -> str:
    """Build an ElevenLabs voice search query from a free-text character description."""
    desc_low = description.lower()
    fragments: list[str] = []

    for label, kws in _AGE_KEYWORDS.items():
        if any(k in desc_low for k in kws):
            fragments.append(label)
            break

    for g in _GENDER_KEYWORDS:
        if re.search(rf"\b{g}\b", desc_low):
            fragments.append(g)
            break

    # Tone: pull adjectives from description
    for tone in (
        "sarcastic",
        "authoritative",
        "menacing",
        "gentle",
        "warm",
        "stern",
        "calm",
        "energetic",
        "shy",
        "confident",
    ):
        if tone in desc_low:
            fragments.append(tone)

    return " ".join(fragments) if fragments else description[:80]


def assign_voices_interactive(
    profile: SeriesProfile,
    *,
    el_client: ElevenLabsClient,
) -> SeriesProfile:
    """Walk cast members without a `voice_id` and prompt the user to assign one.

    For each member: try archetype library → search ElevenLabs → manual paste.
    Mutates `profile.cast[i].voice_id`/`voice_archetype` in place AND returns the
    same `profile` (dual side-effect — sibling `upsert_cast_from_extraction`,
    PROF-02 / VOICE-03 backlog). Caller is responsible for `save_profile` and
    `profile.version` bump (PROF-04).
    """
    needing = cast_members_needing_voice(profile)
    log.info(
        "voice_assign.start",
        n_needing=len(needing),
        n_archetypes=len(profile.voice_archetype_library),
    )
    if not needing:
        log.info("voice_assign.no_needing")
        console.print("[green]All cast members have voices assigned.[/green]")
        return profile

    console.print(f"\n[yellow]{len(needing)} cast members need a voice.[/yellow]\n")

    for c in needing:
        console.rule(f"{c.canonical_name} ({c.id})")
        console.print(f"[bold]Description:[/bold] {c.description}")

        # Check archetype library first
        if profile.voice_archetype_library:
            console.print("[dim]Archetype library:[/dim]")
            for arch, vid in profile.voice_archetype_library.items():
                console.print(f"  - {arch} → {vid}")
            from_arch = Prompt.ask("Use an archetype id (or press Enter to search)", default="")
            if from_arch and from_arch in profile.voice_archetype_library:
                c.voice_id = profile.voice_archetype_library[from_arch]
                c.voice_archetype = from_arch
                log.info(
                    "voice_assign.assigned",
                    character_id=c.id,
                    voice_id=c.voice_id,
                    source="archetype",
                    archetype=from_arch,
                )
                continue

        query = suggest_query_from_description(c.description)
        console.print(f"[dim]Suggested search:[/dim] {query}")
        query = Prompt.ask("Refine search query (Enter to use suggestion)", default=query)
        try:
            candidates = el_client.search_voices(query=query, limit=5)
        except ApiError as exc:
            log.error(
                "voice_assign.search.failed",
                character_id=c.id,
                query=query,
                error_class=type(exc).__name__,
                status_code=exc.status_code,
            )
            candidates = []

        log.info(
            "voice_assign.candidates_found",
            character_id=c.id,
            query=query,
            n_candidates=len(candidates),
        )

        if not candidates:
            log.warning("voice_assign.no_candidates", character_id=c.id, query=query)
            console.print("[red]No candidates found.[/red] Paste an ElevenLabs voice_id manually:")
            c.voice_id = Prompt.ask("voice_id")
            log.info(
                "voice_assign.assigned", character_id=c.id, voice_id=c.voice_id, source="manual"
            )
            continue

        for i, cand in enumerate(candidates, start=1):
            console.print(f"  [{i}] {cand.name} — {cand.voice_id} — {cand.description[:80]}")
        choice = Prompt.ask("Pick (number) or paste voice_id", default="1")
        try:
            idx = int(choice) - 1
            c.voice_id = candidates[idx].voice_id
        except (ValueError, IndexError):
            c.voice_id = choice

        log.info(
            "voice_assign.assigned",
            character_id=c.id,
            voice_id=c.voice_id,
            source="search",
        )

        # Offer to add as archetype
        archetype = Prompt.ask(
            f"Save '{c.voice_id}' as a reusable archetype? (label or empty to skip)",
            default="",
        )
        if archetype:
            # Invariant: c.voice_id is set by every reachable path leading here
            # (search-pick / search-paste / no-candidates-manual all assigned
            # before this section; archetype-hit branch `continue`s above).
            assert c.voice_id is not None, "voice_id must be set before archetype save"
            profile.voice_archetype_library[archetype] = c.voice_id
            c.voice_archetype = archetype
            log.info(
                "voice_assign.archetype_saved",
                archetype=archetype,
                voice_id=c.voice_id,
            )

    log.info("voice_assign.done", n_processed=len(needing))
    return profile
