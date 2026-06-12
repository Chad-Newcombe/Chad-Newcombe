# Video Content System — Higgsfield Replacement Plan

A plan for an automated pipeline that produces short-form educational/technical
explainer videos in the style of [@brancheducation](https://www.instagram.com/brancheducation/)
("Simplifying Complexity Through Visual Storytelling — Science | Technology |
Engineering | Education"), without paying for a Higgsfield subscription.

This document is the design spec. No application code has been written yet —
see [Phased Roadmap](#8-phased-roadmap) for what to build first.

---

## 1. What Higgsfield Actually Sells

Higgsfield is an **aggregator + markup layer** on top of AI video models. It
gives you one subscription and a UI/MCP that calls out to Sora 2, Veo 3.1,
Kling 3.0, Wan, Hailuo, Seedance, etc. The value is convenience (one bill,
camera-preset library, DaVinci plugin) — the underlying generation is the
same open/commercial models you can call directly for less.

Current pricing: Free tier, then **Starter $15 → Plus $34–49 → Ultra $84–129 /
month**, credits expire after 90 days, ~40–70 credits per Sora/Veo clip.
([higgsfield.ai/pricing](https://higgsfield.ai/pricing),
[Higgsfield 2026 pricing breakdown](https://www.vo3ai.com/higgsfield-ai-pricing))

**Conclusion:** we don't need to replace "Higgsfield the model" — we need to
replace "Higgsfield the convenience layer" with direct, pay-per-use or
self-hosted access to the same model family, called from an MCP server.

---

## 2. What Branch Education's Content Actually Is

Branch Education's signature look is **3D cutaway/exploded-view technical
animations** (engines, electronics, infrastructure, biology) with clean
labels, camera moves through a mechanism, and calm narration. That style is
fundamentally a **procedural 3D animation problem**, not a diffusion-video
problem — current AI video models (Sora/Veo/Kling/Wan/LTX) are not reliable
at "show me a 4-stroke engine cutaway with correctly labeled, mechanically
consistent parts." They're great at moody B-roll, abstract backgrounds,
intros/hooks, and stylized inserts.

**Implication for the plan:** don't try to make AI video generation do the
whole job. Use the right tool per shot type:

| Shot type | Best tool | Why |
|---|---|---|
| Core "how it works" mechanism/cutaway | **Blender** (scripted via `bpy`, free/OSS) | Precise, labeled, consistent, reusable as a 3D asset library |
| Stylized B-roll, hooks, transitions, backgrounds | **Open video diffusion models** (Wan 2.2, LTX-Video 2, HunyuanVideo 1.5) | This is what Higgsfield was being used for — directly replaceable |
| Diagrams / on-screen graphics / captions / lower-thirds | **Remotion or MoviePy/FFmpeg overlays** | Deterministic, code-driven, free |
| Narration | **Kokoro TTS** (free, local, fast) | Matches Branch Education's calm narrator tone well enough for v1 |
| Music/SFX | Royalty-free library (Pixabay Audio, YouTube Audio Library) | Free |

---

## 3. The Higgsfield Replacement Layer

Two complementary options, both reachable via MCP so Claude agents can call
them directly. Recommend starting with Option A, adding Option B once volume
justifies the GPU cost.

### Option A — `fal.ai` MCP (pay-per-use, zero infra)

[fal.ai](https://fal.ai) hosts the same open-weight models Higgsfield wraps
(Wan 2.2, LTX-Video 2, HunyuanVideo 1.5, plus Kling/Veo/Sora endpoints) at raw
API pricing — **no subscription, no credit expiry, no markup**.

- MCP servers: [`derekalia/fal-mcp-ts`](https://github.com/derekalia/fal-mcp-ts),
  [`raveenb/fal-mcp-server`](https://github.com/raveenb/fal-mcp-server), or fal's own
  documented MCP ([fal.ai/docs/.../mcp](https://fal.ai/docs/documentation/setting-up/mcp))
- Model catalog/pricing reference: [`PHY041/fal-ai-model-database`](https://github.com/PHY041/fal-ai-model-database)
  (1,094 models with pricing, JSON/CSV export — useful for the agent to pick
  the cheapest model that meets a shot's quality bar)

**Indicative per-second costs** (vs. Higgsfield credits, which run ~$0.30–1.00
per *clip* once subscription cost is amortized):

| Model | Cost | Use case |
|---|---|---|
| LTX-Video 2 Fast | $0.04–0.16/sec | Quick B-roll, drafts |
| Wan 2.2 A14B (480p) | $0.04/sec | Background motion, low-stakes shots |
| Wan 2.2 A14B (720p) | $0.08/sec | Hero B-roll |
| HunyuanVideo 1.5 | $0.075/sec | Stylized cinematic inserts |

A typical 45-second Reel might use 4–6 AI clips totaling ~20s of footage →
**roughly $1–3 of raw generation cost**, vs. a $15–84/month subscription that
caps total monthly output via credits.

### Option B — Self-hosted ComfyUI MCP (free beyond GPU cost)

For higher volume, run Wan 2.2 / LTX-Video 2 locally or on a rented GPU
(RunPod/Vast.ai) via ComfyUI, exposed to Claude through an MCP server:

- [`joenorton/comfyui-mcp-server`](https://github.com/joenorton/comfyui-mcp-server) — lightweight, local ComfyUI bridge
- [`shawnrushefsky/comfyui-mcp`](https://github.com/shawnrushefsky/comfyui-mcp) — broader image/video/audio/3D support
- Reference workflows: [Wan 2.2 ComfyUI examples](https://comfyanonymous.github.io/ComfyUI_examples/wan22/)

Marginal cost per clip ≈ electricity/rented-GPU-minutes only.

### Considered and rejected

- **`creativecgl/cgl-higgsfield`** ("unlimited mode, bypasses credit system") —
  this calls Higgsfield's own backend while circumventing their billing. That's
  a ToS violation / account-ban risk and not something I'd build on. **Not
  recommended.**
- **`Open-Generative-AI` / "open-higgsfield-ai" forks** — these are
  self-hosted *UIs* that still proxy through `Muapi.ai`, another paid
  aggregator with its own markup. They don't actually remove the
  subscription-style cost, just rebrand it. Could be a nice front-end later,
  but doesn't solve the cost problem on its own.

---

## 4. System Architecture

Mirrors the agent-pipeline pattern already used in this repo's
`digital-product-agents` project (`src/agents/*` + `Orchestrator` +
Anthropic tool-use loop).

```
Topic idea
   │
   ▼
┌─────────────────┐   research facts, hooks, sources
│ Research Agent   │──────────────┐
└─────────────────┘               │
   │                               ▼
   ▼                       ┌─────────────────┐
┌─────────────────┐        │ Script Agent     │  narration script + scene list
│ Storyboard Agent │◄───────└─────────────────┘
└─────────────────┘
   │ shot list: {type, prompt/blender-scene, duration, on-screen text}
   ▼
┌──────────────────────────────────────────────────────────┐
│ Visual Generation Router                                   │
│  ├─ Blender renderer  (core mechanism/cutaway shots)       │
│  ├─ fal.ai MCP        (AI B-roll/inserts — Higgsfield repl)│
│  └─ ComfyUI MCP       (self-hosted overflow/volume)        │
└──────────────────────────────────────────────────────────┘
   │ rendered clips (.mp4)
   ▼
┌─────────────────┐
│ Voiceover Agent  │  Kokoro/XTTS narration per scene
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ Assembly Agent   │  FFmpeg/MoviePy: stitch clips + VO + captions + music + branding
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ Publishing Agent │  Reels-formatted (9:16, ≤90s) export + caption/hashtags
└─────────────────┘  (reuse marketing-agent patterns from digital-product-agents)
```

---

## 5. Proposed Project Structure

New sibling project alongside `digital-product-agents`, same conventions
(Pydantic models, Anthropic tool-use agents, Typer CLI):

```
video-content-system/
├── PLAN.md                       ← this document
├── main.py                       ← `vc create "<topic>"` CLI entry point
├── pyproject.toml
├── .env.example                  ← ANTHROPIC_API_KEY, FAL_KEY, etc.
├── src/
│   ├── orchestrator.py
│   ├── agents/
│   │   ├── research_agent.py     ← topic facts, sources, hook angle
│   │   ├── script_agent.py       ← narration + scene breakdown
│   │   ├── storyboard_agent.py   ← shot list, routes each shot to a generator
│   │   ├── voiceover_agent.py    ← Kokoro/XTTS narration
│   │   └── publishing_agent.py   ← captions, hashtags, Reels export spec
│   ├── generators/
│   │   ├── blender_renderer.py   ← bpy scripts for cutaway/mechanism scenes
│   │   ├── fal_video_generator.py← wraps fal.ai MCP (Wan/LTX/Hunyuan)
│   │   └── comfyui_generator.py  ← wraps local ComfyUI MCP (optional, phase 2)
│   ├── assembly/
│   │   └── video_assembler.py    ← ffmpeg/moviepy stitching + captions
│   └── models/
│       └── video_project.py      ← Pydantic models: Script, Shot, Scene, Project
├── assets/
│   ├── blender/                  ← reusable .blend scene templates per topic category
│   ├── fonts/ music/ brand/
└── outputs/<project-slug>/
    ├── script.json
    ├── shots/*.mp4
    ├── voiceover/*.wav
    └── final.mp4 + captions.srt + social_post.json
```

---

## 6. MCP / Tooling Setup

1. **fal.ai account** → get `FAL_KEY`, add to `.env`
2. Add an fal MCP server to `.mcp.json` (e.g. `raveenb/fal-mcp-server`) so
   agents can call `fal-ai/wan/v2.2-a14b/image-to-video`,
   `fal-ai/ltx-2/text-to-video/fast`, etc. directly
3. **Blender** installed locally/in CI container, scenes built/maintained as
   `.blend` templates with parameterized labels (Python `bpy` driver scripts)
4. **Kokoro TTS** — `pip install kokoro` (or ONNX runtime), runs locally, no
   API key
5. (Phase 2) **ComfyUI** on a GPU box + `comfyui-mcp-server` for self-hosted
   overflow generation

---

## 7. Cost Comparison

| | Higgsfield | This system |
|---|---|---|
| Monthly fixed cost | $15–129 | $0 |
| Per-video AI clip cost | amortized credits (~$0.30–1/clip, capped by plan) | $1–3 raw fal.ai cost per video (pay only for what's used) |
| Core technical animation | not really supported well | Blender — free, reusable asset library, higher quality for this niche |
| Voiceover | not included | Kokoro — free |
| Scales to zero when unused | No (subscription keeps billing) | Yes |

---

## 8. Phased Roadmap

**Phase 1 — MVP script-to-video for one shot type**
- Research + Script agents (reuse `base.py` Anthropic tool-use loop from
  `digital-product-agents`)
- fal.ai MCP wired up, Storyboard agent produces fal prompts for *all* shots
  (skip Blender for now — fastest path to a working end-to-end video)
- Kokoro voiceover + FFmpeg assembly → single `final.mp4`

**Phase 2 — Branch Education look**
- Build 2–3 reusable Blender scene templates (gears/engine cutaway, circuit
  board, generic "exploded view" rig) parameterized by label text
- Storyboard agent routes "mechanism" shots to Blender, "B-roll/hook" shots
  to fal.ai

**Phase 3 — Publishing automation**
- Publishing agent generates caption/hashtags (pattern already exists in
  `digital-product-agents/src/agents/marketing_agent.py`)
- Optional: Instagram Graph API auto-post or scheduled-draft export

**Phase 4 — Volume/cost optimization**
- Add ComfyUI self-hosted generator once monthly fal.ai spend exceeds the
  cost of a rented GPU for the same volume
- Add `PHY041/fal-ai-model-database` lookups so the Storyboard agent
  auto-selects the cheapest model meeting each shot's quality bar

---

## 9. Risks & Open Questions

- **AI video accuracy**: open models still struggle with consistent
  mechanical/technical detail — this plan deliberately keeps that work in
  Blender rather than forcing it through diffusion video.
- **fal.ai is still a paid API** — not free, just unbundled and pay-per-use.
  Estimate real monthly volume before committing to Phase 4 infra.
- **Voice quality**: Kokoro is English-only and doesn't clone voices; if a
  specific narrator voice/brand is needed, XTTS v2 (voice cloning, slower) or
  a paid TTS (OpenAI/ElevenLabs) may be needed for that one component.
- **Instagram publishing**: Graph API posting requires a Business account +
  app review for some scopes — may start as "export ready-to-upload file +
  caption" and add direct posting later.

---

## 10. Next Steps

1. Confirm this architecture direction (Blender for mechanisms + fal.ai for
   AI inserts) before scaffolding code.
2. Stand up Phase 1 (`research_agent`, `script_agent`, fal.ai MCP wiring,
   Kokoro, FFmpeg assembly) as the first working vertical slice.
3. Pick the first Branch-Education-style topic to validate end-to-end.
