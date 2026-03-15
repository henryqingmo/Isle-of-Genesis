# Isle of Genesis — UI Redesign Specification

**Date:** 2026-03-14
**Status:** Approved (v2)

---

## Overview

Replace the current flat-color canvas and dark GitHub-themed UI chrome with a cozy farming game aesthetic. Three tile types use sprites sliced from `tiny_village/tiny_village_tilemap.png`; the remaining two tile types and all agents are drawn programmatically on the canvas. The redesign covers everything: canvas rendering, toolbar, side panel, and event display.

---

## Scope

Full UI overhaul — canvas sprites, layout restructure, and complete visual reskin of all chrome. No backend changes.

---

## Layout

```
┌─────────────────────────────────────────────┐
│  TOOLBAR (top bar)                          │
├──────────────────────────────┬──────────────┤
│                              │  Metrics     │
│  CANVAS                      │  panel       │
│  (fills remaining space)     │  (right,     │
│                              │  220px wide) │
├──────────────────────────────┴──────────────┤
│  Agent info bar                             │
├─────────────────────────────────────────────┤
│  Event ticker (horizontal scroll)           │
└─────────────────────────────────────────────┘
```

Changes from current layout:
- Event feed panel removed from right column; replaced by horizontal scrolling ticker at the bottom
- Agent info bar sits between the canvas row and the ticker (position unchanged from current)
- Right panel contains only metrics (Village Stats + Market Prices), giving each section more vertical space

---

## Visual Aesthetic

**Theme:** Cozy farming / village sim — warm, earthy, inviting. Reference: Stardew Valley UI.

**Color palette:**
| Role | Color |
|------|-------|
| Page background | `#1a1208` |
| Panel background | `#2d1f0e` |
| Toolbar / section headers | `#3d2b15` |
| Border / dividers | `#7a5c30` |
| Button background | `#5a3e20` |
| Button border | `#8b6040` |
| Primary text | `#f5deb3` |
| Secondary text / muted | `#c8a87a` / `#a08060` |
| Accent / titles | `#f5c842` |

**Typography:** `'Courier New', monospace` throughout.

**Borders:** 2–3px solid warm brown. `border-radius: 3–6px` on panels and buttons.

---

## Toolbar

Same controls as today, reskinned:
- Title: `🏡 Isle of Genesis` in `#f5c842`
- Buttons: Pause / Step / Reset / Replay — warm brown background, border lightens on hover
- Speed slider + Hz label
- Snapshot select dropdown
- Tick display (right-aligned): `📅 Day {N}` (replaces `Tick: N`)

---

## Canvas — Sprite Rendering

### Sprite source

Only `tiny_village/tiny_village_tilemap.png` is used. `player.png` is not used — agents are drawn programmatically (see below).

The tilemap is loaded once at startup:
```js
const TILEMAP = new Image();
TILEMAP.src = 'tiny_village/tiny_village_tilemap.png';
```

The path `tiny_village/tiny_village_tilemap.png` is relative to the page root (i.e., served from the project root by uvicorn's static file handler). If uvicorn does not already serve `tiny_village/` as a static directory, a one-line mount must be added to `server/main.py`:
```python
app.mount("/tiny_village", StaticFiles(directory="tiny_village"), name="tiny_village")
```

### Tile rendering (two-pass per cell)

**Pass 1 — Base fill:** Every cell is filled with a solid color:

| Tile type | Base fill |
|-----------|-----------|
| plain / grass | `#3a7020` |
| forest | `#2a5818` |
| mine | `#3a3028` |
| farm | `#5a7a20` |
| town | `#4a3820` |
| market | `#5a4810` |

**Pass 2 — Overlay:** Three tile types draw a sprite from the tilemap; two draw a programmatic shape.

**Tilemap sprites (16×16 source, `ctx.imageSmoothingEnabled = false`):**

| Tile type | sx | sy | sw | sh | Notes |
|-----------|----|----|----|----|-------|
| forest | 272 | 256 | 16 | 16 | Single-tile sapling/tree |
| mine | 160 | 32 | 16 | 16 | Gray boulder |
| farm | 176 | 352 | 16 | 16 | Tilled soil patch |

Each sprite is drawn centered in the cell, scaled to `cellSize - 4` pixels (2px margin on each side so the base color shows as a subtle border).

**Programmatic shapes:**

- **town** — draw a small house: filled rect (walls, `#c8a050`) + triangle roof (`#8b3a1a`) using canvas path
- **market** — draw an awning shape: filled rect (stall top, `#e8c040`) + narrower rect (counter, `#c8a050`)

Both shapes are drawn at fixed proportions relative to `cellSize`.

### Agent rendering

Agents are drawn programmatically — no sprite sheet used.

Each alive agent is drawn as:
1. A filled circle (radius `cellSize * 0.22`) using the existing profession color:
   - farmer: `#4caf50`, lumberjack: `#795548`, miner: `#78909c`, trader: `#ffd600`
2. A small pixel-art hat or icon drawn on top to distinguish professions visually at larger zoom:
   - farmer: green stalk `|` above circle
   - lumberjack: brown `×` (axe mark)
   - miner: gray `─` (pick)
   - trader: yellow `$`
   All drawn with `ctx.fillText` at `Math.max(8, cellSize * 0.3)` font size, centered on the circle.
3. Selected agent: white stroke ring around the circle (`lineWidth = 1.5`, `strokeStyle = '#fff'`). Selection state is read from the existing `selectedAgentId` variable already present in `canvas.js`.

Dead agents: not rendered (unchanged).

---

## Right Panel — Metrics

Two stacked sections divided by a `#7a5c30` border:

### Village Stats
- Population (alive count / total)
- Total wealth ($)
- Gini coefficient
- Food supply (units per alive agent)
- Two SVG sparklines stacked: population over time (green `#4caf50`), Gini over time (amber `#f5c842`)

### Market Prices
- Food / Wood / Ore current price with trend arrow: `▲` if last tick higher, `▼` if lower, `─` if equal
- Three-line SVG sparkline: food `#90c86a`, wood `#c8a87a`, ore `#78909c`

Sparklines use the existing `charts.js` SVG generation; only stroke colors and background change.

Zero-value inventory fields (e.g. `ore: 0.0`) are still shown — omitting them would cause the bar width to shift on every tick.

---

## Agent Info Bar

Single line between canvas row and event ticker. Content set by `showAgentInfo()` in `canvas.js` (existing function, unchanged logic):

```
🧑 trader_07 · trader · wealth: $312.40 · food: 1.2 wood: 4.0 ore: 0.0 · hunger: 12% energy: 88%
```

Default when nothing selected: `🧑 Click an agent to inspect`.

Style: `background: #3d2b15`, `border-top: 3px solid #7a5c30`, `font-size: 0.68rem`, `color: #c8a87a`. Agent id and numeric values in `#f5deb3`.

---

## Event Ticker

Replaces the `#feed-panel` vertical list. Implementation:

**DOM structure:**
```html
<div id="ticker-bar">
  <span id="ticker-label">📜 Events</span>
  <div id="ticker-track">
    <div id="ticker-inner"><!-- span.ticker-entry elements appended here --></div>
  </div>
</div>
```

**Scroll:** `#ticker-inner` uses `animation: ticker-scroll Xs linear infinite`. The animation duration `X` is recalculated whenever entries are added: `X = ticker-inner.scrollWidth / 60` (pixels per second = 60). This keeps scroll speed constant regardless of content length.

**Loop:** `#ticker-inner` content is duplicated once (CSS clone approach — identical second copy appended) so the scroll appears seamless when it wraps.

**New events:** `feed.js` appends a `<span class="ticker-entry ev-{type}">` to `#ticker-inner`, then rebuilds the duplicate copy and recalculates animation duration. Max 100 entries; oldest pruned when limit is reached (prune from both original and duplicate).

**Color classes** (unchanged from current feed):
- `.ev-trade`: `#3fb950`
- `.ev-starved`: `#f85149`
- `.ev-migrated`: `#d2a8ff`
- `.ev-produced`: `#8b949e`

**Label:** `📜 Events` in `#f5c842`, pinned left, not part of the scrolling element.

---

## Files Changed

| File | Change | Depth |
|------|--------|-------|
| `frontend/index.html` | Full reskin: new palette, layout restructure, ticker DOM | Structural |
| `frontend/canvas.js` | Tilemap loading + two-pass tile render + programmatic agents | Core rewrite of render loop |
| `frontend/feed.js` | Replace vertical list logic with horizontal ticker append + scroll recalc | Moderate |
| `frontend/charts.js` | Color-only change: update stroke/background constants to warm palette | Cosmetic |
| `frontend/app.js` | Change tick display from `Tick: N` to `📅 Day N` | 1-line |
| `server/main.py` | Mount `tiny_village/` as static directory (if not already served) | 1-line |

---

## Out of Scope

- Animation (walking, tool-use frames) — deferred
- Profession-specific distinct sprite art — deferred (programmatic icons used in v1)
- Sound effects
- Any backend simulation logic changes
