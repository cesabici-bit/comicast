"""Pre-flight billing/quota check before running the dry-run pipeline.

Reads .env, queries ElevenLabs user info (free GET, no spend) and makes one
1-token Anthropic call (~$0.0001 if billing OK, AuthError/insufficient_credit
otherwise). Prints structured PASS/FAIL summary. Does not raise.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

print("== Pre-flight billing/quota check ==")
print()

# --- ElevenLabs ---
print("[1/2] ElevenLabs — probe required scopes for the pipeline")
try:
    from elevenlabs import ElevenLabs
    from elevenlabs.core import ApiError

    el_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not el_key:
        print("  FAIL: ELEVENLABS_API_KEY not loaded")
    else:
        client = ElevenLabs(api_key=el_key)

        # Probe 1: user_read (informational only — pipeline does not strictly need)
        print("  [a] user.get (informational; not required by pipeline)")
        try:
            user = client.user.get()
            sub = user.subscription
            tier = getattr(sub, "tier", "?")
            char_count = getattr(sub, "character_count", "?")
            char_limit = getattr(sub, "character_limit", "?")
            print(
                f"      OK tier={tier} chars={char_count}/{char_limit} "
                f"remaining={int(char_limit) - int(char_count)}"
            )
        except ApiError as e:
            sc = getattr(e, "status_code", "?")
            print(f"      MISSING (status={sc}) — no big deal, pipeline does not need user_read")
        except Exception as e:
            print(f"      MISSING ({type(e).__name__}: {e})")

        # Probe 2: voices_read (REQUIRED by voice_assign.py search_voices)
        print("  [b] voices.search (REQUIRED for stage 3 voice assignment)")
        try:
            results = client.voices.search(search="adult man", page_size=1)
            voices_attr = getattr(results, "voices", None)
            n = len(voices_attr) if voices_attr is not None else 0
            print(f"      OK: returned {n} voice candidate(s)")
        except ApiError as e:
            sc = getattr(e, "status_code", "?")
            print(f"      FAIL (status={sc}): {e}")
        except Exception as e:
            print(f"      FAIL ({type(e).__name__}): {e}")

        # Probe 3: text_to_speech (REQUIRED by stage 4 TTS)
        # Use a known public voice id (Rachel = 21m00Tcm4TlvDq8ikWAM) and 6 chars
        # = trivially small spend on paid tiers, free on free tier.
        print("  [c] text_to_speech.convert (REQUIRED for stage 4 — 6 chars only)")
        try:
            audio_iter = client.text_to_speech.convert(
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel, public default
                text="Hello.",
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            # Drain iterator to confirm bytes flow
            total_bytes = sum(len(chunk) for chunk in audio_iter)
            print(f"      OK: received {total_bytes} bytes of MP3")
        except ApiError as e:
            sc = getattr(e, "status_code", "?")
            # Print only the JSON body, not the full headers dump
            body = getattr(e, "body", None)
            print(f"      FAIL (status={sc}) body={body}")
        except Exception as e:
            print(f"      FAIL ({type(e).__name__}): {e}")
except Exception as e:
    print(f"  FAIL unexpected: {type(e).__name__}: {e}")

print()

# --- Anthropic ---
print("[2/2] Anthropic (1-token messages.create on Haiku ~ $0.0000004)")
try:
    import anthropic

    ant_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not ant_key:
        print("  FAIL: ANTHROPIC_API_KEY not loaded")
    else:
        client = anthropic.Anthropic(api_key=ant_key)
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            print(f"  OK: model={resp.model} stop_reason={resp.stop_reason}")
            print(
                f"  usage: input_tokens={resp.usage.input_tokens} "
                f"output_tokens={resp.usage.output_tokens}"
            )
        except anthropic.AuthenticationError as e:
            print(f"  FAIL: AuthenticationError — invalid key. {e}")
        except anthropic.PermissionDeniedError as e:
            print(f"  FAIL: PermissionDeniedError — billing/credit issue? {e}")
        except anthropic.BadRequestError as e:
            msg = str(e)
            if "credit" in msg.lower() or "billing" in msg.lower():
                print(f"  FAIL: insufficient credit/billing. {e}")
            else:
                print(f"  FAIL: BadRequestError {e}")
        except anthropic.APIStatusError as e:
            print(f"  FAIL: APIStatusError status={e.status_code} {e}")
except Exception as e:
    print(f"  FAIL unexpected: {type(e).__name__}: {e}")

print()
print("== End ==")
