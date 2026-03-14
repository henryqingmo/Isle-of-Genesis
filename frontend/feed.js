// feed.js — scrolling event feed
const MAX_FEED_ENTRIES = 100;
const EVENT_CLASS = {
  trade_completed:   "feed-trade",
  trade_failed:      "feed-trade",
  agent_starved:     "feed-starved",
  agent_migrated_in: "feed-migrated",
  resource_produced: "feed-produced",
};
const EVENT_ICON = {
  trade_completed:   "⚡",
  trade_failed:      "✗",
  agent_starved:     "💀",
  agent_migrated_in: "→",
  resource_produced: "·",
};

function appendEvents(events, tick) {
  const list = document.getElementById("feed-list");
  for (const e of events) {
    if (e.event_type === "resource_produced") continue; // too noisy
    const div = document.createElement("div");
    div.className = "feed-entry " + (EVENT_CLASS[e.event_type] || "");
    const icon = EVENT_ICON[e.event_type] || "?";
    const eventTick = e.tick != null ? e.tick : tick;
    div.textContent = `[${eventTick}] ${icon} ${e.event_type} ${e.actors.join(",")}`;
    list.prepend(div);
  }
  // cap DOM entries
  while (list.children.length > MAX_FEED_ENTRIES) {
    list.removeChild(list.lastChild);
  }
}
