# third-umpire — GitHub branding spec (private; for review)

Brand lock: cream #F4F1E8, ink #0F0E0B, quant-blue #1B3DFF, terminal-green #00B870.
Fonts: Fraunces (display), Geist (body), JetBrains Mono (labels/code). No gradients, no glow,
no shadows. SVG font stacks must carry system fallbacks. House style: no em dashes, no
exclamation points, dry voice. Personal capacity, zero Amazon internals, no O-1/visa references.

## Deliverable 1 — Social preview / OG card (NEW), publish/assets/og-card.svg, 1280x640

- Ink #0F0E0B background, flat. Six horizontal rules at y=80,160,240,320,400,480, quant-blue
  14% opacity, 0.5px (ties to banner).
- Left column, safe area x=80..900:
  - Eyebrow y=140: `VERIFICATION SKILL · AGENTIC AI` — JetBrains Mono 12px, quant-blue, ALL CAPS, tracking 0.08em.
  - Hero y=220: `third-umpire` — Fraunces 72px, cream, weight 500, tracking -0.01em. Then a
    terminal cursor `▌` in terminal-green (JetBrains Mono ~68px), x offset recomputed after render.
  - Tagline y=268 / y=304 (two lines): `The independent review for an agentic loop's` /
    `high-stakes calls.` — Geist 24px, cream 88%.
  - Verdict row y=380: three mono labels, 32px gaps, each preceded by a filled circle r=5 in
    its color: `ALLOW` (green) / `REQUIRE_INDEPENDENT_CHECK` (blue) / `ESCALATE` (cream 55%).
    JetBrains Mono 13px, weight 500, ALL CAPS, tracking 0.07em.
  - Footer rule y=560: 1px line quant-blue 60%, x=80..1200.
  - Attribution stamp y=580, right-aligned to x=1200: `SARTHAK GUPTA` (green) /
    `DATA SCIENTIST II, FINANCE MODELS` (cream 72%) / `PERSONAL CAPACITY` (cream 45%). JetBrains Mono 11px.
- Right column x=900..1200: the existing icon.svg scaled to 200x200, centered ~x=1050 y=260.
  No other text on the right.
- Never on the card: any URL, LinkedIn, "Amazon", or internal metrics.

## Deliverable 2 — Root README.md hero + structure

Update research/agentic-loops/skill/README.md to match the polished publish/README.md opening:
- Banner via HTML `<img src="publish/assets/banner.svg" width="100%">` (not Markdown image).
- Tagline (Option A, recommended), italic, standalone line:
  *When an agentic loop grades its own homework on a call that costs real money, one rule applies.*
- Badge row (real numbers only):
  - CI (GitHub default, self-updating)
  - License MIT — color 1B3DFF
  - Python 3.8+ — color 1B3DFF
  - Tests `11 + 2816-row conformance` — color 00B870
  - Dependencies `none` — color 00B870
  - No downloads/stars badges (private repo). No "built with Claude Code" in root README.
- Section order: Why this exists / What it does / How to use it / Decision flow (LINK to
  study/flow.svg, do not inline the Matplotlib SVG) / Case study (one-sentence headline + link
  to study/STUDY.md, do NOT embed savings_bars.png in root) / Works with / Layout /
  Status and honest scope / License + attribution.

## Deliverable 3 (optional) — publish/assets/flow-brand.svg

If an inline decision diagram is wanted, build a NEW brand-aligned SVG (brand fonts, ink
background, hard-ruled boxes) mirroring the logic of the Matplotlib study/flow.svg. Do NOT
modify the Matplotlib original.

## Icon verdict
icon.svg is good as-is. The only judgment call: ESCALATE endpoint (cream 55%) at 128px may
read faint; if so raise to 70% in the 128px export ONLY, never change color or structure.

## Verify before done
1. OG hero text width: `third-umpire` at 72px must not cross x=860 (icon column); else drop to 64px; recompute cursor x.
2. OG verdict row: `REQUIRE_INDEPENDENT_CHECK` is the longest; whole row must stay within x=820; if not, tracking 0.05em or 11px. Do not wrap.
3. OG tagline line 1 (45 chars) must fit 820px; if not, resplit, do not shrink.
4. Icon 128px ESCALATE endpoint legibility (see above).
5. Banner renders in GitHub view (no script/filters; existing banner is clean).
6. Contrast: cream/ink ~16.75:1 (AAA); blue/ink ~5.3:1 and green/ink ~6.0:1 (AA, labels only). No body copy in blue/green.
