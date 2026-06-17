/**
 * SpendWise AI — Modern Minimalist UI Controller
 * Zero-build, pure vanilla JavaScript for financial intelligence & FastMCP agent.
 */

// ─── Application State ───────────────────────────────────────────────────────

const state = {
  threadId: "session-" + Math.random().toString(36).substring(2, 9),
  activeProvider: localStorage.getItem("spendwise_active_provider") || "deepseek",
  activeModel: localStorage.getItem("spendwise_active_model") || "",
  availableModels: [],
  categories: [],
  summary: null,
  budgets: [],
  expenses: [],
  isStreaming: false,
};

// ─── API Key & Base URL Storage Helpers ─────────────────────────────────────

function getStoredApiKey(provider) {
  return localStorage.getItem(`spendwise_${provider}_key`) || "";
}

function setStoredApiKey(provider, key) {
  if (key && key.trim()) {
    localStorage.setItem(`spendwise_${provider}_key`, key.trim());
  } else {
    localStorage.removeItem(`spendwise_${provider}_key`);
  }
}

function getStoredBaseUrl(provider) {
  return localStorage.getItem(`spendwise_${provider}_base_url`) || "";
}

function setStoredBaseUrl(provider, url) {
  if (url && url.trim()) {
    localStorage.setItem(`spendwise_${provider}_base_url`, url.trim());
  } else {
    localStorage.removeItem(`spendwise_${provider}_base_url`);
  }
}

function clearAllStoredKeys() {
  const providers = ["deepseek", "openai", "gemini", "custom"];
  providers.forEach((p) => {
    localStorage.removeItem(`spendwise_${p}_key`);
    localStorage.removeItem(`spendwise_${p}_base_url`);
  });
  localStorage.removeItem("spendwise_active_model");
}

// ─── Color Palette & Taxonomy ───────────────────────────────────────────────

const CATEGORY_COLORS = {
  Food: "#10b981",
  Housing: "#3b82f6",
  Transportation: "#f59e0b",
  Utilities: "#06b6d4",
  Entertainment: "#a855f7",
  Shopping: "#ec4899",
  Health: "#14b8a6",
  Education: "#6366f1",
  Finance: "#84cc16",
  Gifts: "#f43f5e",
  Miscellaneous: "#64748b",
};

function getCategoryColor(category) {
  return CATEGORY_COLORS[category] || "#94a3b8";
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount || 0);
}

// ─── DOM Initializer ────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();

  // Restore active provider selector
  const providerSelect = document.getElementById("providerSelect");
  if (providerSelect && state.activeProvider) {
    providerSelect.value = state.activeProvider;
  }

  await Promise.all([
    loadHealth(),
    loadCategories(),
    refreshDashboard(),
    loadModelsForProvider(state.activeProvider),
  ]);
});

// ─── Event Binding ──────────────────────────────────────────────────────────

function setupEventListeners() {
  // Provider Selector
  const providerSelect = document.getElementById("providerSelect");
  if (providerSelect) {
    providerSelect.addEventListener("change", async (e) => {
      state.activeProvider = e.target.value;
      localStorage.setItem("spendwise_active_provider", state.activeProvider);
      logTelemetry("SYS", `LLM Provider switched to: ${state.activeProvider}`);
      await loadModelsForProvider(state.activeProvider);
    });
  }

  // Model Selector
  const modelSelect = document.getElementById("modelSelect");
  if (modelSelect) {
    modelSelect.addEventListener("change", (e) => {
      const selected = e.target.value;
      if (selected === "__open_settings__") {
        openSettingsModal();
        return;
      }
      state.activeModel = selected;
      localStorage.setItem("spendwise_active_model", state.activeModel);
      logTelemetry("SYS", `Model switched to: ${state.activeModel}`);
    });
  }

  // Seed Button
  const seedBtn = document.getElementById("seedBtn");
  if (seedBtn) seedBtn.addEventListener("click", handleSeedData);

  // Settings Modal
  const settingsModal = document.getElementById("settingsModal");
  const openSettingsBtn = document.getElementById("openSettingsModalBtn");
  const closeSettingsBtn = document.getElementById("closeSettingsModalBtn");
  const cancelSettingsBtn = document.getElementById("cancelSettingsModalBtn");
  const settingsBackdrop = document.getElementById("settingsModalBackdrop");
  const settingsForm = document.getElementById("settingsForm");
  const clearKeysBtn = document.getElementById("clearKeysBtn");

  const openSettingsModal = () => {
    populateSettingsForm();
    const statusBox = document.getElementById("settingsStatusBox");
    if (statusBox) statusBox.style.display = "none";
    settingsModal?.classList.add("open");
  };

  const closeSettingsModal = () => settingsModal?.classList.remove("open");

  openSettingsBtn?.addEventListener("click", openSettingsModal);
  closeSettingsBtn?.addEventListener("click", closeSettingsModal);
  cancelSettingsBtn?.addEventListener("click", closeSettingsModal);
  settingsBackdrop?.addEventListener("click", closeSettingsModal);
  settingsForm?.addEventListener("submit", handleSettingsSubmit);

  if (clearKeysBtn) {
    clearKeysBtn.addEventListener("click", () => {
      if (confirm("Clear all locally stored API keys and endpoints?")) {
        clearAllStoredKeys();
        populateSettingsForm();
        const statusBox = document.getElementById("settingsStatusBox");
        if (statusBox) {
          statusBox.textContent = "All API keys cleared from browser storage.";
          statusBox.className = "settings-status-box success";
          statusBox.style.display = "block";
        }
        loadModelsForProvider(state.activeProvider);
      }
    });
  }

  // Settings Tab Switching
  document.querySelectorAll(".settings-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".settings-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".settings-tab-panel").forEach((p) => p.classList.remove("active"));

      tab.classList.add("active");
      const targetPanel = document.getElementById(tab.dataset.target);
      if (targetPanel) targetPanel.classList.add("active");
    });
  });

  // Modals: Add Expense
  const expenseModal = document.getElementById("expenseModal");
  const openExpenseBtn = document.getElementById("openExpenseModalBtn");
  const closeExpenseBtn = document.getElementById("closeExpenseModalBtn");
  const cancelExpenseBtn = document.getElementById("cancelExpenseModalBtn");
  const expenseBackdrop = document.getElementById("expenseModalBackdrop");
  const expenseForm = document.getElementById("expenseForm");

  const openExpenseModal = () => {
    const dateInput = document.getElementById("expDate");
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];
    expenseModal?.classList.add("open");
    document.getElementById("expAmount")?.focus();
  };

  const closeExpenseModal = () => expenseModal?.classList.remove("open");

  openExpenseBtn?.addEventListener("click", openExpenseModal);
  closeExpenseBtn?.addEventListener("click", closeExpenseModal);
  cancelExpenseBtn?.addEventListener("click", closeExpenseModal);
  expenseBackdrop?.addEventListener("click", closeExpenseModal);
  expenseForm?.addEventListener("submit", handleExpenseSubmit);

  // Modals: Set Budget
  const budgetModal = document.getElementById("budgetModal");
  const openBudgetBtn = document.getElementById("openBudgetModalBtn");
  const closeBudgetBtn = document.getElementById("closeBudgetModalBtn");
  const cancelBudgetBtn = document.getElementById("cancelBudgetModalBtn");
  const budgetBackdrop = document.getElementById("budgetModalBackdrop");
  const budgetForm = document.getElementById("budgetForm");

  const openBudgetModal = () => {
    budgetModal?.classList.add("open");
    document.getElementById("budLimit")?.focus();
  };

  const closeBudgetModal = () => budgetModal?.classList.remove("open");

  openBudgetBtn?.addEventListener("click", openBudgetModal);
  closeBudgetBtn?.addEventListener("click", closeBudgetModal);
  cancelBudgetBtn?.addEventListener("click", closeBudgetModal);
  budgetBackdrop?.addEventListener("click", closeBudgetModal);
  budgetForm?.addEventListener("submit", handleBudgetSubmit);

  // Escape key closes modals
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeExpenseModal();
      closeBudgetModal();
      closeSettingsModal();
    }
  });

  // Table Search & Filter
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", debounce(() => loadExpenses(), 200));
  }

  const categoryFilter = document.getElementById("categoryFilter");
  if (categoryFilter) {
    categoryFilter.addEventListener("change", () => loadExpenses());
  }

  // Reset Chat Session
  const resetChatBtn = document.getElementById("resetChatBtn");
  if (resetChatBtn) {
    resetChatBtn.addEventListener("click", () => {
      state.threadId = "session-" + Math.random().toString(36).substring(2, 9);
      const viewport = document.getElementById("chatViewport");
      if (viewport) {
        viewport.innerHTML = `
          <div class="chat-message msg-assistant">
            <div class="msg-content">
              <p>Conversation session reset (<code>${state.threadId}</code>).</p>
              <p class="mt-2 text-dim">How can I assist you with your finances?</p>
            </div>
          </div>
        `;
      }
      resetPipelineStepper();
      logTelemetry("SYS", `Conversation session reset: ${state.threadId}`);
    });
  }

  // Clear Telemetry Logs
  const clearTelemetryBtn = document.getElementById("clearTelemetryBtn");
  if (clearTelemetryBtn) {
    clearTelemetryBtn.addEventListener("click", () => {
      const logs = document.getElementById("telemetryLogs");
      if (logs) {
        logs.innerHTML = `<div class="t-line t-system"><span class="t-ts">[SYS]</span> Telemetry logs cleared.</div>`;
      }
    });
  }

  // Suggestion Chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const chatInput = document.getElementById("chatInput");
      if (chatInput) {
        chatInput.value = chip.dataset.prompt;
        chatInput.focus();
      }
    });
  });

  // Chat Form Submit
  const chatForm = document.getElementById("chatForm");
  if (chatForm) chatForm.addEventListener("submit", handleChatSubmit);
}

// ─── Settings Modal & Key Management ────────────────────────────────────────

function populateSettingsForm() {
  const keyDeepSeek = document.getElementById("keyDeepSeek");
  const baseDeepSeek = document.getElementById("baseDeepSeek");
  const keyOpenAI = document.getElementById("keyOpenAI");
  const baseOpenAI = document.getElementById("baseOpenAI");
  const keyGemini = document.getElementById("keyGemini");
  const baseCustom = document.getElementById("baseCustom");
  const keyCustom = document.getElementById("keyCustom");

  if (keyDeepSeek) keyDeepSeek.value = getStoredApiKey("deepseek");
  if (baseDeepSeek) baseDeepSeek.value = getStoredBaseUrl("deepseek");
  if (keyOpenAI) keyOpenAI.value = getStoredApiKey("openai");
  if (baseOpenAI) baseOpenAI.value = getStoredBaseUrl("openai");
  if (keyGemini) keyGemini.value = getStoredApiKey("gemini");
  if (baseCustom) baseCustom.value = getStoredBaseUrl("custom");
  if (keyCustom) keyCustom.value = getStoredApiKey("custom");
}

async function handleSettingsSubmit(e) {
  e.preventDefault();
  const saveBtn = document.getElementById("saveSettingsBtn");
  const statusBox = document.getElementById("settingsStatusBox");

  const keyDeepSeek = document.getElementById("keyDeepSeek")?.value;
  const baseDeepSeek = document.getElementById("baseDeepSeek")?.value;
  const keyOpenAI = document.getElementById("keyOpenAI")?.value;
  const baseOpenAI = document.getElementById("baseOpenAI")?.value;
  const keyGemini = document.getElementById("keyGemini")?.value;
  const baseCustom = document.getElementById("baseCustom")?.value;
  const keyCustom = document.getElementById("keyCustom")?.value;

  setStoredApiKey("deepseek", keyDeepSeek);
  setStoredBaseUrl("deepseek", baseDeepSeek);
  setStoredApiKey("openai", keyOpenAI);
  setStoredBaseUrl("openai", baseOpenAI);
  setStoredApiKey("gemini", keyGemini);
  setStoredBaseUrl("custom", baseCustom);
  setStoredApiKey("custom", keyCustom);

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = "Verifying & Fetching Models...";
  }

  try {
    const models = await loadModelsForProvider(state.activeProvider, true);
    
    // If user saved an API key, clear the seeded demo sample data so they start fresh
    const hasKey = Boolean(keyDeepSeek || keyOpenAI || keyGemini || keyCustom);
    if (hasKey) {
      try {
        await fetch("/api/clear", { method: "POST" });
        logTelemetry("SYS", "API Key configured: Sample demo data cleared for clean tracking.");
        await refreshDashboard();
      } catch (e) {
        console.warn("Failed to clear database:", e);
      }
    }

    if (statusBox) {
      statusBox.textContent = `✓ Saved keys & loaded ${models.length} models for ${state.activeProvider}! (Sample data cleared)`;
      statusBox.className = "settings-status-box success";
      statusBox.style.display = "block";
    }

    setTimeout(() => {
      document.getElementById("settingsModal")?.classList.remove("open");
      if (statusBox) statusBox.style.display = "none";
    }, 1200);
  } catch (err) {
    if (statusBox) {
      statusBox.textContent = `⚠️ Saved keys, but model fetch failed: ${err.message}`;
      statusBox.className = "settings-status-box error";
      statusBox.style.display = "block";
    }
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save & Fetch Models";
    }
  }
}

// ─── Dynamic Model Fetching (/models Endpoint) ──────────────────────────────

async function loadModelsForProvider(provider, throwOnError = false) {
  const modelSelect = document.getElementById("modelSelect");
  if (!modelSelect) return [];

  modelSelect.disabled = true;
  modelSelect.innerHTML = `<option value="">Fetching /models...</option>`;

  const apiKey = getStoredApiKey(provider);
  const baseUrl = getStoredBaseUrl(provider);

  try {
    const res = await fetch("/api/models", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: provider,
        api_key: apiKey || null,
        base_url: baseUrl || null,
      }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    state.availableModels = data.models || [];

    modelSelect.innerHTML = "";

    if (state.availableModels.length === 0) {
      modelSelect.innerHTML = `<option value="">No models found</option>`;
      return [];
    }

    state.availableModels.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.name || m.id;
      if (m.description) opt.title = m.description;
      modelSelect.appendChild(opt);
    });

    // Auto-select preferred model
    const savedModel = localStorage.getItem("spendwise_active_model");
    const hasSaved = state.availableModels.some((m) => m.id === savedModel);

    if (hasSaved) {
      modelSelect.value = savedModel;
      state.activeModel = savedModel;
    } else if (data.default_model && state.availableModels.some((m) => m.id === data.default_model)) {
      modelSelect.value = data.default_model;
      state.activeModel = data.default_model;
    } else {
      state.activeModel = state.availableModels[0].id;
      modelSelect.value = state.activeModel;
    }

    localStorage.setItem("spendwise_active_model", state.activeModel);
    modelSelect.disabled = false;

    logTelemetry("MODELS", `Fetched ${state.availableModels.length} models for ${provider} from /models endpoint (Active: ${state.activeModel})`);
    return state.availableModels;
  } catch (err) {
    console.warn(`Failed to fetch models for ${provider}:`, err.message);
    modelSelect.innerHTML = `<option value="__open_settings__">⚙️ Key Required (Configure Settings)</option>`;
    modelSelect.disabled = false;
    logTelemetry("WARN", `Could not fetch models for ${provider}: ${err.message}`);
    if (throwOnError) throw err;
    return [];
  }
}

// ─── API Integrations ───────────────────────────────────────────────────────

async function refreshDashboard() {
  await Promise.all([loadSummary(), loadBudgets(), loadExpenses()]);
}

async function loadHealth() {
  try {
    const res = await fetch("/api/health");
    if (res.ok) {
      const health = await res.json();
      const statusPill = document.getElementById("mcpStatusPill");
      const statusLabel = document.getElementById("mcpStatusText");
      const toolsCountEl = document.getElementById("mcpToolsCount");

      if (statusLabel) {
        statusLabel.textContent = `MCP: ${health.mcp_server === "connected" ? "Connected" : health.mcp_server} (${health.tools_count} Tools)`;
      }
      if (toolsCountEl) {
        toolsCountEl.textContent = `${health.tools_count} Tools`;
      }
      if (statusPill && health.mcp_server === "connected") {
        statusPill.title = `FastMCP Connected over stdio • ${health.tools_count} registered tools`;
      }
    }
  } catch (err) {
    console.error("Health check error:", err);
  }
}

async function loadCategories() {
  try {
    const res = await fetch("/api/categories");
    if (res.ok) {
      const data = await res.json();
      state.categories = data.categories || [];
      populateCategoryDropdowns(state.categories);

      // Populate Left Column Resource Capsule Tags
      const tagsContainer = document.getElementById("resourceCategoryTags");
      if (tagsContainer && state.categories.length > 0) {
        tagsContainer.innerHTML = state.categories.slice(0, 10).map(c => `<span class="res-tag-item">${escapeHtml(c)}</span>`).join("");
      }
    }
  } catch (err) {
    console.error("Categories error:", err);
  }
}

function highlightTopologyNode(nodeId) {
  document.querySelectorAll(".arch-node").forEach((n) => n.classList.remove("active"));
  const target = document.getElementById(nodeId);
  if (target) {
    target.classList.add("active");
    setTimeout(() => target.classList.remove("active"), 1200);
  }
}

function highlightToolDeckCard(toolName, isExecuting) {
  const card = document.getElementById(`cardTool_${toolName}`);
  const badge = document.getElementById(`badge_${toolName}`);
  if (card) {
    if (isExecuting) {
      card.classList.add("executing");
      if (badge) {
        const currentCount = parseInt(badge.textContent || "0", 10) + 1;
        badge.textContent = currentCount;
      }
    } else {
      setTimeout(() => card.classList.remove("executing"), 1000);
    }
  }
}

function populateCategoryDropdowns(categories) {
  const filter = document.getElementById("categoryFilter");
  const expCategory = document.getElementById("expCategory");
  const budCategory = document.getElementById("budCategory");

  if (filter) {
    filter.innerHTML = `<option value="">All Categories</option>`;
    categories.forEach((cat) => {
      const opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = cat;
      filter.appendChild(opt);
    });
  }

  if (expCategory) {
    expCategory.innerHTML = "";
    categories.forEach((cat) => {
      const opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = cat;
      expCategory.appendChild(opt);
    });
  }

  if (budCategory) {
    budCategory.innerHTML = "";
    categories.forEach((cat) => {
      const opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = cat;
      budCategory.appendChild(opt);
    });
  }
}

// ─── Summary & Metrics ──────────────────────────────────────────────────────

async function loadSummary() {
  try {
    const res = await fetch("/api/summary");
    if (res.ok) {
      const summary = await res.json();
      state.summary = summary;
      renderKPIs(summary);
      renderDonut(summary.category_breakdown, summary.total_spent_this_month);
      renderTrend(summary.daily_trends);
    }
  } catch (err) {
    console.error("Summary error:", err);
  }
}

function renderKPIs(summary) {
  const spentEl = document.getElementById("kpiSpent");
  const deltaEl = document.getElementById("kpiDelta");
  const prevEl = document.getElementById("kpiPrevMonth");
  const utilEl = document.getElementById("kpiUtil");
  const utilBadge = document.getElementById("kpiUtilBadge");
  const limitEl = document.getElementById("kpiLimit");
  const topCatEl = document.getElementById("kpiTopCat");
  const topCountEl = document.getElementById("kpiTopCount");
  const topAmtEl = document.getElementById("kpiTopAmt");
  const countEl = document.getElementById("kpiCount");

  if (spentEl) spentEl.textContent = formatCurrency(summary.total_spent_this_month);

  if (deltaEl) {
    if (summary.mom_change_pct !== null && summary.mom_change_pct !== undefined) {
      const isUp = summary.mom_change_pct > 0;
      deltaEl.textContent = `${isUp ? "+" : ""}${summary.mom_change_pct}% MoM`;
      deltaEl.className = `badge ${isUp ? "badge-danger" : "badge-success"}`;
    } else {
      deltaEl.textContent = "Current Month";
      deltaEl.className = "badge badge-neutral";
    }
  }

  if (prevEl) {
    prevEl.textContent = `vs ${formatCurrency(summary.previous_month_spent)} last month`;
  }

  if (utilEl) utilEl.textContent = `${summary.budget_utilization_pct}%`;
  if (utilBadge) {
    const pct = summary.budget_utilization_pct;
    utilBadge.textContent = pct < 75 ? "Safe" : pct < 100 ? "Warning" : "Over Limit";
    utilBadge.className = `badge ${pct < 75 ? "badge-success" : pct < 100 ? "badge-warning" : "badge-danger"}`;
  }

  if (limitEl) limitEl.textContent = `of ${formatCurrency(summary.total_budget_this_month)} limit`;
  if (topCatEl) topCatEl.textContent = summary.top_category || "—";
  if (topAmtEl) topAmtEl.textContent = `${formatCurrency(summary.top_category_amount)} spent`;

  const topCategoryItem = summary.category_breakdown?.find((c) => c.category === summary.top_category);
  if (topCountEl) {
    topCountEl.textContent = topCategoryItem ? `${topCategoryItem.transaction_count} tx` : "0 tx";
  }

  if (countEl) countEl.textContent = summary.total_transactions_this_month;
}

// ─── Charts (Donut & Trend) ─────────────────────────────────────────────────

function renderDonut(breakdown, totalSpent) {
  const svg = document.getElementById("donutSvg");
  const legend = document.getElementById("donutLegend");
  const centerVal = document.getElementById("donutCenterTotal");

  if (centerVal) centerVal.textContent = formatCurrency(totalSpent);
  if (!svg || !legend) return;

  svg.innerHTML = "";
  legend.innerHTML = "";

  if (!breakdown || breakdown.length === 0 || totalSpent <= 0) {
    svg.innerHTML = `<circle cx="90" cy="90" r="64" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="18" />`;
    legend.innerHTML = `<div class="table-empty">No expenses recorded</div>`;
    return;
  }

  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  let accumulatedAngle = 0;

  breakdown.forEach((item) => {
    const slicePct = item.percentage / 100;
    const strokeDash = slicePct * circumference;
    const rotateAngle = accumulatedAngle * 360;
    accumulatedAngle += slicePct;

    const color = getCategoryColor(item.category);

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", "90");
    circle.setAttribute("cy", "90");
    circle.setAttribute("r", radius);
    circle.setAttribute("fill", "none");
    circle.setAttribute("stroke", color);
    circle.setAttribute("stroke-width", "16");
    circle.setAttribute("stroke-dasharray", `${strokeDash} ${circumference}`);
    circle.setAttribute("transform", `rotate(${rotateAngle} 90 90)`);
    circle.setAttribute("class", "donut-segment");

    svg.appendChild(circle);

    // Legend item
    const legendRow = document.createElement("div");
    legendRow.className = "legend-row";
    legendRow.innerHTML = `
      <div class="legend-left">
        <span class="legend-dot" style="background-color: ${color}"></span>
        <span class="legend-name">${item.category}</span>
      </div>
      <span class="legend-val font-mono">${formatCurrency(item.amount)}</span>
    `;
    legend.appendChild(legendRow);
  });
}

function renderTrend(dailyTrends) {
  const svg = document.getElementById("trendSvg");
  const peakLabel = document.getElementById("trendPeakLabel");
  if (!svg) return;

  svg.innerHTML = "";
  if (!dailyTrends || dailyTrends.length === 0) return;

  const maxAmount = Math.max(...dailyTrends.map((d) => d.amount), 50);
  if (peakLabel) peakLabel.textContent = `Peak: ${formatCurrency(maxAmount)}`;

  const width = svg.clientWidth || 300;
  const height = 90;
  const barWidth = Math.max(3, Math.min(12, width / dailyTrends.length - 2));

  dailyTrends.forEach((item, index) => {
    // Power scale (0.55) so everyday expenses ($15-$100) are legible alongside rent
    const normalized = Math.pow(item.amount / maxAmount, 0.55);
    const barHeight = Math.max(4, normalized * (height - 10));
    const x = index * (width / dailyTrends.length) + 1;
    const y = height - barHeight;

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", x);
    rect.setAttribute("y", y);
    rect.setAttribute("width", barWidth);
    rect.setAttribute("height", barHeight);
    rect.setAttribute("class", "trend-bar");

    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = `${item.date}: ${formatCurrency(item.amount)}`;
    rect.appendChild(title);

    svg.appendChild(rect);
  });
}

// ─── Budgets List ───────────────────────────────────────────────────────────

async function loadBudgets() {
  try {
    const res = await fetch("/api/budgets");
    if (res.ok) {
      const data = await res.json();
      state.budgets = data.budgets || [];
      renderBudgets(state.budgets);
    }
  } catch (err) {
    console.error("Budgets error:", err);
  }
}

function renderBudgets(budgets) {
  const list = document.getElementById("budgetsList");
  if (!list) return;

  list.innerHTML = "";
  if (!budgets || budgets.length === 0) {
    list.innerHTML = `<div class="table-empty">No category budgets defined. Click "Set Budget" to add one.</div>`;
    return;
  }

  budgets.forEach((b) => {
    const pct = b.utilization_percentage || 0;
    const isOver = b.is_over_budget;
    const fillClass = pct < 75 ? "fill-safe" : pct < 100 ? "fill-warn" : "fill-danger";

    const item = document.createElement("div");
    item.className = "budget-item";
    item.innerHTML = `
      <div class="budget-row-top">
        <span class="budget-cat">${b.category}</span>
        <span class="budget-pct font-mono ${isOver ? 'text-danger' : ''}">${pct}%</span>
      </div>
      <div class="budget-track">
        <div class="budget-fill ${fillClass}" style="width: ${Math.min(100, pct)}%"></div>
      </div>
      <div class="budget-row-sub font-mono">
        <span>${formatCurrency(b.spent_this_month)} spent</span>
        <span>${formatCurrency(b.limit_amount)} limit</span>
      </div>
    `;
    list.appendChild(item);
  });
}

// ─── Expenses Table ─────────────────────────────────────────────────────────

async function loadExpenses() {
  try {
    const search = document.getElementById("searchInput")?.value || "";
    const category = document.getElementById("categoryFilter")?.value || "";

    const params = new URLSearchParams({ limit: "50" });
    if (search) params.append("search", search);
    if (category) params.append("category", category);

    const res = await fetch(`/api/expenses?${params.toString()}`);
    if (res.ok) {
      const data = await res.json();
      state.expenses = data.expenses || [];
      renderExpensesTable(state.expenses);
    }
  } catch (err) {
    console.error("Expenses error:", err);
  }
}

function renderExpensesTable(expenses) {
  const tbody = document.getElementById("transactionsBody");
  if (!tbody) return;

  tbody.innerHTML = "";
  if (!expenses || expenses.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="table-empty">No matching transactions recorded.</td></tr>`;
    return;
  }

  expenses.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="font-mono text-dim">${item.date}</td>
      <td><span class="badge-cat">${item.category}</span></td>
      <td>
        <span class="tx-subcat">${item.subcategory || ""}</span>
        ${item.note ? `<span class="tx-note text-dim"> • ${item.note}</span>` : ""}
      </td>
      <td class="text-right font-mono font-medium">${formatCurrency(item.amount)}</td>
      <td class="text-center">
        <button class="btn-del" data-id="${item.id}" title="Delete record">&times;</button>
      </td>
    `;

    tr.querySelector(".btn-del")?.addEventListener("click", () => handleDeleteExpense(item.id));
    tbody.appendChild(tr);
  });
}

async function handleDeleteExpense(id) {
  if (!confirm(`Delete transaction #${id}?`)) return;
  try {
    const res = await fetch(`/api/expenses/${id}`, { method: "DELETE" });
    if (res.ok) {
      logTelemetry("REST", `DELETE /api/expenses/${id} succeeded`);
      await refreshDashboard();
    }
  } catch (err) {
    console.error("Delete error:", err);
  }
}

async function handleExpenseSubmit(e) {
  e.preventDefault();
  const amount = parseFloat(document.getElementById("expAmount")?.value);
  const category = document.getElementById("expCategory")?.value;
  const subcategory = document.getElementById("expSubcategory")?.value || null;
  const note = document.getElementById("expNote")?.value || null;
  const date = document.getElementById("expDate")?.value || null;

  if (!amount || !category) return;

  try {
    const res = await fetch("/api/expenses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount, category, subcategory, note, date }),
    });

    if (res.ok) {
      document.getElementById("expenseModal")?.classList.remove("open");
      document.getElementById("expenseForm")?.reset();
      logTelemetry("REST", `POST /api/expenses: $${amount} in ${category}`);
      await refreshDashboard();
    }
  } catch (err) {
    console.error("Create expense error:", err);
  }
}

async function handleBudgetSubmit(e) {
  e.preventDefault();
  const category = document.getElementById("budCategory")?.value;
  const limit_amount = parseFloat(document.getElementById("budLimit")?.value);

  if (!category || !limit_amount) return;

  try {
    const res = await fetch("/api/budgets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category, limit_amount }),
    });

    if (res.ok) {
      document.getElementById("budgetModal")?.classList.remove("open");
      document.getElementById("budgetForm")?.reset();
      logTelemetry("REST", `POST /api/budgets: ${category} set to $${limit_amount}`);
      await refreshDashboard();
    }
  } catch (err) {
    console.error("Set budget error:", err);
  }
}

async function handleSeedData() {
  const seedBtn = document.getElementById("seedBtn");
  if (seedBtn) {
    seedBtn.disabled = true;
    seedBtn.innerHTML = `<span>⏳</span><span>Seeding...</span>`;
  }

  try {
    const res = await fetch("/api/seed", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      logTelemetry("SEED", `Seeded ${data.seeded_expenses} expenses & ${data.seeded_budgets} budgets`);
      await refreshDashboard();
    }
  } catch (err) {
    console.error("Seed error:", err);
  } finally {
    if (seedBtn) {
      seedBtn.disabled = false;
      seedBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v8"/><path d="m4.93 10.93 1.41 1.41"/><path d="M2 18h2"/><path d="M20 18h2"/><path d="m19.07 10.93-1.41 1.41"/><path d="M22 22H2"/><path d="m16 6-4 4-4-4"/><path d="M16 18a4 4 0 0 0-8 0"/></svg>
        <span>Seed Demo</span>
      `;
    }
  }
}

// ─── Real-Time Agent SSE Streaming ──────────────────────────────────────────

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chatInput");
  if (!input || !input.value.trim() || state.isStreaming) return;

  const userMessage = input.value.trim();
  input.value = "";

  appendUserBubble(userMessage);
  resetPipelineStepper();

  state.isStreaming = true;
  const sendBtn = document.getElementById("sendBtn");
  if (sendBtn) sendBtn.disabled = true;

  logTelemetry("USER", userMessage);

  const assistantBubble = createAssistantBubble();
  const msgContent = assistantBubble.querySelector(".msg-content");
  let assistantFullText = "";
  let needsSync = false;
  const apiKey = getStoredApiKey(state.activeProvider);
  const baseUrl = getStoredBaseUrl(state.activeProvider);

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: userMessage,
        thread_id: state.threadId,
        provider: state.activeProvider,
        model: state.activeModel || null,
        api_key: apiKey || null,
        base_url: baseUrl || null,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      throw new Error(errData.detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.substring(6).trim();
        } else if (trimmed.startsWith("data:")) {
          try {
            const data = JSON.parse(trimmed.substring(5).trim());
            if (currentEvent === "token" && data.delta) {
              assistantFullText += data.delta;
              if (msgContent) {
                msgContent.innerHTML = renderMarkdownText(assistantFullText);
                scrollChat();
              }
            }
            handleStreamEvent(currentEvent, data, assistantBubble, msgContent, (flag) => {
              if (flag) needsSync = true;
            });
          } catch (e) {
            console.error("SSE parse error:", e);
          }
        }
      }
    }
  } catch (err) {
    if (msgContent) {
      msgContent.innerHTML += `<div style="color: var(--rose); margin-top: 0.5rem;">⚠️ ${err.message}</div>`;
    }
    logTelemetry("ERR", err.message);
  } finally {
    state.isStreaming = false;
    if (sendBtn) sendBtn.disabled = false;
    if (needsSync) {
      logTelemetry("SYNC", "Refreshing dashboard after tool mutations");
      await refreshDashboard();
    }
  }
}

function handleStreamEvent(eventType, data, bubble, msgContent, onMutation) {
  logTelemetry(eventType.toUpperCase(), JSON.stringify(data));

  switch (eventType) {
    case "lifecycle_start":
      setPipelineStep("stepPrompt");
      break;

    case "pipeline_step":
      if (data.step === "prompt_context") setPipelineStep("stepPrompt");
      else if (data.step === "llm_reasoning") setPipelineStep("stepReasoning");
      else if (data.step === "synthesis") setPipelineStep("stepSynthesis");
      break;

    case "tool_start":
      setPipelineStep("stepMcp");
      appendToolPill(bubble, data);
      // Animate left column architecture diagram & tool matrix
      highlightTopologyNode("nodeMcp");
      highlightToolDeckCard(data.tool, true);
      break;

    case "tool_end":
      updateToolPill(bubble, data);
      highlightTopologyNode("nodeDb");
      highlightToolDeckCard(data.tool, false);
      if (["add_expense", "update_expense", "delete_expense", "set_budget"].includes(data.tool)) {
        onMutation(true);
      }
      break;

    case "token":
      setPipelineStep("stepSynthesis");
      break;

    case "done":
      resetPipelineStepper();
      break;

    case "error":
      if (msgContent) {
        msgContent.innerHTML += `<div style="color: var(--rose); margin-top: 0.5rem;">⚠️ ${data.error}</div>`;
      }
      break;
  }
}

// ─── Chat & Pipeline DOM Helpers ────────────────────────────────────────────

function appendUserBubble(text) {
  const container = document.getElementById("chatViewport");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = "chat-message msg-user";
  bubble.innerHTML = `<div class="msg-content"><p>${escapeHtml(text)}</p></div>`;
  container.appendChild(bubble);
  scrollChat();
}

function createAssistantBubble() {
  const container = document.getElementById("chatViewport");
  const bubble = document.createElement("div");
  bubble.className = "chat-message msg-assistant";
  bubble.innerHTML = `<div class="msg-content"></div>`;
  container.appendChild(bubble);
  scrollChat();
  return bubble;
}

function appendToolPill(bubble, data) {
  const pill = document.createElement("div");
  pill.className = "tool-pill";
  pill.id = `tool-${data.run_id || data.tool}`;
  pill.innerHTML = `
    <div class="tool-pill-header" onclick="this.nextElementSibling.classList.toggle('hidden')">
      <span class="tool-pill-name">⚡ ${data.tool}()</span>
      <span class="tool-pill-dur font-mono">running...</span>
    </div>
    <div class="tool-pill-body">
      <div class="tool-code font-mono">${escapeHtml(JSON.stringify(data.input))}</div>
    </div>
  `;
  bubble.appendChild(pill);
  scrollChat();
}

function updateToolPill(bubble, data) {
  const pill = bubble.querySelector(`#tool-${data.run_id || data.tool}`);
  if (pill) {
    const dur = pill.querySelector(".tool-pill-dur");
    if (dur) dur.textContent = `${data.duration_ms || 0}ms`;

    const body = pill.querySelector(".tool-pill-body");
    if (body) {
      body.innerHTML += `<div class="tool-result font-mono">${escapeHtml(data.output)}</div>`;
    }
  }
}

function scrollChat() {
  const chat = document.getElementById("chatViewport");
  if (chat) chat.scrollTop = chat.scrollHeight;
}

function setPipelineStep(stepId) {
  document.querySelectorAll(".step-item").forEach((s) => s.classList.remove("active"));
  const step = document.getElementById(stepId);
  if (step) step.classList.add("active");
}

function resetPipelineStepper() {
  document.querySelectorAll(".step-item").forEach((s) => s.classList.remove("active"));
}

function logTelemetry(eventType, message) {
  const terminal = document.getElementById("telemetryLogs");
  if (!terminal) return;

  const line = document.createElement("div");
  line.className = "t-line";
  const time = new Date().toISOString().substring(11, 19);

  line.innerHTML = `
    <span class="t-ts">[${time}]</span>
    <span class="t-event">[${eventType}]</span>
    <span class="t-data">${escapeHtml(message)}</span>
  `;

  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

// ─── Utilities ──────────────────────────────────────────────────────────────

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function renderMarkdownText(text) {
  if (!text) return "";
  if (window.marked && typeof window.marked.parse === "function") {
    try {
      return window.marked.parse(text, { breaks: true, gfm: true });
    } catch (e) {
      console.warn("marked.parse error:", e);
    }
  }
  return renderSimpleMarkdown(text);
}

function renderSimpleMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
  // Code blocks
  html = html.replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>");
  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Bullet items
  html = html.replace(/(?:^|\n)[-*]\s+(.+)/g, "<br />&bull; $1");
  // Line breaks
  html = html.replace(/\n/g, "<br />");
  return html;
}
function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}
