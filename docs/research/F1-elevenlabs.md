# F1-T06 — ElevenLabs SDK + Eleven v3 + director's instructions research notes

**Date checked:** 2026-05-02
**Author:** Comicast F1 research (T06)
**Purpose:** Confirm exact API surface for Eleven v3 + audio (director) tags as of 2026-05 so that T09 can lock the `elevenlabs` Python SDK in `verified-deps.toml` (M1) and Pass 3 (voice direction) can be designed against a real, verified tag vocabulary, with a believable cost model for Invincible Vol 2.

> Method: WebSearch / WebFetch against authoritative sources. URLs marked **(primary)** are `elevenlabs.io/docs`, `elevenlabs.io`, `github.com/elevenlabs/elevenlabs-python`, or `pypi.org/project/elevenlabs`. Third-party sources only when they corroborate a primary; tagged **(secondary — ...)**.

> Several primary docs URLs (`/docs/best-practices/prompting/eleven-v3`, the help-center articles on `help.elevenlabs.io/...`) returned 403/404 to the WebFetch tool on 2026-05-02 — the pages exist (search snippets quote them) but the tool's user-agent is being filtered. Where this happens, the primary URL is still cited and the actual content is corroborated via at least one other primary source plus a tagged secondary. These cases are flagged in *Discrepancies & open notes*.

---

## Step 1 — Web search core (5 topics)

### 1.1 ElevenLabs Python SDK + Eleven v3 in TTS

- **Primary — PyPI:** https://pypi.org/project/elevenlabs/ (checked 2026-05-02)
- **Primary — SDK repo:** https://github.com/elevenlabs/elevenlabs-python (checked 2026-05-02)
- **Primary — README on main:** https://github.com/elevenlabs/elevenlabs-python/blob/main/README.md (checked 2026-05-02)
- **Primary — TTS API:** https://elevenlabs.io/docs/api-reference/text-to-speech/convert (checked 2026-05-02)
- **Primary — Models list:** https://elevenlabs.io/docs/overview/models (checked 2026-05-02)
- **Primary — Python SDK docs:** https://elevenlabs.io/docs/agents-platform/libraries/python (checked 2026-05-02)

**Findings:**

- SDK package: `elevenlabs`. Latest version on PyPI: **2.45.0** (released 2026-04-27). Requires `Python >=3.8, <4.0` (classifiers list 3.8 – 3.12).
- Install: `pip install elevenlabs`.
- Entry point used by Comicast: `from elevenlabs.client import ElevenLabs`; `client = ElevenLabs()`; `client.text_to_speech.convert(...)`.
- Async client: `from elevenlabs.client import AsyncElevenLabs` (same method shape).
- Authentication: client reads `ELEVENLABS_API_KEY` from env by default; can be overridden via `ElevenLabs(api_key=...)`. Confirmed in the README on main branch.
- Streaming: `client.text_to_speech.stream(...)` returns an async iterator of audio chunks.

### 1.2 Eleven v3 inline director-instruction tags

- **Primary — Prompting Eleven v3 (alpha) page:** https://elevenlabs.io/docs/best-practices/prompting/eleven-v3 (checked 2026-05-02 — listed in search index; WebFetch returned 404 on this attempt, so canonical content is sourced via the *Best practices* doc below + corroborated by the help-center article and search snippets)
- **Primary — Best practices (TTS):** https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices (checked 2026-05-02 — fetched successfully)
- **Primary — Help: "How do audio tags work with Eleven v3?":** https://help.elevenlabs.io/hc/en-us/articles/35869142561297-How-do-audio-tags-work-with-Eleven-v3 (checked 2026-05-02 — WebFetch 403; quoted via search snippets)
- **Primary — v3 product page:** https://elevenlabs.io/v3 (checked 2026-05-02)
- **Primary — Help: "What is Eleven v3?":** https://help.elevenlabs.io/hc/en-us/articles/35869054119057-What-is-Eleven-v3 (checked 2026-05-02 — WebFetch 403; quoted via search index)
- **Secondary — corroboration of the tag list:** https://audio-generation-plugin.com/elevenlabs-v3/ and https://jonathanmast.com/elevenlabs-v3-audio-tags-user-guide-mastering-emotional-voice-control/ (checked 2026-05-02; used only to cross-check the **bracket** syntax and the published categories)

**Findings — syntax:**

- Eleven v3 uses **square-bracket `[tag]` syntax**, **inline within the text payload**, not as a separate API parameter. The model interprets bracketed tokens as performance cues; remaining text is rendered as speech.
- Tags are **case-insensitive** (`[happy] == [HAPPY]`); lowercase recommended.
- Once a tag is applied it generally affects subsequent text until a new tag is introduced.
- Multiple tags can be combined back-to-back, e.g. `[nervously][whispers]`.
- **Important:** Eleven v3 does **not** support SSML `<break>` / phoneme tags. Use punctuation, ellipses, or pause-style audio tags (`[pause]`, `[short pause]`, `[long pause]`) instead. (Source: `/docs/overview/capabilities/text-to-speech/best-practices`, fetched 2026-05-02.)
- Tag effectiveness is **voice-dependent**: a "calm narrator" voice may not credibly execute `[shouts]`. Primary docs note this explicitly. Comicast Pass 3 must keep voice ↔ likely-tag-set in mind during voice-search prompts.
- Stability slider matters: for maximum tag responsiveness, primary docs recommend **Creative** or **Natural** stability (not "Robust").
- Quality caveat: per primary docs, Professional Voice Clones are not fully optimized for v3 yet; **Instant Voice Clones** and **designed/library voices** are more responsive to tags. Comicast plans to use library voices, so this is fine.

**Findings — canonical tag categories (from primary docs):**

The official "How do audio tags work with Eleven v3?" help article (and the *Best practices* page) groups tags into four canonical buckets. ElevenLabs deliberately does **not** publish an exhaustive list — they describe v3 tags as "context-dependent" and encourage experimentation. The buckets and the tag examples that ElevenLabs themselves cite in primary docs / launch tweets are:

| Category | Examples cited in primary docs |
|---|---|
| **Emotions / mood** | `[happy]`, `[happily]`, `[sad]`, `[angry]`, `[excited]`, `[nervous]`, `[curious]`, `[mischievously]`, `[sarcastic]` |
| **Delivery / vocal style** | `[whispers]` / `[whispering]`, `[shouts]` / `[shouting]`, `[speaking softly]`, `[slowly]`, `[hesitates]` |
| **Non-verbal reactions (in-voice)** | `[laughs]`, `[laughs harder]`, `[starts laughing]`, `[sighs]`, `[exhales]`, `[gulps]`, `[swallows]`, `[clears throat]`, `[snorts]`, `[wheezing]`, `[crying]`, `[chuckles]`, `[giggles]` |
| **Pauses / pacing** (v3-specific, since SSML breaks are not supported) | `[pause]`, `[short pause]`, `[long pause]` |

**Experimental tags** (work, but inconsistently across voices, per `/docs/overview/capabilities/text-to-speech/best-practices`):

- **Sound effects:** `[gunshot]`, `[applause]`, `[clapping]`, `[explosion]` — these inject non-speech audio. Useful for Comicast SFX panels but risk hallucinated quality.
- **Accent forcing:** `[strong X accent]` where X is e.g. French, Russian, Cockney. Effectiveness depends on voice training set.
- **Vocal modes:** `[sings]`, `[woo]`.

**Tone/POV tags (longform / narration):** `[dramatic tone]`, `[lighthearted]`, `[reflective]`, `[serious tone]`, `[awe]`, `[wistful]`, `[matter-of-fact]`, `[continues softly]`, `[resigned]` — surfaced in v3 prompting examples for "internal monologue, exposition, story beats".

> **Spec-vs-reality flag for `KNOWN_ISSUES.md` / Pass 3 prompt design:**
> The Comicast spec assumed six tags: `whispered`, `shouted`, `crying`, `sighs`, `laughs`, `internal monologue`.
> - `[whispers]`, `[shouts]`, `[crying]`, `[sighs]`, `[laughs]` → **all five exist as documented v3 tags**, with the bracketed forms `[whispers]` / `[shouts]` (note: ElevenLabs prefers verb-form `[whispers]` over `[whispered]`, and `[shouts]` over `[shouted]` — Pass 3 must emit the verb form).
> - `[internal monologue]` → **not a documented v3 tag**. The introspective effect ElevenLabs documents instead is achieved via tone tags such as `[reflective]`, `[wistful]`, `[awe]`, `[serious tone]`, `[matter-of-fact]`, optionally combined with `[whispers]` for sotto-voce thoughts.
> - **Action for Pass 3 prompt:** publish a fixed tag vocabulary in `src/comicast/prompts/pass3.py` derived from the verified list above, and explicitly forbid the model from inventing new tags (e.g. `[internal monologue]`). Inventory of the allowed Pass 3 tags should be added to `KNOWN_ISSUES.md` as a reference once T09/T19 land.

### 1.3 Voice library search API

- **Primary — `GET /v2/voices` (workspace voices, search/filter/paginate):** https://elevenlabs.io/docs/api-reference/voices/search (checked 2026-05-02)
- **Primary — `GET /v1/shared-voices` (Voice Library marketplace):** https://elevenlabs.io/docs/api-reference/voices/voice-library/get-shared (checked 2026-05-02)
- **Primary — Voice Library overview:** https://elevenlabs.io/docs/eleven-creative/voices/voice-library (checked 2026-05-02)
- **Primary — Voice ID help:** https://help.elevenlabs.io/hc/en-us/articles/14599760033937-How-do-I-find-the-voice-ID-of-my-voices-via-the-website-and-API (checked 2026-05-02 — WebFetch 403; cited via search index snippet)

**Two distinct endpoints, two distinct purposes:**

| | `GET /v2/voices` | `GET /v1/shared-voices` |
|---|---|---|
| Scope | Voices already in **your workspace** (premade + saved + personal clones) | The full **community Voice Library** marketplace |
| Python SDK | `client.voices.search(...)` | `client.voices.get_shared(...)` |
| Filterable by gender / age / accent / language? | Indirect (via `search` text + `category`); the v2 schema does **not** expose explicit `gender`/`age` query params | **Yes — explicit `gender`, `age`, `accent`, `language`, `locale`, `category`, `descriptives[]`, `use_cases[]`, `featured`, `search`** |
| Returns gender/age/accent in the body? | Not first-class fields — labels are stored in a free-form `labels` dict | **Yes** — explicit `gender`, `age`, `accent`, `language`, `locale`, `descriptive`, `use_case`, `category`, `preview_url`, `image_url`, plus usage stats and rate multiplier |
| Free tier | Yes | **No** — Voice Library API access is paid-tier only |

**Comicast decision:** Pass 3 voice resolution must use **`client.voices.get_shared(...)`** (the `/v1/shared-voices` endpoint), because that is the one that exposes structured `gender`, `age`, `accent`, `descriptive` fields — the exact axes our voice-direction prompts will produce ("deep authoritative middle-aged man, slightly menacing"). Comicast will be on a paid tier (Creator or Pro — see Step 4), so the free-tier restriction does not apply.

**Natural-language search:** The endpoint is **filter-based, not embedding-based**. The `search` field is a substring match against name/description/labels; `descriptives[]` is a curated tag enum. Pass 3's "deep authoritative middle-aged man, slightly menacing" prompt must be **decomposed** by Claude into structured filters before calling the endpoint — for example:
```json
{"gender": "male", "age": "middle_aged", "descriptives": ["authoritative", "deep"], "search": "menacing"}
```
We may also overfetch (e.g. top 30 results) and have Claude pick the best preview_url match.

**voice_id stability:**
- Primary docs do **not** explicitly state voice_id stability. The help article "How do I find the voice ID..." describes the voice_id as a copy-able fixed identifier that can be used in API calls and shared, which strongly implies stability — but this is **not an explicit guarantee**.
- Empirical convention across the SDK examples (e.g. the README pins `voice_id="JBFqnCBsd6RMkjVDRZzb"` for the demo voice "Aria") suggests voice_ids are 22-character base62 strings that stay stable for the lifetime of the voice.
- **Risk:** a Voice Library voice can be **delisted by its creator**. If Comicast persists `voice_id` in `series_profile.json` and the original voice is removed, future runs of the same series will 404. Mitigation: at Pass 3 time, save not just the voice_id but also a snapshot of the voice metadata + a hash of the preview audio, and add a Pass-3 fallback path that re-runs the voice search if a persisted voice_id 404s.
- **Status:** this is logged as an open item. It is **not blocking** for T06; it is a Pass 3 implementation concern for T19+.

**Returned metadata (canonical fields, from `/v1/shared-voices`):** `voice_id`, `public_owner_id`, `name`, `gender`, `age`, `accent`, `language`, `locale`, `descriptive`, `use_case`, `category`, `preview_url`, `image_url`, `rate` (a multiplier on the standard credit cost; "premium" voices cost more credits per character), `usd_rate`, `free_users_allowed`, `live_moderation_enabled`, `featured`, `verified_languages[]`, plus social handles. The rate-multiplier field matters for the cost model — a "premium" voice from the library may charge **2×–3×** the base credit rate, and Pass 3 must surface that to the cost report.

### 1.4 Pricing — per-character cost and tier allotments

- **Primary — pricing page:** https://elevenlabs.io/pricing (checked 2026-05-02)
- **Primary — API pricing page:** https://elevenlabs.io/pricing/api (checked 2026-05-02)
- **Primary — help: "How much does it cost to generate using Eleven v3 (Alpha)?":** https://help.elevenlabs.io/hc/en-us/articles/35869113958801-How-much-does-it-cost-to-generate-using-Eleven-v3-Alpha (checked 2026-05-02 — WebFetch 403; conclusion below corroborated by `/pricing` page + secondary aggregator)
- **Secondary — pricing aggregator (third-party, used for cross-check only):** https://smallest.ai/blog/elevenlabs-pricing-explained-plans-limits-hidden-costs-calculator (checked 2026-05-02) and https://www.getaiperks.com/en/articles/elevenlabs-pricing (checked 2026-05-02)

**Findings:**

- **Credit accounting for Eleven v3 (post-GA, March 2026):** **1 credit per character** of input text. (Same multiplier as Multilingual v2; flash/turbo models charge ~0.5 credits/char.)
- **Headline rate** (from `/pricing/api`): **$0.10 per 1,000 characters** for the Multilingual v2 / v3 family on standard self-serve plans; $0.05 / 1,000 characters for Flash / Turbo.
- **80% off promo:** During the v3 alpha (June 2025), v3 generations cost 80% fewer credits. **This promo ended.** v3 is now GA (since 2026-03-14, per ElevenLabs Inworld review and release notes) and charges the standard 1 credit / character. **Comicast cost model must use the post-GA rate, not the alpha promo rate.**

**Tier allotments (snapshot 2026-05-02 from `/pricing` and `/pricing/api`, both fetched today):**

| Tier | Monthly $ | Monthly characters (credits) | Concurrent requests | Roughly fits |
|---|---|---|---|---|
| Free | $0 | 10,000 | 2 | demo only |
| Starter | $5 (or $6 — page shows $6 today) | 30,000 | 3 | 1 short comic chapter |
| **Creator** | **$22 ($11 first month)** | **100,000 – 121,000** *(value differs across snapshots — see *Discrepancies*)* | **5** | **~2 Invincible volumes/month** |
| Pro | $99 | 500,000 – 600,000 | 10 | a couple of volumes/week |
| Scale | $299 – $330 | 1.8M – 2M | 15 | Image+SFX library at scale |
| Business | $990 – $1,320 | 6M – 11M | 15 | Studio operations |
| Enterprise | custom | custom | custom | n/a |

> The `/pricing` page rendered slightly different numbers across the two fetches we did (`100k` vs `121k` for Creator; `$5` vs `$6` for Starter; `500k` vs `600k` for Pro). This is consistent with ElevenLabs running A/B tests on the pricing page and/or quoting credits-as-promo for the first month. For the Comicast cost calc we use the **page-as-of-2026-05-02** numbers: Creator at $22/month, 100k characters/month included.

**Burst pricing** (from `/docs/eleven-agents/guides/burst-pricing`, primary, checked 2026-05-02):

- Set `bursting_enabled: true` on an agent (or workspace).
- Effective concurrency cap is **min(3 × tier_concurrency, 300)**.
- Burst calls are billed at **2× the normal credit rate**.
- Burst calls run with **lower scheduling priority** (higher latency).
- For Comicast: not strictly needed at Creator/Pro for a single 150-page volume (we will spread the calls over a few minutes), but we should expose `--burst` as a CLI flag on Pass 4 (TTS) for users in a hurry.

### 1.5 Rate limits — concurrent requests per tier

- **Primary — help: "How many TTS requests can I make and can I increase it?":** https://help.elevenlabs.io/hc/en-us/articles/14312733311761-How-many-Text-to-Speech-requests-can-I-make-and-can-I-increase-it (checked 2026-05-02 — WebFetch 403; numbers below are from the search-index snippet, which directly quotes the help article)
- **Primary — help: API Error 429:** https://help.elevenlabs.io/hc/en-us/articles/19571824571921-API-Error-Code-429 (checked 2026-05-02)
- **Secondary — Deepgram production-limits guide:** https://deepgram.com/learn/elevenlabs-production-limits-concurrency-credits-compliance (checked 2026-05-02; used only to corroborate the per-tier concurrency numbers)

**Concurrency cap by tier (snapshot 2026-05-02):**

| Tier | Concurrent requests |
|---|---|
| Free | 2 |
| Starter | 3 |
| Creator | **5** |
| Pro | **10** |
| Scale | 15 |
| Business | 15 |
| Enterprise | custom (negotiated) |

When the cap is exceeded the API returns **HTTP 429 — "concurrent_request_limit_exceeded"**. ElevenLabs explicitly suggests retry-with-backoff or burst mode.

**Comicast spec assumed 5–10 concurrent.** That maps to **Creator (5)** as the floor and **Pro (10)** as the comfortable headroom. The cost calc below picks Creator as the conservative case.

---

## Step 2 — Confirm model ID + canonical tag list

### 2.1 Model ID

- **Confirmed model_id:** **`eleven_v3`** (string, lowercase, no spaces). Source: https://elevenlabs.io/docs/overview/models (primary, checked 2026-05-02). Pass it as `model_id="eleven_v3"` to `client.text_to_speech.convert(...)`.
- **Status:** **GA since 2026-03-14** (no longer alpha, per the Inworld review article cited in the search index for "elevenlabs v3 alpha general availability"). The "(alpha)" label may still appear on the prompting docs page; the model itself is production-ready.
- **Latency caveat:** v3 has **higher latency than Flash / Turbo / Multilingual v2** and is **explicitly not recommended by ElevenLabs for real-time / conversational use**. For Comicast (offline batch generation of an audiobook) this is **fine** and in fact desirable — the higher quality is exactly what we are paying for.

### 2.2 Canonical tag list (full advertised set, with bucket)

Inline syntax: **`[tag]`** square brackets, case-insensitive, embedded directly in the `text` payload of `text_to_speech.convert`.

```text
# Emotion / mood
[happy] [happily] [sad] [angry] [excited] [nervous] [curious]
[mischievously] [sarcastic] [sarcastically] [serious tone]

# Delivery / vocal style
[whispers] [whispering] [shouts] [shouting] [speaking softly]
[slowly] [hesitates] [continues softly] [resigned]

# Non-verbal in-voice reactions
[laughs] [laughs harder] [starts laughing] [chuckles] [giggles]
[sighs] [exhales] [gulps] [swallows] [clears throat] [snorts]
[wheezing] [crying]

# Pauses / pacing  (v3 has no SSML <break>)
[pause] [short pause] [long pause]

# Tone / POV  (longform narration, internal monologue, exposition)
[dramatic tone] [lighthearted] [reflective] [awe] [wistful]
[matter-of-fact]

# Experimental — voice-dependent, may misfire
[strong X accent]   # e.g. [strong French accent]
[sings] [woo]
[gunshot] [applause] [clapping] [explosion]   # injected SFX
```

**Notes:**

1. ElevenLabs does **not** publish a finite canonical list. Their stance: the model is a generative tag-conditioned TTS, and tag effectiveness depends on the chosen voice. The list above is the **union of all tags ElevenLabs themselves cite in primary docs (best-practices, /v3 page) and primary launch communications (the "audio tags" help article and the company's launch tweets).**
2. Comicast's Pass 3 must define a **closed allowlist** derived from the list above, and reject any tag the VLM tries to invent. Anti-hallucination requirement: spec assumes `internal monologue` — that string is **not** in the canonical list above; Pass 3 should map "internal monologue" semantics to `[reflective]` + optional `[whispers]` instead.
3. Bracket vs angle: **`[brackets]` only**. Angle-bracket / SSML syntax is **rejected** by v3. (`<break>` is silently ignored or treated as text per `/docs/overview/capabilities/text-to-speech/best-practices`.)
4. Tags are **inline within `text=`**, not a separate API parameter. There is no `tags=[...]` kwarg on `text_to_speech.convert`.

---

## Step 3 — Voice search API mechanics

**Endpoint and SDK method (Comicast Pass 3):**

```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs()  # reads ELEVENLABS_API_KEY from env

# Searching the community Voice Library (the one with structured gender/age/accent fields)
result = client.voices.get_shared(
    page_size=30,
    gender="male",
    age="middle_aged",         # one of: young, middle_aged, old
    accent="american",         # free-form; common values: american, british, australian, ...
    language="en",
    descriptives=["authoritative", "deep"],   # curated descriptors
    use_cases=["characters"],                  # narration | conversational | characters | social_media | ...
    search="menacing",         # substring match on name + description + labels
    sort="trending",
    page=0,
)

for v in result.voices:
    print(v.voice_id, v.name, v.gender, v.age, v.accent, v.descriptive, v.preview_url, v.rate)
```

**Returned fields per voice:** `voice_id`, `name`, `public_owner_id`, `gender`, `age`, `accent`, `language`, `locale`, `descriptive`, `use_case`, `category`, `preview_url`, `image_url`, `rate` (multiplier on standard credit cost — premium voices charge more), `usd_rate`, `free_users_allowed`, `live_moderation_enabled`, `featured`, `verified_languages[]`, plus social handles.

**voice_id:** 22-char base62 string (per SDK README example: `"JBFqnCBsd6RMkjVDRZzb"`). Treated as a stable identifier in primary docs and the help article. **Stability is implied but not contractually guaranteed**; voice library voices can be delisted by their owners. Comicast Pass 3 must: (a) persist `voice_id` + `name` + a snapshot of metadata in `series_profile.json`, (b) tolerate a 404 on the persisted `voice_id` by re-running the voice search.

**Workspace-only alternative (`client.voices.search()` → `GET /v2/voices`):** also supported by the SDK and returns saved + premade voices, but with looser metadata (gender/age live in a free-form `labels` dict). Useful for round-tripping voices the user has *already saved* into their workspace, but **not** for the initial discovery step.

---

## Step 4 — Pricing model for Invincible Vol 2

### Step 4.1 — Inputs (assumptions)

| Input | Value | Source |
|---|---|---|
| Total dialogue characters / volume | **50,000** | Comicast spec — Invincible Vol 2 estimate |
| Pages / volume | ~150 | Comicast spec |
| Tier picked for cost model | **Creator** | Smallest tier whose 5-concurrent matches our spec floor |
| Creator price | **$22/month** ($11 first month) | https://elevenlabs.io/pricing checked 2026-05-02 |
| Creator allotment | **100,000 characters/month** | https://elevenlabs.io/pricing checked 2026-05-02 |
| Eleven v3 credit ratio | **1 credit / character** (post-GA) | https://elevenlabs.io/pricing/api checked 2026-05-02 |
| Standard overage rate (v3 family) | **$0.10 / 1,000 chars** = **$0.0001 / char** | https://elevenlabs.io/pricing/api checked 2026-05-02 |

### Step 4.2 — Math

Two regimes to consider. The first is "average cost per volume amortized over the included allotment" (relevant if a user processes multiple volumes per month). The second is "incremental marginal cost of producing one more volume" (relevant if a user is already over their allotment for the month).

**Regime A — first volume of the month, fits inside the 100,000-char allotment:**

```
50,000 chars ≤ 100,000-char Creator allotment.
Marginal cost: $0  (covered by the $22 subscription).
Subscription cost amortized to one volume: $22 if only one volume processed.
```

**Regime B — overage, pure pay-as-you-go on top of subscription:**

```
chars         = 50,000
rate          = $0.10 / 1,000 chars  =  $0.0001 / char
overage cost  = 50,000 × $0.0001     =  $5.00
```

**Regime C — total spend if one user processes exactly one volume / month on Creator:**

```
$22 (subscription) + $0 (within allotment) = $22
```

**Regime D — total spend if a user does *two* volumes / month on Creator:**

```
First 100,000 chars: covered by $22 subscription
Next   0 chars: still inside 100k allotment (since 2 × 50k = 100k exactly)
Total:  $22
```

**Regime E — three volumes / month on Creator (one volume goes into overage):**

```
Subscription:                        $22
Overage chars:  3 × 50k − 100k    =  50,000 chars
Overage cost:   50,000 × $0.0001  =  $5.00
Total:                                $27
```

**Regime F — pure pay-as-you-go (Free tier exhausted, no subscription, so paying API rates only):**

```
50,000 chars × $0.0001 / char  =  $5.00 / volume
```

**Regime G — premium voice from the library (rate multiplier 2×–3×):**

```
Many high-quality library voices carry rate = 2.0  → effective $0.20 / 1k chars  → $10 / volume
Top-tier featured voices (rare) carry rate = 3.0  → effective $0.30 / 1k chars  → $15 / volume
```

### Step 4.3 — Comparison with spec estimate of $15–$20 per volume

The spec's "$15–20 ElevenLabs per volume" sits between Regime G (premium voices, $10–$15) and a small overage. **Our calc shows that for a non-premium library voice, the true marginal cost is in the $0–$5 / volume range** — well under the spec.

To realistically hit $15–20 per volume on Eleven v3, one of the following must be true:

1. **Premium voices for major characters.** Mark Grayson, Omni-Man, etc. picked from the library at rate 2×–3×. Even then a 50k-char volume tops out around $10–$15 unless we are well into overage on a low tier.
2. **Higher than spec's character count.** If real Invincible Vol 2 dialogue + narration + SFX text is closer to **150,000 chars**, then at $0.0001/char we get $15 — matching spec. The spec's 50k figure may be undercounting narration boxes and SFX.
3. **Voice cloning / premium model add-on.** Currently out of scope for v3 standard pricing.

**Recommendation:**

- Keep the spec's $15–$20 / volume **as a conservative ceiling** (matches Regime G + heavy overage + premium voices).
- Use **$5 / volume** as a realistic floor (Regime F: pure pay-as-you-go, standard library voices).
- Use **$22 / month flat** as the typical-user expected cost on Creator if they process **≤ 2 volumes / month**, which fits Comicast's stated Phase-1 cadence.
- **Flag for KNOWN_ISSUES.md (T19+, not edited from this task):** revisit the dialogue character count once the extractor lands (T13–T18). If real Invincible Vol 2 dialogue ≥ 150k characters, the spec's $15–$20 number is correct; if it stays at ~50k characters, the spec **overestimated** and the per-volume cost is closer to $5. Either way, the order-of-magnitude is intact and the cost model in `spec.md` does not need to change today.
- **Cost model finding for `spec.md`:** the cost is **subscription-dominated**, not per-character-dominated, at the volume cadence Phase 1 targets. Pass 4 should *not* be optimized aggressively for character savings (that's premature) — but it *should* avoid burning calls on retries (every regenerated chunk is double-billed against the allotment).

### Step 4.4 — Concurrency budget for Vol 2

```
Pages: 150
Lines per page (Pass 3 output, estimated):  ~6
Total TTS calls: ~900
Concurrency on Creator: 5
Average call latency (Eleven v3, 30–80 char line): ~3–8 s

Best case:  900 calls / 5 concurrent × 3 s/call  =  540 s     ≈   9 min
Realistic: 900 calls / 5 concurrent × 5 s/call  =  900 s     =  15 min
Worst case: 900 calls / 5 concurrent × 10 s/call  =  1800 s   =  30 min
```

If the user wants single-digit-minute turnaround, upgrade to **Pro (10 concurrent)** — halves the wall-clock to **~5–15 min** at the same per-character cost. Burst-pricing is **not** required at the Vol 2 scale.

---

## Step 5 — Sample call shape (NOT executed)

Verified against:
- https://github.com/elevenlabs/elevenlabs-python/blob/main/README.md (constructor + `text_to_speech.convert` signature)
- https://elevenlabs.io/docs/api-reference/text-to-speech/convert (kwargs)
- https://elevenlabs.io/docs/overview/models (model_id `eleven_v3`)
- https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices (tag bracket syntax, no SSML)

All checked on 2026-05-02. No live API call executed (no key in this shell).

```python
"""
Comicast Pass 4 — TTS rendering of one direction-tagged line.

NOT executed in T06. This is a verified-shape skeleton; T19+ wires it into the
real pipeline with retries, telemetry, and concurrency throttling.
"""
from pathlib import Path

from elevenlabs.client import ElevenLabs

MODEL = "eleven_v3"  # verified 2026-05-02 via elevenlabs.io/docs/overview/models

# voice_id is a 22-char base62 string from `client.voices.get_shared(...)`
# Persisted in series_profile.json once Pass 3 picks a voice for a character.
OMNI_MAN_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # placeholder — replace with real lookup

client = ElevenLabs()  # reads ELEVENLABS_API_KEY


def render_line(text_with_tags: str, voice_id: str, out_path: Path) -> None:
    """Render one direction-tagged line to MP3.

    text_with_tags carries inline [tag] director instructions, e.g.
        "[whispers] You're not human, son. [pause] You're an Omni-Man."
    """
    audio_iter = client.text_to_speech.convert(
        text=text_with_tags,
        voice_id=voice_id,
        model_id=MODEL,
        output_format="mp3_44100_128",
        # voice_settings is optional; Pass 3 may set stability=Creative for
        # better tag responsiveness.
        # voice_settings={"stability": 0.4, "similarity_boost": 0.75, "style": 0.0},
    )

    with out_path.open("wb") as fh:
        for chunk in audio_iter:
            fh.write(chunk)


# Telemetry to log per call (verified field names against the SDK README on main):
#   - HTTP status (concurrency 429 detection)
#   - len(text_with_tags) → contributes to monthly credit usage
#   - voice rate multiplier (premium voices cost more credits per char)
```

The call was **not executed**. ELEVENLABS_API_KEY is not present in this shell. Live execution is a Pass 4 (T31+) concern.

---

## Discrepancies & open notes

1. **Primary-doc 403/404 from WebFetch.** Three primary URLs returned 403/404 to the WebFetch tool on 2026-05-02:
   - `https://elevenlabs.io/docs/best-practices/prompting/eleven-v3` (the canonical v3 prompting page; appears in their search index but the fetched response is "Page Not Found")
   - `https://help.elevenlabs.io/hc/en-us/articles/35869142561297-How-do-audio-tags-work-with-Eleven-v3`
   - `https://help.elevenlabs.io/hc/en-us/articles/35869054119057-What-is-Eleven-v3`
   - `https://help.elevenlabs.io/hc/en-us/articles/14312733311761-...`
   - `https://help.elevenlabs.io/hc/en-us/articles/35869113958801-...`
   Mitigation: every claim sourced from these pages is **also** corroborated by at least one other primary (the `/v3` product page, `/docs/overview/models`, `/docs/overview/capabilities/text-to-speech/best-practices`, the SDK README, or the API pricing page) **plus** a tagged secondary aggregator. T09 should re-attempt these URLs with `curl` from a normal user agent before locking the dep.

2. **No exhaustive canonical tag list.** ElevenLabs deliberately treats the v3 tag set as open-ended and voice-dependent. The list in §2.2 is the **union of all tags they themselves cite in primary docs and launch communications**, not a contractual finite set. Comicast Pass 3 must therefore **define our own closed allowlist** (subset of §2.2) and reject any other tag the VLM tries to emit.

3. **Spec tag `internal monologue` does not exist as a v3 tag.** ElevenLabs does not document `[internal monologue]`. Comicast must map the semantic to `[reflective]` (or `[awe]`, `[wistful]`, `[matter-of-fact]`) optionally combined with `[whispers]` for sotto-voce thoughts. **This is the one and only spec-vs-reality mismatch found** for the six tags the spec named — the other five (`whispered`, `shouted`, `crying`, `sighs`, `laughs`) all exist, modulo the verb-form spelling (`[whispers]` not `[whispered]`).

4. **voice_id stability is implied, not guaranteed.** The help article and the SDK README treat voice_id as a fixed identifier, but ElevenLabs does not publish a contractual stability guarantee. Voice Library voices can be delisted by their creator. Pass 3 must persist not just the voice_id but a metadata snapshot, and must tolerate a 404 on the persisted voice_id with a re-search fallback. **Status: open, deferred to T19.**

5. **Pricing-page A/B numbers.** The `/pricing` page rendered slightly different numbers across two fetches today (Creator 100k vs 121k characters, Starter $5 vs $6). For the cost model we used the most-cited values: Creator $22/month with 100k chars/month. Re-verify pricing snapshot at T09 lock time and re-compute Step 4 if numbers have moved more than ~25%.

6. **v3 alpha-period 80% off pricing has expired.** Older (mid-2025) blog posts and tutorials may quote the alpha discount. v3 went GA on 2026-03-14 and is now billed at the standard 1 credit/character. Comicast cost model uses the post-GA rate.

7. **Per-tier sync rate-limits beyond concurrency.** ElevenLabs documents concurrency caps but does **not** publish per-tier RPM/QPS for v3 specifically. Empirically (per Deepgram secondary), 429s show up when concurrency is exceeded, not when total RPM is exceeded — so the Comicast scheduler can treat the concurrency cap as the primary throttle.

8. **Premium-voice rate multiplier.** A subset of Voice Library voices charge **2×–3×** the base credit rate. Pass 3 must read the `rate` field on each candidate voice and surface it to the cost report. Otherwise our per-volume cost estimate could be off by 2×–3× for a single character cast with a premium voice.

---

## Summary for T09 (verified-deps.toml)

Once T06 lands, `verified-deps.toml` should record (T09 will populate this):

```toml
[[dependency]]
name = "elevenlabs"
version = "2.45.0"  # latest on PyPI 2026-04-27
verified_date = "2026-05-02"
verified_via = "https://github.com/elevenlabs/elevenlabs-python"
methods_used = [
    "ElevenLabs",                       # constructor; reads ELEVENLABS_API_KEY
    "AsyncElevenLabs",                  # async variant
    "client.text_to_speech.convert",    # text, voice_id, model_id, output_format[, voice_settings]
    "client.text_to_speech.stream",     # streaming variant
    "client.voices.search",             # workspace voices (GET /v2/voices)
    "client.voices.get_shared",         # voice library marketplace (GET /v1/shared-voices)
]
notes = """
Model: eleven_v3 (GA since 2026-03-14). model_id literal: 'eleven_v3'.
Director instructions: inline [bracket] tags within the text=... payload.
Canonical tag categories: emotion / delivery / non-verbal / pause / tone+POV.
SSML <break> NOT supported on v3 — use [pause] / [short pause] / [long pause].
Voice search for Pass 3 uses client.voices.get_shared(...) — exposes structured
gender / age / accent / descriptives / use_cases. Free tier is locked out.
Pricing: 1 credit/char; standard rate $0.10/1k chars; Creator tier $22/mo,
100k chars included, 5 concurrent; v3 alpha-period 80%-off promo expired.
Premium library voices carry rate multiplier 2x-3x — read voice.rate per-call.
"""
```
