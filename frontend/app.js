const API_URL = window.location.origin;

// ==================== TAB NAVIGATION ====================

document.addEventListener("DOMContentLoaded", () => {
    const navItems = document.querySelectorAll(".nav-item");
    const pageTitles = {
        dashboard: "Dashboard",
        expenses: "Expenses",
        stats: "Analytics",
        advice: "AI Advice",
        chat: "Chat Assistant"
    };

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const tab = item.dataset.tab;

            // Update active nav
            navItems.forEach(n => n.classList.remove("active"));
            item.classList.add("active");

            // Update active tab
            document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
            document.getElementById(`tab-${tab}`).classList.add("active");

            // Update page title
            document.getElementById("pageTitle").textContent = pageTitles[tab] || "Dashboard";

            // Load tab data
            switch (tab) {
                case "dashboard": loadDashboard(); break;
                case "expenses": loadAllExpenses(); break;
                case "stats": loadStats(); break;
                case "advice": loadAdvice(); break;
                case "chat": loadChatHistory(); break;
            }
        });
    });

    // Load dashboard on init
    loadDashboard();
});

// ==================== DASHBOARD ====================

async function loadDashboard() {
    try {
        const [statsRes, expensesRes] = await Promise.all([
            fetch(`${API_URL}/stats`),
            fetch(`${API_URL}/expenses`)
        ]);

        const stats = await statsRes.json();
        const expenses = await expensesRes.json();

        // Update stat cards
        document.getElementById("dashTotal").textContent = `$${stats.total.toFixed(2)}`;
        document.getElementById("dashCount").textContent = stats.expense_count;

        const categories = Object.keys(stats.by_category || {});
        document.getElementById("dashCategories").textContent = categories.length;

        if (categories.length > 0) {
            const topCat = categories.reduce((a, b) =>
                stats.by_category[a] > stats.by_category[b] ? a : b
            );
            document.getElementById("dashTopCategory").textContent = topCat;
        } else {
            document.getElementById("dashTopCategory").textContent = "—";
        }

        // Recent expenses
        const container = document.getElementById("recentExpenses");
        const recent = expenses.slice(0, 5);

        if (recent.length === 0) {
            container.innerHTML = '<div class="empty-state">No expenses yet. Add your first expense above!</div>';
        } else {
            container.innerHTML = recent.map(exp => expenseItemHTML(exp)).join("");
        }
    } catch (error) {
        console.error("Dashboard load error:", error);
        document.getElementById("dashTotal").textContent = "Error";
    }
}

async function submitQuickExpense() {
    const text = document.getElementById("quickExpenseInput").value.trim();
    const btn = document.getElementById("quickSubmitBtn");
    const resultDiv = document.getElementById("quickResult");

    if (!text) {
        showResult(resultDiv, "Please enter expense text.", "error");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Processing...";

    try {
        const response = await fetch(`${API_URL}/parse-expenses`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });

        const data = await response.json();

        if (data.saved && data.saved.length > 0) {
            showResult(resultDiv, data.message, "success");
            document.getElementById("quickExpenseInput").value = "";
            loadDashboard();
        } else {
            showResult(resultDiv, data.message || "No expenses found.", "error");
        }
    } catch (error) {
        showResult(resultDiv, "Error connecting to server.", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Parse & Save";
    }
}

// ==================== EXPENSES TAB ====================

async function loadAllExpenses() {
    const container = document.getElementById("allExpenses");
    container.innerHTML = '<div class="loading">Loading expenses...</div>';

    try {
        const response = await fetch(`${API_URL}/expenses`);
        const expenses = await response.json();

        if (expenses.length === 0) {
            container.innerHTML = '<div class="empty-state">No expenses recorded yet.</div>';
        } else {
            container.innerHTML = expenses.map(exp => expenseItemHTML(exp)).join("");
        }
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Error loading expenses.</div>';
    }
}

async function submitExpense() {
    const text = document.getElementById("expenseInput").value.trim();
    const btn = document.getElementById("parseSubmitBtn");
    const resultDiv = document.getElementById("parseResult");

    if (!text) {
        showResult(resultDiv, "Please enter expense text.", "error");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Processing...";

    try {
        const response = await fetch(`${API_URL}/parse-expenses`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });

        const data = await response.json();

        if (data.saved && data.saved.length > 0) {
            showResult(resultDiv, data.message, "success");
            document.getElementById("expenseInput").value = "";
            loadAllExpenses();
        } else {
            showResult(resultDiv, data.message || "No expenses found.", "error");
        }
    } catch (error) {
        showResult(resultDiv, "Error connecting to server.", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Parse & Save";
    }
}

function expenseItemHTML(exp) {
    const date = exp.created_at ? new Date(exp.created_at).toLocaleString() : "";
    return `
        <div class="expense-item">
            <div class="expense-info">
                <div class="expense-name">${escapeHtml(exp.item)}</div>
                <div class="expense-category">${escapeHtml(exp.category)}</div>
                <div class="expense-date">${date}</div>
            </div>
            <div class="expense-amount">$${parseFloat(exp.amount).toFixed(2)}</div>
        </div>
    `;
}

// ==================== STATS / ANALYTICS TAB ====================

async function loadStats() {
    const overview = document.getElementById("statsOverview");
    const chart = document.getElementById("categoryChart");

    overview.innerHTML = '<div class="loading">Loading stats...</div>';
    chart.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const response = await fetch(`${API_URL}/stats`);
        const stats = await response.json();

        // Overview
        const byCategory = stats.by_category || {};
        const categories = Object.keys(byCategory);

        overview.innerHTML = `
            <div class="stat-box">
                <div class="label">Total Spending</div>
                <div class="value">$${stats.total.toFixed(2)}</div>
            </div>
            <div class="stat-box" style="background: linear-gradient(135deg, #f093fb, #f5576c);">
                <div class="label">Total Expenses</div>
                <div class="value">${stats.expense_count}</div>
            </div>
            <div class="stat-box" style="background: linear-gradient(135deg, #4facfe, #00f2fe);">
                <div class="label">Categories</div>
                <div class="value">${categories.length}</div>
            </div>
        `;

        // Category bars
        if (categories.length === 0) {
            chart.innerHTML = '<div class="empty-state">No category data available.</div>';
            return;
        }

        const maxVal = Math.max(...Object.values(byCategory));

        chart.innerHTML = categories.map(cat => {
            const amount = byCategory[cat];
            const pct = maxVal > 0 ? (amount / maxVal) * 100 : 0;
            return `
                <div class="category-bar">
                    <div class="category-label">${escapeHtml(cat)}</div>
                    <div class="category-track">
                        <div class="category-fill" style="width: ${pct}%;">$${amount.toFixed(2)}</div>
                    </div>
                </div>
            `;
        }).join("");

    } catch (error) {
        overview.innerHTML = '<div class="empty-state">Error loading stats.</div>';
        chart.innerHTML = "";
    }
}

// ==================== ADVICE TAB ====================

async function loadAdvice() {
    const container = document.getElementById("adviceContent");
    const historyContainer = document.getElementById("adviceHistory");

    container.innerHTML = '<div class="loading">Loading advice...</div>';
    historyContainer.innerHTML = '<div class="loading">Loading...</div>';

    await generateAdvice();
    await loadAdviceHistory();
}

async function generateAdvice() {
    const container = document.getElementById("adviceContent");
    container.innerHTML = '<div class="loading">Generating advice...</div>';

    try {
        const response = await fetch(`${API_URL}/advice`);
        const data = await response.json();

        const tips = data.tips || [];

        if (tips.length === 0) {
            container.innerHTML = '<div class="empty-state">No advice available. Add more expenses for personalized tips.</div>';
            return;
        }

        container.innerHTML = tips.map((t, i) => `
            <div class="advice-item">
                <span class="tip-number">${i + 1}</span>
                <span class="tip-text">${escapeHtml(t.tip)}</span>
            </div>
        `).join("");

    } catch (error) {
        container.innerHTML = '<div class="empty-state">Error generating advice.</div>';
    }
}

async function loadAdviceHistory() {
    const container = document.getElementById("adviceHistory");

    try {
        const response = await fetch(`${API_URL}/advice/history`);
        const history = await response.json();

        if (history.length === 0) {
            container.innerHTML = '<div class="empty-state">No advice history yet.</div>';
            return;
        }

        container.innerHTML = history.map(item => {
            const date = item.created_at ? new Date(item.created_at).toLocaleString() : "";
            return `
                <div class="advice-history-item">
                    ${escapeHtml(item.content.substring(0, 150))}${item.content.length > 150 ? "..." : ""}
                    <div class="advice-history-date">${date}</div>
                </div>
            `;
        }).join("");

    } catch (error) {
        container.innerHTML = '<div class="empty-state">Error loading advice history.</div>';
    }
}

// ==================== CHAT TAB ====================

async function loadChatHistory() {
    const container = document.getElementById("chatMessages");

    try {
        const response = await fetch(`${API_URL}/chat/history`);
        const history = await response.json();

        if (history.length > 0) {
            let html = `
                <div class="chat-message bot">
                    <div class="message-content">
                        👋 Hi! I'm your financial assistant. Ask me about your spending, budget tips, or how to save money.
                    </div>
                </div>
            `;

            history.forEach(msg => {
                html += `
                    <div class="chat-message user">
                        <div class="message-content">${escapeHtml(msg.user_message)}</div>
                    </div>
                    <div class="chat-message bot">
                        <div class="message-content">${escapeHtml(msg.bot_response)}</div>
                    </div>
                `;
            });

            container.innerHTML = html;
            scrollToBottom(container);
        }
    } catch (error) {
        console.error("Chat history load error:", error);
    }
}

async function sendChatMessage() {
    const input = document.getElementById("chatInput");
    const message = input.value.trim();
    const container = document.getElementById("chatMessages");

    if (!message) return;

    // Add user message
    container.innerHTML += `
        <div class="chat-message user">
            <div class="message-content">${escapeHtml(message)}</div>
        </div>
    `;

    input.value = "";
    scrollToBottom(container);

    // Add loading
    const loadingId = "loading-" + Date.now();
    container.innerHTML += `
        <div class="chat-message bot" id="${loadingId}">
            <div class="message-content">Thinking...</div>
        </div>
    `;
    scrollToBottom(container);

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        // Replace loading with response
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) {
            loadingEl.querySelector(".message-content").textContent = data.response || "Sorry, I couldn't process that.";
        }
        scrollToBottom(container);
    } catch (error) {
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) {
            loadingEl.querySelector(".message-content").textContent = "Error connecting to server.";
        }
    }
}

function handleChatKeypress(event) {
    if (event.key === "Enter") {
        sendChatMessage();
    }
}

// ==================== UTILITIES ====================

function showResult(element, message, type) {
    element.textContent = message;
    element.className = `result-message ${type}`;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom(container) {
    container.scrollTop = container.scrollHeight;
}

async function refreshAll() {
    const activeTab = document.querySelector(".nav-item.active");
    if (activeTab) {
        activeTab.click();
    }
}
