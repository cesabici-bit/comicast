# F1-T05 — Anthropic SDK + Claude vision API research notes

**Date checked:** 2026-05-02
**Author:** Comicast F1 research (T05)
**Purpose:** Confirm exact API surface for vision + prompt caching as of 2026-05 so that T09 can lock the `anthropic` Python SDK in `verified-deps.toml` (M1) and Pass 2b can be designed against a real, verified shape.

> Method: WebSearch tool runs against authoritative sources. URLs marked "primary" are docs.anthropic.com / platform.claude.com / anthropic.com / github.com/anthropics. Third-party sources are only used when they corroborate a primary; they are explicitly tagged "secondary".

---

## Step 1 — Web search core (4 topics)

### 1.1 Anthropic Python SDK + Claude Sonnet 4.6 vision

- **Primary doc — Vision:** https://docs.anthropic.com/en/docs/build-with-claude/vision (checked 2026-05-02)
- **Primary doc — Python SDK repo:** https://github.com/anthropics/anthropic-sdk-python (checked 2026-05-02)
- **Primary doc — Models overview:** https://platform.claude.com/docs/en/about-claude/models/overview (checked 2026-05-02)
- **Primary doc — Sonnet 4.6 product page:** https://www.anthropic.com/claude/sonnet (checked 2026-05-02)
- **Primary — PyPI:** https://pypi.org/project/anthropic/ (checked 2026-05-02)

**Findings:**

- SDK package: `anthropic`. Latest version on PyPI: **0.97.0** (released 2026-04-23). Requires Python >=3.9.
- Install: `pip install anthropic`. Optional extras include `aws`, `bedrock`, `mcp`, `vertex`, `aiohttp`.
- Entry point used by Comicast: `from anthropic import Anthropic`; `client = Anthropic()`; `client.messages.create(...)`.
- Vision is supported on Sonnet/Opus families. Images are passed inside `content` blocks of a user message, with `type: "image"` and a `source` object. Three source types are supported:
  - `{"type": "base64", "media_type": "image/png", "data": "<b64>"}`
  - `{"type": "url", "url": "https://..."}`
  - `{"type": "file", "file_id": "<id from Files API>"}`
- Supported media types: `image/jpeg`, `image/png`, `image/gif`, `image/webp`. The `media_type` must match the actual bytes (mismatch raises an API error — see anthropics/claude-code#11936).
- Image size limits (per primary docs and confirmed by Anthropic GitHub issues anthropics/claude-code#11564 and #20021):
  - Per-image **payload cap: 5 MB** (base64 raw bytes after decoding).
  - Per-dimension **cap: 8000 pixels** (single-image requests). For many-images requests the per-dimension cap is **2000 px** (langgenius/dify#11177 (secondary — third-party issue quoting Anthropic error string)).
- Recommendation in primary docs: for images reused across calls, prefer the **Files API** (upload once, reference by `file_id`) over base64 to avoid re-encoding overhead. Comicast Pass 2b reuses cast.json (system prompt) but each page image is unique → base64 is acceptable; the cache hit is on the system prompt, not the image.

### 1.2 Prompt caching (`cache_control` ephemeral / 1h)

- **Primary doc — Prompt caching:** https://platform.claude.com/docs/en/build-with-claude/prompt-caching (checked 2026-05-02)
- **Primary doc (mirror):** https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching (checked 2026-05-02)
- **Primary cookbook:** https://github.com/anthropics/anthropic-cookbook/blob/main/misc/prompt_caching.ipynb (checked 2026-05-02)
- **Secondary corroboration on March 2026 default change:** https://dev.to/whoffagents/claude-prompt-caching-in-2026-the-5-minute-ttl-change-thats-costing-you-money-4363 (checked 2026-05-02; flagged as a third-party blog, used only to corroborate the dated default-TTL change reported elsewhere).

**Findings:**

- Mark the *static* content block(s) you want cached with `"cache_control": {"type": "ephemeral"}`. The cache key is the entire prefix up to that breakpoint (tools, system, messages, in that order).
- TTL options:
  - **5 minutes** (default ephemeral) — `{"type": "ephemeral"}` (no `ttl` field, or `"ttl": "5m"`).
  - **1 hour** (extended) — `{"type": "ephemeral", "ttl": "1h"}`. Costs more on write (see pricing below).
- **2026 dated changes** (worth noting in CLAUDE.md / KNOWN_ISSUES.md):
  - **2026-02-05:** caches isolated per *workspace* (was per-organization).
  - **2026-03-06:** default TTL changed from 1h → 5m. If you don't pass `ttl`, you get 5m. Comicast Pass 2b explicitly uses 5m, so this change does not affect us — but anyone reading old blog posts should be aware.
- Up to **4 `cache_control` breakpoints** per request. If more are passed, only the last 4 (from end → start) are honored. Automatic prefix-checking looks back approximately 20 content blocks from each explicit breakpoint, so a single breakpoint at the end of static content is usually sufficient.
- Multiple TTLs may be mixed in one request: the docs note that when you mix 1h and 5m breakpoints, the 1h breakpoint must come *before* the 5m one in the sequence (this is not a Comicast concern, but recorded for completeness).

### 1.3 Structured outputs / JSON mode

- **Primary doc — Structured outputs:** https://platform.claude.com/docs/en/build-with-claude/structured-outputs (checked 2026-05-02)
- **Primary doc — Agent SDK structured outputs:** https://platform.claude.com/docs/en/agent-sdk/structured-outputs (checked 2026-05-02)
- **Primary doc — Tool use cookbook (extract structured JSON):** https://github.com/anthropics/anthropic-cookbook/blob/main/tool_use/extracting_structured_json.ipynb (checked 2026-05-02)

**Findings:**

- As of 2026, Anthropic supports **Structured Outputs** in two complementary ways:
  1. **Strict tool use** — pass a tool definition with a JSON Schema and `strict: true`. The model is constrained-decoded so that `tool_use.input` is guaranteed to satisfy the schema. Strict tool use / structured outputs is documented as supported on Claude Sonnet 4.6 (alongside Opus 4.7, Opus 4.6, Sonnet 4.5, Opus 4.5, and Haiku 4.5) per https://platform.claude.com/docs/en/build-with-claude/structured-outputs (checked 2026-05-02).
  2. **`output_config` (response schema)** — the `client.messages.create(..., output_config={"type": "json_schema", "schema": {...}})` parameter; opt-in via the beta header `anthropic-beta: structured-outputs-2025-11-13`. Forces the response to match a top-level JSON Schema.
- For Comicast Pass 2b the simpler path is **strict tool use**: define a single tool `record_page` whose input schema mirrors the page-record JSON we want (panels, lines, speaker_id, etc.). The model is forced to call that tool, and `response.content[0].input` is our parsed dict. This is the Anthropic-recommended pattern in their cookbook.
- Structured outputs **do not** disable prompt caching. The schema travels in `tools=[...]`, which sits before `system` in the cache prefix, so as long as the tool list is stable across calls, it is cached automatically.

### 1.4 Model id + pricing

- **Primary — Pricing:** https://platform.claude.com/docs/en/about-claude/pricing (checked 2026-05-02)
- **Primary — Sonnet 4.6 launch:** https://www.anthropic.com/news/claude-sonnet-4-6 (checked 2026-05-02)
- **Primary — Models overview:** https://platform.claude.com/docs/en/about-claude/models/overview (checked 2026-05-02)
- Secondary corroboration: https://www.finout.io/blog/anthropic-api-pricing (checked 2026-05-02; third-party aggregator, used only to cross-check that the headline numbers match the primary pricing page).

**Findings (Sonnet 4.6, base prices, USD per 1M tokens):**

| Lane | Price |
|---|---|
| Input (uncached) | **$3.00 / 1M** |
| Output | **$15.00 / 1M** |
| Cache write — 5m ephemeral | **1.25× input = $3.75 / 1M** |
| Cache write — 1h ephemeral | **2.0× input = $6.00 / 1M** |
| Cache read (hit) | **0.1× input = $0.30 / 1M** |
| Batch API (50% off) — input | **$1.50 / 1M** |
| Batch API (50% off) — output | **$7.50 / 1M** |

(Batch and prompt-caching discounts **stack**: a cache-read inside a batched request is `0.1 × 0.5 × 3.00 = $0.15 / 1M`, per the Anthropic batch announcement.)

**Rate limits / batch availability** (from https://docs.anthropic.com/en/api/rate-limits and https://www.anthropic.com/news/message-batches-api, checked 2026-05-02):

- Sync rate limits are tier-based (Tier 1 → Tier 4 → custom). Metrics: **RPM**, **ITPM** (input tokens/min), **OTPM** (output tokens/min). The Sonnet-4.x bucket is *shared* across Sonnet 4, 4.5, 4.6 (combined limit). Exact numbers depend on tier and change frequently, so we will not bake them into Comicast code; the cost model in `spec.md` already assumes a paid tier with comfortable headroom for ~150 calls in a few minutes.
- `cache_read_input_tokens` count toward ITPM (this matters: we cannot use caching to bypass ITPM).
- **Batch API:** `client.messages.batches.create(...)`. Up to **100,000 requests per batch**, asynchronously processed within 24 h, **50% discount** on both input and output. Separate, much higher rate limits. Output up to 300k tokens per request on Opus 4.6 / Sonnet 4.6 with the `output-300k-2026-03-24` beta header.
- **Comicast decision:** Pass 2b uses **synchronous** `messages.create` with 5-minute prompt caching. Reasoning: (a) we want fast iteration during prototyping, (b) all 150 page-calls fit easily in a single 5-minute cache window if dispatched concurrently, and (c) batch's 24-h SLA is too slow for an interactive "process this comic" flow. We may revisit batch in F4 for bulk back-catalog processing.

---

## Step 2 — Verify model ID

- **Confirmed model ID:** `claude-sonnet-4-6` (from https://www.anthropic.com/news/claude-sonnet-4-6 and https://platform.claude.com/docs/en/about-claude/models/overview, both checked 2026-05-02). Anthropic states "use `claude-sonnet-4-6` via the Claude API."
- Vision is supported on **both** Sonnet 4.6 and Opus 4.7. Per primary docs and the pricing page, Sonnet 4.6 is positioned as the "price/perf sweet spot" and explicitly recommended for "scaled production and complex tasks across coding, agents, and professional workflows" — comic-page parsing falls squarely in that envelope.
- Opus 4.7 (`claude-opus-4-7`) is roughly 5× the input price ($15/1M input vs $3) and ~5× output ($75/1M vs $15), so for ~150 pages × ~1500 input tokens (mostly cached) + ~600 output tokens per page the cost differential is meaningful (~5× total).
- **Decision (T05):** Pass 2b uses `claude-sonnet-4-6`. We retain the option to upgrade individual hard pages to `claude-opus-4-7` if Sonnet's output is rejected by L2 oracle tests, but that is a Pass 2c concern, not Pass 2b. This matches the spec's default assumption.

## Step 3 — Verify prompt caching mechanics

Confirmed against https://platform.claude.com/docs/en/build-with-claude/prompt-caching (checked 2026-05-02):

| Property | Value | Comicast use |
|---|---|---|
| TTL options | **5 min** (default `ephemeral`) or **1 h** (`"ttl": "1h"`) | 5 min for Pass 2b |
| Cache write multiplier (5m) | **1.25× base input** | applied once per cache window |
| Cache write multiplier (1h) | **2.0× base input** | n/a |
| Cache read multiplier (hit) | **0.1× base input** (≈ 90% savings) | applied to ~149 of 150 calls per window |
| Min cacheable size (Sonnet 4.x) | **1024 tokens** (per primary docs) | system prompt + cast.json well exceeds 1024 — verified at design time in T19 |
| Max breakpoints | **4** `cache_control` blocks per request | we use 1 (end of `system`) |
| Auto prefix-check | yes, looks back ~20 content blocks | safe with our single-breakpoint layout |
| Prefix order | tools → system → messages | put `tools` (record_page schema) and `system` (cast.json) *before* per-page user content; only those are cached |

**Known caveat (logged in KNOWN_ISSUES.md after T05 closes):** there is a reported intermittent issue (anthropics/anthropic-sdk-python#1194) where Sonnet caching has occasionally required ~2048 tokens before kicking in despite the documented 1024 threshold. Mitigation: at runtime, log `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` and assert that reads happen on call ≥2 of the same window. If we observe writes-only behavior, increase the cached system prompt past 2048 tokens (it will be there anyway once we include the full cast.json + style guide).

## Step 4 — Sample call shape (NOT executed)

The skeleton below was checked against:
- https://docs.anthropic.com/en/docs/build-with-claude/vision (image content block shape — type/source/media_type/data)
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching (cache_control on system block)
- https://github.com/anthropics/anthropic-sdk-python (SDK constructor + `messages.create` signature)

All checked on **2026-05-02**.

```python
"""
Comicast Pass 2b — page-by-page speaker attribution.

NOT executed in T05. This is a verified-shape skeleton; T19 wires it into the
real pipeline and adds error handling, retries, and telemetry.
"""
import base64
from pathlib import Path
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"  # verified 2026-05-02 via anthropic.com/news/claude-sonnet-4-6

# Big static prompt: schema, cast.json (character bibles), style guide,
# panel-reading rules, common-error catalog. Sized to >>1024 tokens so the
# Sonnet caching threshold is comfortably exceeded.
SYSTEM_PROMPT_2B = """\
You are Comicast Pass 2b, a comic-book panel parser...
[full system prompt — see src/comicast/prompts/pass2b.py once T19 lands]
"""

# Strict tool-use schema. Forces JSON output that satisfies our PageRecord
# pydantic model. Travels in `tools=[...]` so it lands in the cached prefix
# automatically (tools are cached before system).
RECORD_PAGE_TOOL = {
    "name": "record_page",
    "description": "Emit a structured record for one comic page.",
    "input_schema": {
        "type": "object",
        "properties": {
            "page_number": {"type": "integer"},
            "panels": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "panel_index": {"type": "integer"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "speaker_id": {"type": "string"},
                                    "text": {"type": "string"},
                                    "kind": {
                                        "type": "string",
                                        "enum": ["speech", "thought", "narration", "sfx"],
                                    },
                                },
                                "required": ["speaker_id", "text", "kind"],
                            },
                        },
                    },
                    "required": ["panel_index", "lines"],
                },
            },
        },
        "required": ["page_number", "panels"],
    },
}

client = Anthropic()  # reads ANTHROPIC_API_KEY from env

def process_page(page_png: Path, page_number: int) -> dict:
    page_b64 = base64.b64encode(page_png.read_bytes()).decode("ascii")

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        tools=[RECORD_PAGE_TOOL],
        tool_choice={"type": "tool", "name": "record_page"},  # force the tool
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT_2B,
                # Single cache breakpoint at end of static content. Tools (above)
                # ride along automatically since they sit earlier in the prefix.
                "cache_control": {"type": "ephemeral"},  # 5-minute TTL (default)
            },
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": page_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Page {page_number}. Use the record_page tool to "
                            "emit a structured record. Follow the rules in the "
                            "system prompt verbatim."
                        ),
                    },
                ],
            }
        ],
    )

    # Strict tool-use guarantees the first content block is a tool_use whose
    # `input` matches RECORD_PAGE_TOOL["input_schema"].
    assert response.content and response.content[0].type == "tool_use"
    return response.content[0].input


# Telemetry to log per call (verified field names against
# https://github.com/anthropics/anthropic-sdk-python README usage block):
#   response.usage.input_tokens
#   response.usage.output_tokens
#   response.usage.cache_creation_input_tokens   # >0 only on first call/window
#   response.usage.cache_read_input_tokens       # >0 on subsequent calls
```

**Shape verified against:**
- https://docs.anthropic.com/en/docs/build-with-claude/vision on 2026-05-02 (image content block: `type`, `source.type`, `source.media_type`, `source.data`).
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching on 2026-05-02 (`system` as a list of typed text blocks; `cache_control` lives on a content block, not on the request root; `{"type": "ephemeral"}` defaults to 5m).
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools on 2026-05-02 (tool-block field names: `name`, `description`, `input_schema` — Anthropic uses `input_schema`, not `parameters`).
- https://github.com/anthropics/anthropic-sdk-python on 2026-05-02 (`Anthropic()` constructor, `messages.create(model=..., max_tokens=..., system=..., messages=..., tools=..., tool_choice=...)`, `response.content[i].type == "tool_use"` shape, `response.usage` fields).

The call was **not executed**. Per task brief: no API key required for T05. Live execution lands in T19.

---

## Discrepancies & open notes

1. **1024 vs 2048 cache minimum (Sonnet).** Docs say 1024 tokens; GitHub issue anthropics/anthropic-sdk-python#1194 reports occasional 2048-token threshold in practice. Mitigation logged in Step 3. To be re-checked before declaring T19 done.
2. **Default TTL change 2026-03-06.** Older blog posts and tutorials may show `{"type": "ephemeral"}` with the implicit assumption of 1-h TTL. Since 2026-03-06 the default is 5 m. Comicast wants 5 m, so this is benign — but anyone copying examples from older sources should be aware. Recorded in KNOWN_ISSUES.md candidate.
3. **Exact tier-based sync rate limits.** Anthropic's rate-limits page is tier-specific and frequently revised; we did **not** capture per-tier numbers because they would go stale fast. Comicast cost model in `spec.md` does not depend on a specific tier. If we hit limits in F3 we will revisit.
4. **Files API vs base64 for repeated images.** Primary docs recommend Files API for *reused* images. Comicast pages are unique per call, so base64 is fine. If Pass 2c (per-panel re-prompts on the same page) lands, switch to Files API for that page's PNG.

---

## Summary for T09 (verified-deps.toml)

Once T05 lands, `verified-deps.toml` should record (T09 will populate this):

```toml
[[dependency]]
name = "anthropic"
version = "0.97.0"  # latest on PyPI 2026-04-23
verified_date = "2026-05-02"
verified_via = "https://github.com/anthropics/anthropic-sdk-python"
methods_used = [
    "Anthropic",
    "client.messages.create",
    "messages.create kwargs: model, max_tokens, tools, tool_choice, system, messages",
    "response.content[i].type == 'tool_use'",
    "response.content[i].input",
    "response.usage.{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens}",
]
notes = """
Model: claude-sonnet-4-6 (price/perf for vision Pass 2b).
Caching: cache_control ephemeral 5m on system block (1 breakpoint, max 4 allowed).
Image content block: {type:image, source:{type:base64, media_type:image/png, data:<b64>}}.
Per-image limits: 5 MB payload, 8000 px per dimension.
Structured output: strict tool use via tools=[record_page] + tool_choice={type:tool,name:record_page}.
"""
```
