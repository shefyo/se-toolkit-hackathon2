const API_URL = "";

async function addExpenses() {
    const text = document.getElementById("expenseText").value.trim();
    const messageEl = document.getElementById("message");
    const addBtn = document.getElementById("addBtn");

    if (!text) {
        showMessage("Please enter some text describing your expenses.", "error");
        return;
    }

    addBtn.disabled = true;
    addBtn.textContent = "Processing...";
    messageEl.className = "message";

    try {
        const response = await fetch("/parse-expenses", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to parse expenses");
        }

        const data = await response.json();

        if (data.expenses.length === 0) {
            showMessage("No expenses found in the text.", "error");
        } else {
            showMessage(
                `Successfully added ${data.expenses.length} expense(s)!`,
                "success"
            );
            document.getElementById("expenseText").value = "";
            await loadExpenses();
        }
    } catch (error) {
        showMessage(error.message, "error");
    } finally {
        addBtn.disabled = false;
        addBtn.textContent = "Add Expenses";
    }
}

async function loadExpenses() {
    const expensesList = document.getElementById("expensesList");
    expensesList.innerHTML = '<p class="loading">Loading expenses...</p>';

    try {
        const response = await fetch("/expenses");
        if (!response.ok) throw new Error("Failed to load expenses");

        const data = await response.json();

        if (data.expenses.length === 0) {
            expensesList.innerHTML =
                '<p class="empty-state">No expenses yet. Add some above!</p>';
            return;
        }

        expensesList.innerHTML = data.expenses
            .map(
                (expense) => `
            <div class="expense-item">
                <div class="expense-info">
                    <div class="expense-item-name">${escapeHtml(expense.item)}</div>
                    <span class="expense-category">${escapeHtml(expense.category)}</span>
                    <div class="expense-date">${formatDate(expense.created_at)}</div>
                </div>
                <div class="expense-amount">$${expense.amount.toFixed(2)}</div>
            </div>
        `
            )
            .join("");
    } catch (error) {
        expensesList.innerHTML =
            '<p class="empty-state">Failed to load expenses.</p>';
    }
}

function showMessage(text, type) {
    const messageEl = document.getElementById("message");
    messageEl.textContent = text;
    messageEl.className = `message ${type}`;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleString();
}

// Load expenses on page load
document.addEventListener("DOMContentLoaded", loadExpenses);
