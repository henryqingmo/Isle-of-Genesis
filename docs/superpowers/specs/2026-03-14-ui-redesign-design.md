# Isle of Genesis — UI Redesign Specification

**Date:** 2026-03-14
**Status:** Approved

---

## Overview

Replace the current flat-color canvas and dark GitHub-themed UI chrome with a cozy farming game aesthetic that uses the provided `tiny_village/tiny_village_tilemap.png` and `tiny_village/player.png` sprite sheets. The redesign covers everything: canvas rendering, toolbar, side panel, and event display.

---

## Scope

Full UI overhaul — canvas sprites, layout restructure, and complete visual reskin of all chrome.

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
- Agent info bar moved between canvas and ticker (was below canvas already)
- Right panel now contains only metrics (Village Stats + Market Prices), giving it more vertical space per section

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

**Typography:** `'Courier New', monospace` throughout — consistent with existing codebase, fits the pixel-art aesthetic.

**Borders:** 2–3px solid borders with warm brown tones. Subtle `border-radius: 3–6px` on panels and buttons. Double-border on the outermost UI frame (`box-shadow` trick: `0 0 0 6px #1a1208, 0 0 0 8px #7a5c30`).

---

## Toolbar

Same controls as today, reskinned:
- Title: `🏡 Isle of Genesis` in `#f5c842`
- Buttons: Pause / Step / Reset / Replay — warm brown background, hover lightens border
- Speed slider + label
- Snapshot select dropdown
- Tick display (right-aligned): `📅 Day {N}`

---

## Canvas — Sprite Rendering

### Approach: Sprite sheet slicing via `drawImage()`

Both PNGs are loaded as `Image` objects. Sprites are sliced at runtime using:

```js
ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh)
```

No external build step. No extracted files. Coordinates are hardcoded constants.

### Tile rendering (two-pass per cell)

**Pass 1 — Grass base:** Every cell is filled with a solid grass-green color by tile type:

| Tile type | Base fill |
|-----------|-----------|
| (any / plain) | `#3a7020` |
| forest | `#2a5818` |
| mine | `#3a3028` |
| farm | `#5a7a20` |
| town | `#4a3820` |
| market | `#5a4810` |

**Pass 2 — Overlay sprite:** A centered sprite from `tiny_village_tilemap.png` is drawn on top of the base color. Sprite is scaled to fit within the cell (leaving a small margin so the base color shows as a border).

Tile-to-sprite mapping (pixel coordinates TBD during implementation by inspecting the sheet):

| Tile type | Sprite description |
|-----------|--------------------|
| farm | Crop / farm plot tile |
| forest | Single tree (leafy) |
| mine | Rock / boulder |
| town | Wooden house / building |
| market | Market stall / shop |

### Agent rendering

Each alive agent is drawn as a single frame from `tiny_village/player.png`:
- Frame: facing-down idle (top-left of the sheet)
- Position: bottom-right corner of the agent's cell, scaled to ~40% of cell size
- Selected agent: white glow ring drawn beneath the sprite

Agent sprite is the same frame for all professions in v1. Profession is communicated by a small colored dot (existing behavior) drawn at bottom-right of the sprite, or by the existing color scheme if the sprite is too small to read at scale.

Dead agents: not rendered (unchanged from current behavior).

---

## Right Panel — Metrics

Two stacked sections, separated by a divider:

### Village Stats
- Population (alive / total)
- Total wealth ($)
- Gini coefficient
- Food supply (units per agent)
- Two SVG sparklines: population over time, Gini over time

### Market Prices
- Food / Wood / Ore current prices with trend arrow (▲ ▼ ─)
- Three-line SVG sparkline (one per resource, color-coded green/tan/slate)

---

## Agent Info Bar

Single line between canvas and event ticker:
```
🧑 trader_07 · trader · wealth: $312.40 · food: 1.2 wood: 4.0 ore: 0.0 · hunger: 12% energy: 88%
```
Default text when nothing selected: `Click an agent to inspect`.

Styled as a parchment-tone bar (`#3d2b15` background, `#7a5c30` top border).

---

## Event Ticker

Horizontal continuously-scrolling bar at the bottom of the UI:

- Single line, left-to-right scroll animation (CSS `@keyframes` translate)
- Events separated by `·` or whitespace gap
- Color-coded by type (unchanged):
  - Trade: `#3fb950` (green)
  - Starvation: `#f85149` (red)
  - Migration: `#d2a8ff` (purple)
  - Production: `#a08060` (muted)
- Max events in DOM: 100 (same as current feed, pruned as ticker grows)
- Label: `📜 Events` pinned at left, non-scrolling

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/index.html` | Full reskin: new color palette, layout, ticker structure |
| `frontend/canvas.js` | Sprite sheet loading + two-pass tile rendering + player sprite agents |
| `frontend/feed.js` | Convert from vertical feed to horizontal ticker entries |
| `frontend/charts.js` | Reskin SVG sparklines to match warm palette |
| `frontend/app.js` | Minor: update tick display label from `Tick:` to `📅 Day` |

No backend changes required.

---

## Sprite Sheet Notes

Both images live at `tiny_village/` relative to the project root. The frontend will reference them as:

```js
const TILEMAP = new Image();
TILEMAP.src = '../tiny_village/tiny_village_tilemap.png';

const PLAYER = new Image();
PLAYER.src = '../tiny_village/player.png';
```

Exact sprite coordinates for each tile type and player frame will be determined by visual inspection of the sheets during implementation and stored as named constants at the top of `canvas.js`.

---

## Out of Scope

- Animation (walking, tool-use frames) — deferred
- Multiple profession-specific player sprites — deferred (all use same frame in v1)
- Sound effects
- Backend changes
