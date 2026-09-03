# ShiftMate portfolio video visual identity

## Intent

Warm editorial confidence with inspectable technical detail. The video should
feel like a concise engineering case study for a Taiwanese professor—not an ad,
an admin dashboard recording, or an AI spectacle.

## Palette

- Canvas: `#0e1814` deep green-black.
- Surface: `#17241e` and `#1f3028`.
- Primary text: `#f2f0e8` warm cream.
- Secondary text: `#b9c5bd`.
- Evidence accent: `#8fbea0` sage green.
- Warning accent: `#d5a85d` muted warm gold.
- Failure/refusal accent: `#d58b78` muted coral.

Contrast must remain readable at 1920×1080 and after compression. Color never
carries state by itself; every state also has a label or icon.

## Typography

- Display and scene statements: Georgia, bold.
- Body, metrics, evidence labels, and subtitles: IBM Plex Mono.
- Do not use Inter in the video.
- Traditional Chinese subtitles are primary; English subtitles are smaller and
  lower-contrast beneath them. Keep both inside a 72 px safe area.

## Motion

- One clear hierarchy per scene: statement, proof, then boundary.
- Use restrained fades, 20–40 px vertical reveals, progress-line wipes, and
  short staggered evidence cards.
- Each scene enters after its transition and remains readable before the next
  transition. No infinite motion, bouncing, 3D camera effects, or decorative
  particle backgrounds.

## Composition

- 1920×1080, 30 fps, approximately 150 seconds.
- Five scenes: problem/result, AI review, RAG/assistant, safety/cloud, limits/CTA.
- Use text, simple diagrams, metric cards, and code-like evidence labels rather
  than browser chrome screenshots.
- Maintain generous negative space and a maximum of two conceptual groups per
  frame.

## Voice

- Local Mandarin TTS voice `zf_xiaoxiao`, speed `0.9`.
- Calm, clear, technically trustworthy. No paid or external voice service.

## Anti-patterns

- No fabricated customer, production-accuracy, legal-compliance, or cost claims.
- No private schedule, payroll, secret, access token, or production database data.
- No model output presented as confirmed truth.
- No tiny code walls, dense tables, subtitle overlap, or text outside safe areas.
