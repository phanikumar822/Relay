function normalizeEvent(event) {
  const priority = (event.priority || "MEDIUM").toUpperCase();
  const textContent = `${event.title || ""} ${event.summary || ""} ${event.platform || ""} ${event.location || ""}`.toLowerCase();

  let isOnline = event.is_online;
  if (isOnline === undefined || isOnline === null) {
    isOnline = /online|virtual|webinar|remote|zoom|stream|discord|meet\.google/i.test(textContent);
  }

  let isFree = event.is_free;
  if (isFree === undefined || isFree === null) {
    const isPaid = /ticket price|entry fee|registration fee|\$\d+|inr \d+|rs\.?\s*\d+/i.test(textContent);
    isFree = !isPaid;
  }

  return {
    ...event,
    priority: ["HIGH", "MEDIUM", "LOW"].includes(priority) ? priority : "MEDIUM",
    isOnline: Boolean(isOnline),
    isOffline: !Boolean(isOnline),
    isFree: Boolean(isFree)
  };
}

function calculatePriorityStats(eventsList) {
  const priorities = ["HIGH", "MEDIUM", "LOW"];
  const stats = {};

  priorities.forEach((priorityKey) => {
    stats[priorityKey] = {
      total: 0,
      online: 0,
      offline: 0,
      free: 0
    };
  });

  eventsList.forEach((rawEvent) => {
    const event = normalizeEvent(rawEvent);
    const targetStats = stats[event.priority];
    if (targetStats) {
      targetStats.total += 1;
      if (event.isOnline) targetStats.online += 1;
      if (event.isOffline) targetStats.offline += 1;
      if (event.isFree) targetStats.free += 1;
    }
  });

  return stats;
}

function createFilterSectionHtml(taskId, priorityKey, priorityLabel, icon, stats) {
  const data = stats[priorityKey];

  return `
    <div class="priority-filter-group">
      <div class="priority-group-title">
        <span>${icon} <strong>${priorityLabel}</strong> (${data.total})</span>
      </div>
      <div class="priority-subchips">
        <button type="button" class="filter-pill active" data-task="${taskId}" data-priority="${priorityKey}" data-type="all" onclick="setEventFilter('${taskId}', '${priorityKey}', 'all', this)">
          All (${data.total})
        </button>
        <button type="button" class="filter-pill" data-task="${taskId}" data-priority="${priorityKey}" data-type="online" onclick="setEventFilter('${taskId}', '${priorityKey}', 'online', this)">
          🌐 Online (${data.online})
        </button>
        <button type="button" class="filter-pill" data-task="${taskId}" data-priority="${priorityKey}" data-type="offline" onclick="setEventFilter('${taskId}', '${priorityKey}', 'offline', this)">
          📍 Offline (${data.offline})
        </button>
        <button type="button" class="filter-pill" data-task="${taskId}" data-priority="${priorityKey}" data-type="free" onclick="setEventFilter('${taskId}', '${priorityKey}', 'free', this)">
          🎟️ Free (${data.free})
        </button>
      </div>
    </div>
  `;
}

function createInteractiveFilterBar(taskId, eventsList) {
  const stats = calculatePriorityStats(eventsList);
  const totalEvents = eventsList.length;

  const highSection = createFilterSectionHtml(taskId, "HIGH", "High Priority", "🔥", stats);
  const mediumSection = createFilterSectionHtml(taskId, "MEDIUM", "Medium Priority", "⚡", stats);
  const lowSection = createFilterSectionHtml(taskId, "LOW", "Low Priority", "📌", stats);

  return `
    <div class="interactive-filter-bar" id="filterBar-${taskId}">
      <div class="filter-bar-header">
        <span class="filter-bar-heading">Filter Events by Priority & Type:</span>
        <button type="button" class="btn btn-secondary btn-sm" onclick="resetEventFilters('${taskId}')" style="padding: 0.2rem 0.6rem; font-size: 0.75rem;">
          Show All (${totalEvents})
        </button>
      </div>
      <div class="priority-filter-grid">
        ${highSection}
        ${mediumSection}
        ${lowSection}
      </div>
    </div>
  `;
}

function setEventFilter(taskId, targetPriority, filterType, buttonElement) {
  const filterBar = document.getElementById(`filterBar-${taskId}`);
  if (filterBar) {
    const allPills = filterBar.querySelectorAll(".filter-pill");
    allPills.forEach((pill) => pill.classList.remove("active"));
  }

  if (buttonElement) {
    buttonElement.classList.add("active");
  }

  const container = document.getElementById(`eventContainer-${taskId}`);
  if (!container) return;

  const eventCards = container.querySelectorAll(".event-card");
  eventCards.forEach((card) => {
    const cardPriority = card.getAttribute("data-priority");
    const isOnline = card.getAttribute("data-online") === "true";
    const isOffline = card.getAttribute("data-offline") === "true";
    const isFree = card.getAttribute("data-free") === "true";

    const matchesPriority = cardPriority === targetPriority;

    let matchesType = true;
    if (filterType === "online") matchesType = isOnline;
    else if (filterType === "offline") matchesType = isOffline;
    else if (filterType === "free") matchesType = isFree;

    if (matchesPriority && matchesType) {
      card.style.display = "block";
    } else {
      card.style.display = "none";
    }
  });
}

function resetEventFilters(taskId) {
  const filterBar = document.getElementById(`filterBar-${taskId}`);
  if (filterBar) {
    const allPills = filterBar.querySelectorAll(".filter-pill");
    allPills.forEach((pill) => pill.classList.remove("active"));
  }

  const container = document.getElementById(`eventContainer-${taskId}`);
  if (!container) return;

  const eventCards = container.querySelectorAll(".event-card");
  eventCards.forEach((card) => {
    card.style.display = "block";
  });
}
