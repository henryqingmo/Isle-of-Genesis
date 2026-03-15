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

function appendEvents(events, tick) {
  for (const e of events) {
    if (e.event_type === "resource_produced") continue; // too noisy
    const icon = EVENT_ICON[e.event_type] || "?";
    const t = e.tick != null ? e.tick : tick;
    const text = `[${t}] ${icon} ${e.event_type} ${e.actors.join(",")}`;
    const cls = EVENT_CLASS[e.event_type] || "";
    tickerEntries.push({ text, cls });
  }
  // prune oldest
  while (tickerEntries.length > MAX_TICKER_ENTRIES) tickerEntries.shift();
  renderTicker();
}

function renderTicker() {
  const inner = document.getElementById("ticker-inner");
  if (!inner) return;

  // Build original spans
  const originals = tickerEntries.map(e => {
    const span = document.createElement("span");
    span.className = "ticker-entry" + (e.cls ? " " + e.cls : "");
    span.textContent = e.text;
    return span;
  });

  // Build duplicate spans for seamless loop
  const duplicates = originals.map(s => s.cloneNode(true));

  inner.innerHTML = "";
  originals.forEach(s => inner.appendChild(s));
  duplicates.forEach(s => inner.appendChild(s));

  // Recalculate scroll speed (constant px/s = 60)
  // Use half the scrollWidth because content is duplicated
  requestAnimationFrame(() => {
    const halfWidth = inner.scrollWidth / 2;
    const duration = Math.max(5, halfWidth / 60);
    inner.style.animation = "none";
    // Force reflow so animation restarts cleanly
    void inner.offsetWidth;
    inner.style.animation = `ticker-scroll ${duration}s linear infinite`;
  });
}

// Reset ticker on simulation reset
function resetTicker() {
  tickerEntries.length = 0;
  const inner = document.getElementById("ticker-inner");
  if (inner) inner.innerHTML = "";
}
