# Quiet Brain — Free Video Content System

A plan for an automated pipeline that produces short-form educational/technical
explainer videos for the **Quiet Brain** channel, in the visual style of
[@brancheducation](https://www.instagram.com/brancheducation/) ("Simplifying
Complexity Through Visual Storytelling — Science | Technology | Engineering |
Education").

**Hard constraints (confirmed with owner):**
- **Strictly free** — no paid generation APIs, no subscriptions (this rules out
  Higgsfield *and* its pay-per-use alternatives like fal.ai).
- **Mac / Apple Silicon** — everything must run locally on an M-series Mac.
- **Starting fresh** — no existing workflow to preserve; greenfield build.

> The one unavoidable cost is the **Claude API** that orchestrates the agents
> (the same brain the existing `digital-product-agents` project uses). That's
> an LLM token cost, not a video-service cost. If even that must be $0, the
> agents can be swapped for a local LLM (e.g. Ollama) later — see §9.

This document is the design spec. No application code has been written yet —
see [Phased Roadmap](#8-phased-roadmap).

---

## 1. The Key Realization: We Don't Want a Higgsfield Replacement

Higgsfield is an **aggregator + markup layer** over AI *diffusion-video* models
(Sora, Veo, Kling, Wan, etc.). Its alternatives — fal.ai, self-hosted ComfyUI,
"open-higgsfield" forks — are the same category of tool. Two problems for us:

1. **They cost money.** Higgsfield is $15–129/mo with expiring credits
   ([pricing](https://higgsfield.ai/pricing)); fal.ai is ~$1–3/video pay-per-use.
   Both violate the strictly-free constraint.
2. **They're the wrong tool for this look.** Branch Education's signature is
   **precise, labeled, mechanically-consistent 3D cutaways and clean 2D
   technical diagrams** — engines, circuits, infrastructure, biology. AI
   diffusion video cannot reliably produce "a 4-stroke engine cutaway with
   correctly labeled parts that stay consistent across a camera move." That's a
   **procedural animation** problem, not a generative-video problem.

**Conclusion:** the real answer isn't "replace Higgsfield with a cheaper
generator." It's "use the free, Mac-native *animation* tools that actually
produce this style." AI video becomes an *optional garnish* (stylized B-roll),
run locally and free, not the engine.

---

## 2. The Free, Mac-Native Stack

| Job | Tool | Cost | Apple Silicon notes |
|---|---|---|---|
| 2D conceptual/technical animation (the core Branch Ed look) | **Manim Community Edition** | Free (OSS) | Pure Python, runs natively; the 3Blue1Brown engine |
| 3D cutaway / exploded-view / mechanism shots | **Blender** + `bpy` scripting | Free (OSS) | Metal (GPU) accelerated on M-series |
| On-screen captions, lower-thirds, motion text | **Manim / MoviePy / FFmpeg** | Free | Native |
| Narration (calm Branch-Ed-style voiceover) | **Kokoro TTS** (82M, local) | Free | Runs on MPS/CPU; English only |
| Optional stylized B-roll / hooks / backgrounds | **Local ComfyUI** (Wan 2.2 5B, LTX-Video) | Free (electricity only) | MPS works but **slow** — keep optional |
| Live-action filler (if ever needed) | **Pexels / Pixabay** free API | Free | Free API key |
| Music / SFX | Pixabay Audio, YouTube Audio Library | Free (royalty-free) | — |
| Final assembly (stitch + VO + captions + branding) | **FFmpeg / MoviePy** | Free | Native |
| Agent orchestration ("brain") | **Claude API** | Token cost (see §9) | — |

**Why Manim is the centerpiece:** it produces exactly the clean, animated,
label-driven explainer style Branch Education uses, it's deterministic
(re-renderable, version-controllable), and it's free and native on Mac. Blender
handles the genuinely-3D shots Manim can't. Together they cover ~90% of the
target look with **zero generation cost**.

---

## 3. System Architecture

Mirrors the agent-pipeline pattern already proven in this repo's
`digital-product-agents` project (`src/agents/*` + `Orchestrator` + Anthropic
tool-use loop).

```
Topic idea (for Quiet Brain)
   │
   ▼
┌─────────────────┐   facts, sources, hook angle
│ Research Agent   │──────────────┐
└─────────────────┘               │
   │                               ▼
   ▼                       ┌─────────────────┐
┌─────────────────┐        │ Script Agent     │  narration + scene list
│ Storyboard Agent │◄───────└─────────────────┘
└─────────────────┘
   │ shot list: {type, manim-spec | blender-scene | comfy-prompt, duration, labels}
   ▼
┌──────────────────────────────────────────────────────────┐
│ Visual Generation Router (all free, all local)            │
│  ├─ Manim renderer    (2D concept/diagram/technical anim) │  ← primary
│  ├─ Blender renderer  (3D cutaway / exploded-view)        │  ← primary
│  └─ ComfyUI (local)   (optional stylized B-roll, MPS)     │  ← optional
└──────────────────────────────────────────────────────────┘
   │ rendered clips (.mp4)
   ▼
┌─────────────────┐
│ Voiceover Agent  │  Kokoro narration per scene (local, free)
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ Assembly Agent   │  FFmpeg/MoviePy: clips + VO + captions + music + branding
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ Publishing Agent │  Reels-formatted (9:16, ≤90s) export + caption/hashtags
└─────────────────┘  (reuse marketing-agent patterns from digital-product-agents)
```

---

## 4. Proposed Project Structure

New sibling project alongside `digital-product-agents`, same conventions
(Pydantic models, Anthropic tool-use agents, Typer CLI):

```
quiet-brain/
├── PLAN.md                       ← this document
├── main.py                       ← `qb create "<topic>"` CLI entry point
├── pyproject.toml
├── .env.example                  ← ANTHROPIC_API_KEY (only key needed for v1)
├── src/
│   ├── orchestrator.py
│   ├── agents/
│   │   ├── research_agent.py     ← topic facts, sources, hook angle
│   │   ├── script_agent.py       ← narration + scene breakdown
│   │   ├── storyboard_agent.py   ← shot list, routes each shot to a renderer
│   │   ├── voiceover_agent.py    ← Kokoro narration
│   │   └── publishing_agent.py   ← captions, hashtags, Reels export spec
│   ├── generators/
│   │   ├── manim_renderer.py     ← generates + renders Manim scenes (primary)
│   │   ├── blender_renderer.py   ← bpy scripts for 3D cutaways (primary)
│   │   └── comfyui_local.py      ← optional local ComfyUI B-roll (phase 3)
│   ├── assembly/
│   │   └── video_assembler.py    ← ffmpeg/moviepy stitching + captions
│   └── models/
│       └── video_project.py      ← Pydantic: Script, Shot, Scene, Project
├── assets/
│   ├── manim/                    ← reusable Manim scene templates + Quiet Brain theme
│   ├── blender/                  ← reusable .blend templates (cutaway rigs)
│   ├── brand/                    ← Quiet Brain logo, color palette, fonts
│   └── music/
└── outputs/<project-slug>/
    ├── script.json
    ├── shots/*.mp4
    ├── voiceover/*.wav
    └── final.mp4 + captions.srt + social_post.json
```

---

## 5. Quiet Brain Brand Layer

Because this is a *channel*, not a one-off, the system bakes in brand
consistency so every video looks like Quiet Brain:

- **Manim theme module** — fixed color palette, fonts, label styling, intro/outro
  animation, so all 2D shots share an identity.
- **Blender template scenes** — consistent lighting/material/camera presets.
- **Voiceover** — a single fixed Kokoro voice preset = consistent narrator.
- **Caption/branding overlay** — logo bug + caption style applied in assembly.
- **Publishing agent** — Quiet-Brain-voiced captions + a reusable hashtag set.

*(Open question for owner: confirm the Quiet Brain name/handle, palette, and
narrator-voice preference — these become config constants.)*

---

## 6. Tooling Setup (all free)

1. `pip install manim` (+ system deps: `ffmpeg`, `cairo`, `pango` via Homebrew)
2. Install **Blender** (free) — driven headless via `blender --background --python`
3. `pip install kokoro` (or ONNX runtime) — local TTS, no key
4. `ANTHROPIC_API_KEY` in `.env` — the only required key for v1
5. (Phase 3, optional) **ComfyUI** locally with MPS + Wan 2.2 5B / LTX-Video
   GGUF weights; optionally a local ComfyUI MCP
   ([`joenorton/comfyui-mcp-server`](https://github.com/joenorton/comfyui-mcp-server))
6. (Optional) Free **Pexels/Pixabay** API keys for stock B-roll

---

## 7. Cost Comparison

| | Higgsfield | fal.ai route | **This plan (Quiet Brain)** |
|---|---|---|---|
| Monthly fixed cost | $15–129 | $0 | **$0** |
| Per-video generation cost | capped credits | ~$1–3/video | **$0** (local render) |
| Core technical animation | weak | weak | **Manim + Blender — free, exact, reusable** |
| Voiceover | not included | not included | **Kokoro — free** |
| Only running cost | subscription | per-clip API | **Claude API tokens for the agents** |

---

## 8. Phased Roadmap

**Phase 1 — Free script-to-video vertical slice (Manim only)**
- Research + Script agents (reuse `base.py` Anthropic tool-use loop from
  `digital-product-agents`)
- Storyboard agent emits **Manim scene specs** for every shot
- `manim_renderer.py` generates + renders scenes → clips
- Kokoro voiceover + FFmpeg assembly → one `final.mp4` (9:16 Reel)
- **Goal:** a complete, watchable Quiet Brain video at $0 generation cost.

**Phase 2 — Add the 3D Branch-Education look (Blender)**
- 2–3 reusable Blender cutaway templates (gears/engine, circuit, exploded view)
  parameterized by label text
- Storyboard agent routes "3D mechanism" shots to Blender, "diagram/concept"
  shots to Manim
- Lock in the Quiet Brain brand layer (§5)

**Phase 3 — Optional local AI B-roll**
- Add `comfyui_local.py` for stylized hooks/backgrounds via Wan 2.2 5B / LTX on
  MPS — strictly free, just slow; used sparingly where it adds polish

**Phase 4 — Publishing automation**
- Publishing agent generates Quiet-Brain captions/hashtags (pattern exists in
  `digital-product-agents/src/agents/marketing_agent.py`)
- Optional: export ready-to-upload Reel + caption; direct Instagram posting later

---

## 9. Risks & Open Questions

- **Claude API is the one cost.** If "strictly free" must include the brain,
  swap the Anthropic tool-use loop for a **local LLM via Ollama** (e.g. Llama
  3.x / Qwen on Apple Silicon). Doable but lower output quality; recommend
  starting with Claude and revisiting only if cost matters.
- **Manim/Blender have a learning curve.** The agents *generate* the scene code,
  but expect iteration to get the Quiet Brain look dialed in. This is the main
  effort cost in exchange for $0 generation cost.
- **Kokoro is English-only, no voice cloning.** Fine for a consistent narrator;
  if a specific cloned voice is wanted later, XTTS v2 (local, free, slower) can
  swap in.
- **Local ComfyUI on Apple Silicon is slow.** Kept optional precisely for this
  reason — never on the critical path.
- **Instagram publishing** likely starts as "export file + caption," with
  Graph API auto-posting added later (needs a Business account + app review).
- **Confirm Quiet Brain specifics** — handle, palette, fonts, narrator voice,
  first topics — to populate the brand config (§5).

---

## 10. Next Steps

1. Confirm: Quiet Brain = the channel, Branch Education = style reference, and
   the brand specifics in §5/§9.
2. Build Phase 1 (Research + Script + Storyboard agents, `manim_renderer.py`,
   Kokoro, FFmpeg assembly) as the first free, end-to-end vertical slice.
3. Pick the first Quiet Brain topic to validate the look end-to-end.
