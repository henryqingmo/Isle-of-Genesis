// feed.js — horizontal scrolling event ticker
const MAX_TICKER_ENTRIES = 100;

const EVENT_CLASS = {
  trade_completed:   "ev-trade",
  trade_failed:      "ev-trade",
  agent_starved:     "ev-starved",
  agent_migrated_in: "ev-migrated",
  resource_produced: "ev-produced",
};

const EVENT_ICON = {
  trade_completed:   "⚡",
  trade_failed:      "✗",
  agent_starved:     "💀",
  agent_migrated_in: "→",
  resource_produced: "·",
};

// Internal list of entry objects {text, cls} — kept separate from DOM
const tickerEntries = [];
// Number of "original" spans currently rendered in the first half of #ticker-inner
let _tickerRenderedCount = 0;

function appendEvents(events, tick) {
  let added = 0;
  for (const e of events) {
    if (e.event_type === "resource_produced") continue; // too noisy
    const icon = EVENT_ICON[e.event_type] || "?";
    const t = e.tick != null ? e.tick : tick;
    const text = `[${t}] ${icon} ${e.event_type} ${e.actors.join(",")}`;
    const cls = EVENT_CLASS[e.event_type] || "";
    tickerEntries.push({ text, cls });
    added++;
  }
  let pruned = false;
  while (tickerEntries.length > MAX_TICKER_ENTRIES) { tickerEntries.shift(); pruned = true; }
  if (added > 0) renderTicker(pruned);
}

function _makeSpan(e) {
  const span = document.createElement("span");
  span.className = "ticker-entry" + (e.cls ? " " + e.cls : "");
  span.textContent = e.text;
  return span;
}

function renderTicker(pruned = false) {
  const inner = document.getElementById("ticker-inner");
  if (!inner) return;

  const firstRender = inner.children.length === 0;

  if (firstRender || pruned) {
    // Full rebuild — restart animation from beginning
    const originals = tickerEntries.map(_makeSpan);
    const duplicates = originals.map(s => s.cloneNode(true));
    inner.innerHTML = "";
    originals.forEach(s => inner.appendChild(s));
    duplicates.forEach(s => inner.appendChild(s));
    _tickerRenderedCount = tickerEntries.length;

    requestAnimationFrame(() => {
      const halfWidth = inner.scrollWidth / 2;
      const duration = Math.max(5, halfWidth / 60);
      inner.style.animation = "none";
      void inner.offsetWidth; // force reflow so animation restarts cleanly
      inner.style.animation = `ticker-scroll ${duration}s linear infinite`;
    });
  } else {
    // Append only — splice new spans into both halves without restarting animation
    // DOM structure: [orig0..orig(n-1), dup0..dup(n-1)] where n = _tickerRenderedCount
    const newEntries = tickerEntries.slice(_tickerRenderedCount);
    if (newEntries.length === 0) return;

    const insertBefore = inner.children[_tickerRenderedCount]; // first dup span
    const newOriginals = newEntries.map(_makeSpan);
    const newDuplicates = newOriginals.map(s => s.cloneNode(true));

    newOriginals.forEach(s => inner.insertBefore(s, insertBefore));
    newDuplicates.forEach(s => inner.appendChild(s));
    _tickerRenderedCount = tickerEntries.length;

    // Update only the duration; animationDuration change does not reset scroll position
    requestAnimationFrame(() => {
      const halfWidth = inner.scrollWidth / 2;
      const duration = Math.max(5, halfWidth / 60);
      inner.style.animationDuration = `${duration}s`;
    });
  }
}

// Reset ticker on simulation reset
function resetTicker() {
  tickerEntries.length = 0;
  _tickerRenderedCount = 0;
  const inner = document.getElementById("ticker-inner");
  if (inner) { inner.innerHTML = ""; inner.style.animation = ""; }
}
