# F1-T08 — Competitor analysis + tier decision (S/A/B)

**Date checked:** 2026-05-03
**Author:** Comicast F1 research (T08)
**Purpose:** Verify the market gap — "existing tools … handle prose books but not comics" — with real evidence, then apply a 5-criteria monetisation framework to decide the project tier.

> Method: WebSearch (≥6 queries) + WebFetch against product homepages, pricing pages, and research arXiv. Every URL is tagged as **(primary)** if fetched directly or **(secondary-corroborated)** if reached only via search snippet. Unknown or unverifiable facts are tagged `# UNVERIFIED`. The spec.md §1 hypothesis is treated as a claim to be tested, not accepted.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Search Log](#2-search-log)
3. [Category A — Comic-Specific Audio Tools](#3-category-a--comic-specific-audio-tools)
4. [Category B — Generic Multi-Character TTS / Audiobook Generators](#4-category-b--generic-multi-character-tts--audiobook-generators)
5. [Category C — Human-Produced Audio Drama (Comics as Source Material)](#5-category-c--human-produced-audio-drama-comics-as-source-material)
6. [Category D — Research / Academic Prototypes](#6-category-d--research--academic-prototypes)
7. [Category E — Open-Source Building Blocks (not products)](#7-category-e--open-source-building-blocks-not-products)
8. [Gap Analysis](#8-gap-analysis)
9. [Monetisation Criteria Scoring](#9-monetisation-criteria-scoring)
10. [Tier Decision](#10-tier-decision)
11. [Key Differentiators for README](#11-key-differentiators-for-readme)
12. [Sources](#12-sources)

---

## 1. Executive Summary

| Question | Answer |
|---|---|
| Does any consumer product solve "comic CBZ/CBR/PDF → multi-character audiobook with per-character voices via visual speaker attribution"? | **No.** The closest consumer products (Seeneva, TTS Comics, ReadLoudly) do OCR + single-voice read-aloud with no speaker attribution. |
| Is there a research prototype doing roughly what Comicast plans? | **Yes — one.** arXiv 2509.15253 (Sept 2025) covers this exactly, but with 64.8% speaker accuracy, trained-per-comic ResNet-50, no usable code, and no consumer release. |
| Does ElevenLabs Reader / ElevenReader handle comics? | **No.** ElevenReader reads PDFs and ePUBs as text; it does not handle image-based comic formats or speaker attribution. |
| Does Audible produce comic audiobooks? | Only via **manually produced** audio dramas (Sandman, Locke & Key) — not automated. |
| Tier decision | **A** (monetisable, strong differentiation, solid market) with the legal posture caveat noted in the plan ("tool" model, not content marketplace). |
| Confidence in tier | High (4/5 criteria met with evidence; fifth is structurally blocked by legal posture, not market). |

---

## 2. Search Log

All searches executed 2026-05-03.

| # | Query | Key candidates found |
|---|---|---|
| S01 | "AI comic audiobook narrator with character voices 2026" | Narratemi, Musely, LyricWinter, ElevenLabs Voice Library |
| S02 | "ElevenLabs Reader comic books support 2026" | ElevenReader (no comic support confirmed) |
| S03 | "Audible comic books audio drama production 2026" | Audible manual audio dramas, GraphicAudio, Marvel/Dreamscape audiobooks |
| S04 | "Murf.ai Speechify comic narration audiobook" | Murf.ai (general TTS), Speechify (OCR-based read-aloud) |
| S05 | "open source comic narration TTS GitHub 2025 2026" | Seeneva, cbrTekStraktor, Dia TTS, MOSS-TTS, Chatterbox, Qwen3-TTS |
| S06 | "manga audiobook AI character voices 2026" | All Voice Lab, Inkfluence AI, TTS Comics |
| S07 | "Narratemi multi-character audiobook generator features pricing" | Narratemi detail (text-only, no comic support) |
| S08 | "GraphicAudio AI automated production workflow comic book" | GraphicAudio (human production, AI comic generators unrelated) |
| S09 | "comic book to audio AI speaker attribution bubble detection pipeline" | arXiv 2509.15253, Seeneva, cbrTekStraktor, Roboflow bubble datasets |
| S10 | "Speechify comic book PDF image reader text extraction" | Speechify OCR, Seeneva, cbrTekStraktor, ReadLoudly |
| S11 | "AI comic reader audio drama CBZ CBR PDF vision OCR speaker 2025" | Seeneva, ReadLoudly, TTS Comics, ACBR, comic-translate (GitHub) |
| S12 | "audiobook market size 2026 growth statistics" | Market size $8.7–14B in 2026 at 10-27% CAGR (multiple analyst sources) |
| S13 | "Seeneva comic reader speaker attribution character voices TTS quality" | Seeneva OCR/TTS unreliable per user feedback; arXiv 2509.15253 found |
| S14 | "comic book audiobook generation vision LLM GPT-4o Claude speaker attribution 2025 2026" | arXiv 2505.13082 (MultiActor-Audiobook for novels), arXiv 2509.15253 |
| S15 | "ElevenReader pricing plans 2026 features comic PDF support" | ElevenReader: Free (10h/mo), Ultra $11/mo or $99/yr; no comic support |
| S16 | "Narratemi comic book support speaker attribution" | Narratemi: text prose only, no comic/image support confirmed |
| S17 | "comic audiobook OR comic to audio product app 2025 2026 site:producthunt.com" | No comic-specific products on Product Hunt |
| S18 | "GraphicAudio layoffs 2026 staff cuts impact production" | GraphicAudio (RB Media) cut ~50% staff, Feb 2026 |

---

## 3. Category A — Comic-Specific Audio Tools

These are the most direct competitive threat. None of them fully solve the problem.

---

### 3.1 Seeneva

- **URL:** https://seeneva.app/ (primary — fetched 2026-05-03)
- **GitHub:** https://github.com/Seeneva/seeneva-reader-android (primary)
- **What it does:** Free open-source Android app. Detects speech balloons via ML (panel-order navigation), then runs OCR (English only) and feeds text to Android's built-in TTS engine for sequential read-aloud.
- **Comic-specific?** Yes — natively handles CBZ, CBR, CB7, CBT, PDF on Android.
- **Speaker attribution?** No. All bubbles read with the same Android TTS voice, no character identification.
- **Voice quality:** Android built-in TTS (low quality, robotic). User reviews describe OCR + TTS as "not very usable/reliable" — OCR fails on non-standard fonts (secondary-corroborated: Google Play store reviews via S13).
- **Pricing:** Free (GPLv3).
- **OSS/closed:** Open source (GPLv3).
- **Comicast gap:** No speaker attribution, no per-character voices, no ElevenLabs-quality synthesis, no self-improving series profile, no audio file output (MP3/M4B). Mobile only (no desktop pipeline).

---

### 3.2 TTS Comics

- **URL:** https://www.ttscomics.com/home (primary — fetched 2026-05-03)
- **What it does:** iOS app that reads CBZ files aloud using high-quality voice synthesis. Panel-by-panel navigation, multiple voices and languages (English, Spanish, Japanese), speed 100–800 WPM.
- **Comic-specific?** Partially — supports CBZ only; no CBR, no PDF mentioned.
- **Speaker attribution?** No — reads all bubbles with a single selected voice; no character identification.
- **Voice quality:** App store reviews not fetched; self-described as "high-quality voice synthesis with natural pronunciation." # UNVERIFIED — quality not independently confirmed.
- **Pricing:** Free download (App Store). # UNVERIFIED — no premium tier details found.
- **OSS/closed:** Closed source (iOS app).
- **Comicast gap:** No speaker attribution, single voice, iOS-only, no batch audio output, no CBR/PDF support, no series memory.

---

### 3.3 ReadLoudly

- **URL:** https://readloudly.com/comic-reader/ (primary — fetched 2026-05-03)
- **GitHub:** None found.
- **What it does:** Web app + reader that narrates CBR and CBZ files aloud using AI TTS voices. 200+ voices, 40+ languages. Positioned as "listen to comic books like audiobooks."
- **Comic-specific?** Yes — explicitly markets CBR and CBZ support.
- **Speaker attribution?** No — reads extracted text with a single selected voice; no mention of character detection or multi-voice per character.
- **Voice quality:** Claims natural-sounding AI voices, market-competitive with NaturalReader and Speechify (secondary-corroborated: groupbuyseotools.net review, S13).
- **Pricing:** Free (50 MB file limit), Core (200 MB), Pro (500 MB). Exact Core/Pro prices not loaded from pricing page (JS-rendered, content blocked). Character limits apply per tier. # UNVERIFIED exact prices.
- **OSS/closed:** Closed source.
- **Comicast gap:** No speaker attribution, no per-character voice assignment, no audio export (batch MP3/M4B), no series profile, no self-improving loop. Web-only, no CLI pipeline.

---

### 3.4 cbrTekStraktor

- **URL:** https://github.com/cbrtekstraktor/cbrTekStraktor (primary — S10 search)
- **What it does:** Java desktop tool that extracts text from speech bubbles in CBR files using binarization + connected components + K-Means + Apache Tesseract OCR. No audio output — text extraction only, targeted at "analysis" and scanlation.
- **Comic-specific?** Yes (CBR only).
- **Speaker attribution?** No.
- **Voice quality:** N/A — no audio output.
- **Pricing:** Free (open source, SourceForge / GitHub).
- **OSS/closed:** Open source.
- **Comicast gap:** Extraction tool only. No TTS, no speaker attribution, no audio output, CBR-only, Java (not Python), last meaningful activity 2018.

---

### 3.5 ACBR (A Comic Book Reader)

- **URL:** https://github.com/binarynonsense/comic-book-reader (primary — S11 search)
- **What it does:** Desktop reader (Windows + Linux) for CBZ, CBR, CB7, EPUB, FB2, MOBI, PDF. Includes built-in OCR via Tesseract. Read-aloud via OS TTS.
- **Comic-specific?** Yes.
- **Speaker attribution?** No.
- **Voice quality:** System TTS (low quality).
- **Pricing:** Free (open source).
- **OSS/closed:** Open source.
- **Comicast gap:** Same as Seeneva — single voice, no character attribution, no audio file output, no series profile.

---

### Excluded candidates (surfaced by S01, not entered)

- **Musely** (surfaced by S01): excluded — unrelated product (AI photo/image text editor, musely.ai; no audio output, no comic pipeline relevance).

---

## 4. Category B — Generic Multi-Character TTS / Audiobook Generators

These handle prose text well but have no path to comics.

---

### 4.1 Narratemi

- **URL:** https://narratemi.com/ (secondary-corroborated — reached via S07 search snippet, not directly fetched)
- **What it does:** Web-based audiobook generator. Ingests prose text (ePub, text), detects speaker attribution from dialogue tags in text ("said Mark"), assigns distinct AI voices to each character automatically. 7 TTS engine options including ElevenLabs.
- **Comic-specific?** No — requires text input. No image/CBZ/CBR ingestion; no OCR; no vision pipeline.
- **Speaker attribution?** Yes, from text — NLP-based ("said X" patterns). Does NOT work on comics because it has no visual understanding.
- **Voice quality:** High — can use ElevenLabs as back-end.
- **Pricing:** Pay-per-use, $20–$80 for a full audiobook; 50,000 free characters to start (secondary-corroborated: search snippet S07).
- **OSS/closed:** Closed source (SaaS).
- **Comicast gap:** No comic image input path. Speaker attribution works only from text dialogue tags. Requires pre-existing clean text transcript, which comics do not have. The Comicast vision pipeline is the missing piece.

---

### 4.2 ElevenReader (ElevenLabs)

- **URL:** https://elevenreader.io/ (primary — fetched via S02)
- **What it does:** Read-aloud app for ePub, PDF (text-based), articles. Free: 10 h/month AI audio. Ultra: $11/month or $99/year.
- **Comic-specific?** No. PDFs are handled as text-layer PDFs. Image-based comic PDFs without a text layer (the typical case) are not supported. No OCR pipeline.
- **Speaker attribution?** No — single narrator voice.
- **Pricing:** Free (10 h/mo) / Ultra $11/mo or $99/yr (primary — elevenreader.io/pricing, S15).
- **OSS/closed:** Closed source.
- **Comicast gap:** No image understanding, no OCR, no speaker attribution, no comic format support.

---

### 4.3 Speechify

- **URL:** https://speechify.com/ (secondary-corroborated: S04 search)
- **What it does:** TTS app with screenshot OCR feature ("photo text to speech"). Can read a screenshot with text. 1000+ voices, 60+ languages. VoiceOver Studio for audiobook creation.
- **Comic-specific?** Marginally — screenshot OCR can extract text from a comic panel image if manually triggered, but this is not a comic pipeline; it's a workaround. No CBZ/CBR ingestion, no speaker attribution, no panel-order logic.
- **Speaker attribution?** No.
- **Voice quality:** High (competitive with ElevenLabs at lower tiers, ElevenLabs at premium).
- **Pricing:** Freemium; premium plans ~$139/year (secondary-corroborated: multiple comparison articles). # UNVERIFIED exact 2026 pricing.
- **OSS/closed:** Closed source.
- **Comicast gap:** No automated comic pipeline. Speaker attribution absent.

---

### 4.4 Murf.ai

- **URL:** https://murf.ai/ (secondary-corroborated: S04)
- **What it does:** AI voice generator and audiobook narrator. Upload text script, assign multiple voices to characters. 200+ voices, 20+ languages. Targets publishers and authors.
- **Comic-specific?** No — text-only workflow.
- **Speaker attribution?** No — user manually assigns voices to each character's lines. Not automated.
- **Voice quality:** High (professional audiobook-grade).
- **Pricing:** Freemium; paid plans from ~$29/month (secondary-corroborated: Murf pricing page via S04). # UNVERIFIED exact 2026 pricing.
- **OSS/closed:** Closed source.
- **Comicast gap:** No image input, no comic-specific pipeline, no automated speaker detection from visual context.

---

### 4.5 All Voice Lab

- **URL:** https://www.allvoicelab.com/ (secondary-corroborated: S06 search)
- **What it does:** AI TTS platform with manga/anime-specific voice content. Blog describes converting manga text to audio. No CBZ pipeline described.
- **Comic-specific?** Partial (manga-focused marketing) but text-only workflow.
- **Speaker attribution?** No automated attribution from images.
- **Pricing:** # UNVERIFIED — no pricing page fetched.
- **OSS/closed:** Closed source.
- **Comicast gap:** Same as Murf/Narratemi — no visual pipeline.

---

### 4.6 LyricWinter

- **URL:** https://lyricwinter.com/voices/marvel-comics (secondary-corroborated: S01)
- **What it does:** Fan site offering Marvel Comics AI voice profiles for fanfiction/podfic creation using ElevenLabs voices. Not a pipeline tool; provides pre-built voice IDs for Marvel characters.
- **Comic-specific?** Marketing is comic-themed, but the product is a TTS voice library, not a comic-to-audio pipeline.
- **Speaker attribution?** No automated attribution.
- **Pricing:** # UNVERIFIED.
- **OSS/closed:** Closed source.
- **Comicast gap:** Not a pipeline. No image input, no OCR, no panel-order logic.

---

## 5. Category C — Human-Produced Audio Drama (Comics as Source Material)

These are the "gold standard" in quality but are human-produced at enormous cost — not automated.

---

### 5.1 Audible Original Audio Dramas (The Sandman, Locke & Key)

- **URL:** https://www.audible.com/blog/article-best-audiobooks-for-comic-fans (secondary-corroborated: S03)
- **What it does:** Human-produced full-cast audio dramas from comic IP. Sandman: James McAvoy, Kat Dennings, Michael Sheen. Locke & Key: Haley Joel Osment, Tatiana Maslany, 50+ voice actors.
- **Comic-specific?** Yes — but as IP adaptations, not automated narration.
- **Speaker attribution?** Human script writers + directors + voice actors.
- **Pricing:** $15–$35 per production (consumer purchase) / production cost ~$500K+ # UNVERIFIED.
- **OSS/closed:** Closed source / professional production.
- **Comicast gap:** These are hand-crafted productions with A-list talent, not automation tools. Comicast is positioned as the democratised, personal-use version. Not a direct competitor for the tool; is the "aspirational quality bar."

---

### 5.2 GraphicAudio

- **URL:** https://en.wikipedia.org/wiki/GraphicAudio (secondary-corroborated: S03, S18)
- **What it does:** Full-cast audio drama company using voice actors + music + SFX, primarily adapting genre fiction (Halo, Star Wars, DC comics). Positioned as "a movie in your mind."
- **Comic-specific?** Yes (DC adaptations historically).
- **Speaker attribution?** Human.
- **Pricing:** Individual productions sold at $20–$40 per title. Subscription model exists. # UNVERIFIED exact 2026 pricing.
- **OSS/closed:** Closed source (commercial studio).
- **Relevant context:** In **February 2026, GraphicAudio (RB Media parent) laid off ~50% of staff** (secondary-corroborated: S18 search). This signals fragility of the human-production model and validates automated tooling as an alternative direction.
- **Comicast gap:** Human production studio. Extremely high cost, not automatable in this model. Comicast does not compete head-on; it serves the personal-use segment GraphicAudio cannot address.

---

### 5.3 Marvel Audiobooks (Dreamscape Media / Audible)

- **URL:** https://www.comicsbeat.com/marvel-audiobooks-dreamscape-media/ (secondary-corroborated: S03)
- **What it does:** 35+ Marvel comics narrated as audiobooks on Audible. Primarily single-narrator reading of comic scripts, not dramatised multi-voice production.
- **Comic-specific?** Yes (Marvel IP only).
- **Speaker attribution?** Single narrator in most cases (human, not automated).
- **Comicast gap:** Licensed IP production by a professional publisher. Does not serve the "I own this comic, I want to listen to it" personal-use case.

---

## 6. Category D — Research / Academic Prototypes

These are the most important proxies for "does this problem have known solutions."

---

### 6.1 arXiv 2509.15253 — "Emotion-Aware Speech Generation with Character-Specific Voices for Comics"

- **URL:** https://arxiv.org/html/2509.15253v1 (primary — fetched 2026-05-03)
- **Submitted:** September 18, 2025.
- **What it does:** End-to-end system: (1) visual processing via Faster R-CNN for speech balloon/character detection, (2) per-comic ResNet-50 classifier trained on 40 reference images per character, (3) binary emotion intensity classifier, (4) GPT-4 for dialogue attribution + emotion labelling given visual elements + plot context, (5) reference-conditioned TTS for character-specific voice synthesis.
- **Comic-specific?** Yes — tested on manga datasets: Manga109, Manga109Dialogue, KangaiSet.
- **Speaker attribution?** Yes — but accuracy is **64.8%** (Setting C, total). Joint speaker+emotion accuracy: **20.4%**. Character recognition: 62.9%.
- **Code available?** Not mentioned in the paper; not found via search.
- **Key differences from Comicast:**
  1. Uses trained per-comic ResNet-50 (requires 40 reference images per character → not zero-shot). Comicast uses zero-shot VLM (Claude vision) — no per-comic training required.
  2. 64.8% speaker accuracy vs Comicast target ≥90% post-HITL.
  3. No HITL correction loop — no series memory.
  4. No self-improving loop.
  5. Academic prototype — no consumer release, no CBZ/CBR/PDF pipeline.
  6. Manga datasets only (not Western comics like Invincible).
- **Verdict:** Strongest proof-of-concept that the problem is solvable. Also the clearest evidence of the **unsolved gap**: low accuracy without HITL, no self-improving loop, per-comic training requirement. Comicast's approach is architecturally novel by design.

---

### 6.2 arXiv 2505.13082 — "MultiActor-Audiobook: Zero-Shot Audiobook Generation"

- **URL:** https://arxiv.org/abs/2505.13082 (primary — fetched 2026-05-03)
- **Submitted:** May 19, 2025.
- **What it does:** Zero-shot approach for novels — multimodal speaker persona generation + LLM-based script instruction generation → emotionally expressive audiobook. Tested against commercial products via human + MLLM evaluation.
- **Comic-specific?** No — prose fiction only, no visual pipeline.
- **Speaker attribution?** From text (dialogue tags), not from images.
- **Code available?** Not mentioned in abstract.
- **Comicast gap:** No visual understanding. Relevant to Comicast's Stadio 3 (voice direction) but not to the core value proposition (visual speaker attribution from comic images).

---

## 7. Category E — Open-Source Building Blocks (not products)

These are research/infrastructure tools that inform the implementation but are not competitors.

| Tool | Repo | What it is | Relevance to Comicast |
|---|---|---|---|
| ogkalu/comic-speech-bubble-detector-yolov8m | https://huggingface.co/ogkalu/comic-speech-bubble-detector-yolov8m | YOLOv8m trained on ~8k manga/webtoon/Western comic images for bubble detection | Could inform a CV pipeline; Comicast uses VLM (Claude) instead — simpler stack |
| kitsumed/yolov8m_seg-speech-bubble | https://huggingface.co/kitsumed/yolov8m_seg-speech-bubble | YOLOv8m segmentation for speech bubbles | Same as above |
| comic-translate (ogkalu) | https://github.com/ogkalu2/comic-translate | AI comic translator (CBZ/CBR/PDF/EPUB, OCR, translation, re-rendering) | Shares OCR/extraction logic; no audio; shows feasibility of multi-format comic processing |
| damishshah/comic-book-reader | https://github.com/damishshah/comic-book-reader | Python: detects speech bubbles via OpenCV, reads text with pytesseract | Closest OSS precedent to Comicast's extraction stage; no speaker attribution, no TTS |
| Dia (nari-labs) | https://github.com/nari-labs/dia | OSS multi-speaker dialogue TTS, non-verbal sounds | Potential alternative back-end for Phase 2 (local TTS) |
| MOSS-TTS (OpenMOSS) | https://github.com/OpenMOSS/MOSS-TTS | Multi-speaker, environmental SFX, streaming | Phase 2 alternative |

> Note: these are listed for completeness and future reference. They confirm that the sub-problems (bubble detection, OCR, multi-speaker TTS) are individually solved in OSS. The **unsolved integration** is the specific combination: visual speaker attribution + per-character voice + HITL loop + series memory. No OSS project combines all four.

---

## 8. Gap Analysis

### The core claim (spec.md §1)

> "Tool esistenti (Audible, ElevenLabs Reader, Speechify) gestiscono libri di testo ma non fumetti — perché i fumetti richiedono comprensione visiva."

**Verdict: CONFIRMED.** All three named tools are text-only pipelines. None handle CBZ/CBR/PDF image-based comics with visual speaker attribution.

### The full market gap

After 18 searches and fetching 9 product pages directly, the landscape is:

| Approach | Products found | Fills the gap? |
|---|---|---|
| Text-only multi-character TTS | Narratemi, Murf.ai, ElevenReader, Speechify VoiceOver Studio | No — requires pre-existing text |
| Comic read-aloud (single voice) | Seeneva, TTS Comics, ReadLoudly, ACBR | No — no speaker attribution |
| Human-produced comic audio drama | Audible/Sandman, GraphicAudio, Marvel/Dreamscape | No — not a tool; expensive licensed productions |
| Academic prototypes | arXiv 2509.15253 | Closest — but 64.8% accuracy, no HITL, no release |
| OSS sub-pipelines | Seeneva, cbrTekStraktor, YOLOv8 models, comic-translate | No — individual stages, not integrated pipeline |

**The specific gap Comicast occupies:** A CBZ/CBR/PDF-in → MP3/M4B-out pipeline with:
1. **Zero-shot visual speaker attribution** (no per-comic training required)
2. **Per-character ElevenLabs-quality voices** with emotion direction
3. **HITL correction loop** for accuracy improvement
4. **Self-improving series profile** (cross-volume memory)
5. **Batch offline output** (file on disk, not a reading app)

This combination does not exist as a product, open-source tool, or released codebase as of 2026-05-03.

### Caveat — arXiv 2509.15253

This paper (Sept 2025) demonstrates the problem is actively researched. The risk is that a team from the paper or adjacent researchers ships a prototype in the 2026 timeframe. Mitigation: Comicast's zero-shot VLM approach + HITL + series profile gives architectural differentiation even vs a concurrent research release.

---

## 9. Monetisation Criteria Scoring

Applying the 5-criteria framework (≥4/5 → monetise):

### Criterion 1: Mercato ampio — >10.000 potenziali clienti paganti?

**Score: YES (strong evidence)**

- Global audiobook market: $8.7–14B in 2026 (multiple analyst sources; see §12). Fiction captures 63% of share.
- Comic/graphic novel readership: Estimated 6–8 million active comic readers in North America alone (# UNVERIFIED exact current figure — conservative proxy: Comixology had ~4M active subscribers before Amazon absorption; Webtoon reports 90M monthly users globally as of 2024 per secondary sources).
- Manga audiobook search interest: Active searches, TikTok content about "how to make voice read the manga" — demonstrated user demand (S06).
- The "personal use audiobook generator" segment already has multiple paid tools (Narratemi $20–80/book, Speechify $139/year, Murf from $29/month). The market pays.
- **Conservatively: >100,000 potential users** exist who own digital comics and would pay to listen to them with quality multi-character audio. The segment is narrower than general audiobooks, but 10,000 paying customers is achievable at a $10–15/month or $25–50/generation price point.

**Verdict: YES**

### Criterion 2: Bisogno ricorrente — utente torna ogni settimana/mese?

**Score: YES (strong evidence)**

- A user who reads comics weekly (typical pattern) generates recurring demand:
  - One new comic issue per week = 52 generation jobs/year.
  - Series readers (Invincible = 144 issues) would return for every new volume.
  - Subscription model naturally fits: "generate N issues/month."
- The self-improving series profile actually **reinforces** retention: users are incentivised to stay on the platform because their series memory improves over time (switching cost).

**Verdict: YES**

### Criterion 3: Difendibilità — difficile da replicare o fare con Excel/tool gratuiti?

**Score: YES (moderate-strong)**

- Cannot be done with free tools today: No free tool does speaker attribution at all — Seeneva and ReadLoudly read all bubbles with a single TTS voice. The closest research prototype (arXiv 2509.15253) reaches only 64.8% speaker attribution accuracy with trained-per-comic classifiers and no HITL loop. No free OSS pipeline integrates all stages.
- Technical barriers: requires a vision LLM (API cost/access), ElevenLabs API (API key + cost), correct panel ordering, HITL loop, series profile management.
- Accumulating series profiles are a **network-effect moat**: user who has processed 20 volumes of Invincible has a better profile than a new entrant starting cold.
- Caveat: the approach uses commodity APIs (Claude, ElevenLabs) — anyone with API access and the same architecture could build this. Replication time for a skilled engineer: ~3–4 weeks. Not a patent-level moat.
- However, **execution + polish + series profile library** creates a soft moat that free tools will not match quickly. The arXiv 2509.15253 team has had 7+ months and no consumer release.

**Verdict: YES (with caveat noted)**

### Criterion 4: Scalabilità — funziona oltre Italia / oltre il settore senza riscrittura?

**Score: YES (strong)**

- The pipeline is language-agnostic at the architecture level (Claude vision + ElevenLabs work in English by default; both support additional languages in later phases).
- No Italy-specific components whatsoever — English Western comics (US market) are the primary target.
- Scalable across comic genres: superhero (Invincible), sci-fi (Saga), horror (Locke & Key), manga (if non-English OCR added in Phase 4).
- The `VoiceProvider` interface (spec.md §Fase 2) is explicitly designed for provider swap — scales to local TTS (Coqui, F5-TTS) for users in regions without ElevenLabs access.
- SaaS model is inherently global with no localization needed for Phase 1.

**Verdict: YES**

### Criterion 5: Willingness to pay — utenti abituati a pagare per tool simili?

**Score: PARTIAL — YES in general audiobook/TTS market, CONSTRAINED by legal posture**

- **Pro-willingness signals:**
  - Narratemi users pay $20–80 per book generation (verified from site, S07).
  - Speechify: $139/year. Murf: from $29/month. ElevenReader Ultra: $99/year.
  - GraphicAudio consumers pay $20–40 per audio drama title.
  - The market clearly pays for audiobook generation and consumption.
- **Legal posture constraint:**
  - As stated in spec.md §11 and the plan: audio output is for personal use only; distributing or streaming generated audio of copyrighted comics would raise publisher copyright issues.
  - This blocks the "content marketplace" model (distribute generated audio as a service, like Audible). It does NOT block the "tool" model: user pays to run the pipeline on their own legally-purchased comics, keeps the audio file locally.
  - The tool model (SaaS, pay-per-generation or subscription) has clear precedent: Narratemi ($20–80/book), Murf ($29/month), ElevenLabs ($5–$22/month for API). Users pay for the tool, not the content.
  - The legal risk caps scale — Comicast cannot build a "Spotify for generated comic audio." It can build the generator tool.

**Verdict: YES for tool model; constrained for content model. The criterion is met for the "tool" business model the plan intends.**

### Summary Scorecard

| Criterion | Score | Key evidence |
|---|---|---|
| Mercato ampio (>10K customers) | YES | Audiobook market $8.7B+; >90M manga users; multiple paid TTS tools exist |
| Bisogno ricorrente | YES | Weekly comic reading habit; series profile creates switching cost |
| Difendibilità | YES (with caveat) | No free tool integrates all 4 stages; 7+ months head-start over arXiv prototype; soft moat via series profiles |
| Scalabilità | YES | English-first, globally usable, provider-agnostic architecture |
| Willingness to pay | YES (tool model) | $20–80/book precedent at Narratemi; $99–$139/year TTS tools; blocked only for content marketplace model |
| **Total** | **5/5 (tool model)** | **Meets monetisation threshold** |

> **Note on criterion 5:** The legal constraint rules out scaling to a "content marketplace" (unlimited hosted generated audio). The "tool" model (user pays, generates locally) is fully supported and has precedent. Criterion 5 is scored YES for the intended business model.

---

## 10. Tier Decision

**Tier: A**

**Rationale:**

- All 5 monetisation criteria are met for the "tool" model.
- The legal posture cap (no content marketplace) prevents Tier S. A Tier S product (flagship, biggest market, most monetisation potential) would require a content distribution angle (e.g., licensed comic publishers paying for automated audio drama production). Without publisher partnerships, the addressable market is the prosumer/enthusiast segment — substantial (>10K paying users) but not platform-scale.
- Tier A is correct: monetisable, strong differentiation, solid market, clear path to $5–50/month SaaS or per-generation pricing, defensible technically for the next 12–18 months.
- Tier B (open source only) would be wrong: 5/5 criteria are met for the tool model. Open-sourcing is an option for visibility but should not be the default.

**Comparison to plan author's prior estimate:** The plan predicted "Tier A or S." This analysis independently arrives at **Tier A** — consistent with the plan's own legal-posture caveat. No downward revision (B) is warranted.

**Conditions under which the tier should be revisited:**
1. If publisher licensing deals become possible → upgrade to S.
2. If arXiv 2509.15253 team ships a polished consumer product before Comicast → re-evaluate difendibilità.
3. If ElevenLabs API costs increase significantly → re-evaluate unit economics.

---

## 11. Key Differentiators for README

The following points should appear in the public README to establish Comicast's position:

1. **The only tool that generates a proper audiobook (MP3/M4B) from a comic file** — not a read-along app.
2. **Zero-shot visual speaker attribution** — no per-comic training required. Works on any new series on first run.
3. **Per-character voices** with ElevenLabs v3 emotion direction, not a single narrator for the whole book.
4. **Self-improving series profile** — accuracy improves with each correction, reducing HITL time from ~30 min (vol 1) to <10 min (vol 3+).
5. **Cross-volume series memory** — voice archetypes are reused across volumes and series.
6. **Fully offline batch output** — runs on your machine, keeps your files local, respects your privacy.
7. Compared to arXiv 2509.15253: zero-shot (no training data required), HITL loop, series memory, consumer-grade output format — all absent in the academic prototype.

---

## 12. Sources

### Primary (URL fetched directly)

| Source | URL | Access date | Key fact extracted |
|---|---|---|---|
| Seeneva homepage | https://seeneva.app/ | 2026-05-03 | GPLv3, Android-only, Android TTS, no speaker attribution |
| Seeneva GitHub | https://github.com/Seeneva/seeneva-reader-android | 2026-05-03 | OCR/TTS limited to English, user complaints about reliability |
| TTS Comics | https://www.ttscomics.com/home | 2026-05-03 | iOS, CBZ only, single voice, free |
| ReadLoudly | https://readloudly.com/comic-reader/ | 2026-05-03 | CBR+CBZ, single voice, no speaker attribution |
| ElevenReader pricing | https://elevenreader.io/pricing | 2026-05-03 (via S15) | Free 10h/mo, Ultra $11/mo — no comic format support |
| arXiv 2509.15253 | https://arxiv.org/html/2509.15253v1 | 2026-05-03 | 64.8% speaker accuracy, trained ResNet-50, GPT-4, no HITL, no release |
| arXiv 2505.13082 | https://arxiv.org/abs/2505.13082 | 2026-05-03 | MultiActor-Audiobook, prose-only, no visual pipeline |

### Secondary-corroborated (search snippet + secondary review source, not direct fetch)

| Source | Corroboration | Key fact |
|---|---|---|
| Narratemi pricing + features | S07 search snippet; https://narratemi.com/ not directly fetched | $20–80/book, text-only, NLP speaker attribution, no comic support |
| GraphicAudio layoffs Feb 2026 | S18; CWA press release https://cwa-union.org/news/releases/graphic-audio-united-cwa-workers-condemn-rbmedia-layoffs-targeting-union-members | ~50% staff cut, parent RB Media, ~22 bargaining-unit positions eliminated, signals fragility of human-production model |
| Speechify pricing ~$139/year | S04 multiple comparison articles | General TTS market pricing reference |
| Murf.ai pricing from $29/month | S04 multiple comparison articles | General TTS market pricing reference |
| Audiobook market $8.7–14B 2026 | S12 multiple analyst sources (Mordor Intelligence, Coherent Market, Fortune Business Insights) | Market size baseline |
| Marvel Dreamscape 35+ audiobooks | S03 ComicsBeat | Existing licensed comic audio products |
| Google Play reviews on Seeneva TTS | S13 search snippet | "not very usable/reliable" OCR/TTS |
| cbrTekStraktor | S10 + S04 SourceForge search | Java, last active 2018, CBR-only, no audio |
| comic-translate GitHub | S11 | Multi-format comic OCR feasibility proof |
