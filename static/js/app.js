// Non-AI Basic, Clean, High-Utility Frontend Application Logic
let authMode = "login";
let pollTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  initApp();
  document.getElementById("logoutBtn").addEventListener("click", handleLogout);
});

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token, email) {
  localStorage.setItem("token", token);
  localStorage.setItem("email", email);
}

function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("email");
  if (pollTimer) clearInterval(pollTimer);
}

async function initApp() {
  const token = getToken();
  const authSection = document.getElementById("authSection");
  const dashboardSection = document.getElementById("dashboardSection");
  const navUserSection = document.getElementById("navUserSection");
  const userEmailBadge = document.getElementById("userEmailBadge");

  if (!token) {
    authSection.classList.remove("hidden");
    dashboardSection.classList.add("hidden");
    navUserSection.classList.add("hidden");
    return;
  }

  // Verify token via /api/auth/me
  try {
    const res = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (res.ok) {
      const user = await res.json();
      userEmailBadge.textContent = user.email || localStorage.getItem("email") || "User";
      navUserSection.classList.remove("hidden");
      authSection.classList.add("hidden");
      dashboardSection.classList.remove("hidden");
      fetchTaskHistory();
      startPolling();
    } else {
      clearAuth();
      authSection.classList.remove("hidden");
      dashboardSection.classList.add("hidden");
      navUserSection.classList.add("hidden");
    }
  } catch (err) {
    console.error("Auth check failed:", err);
    clearAuth();
    authSection.classList.remove("hidden");
    dashboardSection.classList.add("hidden");
  }
}

function switchAuthTab(mode) {
  authMode = mode;
  const tabLogin = document.getElementById("tabLogin");
  const tabSignup = document.getElementById("tabSignup");
  const submitBtn = document.getElementById("authSubmitBtn");
  const alertBox = document.getElementById("authAlert");

  alertBox.classList.add("hidden");
  if (mode === "login") {
    tabLogin.classList.add("active");
    tabSignup.classList.remove("active");
    submitBtn.textContent = "Sign In";
  } else {
    tabSignup.classList.add("active");
    tabLogin.classList.remove("active");
    submitBtn.textContent = "Create Account";
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const alertBox = document.getElementById("authAlert");
  const submitBtn = document.getElementById("authSubmitBtn");

  alertBox.classList.add("hidden");
  submitBtn.disabled = true;

  try {
    if (authMode === "signup") {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Signup failed");
      }

      // Automatically log the user in after successful signup
      alertBox.className = "alert alert-success";
      alertBox.textContent = "Account created successfully! Logging you in...";
      alertBox.classList.remove("hidden");
    }

    // Login (OAuth2 form-encoded)
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const loginRes = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString()
    });

    const loginData = await loginRes.json();
    if (!loginRes.ok) {
      throw new Error(loginData.detail || "Invalid email or password");
    }

    setToken(loginData.access_token, loginData.email || email);
    document.getElementById("authPassword").value = "";
    initApp();
  } catch (err) {
    alertBox.className = "alert alert-danger";
    alertBox.textContent = err.message;
    alertBox.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
  }
}

function handleLogout() {
  clearAuth();
  initApp();
}

function fillPrompt(text) {
  const promptArea = document.getElementById("taskPrompt");
  promptArea.value = text;
  promptArea.focus();
}

function toggleExecutionMode() {
  const selectedMode = document.querySelector('input[name="executionMode"]:checked').value;
  const immediateHelper = document.getElementById("immediateHelper");
  const scheduledInputs = document.getElementById("scheduledInputs");
  const targetDayInput = document.getElementById("targetDay");

  if (selectedMode === "immediate") {
    immediateHelper.classList.remove("hidden");
    scheduledInputs.classList.add("hidden");
    targetDayInput.removeAttribute("required");
  } else {
    immediateHelper.classList.add("hidden");
    scheduledInputs.classList.remove("hidden");
    targetDayInput.setAttribute("required", "required");
    // Ensure date picker default is at least tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    targetDayInput.min = tomorrow.toISOString().split("T")[0];
    if (!targetDayInput.value) {
      targetDayInput.value = targetDayInput.min;
    }
  }
}

async function handleTaskSubmit(e) {
  e.preventDefault();
  const promptInput = document.getElementById("taskPrompt");
  const prompt = promptInput.value.trim();
  const submitBtn = document.getElementById("taskSubmitBtn");
  const alertBox = document.getElementById("taskAlert");

  if (!prompt) return;

  const selectedMode = document.querySelector('input[name="executionMode"]:checked').value;
  const payload = {
    prompt,
    mode: selectedMode
  };

  if (selectedMode === "scheduled") {
    const targetDay = document.getElementById("targetDay").value;
    const dailyRunVal = parseInt(document.getElementById("dailyRunMinutes").value, 10);
    const dailyRunMinutes = Math.min(Math.max(1, isNaN(dailyRunVal) ? 60 : dailyRunVal), 60);

    if (!targetDay) {
      alertBox.className = "alert alert-danger";
      alertBox.textContent = "Please select a Target End Day / Date for multi-day scheduled execution.";
      alertBox.classList.remove("hidden");
      return;
    }

    payload.target_day = targetDay;
    payload.daily_run_minutes = dailyRunMinutes;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Queuing...";
  alertBox.classList.add("hidden");

  try {
    const res = await fetch("/api/tasks/run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getToken()}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to trigger discovery task");
    }

    alertBox.className = "alert alert-success";
    alertBox.textContent = selectedMode === "scheduled"
      ? `Task queued for multi-day scheduled execution until ${payload.target_day} (${payload.daily_run_minutes}m daily run).`
      : "Immediate task queued! Running pipeline and sending email digest...";
    alertBox.classList.remove("hidden");
    promptInput.value = "";
    fetchTaskHistory();
    startPolling();
  } catch (err) {
    alertBox.className = "alert alert-danger";
    alertBox.textContent = err.message;
    alertBox.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "🚀 Submit Discovery Task";
  }
}

async function fetchTaskHistory() {
  const token = getToken();
  if (!token) return;

  const container = document.getElementById("taskListContainer");

  try {
    const res = await fetch("/api/tasks/history", {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
      if (res.status === 401) {
        clearAuth();
        initApp();
      }
      return;
    }

    const tasks = await res.json();
    renderTasks(tasks);
  } catch (err) {
    console.error("Failed to fetch history:", err);
  }
}

function renderTasks(tasks) {
  const container = document.getElementById("taskListContainer");
  if (!tasks || tasks.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">No discovery tasks yet. Submit your first prompt above!</p>`;
    return;
  }

  let html = "";
  let hasActiveTasks = false;

  tasks.forEach((t) => {
    const status = t.status || "UNKNOWN";
    let badgeClass = "badge-queued";
    if (status === "RUNNING") badgeClass = "badge-running";
    else if (status.startsWith("WAITING") || status.startsWith("PAUSED")) badgeClass = "badge-waiting";
    else if (status === "COMPLETED") badgeClass = "badge-completed";
    else if (status === "FAILED") badgeClass = "badge-failed";

    if (status === "QUEUED" || status.startsWith("RUNNING") || status.startsWith("WAITING") || status.startsWith("PAUSED")) {
      hasActiveTasks = true;
    }

    const mode = t.mode || "immediate";
    const modeBadge = mode === "scheduled"
      ? `<span class="badge" style="background:#f8fafc; color:#334155; border:1px solid #cbd5e1; font-size:0.7rem;">📅 Scheduled till ${t.target_day || "end"} (${t.daily_run_minutes || 60}m/day)</span>`
      : `<span class="badge" style="background:#f8fafc; color:#334155; border:1px solid #cbd5e1; font-size:0.7rem;">⚡ Immediate</span>`;

    const emailStatus = t.email_dispatched
      ? `<span style="color: var(--success); font-weight: 600;">✉️ Email Dispatched</span>`
      : `<span style="color: var(--text-muted);">✉️ Not sent</span>`;

    const dateStr = t.created_at ? new Date(t.created_at).toLocaleString() : "";

    window.__taskResults = window.__taskResults || {};
    window.__taskResults[t.task_id] = { results: t.results, prompt: t.prompt };

    let resultsHtml = "";
    if (Array.isArray(t.results) && t.results.length > 0) {
      const filterBarHtml = typeof createInteractiveFilterBar === "function"
        ? createInteractiveFilterBar(t.task_id, t.results)
        : "";

      resultsHtml = `
        <div class="event-results">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div class="event-results-title" style="margin-bottom: 0;">Found Events (${t.results.length})</div>
            <div style="display: flex; gap: 0.4rem;">
              <button class="btn btn-secondary btn-sm" onclick="handleExportCsv('${t.task_id}')" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">
                📊 Export CSV
              </button>
              <button class="btn btn-secondary btn-sm" onclick="handleExportMarkdown('${t.task_id}')" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">
                📋 Export Markdown
              </button>
            </div>
          </div>
          ${filterBarHtml}
          <div id="eventContainer-${t.task_id}">
          ${t.results
            .map((ev) => {
              const normalized = typeof normalizeEvent === "function"
                ? normalizeEvent(ev)
                : { priority: (ev.priority || "MEDIUM").toUpperCase(), isOnline: true, isOffline: false, isFree: true };

              const priority = normalized.priority;
              let pClass = "badge-priority-medium";
              if (priority === "HIGH") pClass = "badge-priority-high";
              else if (priority === "LOW") pClass = "badge-priority-low";

              const attendanceBadge = normalized.isOnline
                ? `<span class="event-tag tag-online">🌐 Online</span>`
                : `<span class="event-tag tag-offline">📍 Offline</span>`;

              const costBadge = normalized.isFree
                ? `<span class="event-tag tag-free">🎟️ Free</span>`
                : `<span class="event-tag tag-paid">💳 Paid</span>`;

              const titleSafe = encodeURIComponent(ev.title || "Tech Event");
              const dateSafe = encodeURIComponent(ev.date || "");
              const urlSafe = encodeURIComponent(ev.url || "");
              const summarySafe = encodeURIComponent(ev.summary || "");

              return `
              <div class="event-card" data-priority="${priority}" data-online="${normalized.isOnline}" data-offline="${normalized.isOffline}" data-free="${normalized.isFree}">
                <div class="event-card-header">
                  <a href="${ev.url}" target="_blank" rel="noopener noreferrer" class="event-card-title">
                    ${ev.title || "Untitled Event"} ↗
                  </a>
                  <span class="badge ${pClass}">${priority}</span>
                </div>
                <div class="event-card-meta">
                  <span><strong>Date:</strong> ${ev.date || "TBD"}</span> &bull;
                  <span><strong>Host:</strong> ${ev.organizer || ev.platform || "Web"}</span>
                </div>
                <div class="event-tags-container">
                  ${attendanceBadge}
                  ${costBadge}
                </div>
                ${ev.summary ? `<div class="event-card-desc">${ev.summary}</div>` : ""}
                <div style="margin-top: 0.5rem; display: flex; justify-content: flex-end;">
                  <button class="btn btn-secondary btn-sm" onclick="handleAddToCalendar('${titleSafe}', '${dateSafe}', '${urlSafe}', '${summarySafe}')" style="padding: 0.2rem 0.55rem; font-size: 0.75rem;">
                    📅 Add to Calendar
                  </button>
                </div>
              </div>
            `;
            })
            .join("")}
          </div>
        </div>
      `;
    } else if (t.results && t.results.error) {
      resultsHtml = `
        <div class="event-results">
          <div class="alert alert-danger" style="margin-bottom: 0;">
            <strong>Error:</strong> ${t.results.error}
          </div>
        </div>
      `;
    }

    html += `
      <div class="task-item">
        <div class="task-header">
          <div style="flex: 1;">
            <div class="task-prompt">${escapeHtml(t.prompt)}</div>
            <div class="task-meta">
              <span><strong>Task ID:</strong> ${t.task_id.substring(0, 8)}...</span>
              <span>${modeBadge}</span>
              <span><strong>Created:</strong> ${dateStr}</span>
              <span>${emailStatus}</span>
            </div>
          </div>
          <div>
            <span class="badge ${badgeClass}">${status}</span>
          </div>
        </div>
        ${resultsHtml}
      </div>
    `;
  });

  container.innerHTML = html;

  // If there are running or waiting tasks, ensure polling is active
  if (!hasActiveTasks && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(fetchTaskHistory, 4000);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function handleAddToCalendar(encodedTitle, encodedDate, encodedUrl, encodedSummary) {
  const title = decodeURIComponent(encodedTitle);
  const dateStr = decodeURIComponent(encodedDate);
  const url = decodeURIComponent(encodedUrl);
  const summary = decodeURIComponent(encodedSummary);
  addToGoogleCalendar(title, dateStr, url, summary);
}

function handleExportCsv(taskId) {
  const taskData = window.__taskResults && window.__taskResults[taskId];
  if (!taskData || !taskData.results) return;
  exportEventsAsCsv(taskData.results, taskId);
}

function handleExportMarkdown(taskId) {
  const taskData = window.__taskResults && window.__taskResults[taskId];
  if (!taskData || !taskData.results) return;
  exportEventsAsMarkdown(taskData.results, taskId, taskData.prompt);
}
