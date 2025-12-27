let expenses = [];
let income = [];

// Chart instances
let categoryChart, paymentChart, trendChart;

// Fetch data
async function loadData() {
    try {
        const [expensesRes, incomeRes] = await Promise.all([
            fetch('/api/expenses'),
            fetch('/api/income')
        ]);
        
        expenses = await expensesRes.json();
        income = await incomeRes.json();
        
        updateSummaryCards();
        createCategoryChart();
        createPaymentChart();
        createTrendChart();
        displayTopExpenses();
        displayRecentActivity();
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// Format currency
function formatCurrency(amount) {
    return '₹' + Number(amount).toLocaleString('en-IN', { 
        minimumFractionDigits: 0, 
        maximumFractionDigits: 0 
    });
}

// Update summary cards
function updateSummaryCards() {
    const totalIncome = income.reduce((sum, item) => sum + parseFloat(item.amount || 0), 0);
    const totalExpenses = expenses.reduce((sum, item) => sum + parseFloat(item.amount || 0), 0);
    const netBalance = totalIncome - totalExpenses;
    const savingsRate = totalIncome > 0 ? ((netBalance / totalIncome) * 100).toFixed(1) : 0;
    
    document.getElementById('totalIncome').textContent = formatCurrency(totalIncome);
    document.getElementById('totalExpenses').textContent = formatCurrency(totalExpenses);
    document.getElementById('netBalance').textContent = formatCurrency(netBalance);
    document.getElementById('savingsRate').textContent = savingsRate + '%';
    
    document.getElementById('incomeCount').textContent = income.length + ' entries';
    document.getElementById('expenseCount').textContent = expenses.length + ' entries';
    
    const balanceStatus = netBalance > 0 ? '🎉 Surplus' : netBalance < 0 ? '⚠️ Deficit' : '— Balanced';
    document.getElementById('balanceStatus').textContent = balanceStatus;
}

// Category Chart (Doughnut)
function createCategoryChart() {
    const categoryData = {};
    
    expenses.forEach(expense => {
        const category = expense.category || 'Other';
        categoryData[category] = (categoryData[category] || 0) + parseFloat(expense.amount || 0);
    });
    
    const labels = Object.keys(categoryData);
    const data = Object.values(categoryData);
    
    const colors = [
        '#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6',
        '#ec4899', '#10b981', '#6366f1', '#14b8a6', '#f97316'
    ];
    
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    if (categoryChart) categoryChart.destroy();
    
    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: '#0f172a',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#e5e7eb',
                        padding: 15,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = formatCurrency(context.parsed);
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Payment Method Chart (Pie)
function createPaymentChart() {
    const paymentData = {};
    
    expenses.forEach(expense => {
        const payment = expense.payment_mode || 'Unknown';
        paymentData[payment] = (paymentData[payment] || 0) + parseFloat(expense.amount || 0);
    });
    
    const labels = Object.keys(paymentData);
    const data = Object.values(paymentData);
    
    const colors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444'];
    
    const ctx = document.getElementById('paymentChart').getContext('2d');
    
    if (paymentChart) paymentChart.destroy();
    
    paymentChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: '#0f172a',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#e5e7eb',
                        padding: 15,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = formatCurrency(context.parsed);
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Trend Chart (Line)
function createTrendChart() {
    // Group by month
    const monthlyData = {};
    
    expenses.forEach(expense => {
        const date = new Date(expense.purchase_date);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        if (!monthlyData[monthKey]) monthlyData[monthKey] = { expenses: 0, income: 0 };
        monthlyData[monthKey].expenses += parseFloat(expense.amount || 0);
    });
    
    income.forEach(inc => {
        const date = new Date(inc.income_date);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        if (!monthlyData[monthKey]) monthlyData[monthKey] = { expenses: 0, income: 0 };
        monthlyData[monthKey].income += parseFloat(inc.amount || 0);
    });
    
    const sortedMonths = Object.keys(monthlyData).sort();
    const labels = sortedMonths.map(month => {
        const [year, m] = month.split('-');
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${months[parseInt(m) - 1]} ${year}`;
    });
    
    const expenseData = sortedMonths.map(month => monthlyData[month].expenses);
    const incomeData = sortedMonths.map(month => monthlyData[month].income);
    
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    if (trendChart) trendChart.destroy();
    
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Income',
                    data: incomeData,
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 3
                },
                {
                    label: 'Expenses',
                    data: expenseData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#e5e7eb',
                        padding: 20,
                        font: { size: 13 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + formatCurrency(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#1e293b'
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                },
                y: {
                    grid: {
                        color: '#1e293b'
                    },
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        }
                    }
                }
            }
        }
    });
}

// Display top 5 expenses
function displayTopExpenses() {
    const sorted = [...expenses].sort((a, b) => parseFloat(b.amount) - parseFloat(a.amount));
    const top5 = sorted.slice(0, 5);
    
    const html = top5.map((expense, index) => `
        <div class="expense-item">
            <div class="expense-rank">${index + 1}</div>
            <div class="expense-details">
                <div class="expense-name">${expense.item}</div>
                <div class="expense-category">${expense.category || 'Other'}</div>
            </div>
            <div class="expense-amount">${formatCurrency(expense.amount)}</div>
        </div>
    `).join('');
    
    document.getElementById('topExpenses').innerHTML = html || '<p style="color:#6b7280;text-align:center;padding:20px;">No expenses yet</p>';
}

// Display recent activity
function displayRecentActivity() {
    const allTransactions = [
        ...expenses.map(e => ({ ...e, type: 'expense', date: e.purchase_date })),
        ...income.map(i => ({ ...i, type: 'income', date: i.income_date }))
    ];
    
    allTransactions.sort((a, b) => new Date(b.date) - new Date(a.date));
    const recent = allTransactions.slice(0, 5);
    
    const html = recent.map(transaction => {
        const isExpense = transaction.type === 'expense';
        const icon = isExpense ? '💸' : '💵';
        const name = isExpense ? transaction.item : transaction.source;
        const amountClass = isExpense ? 'expense' : 'income';
        const amount = isExpense ? '-' + formatCurrency(transaction.amount) : '+' + formatCurrency(transaction.amount);
        
        const date = new Date(transaction.date);
        const dateStr = date.toLocaleDateString('en-IN', { 
            month: 'short', 
            day: 'numeric',
            year: 'numeric'
        });
        
        return `
            <div class="activity-item">
                <div class="activity-icon ${transaction.type}">${icon}</div>
                <div class="activity-details">
                    <div class="activity-name">${name}</div>
                    <div class="activity-date">${dateStr}</div>
                </div>
                <div class="activity-amount ${amountClass}">${amount}</div>
            </div>
        `;
    }).join('');
    
    document.getElementById('recentActivity').innerHTML = html || '<p style="color:#6b7280;text-align:center;padding:20px;">No transactions yet</p>';
}

// Initialize
loadData();