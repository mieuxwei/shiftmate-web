# Reproducing the portfolio video

The source composition is 1920×1080, 30 fps, and 150 seconds. The versioned
`animation-timing.json` records every scene, entrance, card reveal, fade, and
the full-length progress wipe. The composition uses only
synthetic facts already committed to the repository. Voice is generated locally
with Kokoro; no paid speech service or private data is used.

HyperFrames 0.8.25 does not currently list the requested `zf_xiaoxiao` voice,
so the checked render uses its Mandarin female fallback `zf_xiaobei` at the same
requested speed of `0.9`.

```bash
pnpm dlx hyperframes@0.8.25 tts narration-zh-TW.txt \
  --voice zf_xiaobei --lang zh --speed 0.9 --output assets/narration.wav
pnpm install --frozen-lockfile
pnpm exec hyperframes lint
pnpm exec hyperframes validate
pnpm exec hyperframes inspect
pnpm exec hyperframes check --at-transitions --snapshots
pnpm exec hyperframes render --fps 30 --quality high \
  --video-bitrate 900k --output shiftmate-demo.mp4 --strict
```

Run these commands from `portfolio/video`. The release gate also checks the
animation map, rendered subtitle safe areas, final duration, and a file size
below 25 MB.
