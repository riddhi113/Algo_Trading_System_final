//Auth helpers
function getToken() { return localStorage.getItem('algo_token') || ''; }
function authHeaders() { return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` }; }

function handleLogout() {
    localStorage.removeItem('algo_token');
    localStorage.removeItem('algo_user');
    window.location.href = '/';
}

//Show logged-in username
window.addEventListener('DOMContentLoaded', () => {
    const user = localStorage.getItem('algo_user') || 'Admin';
    const el = document.getElementById('hud-user');
    if (el) el.textContent = user;
});

//Broker API functions
async function brokerGetBalance() {
    try {
        const res = await fetch('/api/broker/balance', { headers: authHeaders() });
        if (res.status === 401) { return; } // silently skip — user will see data after RUN BACKTEST
        if (!res.ok) return;
        const d = await res.json();
        const balEl = document.getElementById('broker-balance');
        const eqEl = document.getElementById('broker-equity');
        if (balEl) balEl.textContent = `₹${d.cash_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        if (eqEl) eqEl.textContent = `Total equity: ₹${d.total_equity.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    } catch (e) { /* network error — ignore silently */ }
}

async function brokerGetPositions() {
    const res = await fetch('/api/broker/positions', { headers: authHeaders() });
    if (res.status === 401) { return; }
    const d = await res.json();
    const el = document.getElementById('broker-positions');
    if (d.count === 0) { el.textContent = 'No open positions.'; return; }
    el.innerHTML = d.open_positions.map(p => `
        <div style="border:1px solid rgba(99,179,237,.15);border-radius:8px;padding:.6rem;margin-bottom:.5rem;">
            <strong style="color:#63b3ed;">${p.ticker}</strong>
            <span style="margin-left:.5rem;color:${p.direction === 'LONG' ? '#10b981' : '#ef4444'}">${p.direction}</span>
            <span style="color:#94a3b8;margin-left:.5rem;">Qty: ${p.quantity}</span>
            <span style="color:#94a3b8;margin-left:.5rem;">Entry: ₹${p.entry_price}</span>
            <span style="color:${p.unrealized_pnl >= 0 ? '#10b981' : '#ef4444'};margin-left:.5rem;">PnL: ₹${p.unrealized_pnl}</span>
        </div>`).join('');
}

async function brokerGetHistory() {
    const res = await fetch('/api/broker/history', { headers: authHeaders() });
    if (res.status === 401) { return; }
    const d = await res.json();
    const el = document.getElementById('broker-history');
    if (d.total === 0) { el.textContent = 'No orders placed yet.'; return; }
    el.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:.8rem;">
        <thead><tr style="color:#64748b;border-bottom:1px solid rgba(255,255,255,.08);">
            <th style="text-align:left;padding:.4rem;">ID</th><th>Dir</th><th>Qty</th>
            <th>Entry</th><th>Exit</th><th>PnL</th><th>Reason</th><th>Status</th>
        </tr></thead><tbody>
        ${d.order_history.map(t => `<tr style="border-bottom:1px solid rgba(255,255,255,.04);">
            <td style="padding:.35rem;color:#93c5fd;">${t.trade_id}</td>
            <td style="color:${t.direction === 'LONG' ? '#10b981' : '#ef4444'}">${t.direction}</td>
            <td>${t.quantity}</td>
            <td>₹${t.entry_price}</td>
            <td>${t.exit_price ? '₹' + t.exit_price : '—'}</td>
            <td style="color:${t.pnl >= 0 ? '#10b981' : '#ef4444'}">${t.pnl >= 0 ? '+' : ''}₹${t.pnl}</td>
            <td><span style="background:rgba(59,130,246,.15);color:#93c5fd;padding:1px 6px;border-radius:4px;font-size:.72rem;">${t.exit_reason || 'OPEN'}</span></td>
            <td>${t.status}</td>
        </tr>`).join('')}
        </tbody></table>`;
}

async function brokerPlaceOrder() {
    const ticker = document.getElementById('bo-ticker').value.trim();
    const direction = document.getElementById('bo-dir').value;
    const quantity = parseFloat(document.getElementById('bo-qty').value);
    const price = parseFloat(document.getElementById('bo-price').value);
    const sl = parseFloat(document.getElementById('bo-sl').value) || null;
    const tp = parseFloat(document.getElementById('bo-tp').value) || null;
    const msgEl = document.getElementById('broker-order-msg');

    const res = await fetch('/api/broker/order', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ ticker, direction, quantity, price, stop_loss: sl, take_profit: tp })
    });
    const d = await res.json();
    if (res.ok) {
        msgEl.style.color = '#10b981';
        msgEl.textContent = `✓ Order placed: ${d.trade_id} | ${direction} ${quantity} ${ticker} @ ₹${price} | Cash remaining: ₹${d.cash_remaining}`;
        brokerGetBalance();
    } else {
        msgEl.style.color = '#ef4444';
        msgEl.textContent = `✗ ${d.detail}`;
    }
}

//WebSocket live price feed
const livePrices = {};

function connectLiveWS() {
    const ws = new WebSocket(`ws://${location.host}/ws/live`);
    const statusEl = document.getElementById('ws-status');
    const gridEl = document.getElementById('live-feed-grid');

    ws.onopen = () => {
        if (statusEl) statusEl.innerHTML = '<i class="fa-solid fa-circle" style="color:#10b981;font-size:.55rem;"></i> Live — connected';
    };
    ws.onmessage = (ev) => {
        try {
            const msg = JSON.parse(ev.data);
            if (msg.type !== 'tick' || !gridEl) return;
            msg.data.forEach(tick => {
                const up = tick.change_pct >= 0;
                if (!livePrices[tick.symbol]) {
                    // Create card
                    const card = document.createElement('div');
                    card.id = `lf-${tick.symbol.replace(/[^a-z0-9]/gi, '_')}`;
                    card.style.cssText = 'background:rgba(255,255,255,.04);border:1px solid rgba(99,179,237,.12);border-radius:10px;padding:.75rem;';
                    gridEl.appendChild(card);
                }
                const card = document.getElementById(`lf-${tick.symbol.replace(/[^a-z0-9]/gi, '_')}`);
                if (card) card.innerHTML = `
                    <div style="font-size:.72rem;color:#64748b;margin-bottom:.25rem;">${tick.symbol}</div>
                    <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;">₹${tick.price.toFixed(2)}</div>
                    <div style="font-size:.78rem;color:${up ? '#10b981' : '#ef4444'};margin-top:.15rem;">
                        ${up ? '▲' : '▼'} ${Math.abs(tick.change_pct).toFixed(3)}%
                    </div>
                    <div style="font-size:.7rem;color:#64748b;">${tick.timestamp}</div>`;
                livePrices[tick.symbol] = tick.price;
            });
        } catch { }
    };
    ws.onclose = () => {
        if (statusEl) statusEl.innerHTML = '<i class="fa-solid fa-circle" style="color:#ef4444;font-size:.55rem;"></i> Disconnected — reconnecting...';
        setTimeout(connectLiveWS, 3000);
    };
}
connectLiveWS();

//Auto-load broker balance on page load
window.addEventListener('DOMContentLoaded', () => { brokerGetBalance(); });

//Document Nodes
const form = document.getElementById("backtest-form");
const tickerSelect = document.getElementById("ticker-select");

const strategySelect = document.getElementById("strategy-select");
const maParams = document.getElementById("ma-params");
const macdParams = document.getElementById("macd-params");
const loader = document.getElementById("loader");
const exportCsvBtn = document.getElementById("export-csv-btn");
const tradeSearchInput = document.getElementById("trade-search");

//Tab togglers
const tabButtons = document.querySelectorAll(".tab-btn");
const tabContents = document.querySelectorAll(".tab-content");

//Chart instances
let tvChartInstance = null;
let equityChartInstance = null;
let comparisonChartInstance = null;
let currentTradesData = [];


//TAB CONTROLLER & RESIZING
tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
        const targetTab = btn.getAttribute("data-tab");

        tabButtons.forEach(b => b.classList.remove("active"));
        tabContents.forEach(c => c.classList.remove("active"));

        btn.classList.add("active");
        document.getElementById(targetTab).classList.add("active");

        // Force TradingView chart to resize to new viewport dimensions
        if (targetTab === "price-tab" && tvChartInstance) {
            const container = document.getElementById("tv-chart");
            tvChartInstance.resize(container.clientWidth, container.clientHeight);
        }
    });
});

//Resize handler
window.addEventListener("resize", () => {
    if (tvChartInstance) {
        const container = document.getElementById("tv-chart");
        tvChartInstance.resize(container.clientWidth, container.clientHeight);
    }
});



//Strategy panel visibility
strategySelect.addEventListener("change", (e) => {
    const compareTabBtn = document.getElementById("tab-btn-compare");
    if (e.target.value === "MA_Crossover") {
        maParams.classList.remove("hidden");
        macdParams.classList.add("hidden");
        if (compareTabBtn) compareTabBtn.classList.add("hidden");
    } else if (e.target.value === "MACD") {
        maParams.classList.add("hidden");
        macdParams.classList.remove("hidden");
        if (compareTabBtn) compareTabBtn.classList.add("hidden");
    } else if (e.target.value === "Compare") {
        maParams.classList.remove("hidden");
        macdParams.classList.remove("hidden");
        if (compareTabBtn) compareTabBtn.classList.remove("hidden");
    }
});

//Initial load check for Strategy select panel
window.addEventListener("DOMContentLoaded", () => {
    const compareTabBtn = document.getElementById("tab-btn-compare");
    if (strategySelect.value === "MA_Crossover") {
        maParams.classList.remove("hidden");
        macdParams.classList.add("hidden");
        if (compareTabBtn) compareTabBtn.classList.add("hidden");
    } else if (strategySelect.value === "MACD") {
        maParams.classList.add("hidden");
        macdParams.classList.remove("hidden");
        if (compareTabBtn) compareTabBtn.classList.add("hidden");
    } else if (strategySelect.value === "Compare") {
        maParams.classList.remove("hidden");
        macdParams.classList.remove("hidden");
        if (compareTabBtn) compareTabBtn.classList.remove("hidden");
    }
});

// 2. SUBMIT FORM & API CALL
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    loader.classList.remove("hidden");

    const ticker = tickerSelect.value;
    const start_date = document.getElementById("start-date").value;
    const end_date = document.getElementById("end-date").value;
    const initial_capital = parseFloat(document.getElementById("initial-capital").value);

    const stop_loss_pct = parseFloat(document.getElementById("stop-loss").value) / 100.0;
    const take_profit_pct = parseFloat(document.getElementById("take-profit").value) / 100.0;
    const risk_pct = parseFloat(document.getElementById("risk-pct").value) / 100.0;
    const allow_short = document.getElementById("allow-short").checked;

    const strategy = strategySelect.value;

    let strategy_params = {};
    let endpoint = "/api/backtest";

    if (strategy === "Compare") {
        endpoint = "/api/compare";
        strategy_params = {
            ma_fast_period: parseInt(document.getElementById("ma-fast").value),
            ma_slow_period: parseInt(document.getElementById("ma-slow").value),
            ma_type: document.getElementById("ma-type").value,
            macd_fast_period: parseInt(document.getElementById("macd-fast").value),
            macd_slow_period: parseInt(document.getElementById("macd-slow").value),
            macd_signal_period: parseInt(document.getElementById("macd-signal").value)
        };
    } else if (strategy === "MA_Crossover") {
        strategy_params = {
            fast_period: parseInt(document.getElementById("ma-fast").value),
            slow_period: parseInt(document.getElementById("ma-slow").value),
            ma_type: document.getElementById("ma-type").value
        };
    } else if (strategy === "MACD") {
        strategy_params = {
            fast_period: parseInt(document.getElementById("macd-fast").value),
            slow_period: parseInt(document.getElementById("macd-slow").value),
            signal_period: parseInt(document.getElementById("macd-signal").value)
        };
    }

    const payload = {
        ticker,
        start_date,
        end_date,
        interval: "1d",
        initial_capital,
        stop_loss_pct: stop_loss_pct > 0 ? stop_loss_pct : null,
        take_profit_pct: take_profit_pct > 0 ? take_profit_pct : null,
        risk_pct: risk_pct > 0 ? risk_pct : null,
        allow_short,
        strategy: strategy === "Compare" ? "MA_Crossover" : strategy,
        strategy_params
    };

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify(payload)
        });

        // Check auth FIRST before parsing JSON
        if (response.status === 401) {
            alert('Session expired. Please log in again.');
            localStorage.removeItem('algo_token');
            localStorage.removeItem('algo_user');
            window.location.href = '/';
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Error compiling backtest parameters.");
        }

        if (strategy === "Compare") {
            updateComparisonDashboard(data);
            document.getElementById("tab-btn-compare").click();
        } else {
            updateDashboard(data);
            document.getElementById("tab-btn-price").click();
        }

    } catch (err) {
        alert("Backtest Failed:\n" + err.message);
        console.error(err);
    } finally {
        loader.classList.add("hidden");
    }
});

// ----------------------------------------------------
// 3. UPDATE FRONTEND DASHBOARD HUD & CARDS
// ----------------------------------------------------
function updateDashboard(data) {
    const metrics = data.metrics;

    // 1. Update HUD Top Bar
    document.getElementById("hud-ticker").innerText = data.ticker;
    document.getElementById("hud-dates").innerText = `${data.chart_data[0].date} to ${data.chart_data[data.chart_data.length - 1].date}`;
    document.getElementById("hud-balance").innerText = `₹${metrics.final_equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

    // 2. Update KPI Metric Cards
    updateKPICard("kpi-return", "kpi-profit", metrics.total_pnl_pct, metrics.total_pnl, true);
    updateKPICardSimple("kpi-drawdown", metrics.max_drawdown, false);

    document.getElementById("kpi-winrate").innerText = `${metrics.win_rate.toFixed(1)}%`;
    document.getElementById("kpi-ratio").innerText = `${metrics.winning_trades} wins / ${metrics.losing_trades} losses`;

    document.getElementById("kpi-sharpe").innerText = metrics.sharpe_ratio.toFixed(2);
    updateKPICardSimple("kpi-benchmark", metrics.benchmark_pnl_pct, true);

    // Legend initial labels
    document.getElementById("legend-ticker").innerText = data.ticker;

    // 3. Render TradingView Candlestick Chart
    renderTradingViewChart(data.chart_data, data.ticker, data.status);

    // 4. Render Chart.js Equity Curve
    renderEquityChart(data.equity_curve);

    // 5. Render Trade Logs
    renderTradesTable(data.trades);
    currentTradesData = data.trades;
    tradeSearchInput.value = ""; // Clear search filter on reload
}

function updateKPICard(valueId, subTextId, pct, absolute, positiveIsGood) {
    const valueEl = document.getElementById(valueId);
    const subTextEl = document.getElementById(subTextId);

    const sign = pct >= 0 ? "+" : "";
    valueEl.innerText = `${sign}${pct.toFixed(2)}%`;
    subTextEl.innerText = `${sign}₹${absolute.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const colorClass = (pct >= 0) === positiveIsGood ? "text-green" : "text-red";
    valueEl.className = `kpi-value ${colorClass}`;
    subTextEl.className = `kpi-subtext ${colorClass}`;
}

function updateKPICardSimple(valueId, pct, positiveIsGood) {
    const valueEl = document.getElementById(valueId);
    const sign = pct >= 0 ? "+" : "";
    valueEl.innerText = `${sign}${pct.toFixed(2)}%`;

    const colorClass = (pct >= 0) === positiveIsGood ? "text-green" : "text-red";
    valueEl.className = colorClass;
}

// ----------------------------------------------------
// 4. TRADINGVIEW LIGHTWEIGHT CHARTS RENDERING
// ----------------------------------------------------
function renderTradingViewChart(chartData, ticker) {
    const container = document.getElementById("tv-chart");
    container.innerHTML = ""; // Clear viewport

    const chartOptions = {
        layout: {
            background: { type: 'solid', color: '#090d1a' },
            textColor: '#94a3b8',
            fontFamily: "'Inter', sans-serif"
        },
        grid: {
            vertLines: { color: 'rgba(0, 242, 254, 0.04)' },
            horzLines: { color: 'rgba(0, 242, 254, 0.04)' }
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
                labelBackgroundColor: '#00f2fe',
            },
            horzLine: {
                labelBackgroundColor: '#00f2fe',
            }
        },
        rightPriceScale: {
            borderColor: 'rgba(0, 242, 254, 0.15)',
        },
        timeScale: {
            borderColor: 'rgba(0, 242, 254, 0.15)',
            timeVisible: false,
            secondsVisible: false
        }
    };

    // Create container
    tvChartInstance = LightweightCharts.createChart(container, chartOptions);

    // 1. Add Candlestick Series
    const candlestickSeries = tvChartInstance.addCandlestickSeries({
        upColor: '#08f7a6',
        downColor: '#ff355e',
        borderVisible: true,
        upBorderColor: '#08f7a6',
        downBorderColor: '#ff355e',
        wickUpColor: '#08f7a6',
        wickDownColor: '#ff355e'
    });

    const candles = chartData.map(d => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close
    })).sort((a, b) => new Date(a.time) - new Date(b.time));

    candlestickSeries.setData(candles);

    // 2. Add Volume Histogram Overlay
    const volumeSeries = tvChartInstance.addHistogramSeries({
        color: '#08f7a6',
        priceFormat: { type: 'volume' },
        priceScaleId: '', // Overlay on the main candlestick price scale
    });

    // Scale volume down to bottom 15% of pane
    volumeSeries.priceScale().applyOptions({
        scaleMargins: {
            top: 0.82,
            bottom: 0,
        },
    });

    const volumes = chartData.map(d => ({
        time: d.date,
        value: d.volume,
        color: d.close >= d.open ? 'rgba(8, 247, 166, 0.2)' : 'rgba(255, 53, 94, 0.2)'
    })).sort((a, b) => new Date(a.time) - new Date(b.time));

    volumeSeries.setData(volumes);

    // 3. Add MA overlay lines if strategy is MA_Crossover
    if (chartData[0] && chartData[0].fast_ma !== undefined) {
        const fastSeries = tvChartInstance.addLineSeries({
            color: '#00e5ff',
            lineWidth: 1.5,
            title: 'Fast MA'
        });
        const fastData = chartData
            .filter(d => d.fast_ma !== null)
            .map(d => ({ time: d.date, value: d.fast_ma }));
        fastSeries.setData(fastData);

        const slowSeries = tvChartInstance.addLineSeries({
            color: '#ff9f43',
            lineWidth: 1.5,
            title: 'Slow MA'
        });
        const slowData = chartData
            .filter(d => d.slow_ma !== null)
            .map(d => ({ time: d.date, value: d.slow_ma }));
        slowSeries.setData(slowData);
    }

    // 4. Add Signal Markers
    const markers = [];
    chartData.forEach(d => {
        if (d.signal === "BUY") {
            markers.push({
                time: d.date,
                position: 'belowBar',
                color: '#00e676',
                shape: 'arrowUp',
                text: 'BUY',
                size: 1.5
            });
        } else if (d.signal === "SELL") {
            markers.push({
                time: d.date,
                position: 'aboveBar',
                color: '#ff1744',
                shape: 'arrowDown',
                text: 'SELL',
                size: 1.5
            });
        }
    });

    if (markers.length > 0) {
        // Sort markers chronologically
        markers.sort((a, b) => new Date(a.time) - new Date(b.time));
        candlestickSeries.setMarkers(markers);
    }

    // 5. Update legend details on crosshair move
    tvChartInstance.subscribeCrosshairMove(param => {
        if (param.time) {
            const data = param.seriesData.get(candlestickSeries);
            if (data) {
                document.getElementById("legend-open").innerText = data.open.toFixed(2);
                document.getElementById("legend-high").innerText = data.high.toFixed(2);
                document.getElementById("legend-low").innerText = data.low.toFixed(2);
                document.getElementById("legend-close").innerText = data.close.toFixed(2);

                // Color close depending on change
                const closeEl = document.getElementById("legend-close");
                closeEl.className = data.close >= data.open ? "text-green" : "text-red";
            }
        }
    });

    // Auto-fit contents in screen
    tvChartInstance.timeScale().fitContent();

    // Trigger resize to fill viewport container dimensions
    tvChartInstance.resize(container.clientWidth, container.clientHeight);
}

// ----------------------------------------------------
// 5. CHART.JS CUMULATIVE RETURN CURVE
// ----------------------------------------------------
function renderEquityChart(equityCurve) {
    if (equityChartInstance) {
        equityChartInstance.destroy();
    }

    const labels = equityCurve.map(d => d.date);
    const strategyReturn = equityCurve.map(d => d.strategy_return);
    const benchmarkReturn = equityCurve.map(d => d.benchmark_return);

    const ctx = document.getElementById("equityChart").getContext("2d");
    equityChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Strategy Return (%)",
                    data: strategyReturn,
                    borderColor: "#2196f3",
                    borderWidth: 2.5,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "Benchmark (Buy & Hold) Return (%)",
                    data: benchmarkReturn,
                    borderColor: "#848e9c",
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { labels: { color: "#f1f3f5", font: { family: "'Inter', sans-serif" } } }
            },
            scales: {
                x: {
                    type: "time",
                    time: { unit: "month", displayFormats: { month: "MMM yyyy" } },
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: { color: "#848e9c" }
                },
                y: {
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: {
                        color: "#848e9c",
                        callback: function (value) { return (value >= 0 ? "+" : "") + value.toFixed(1) + "%"; }
                    }
                }
            }
        }
    });
}

// ----------------------------------------------------
// 6. RENDER & FILTER COMPLETED TRADES TABLE
// ----------------------------------------------------
function renderTradesTable(trades) {
    const tbody = document.querySelector("#trades-table tbody");
    tbody.innerHTML = "";

    if (trades.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" class="text-center text-gray">No trades executed in this backtest simulation.</td></tr>`;
        return;
    }

    trades.forEach(t => {
        const row = document.createElement("tr");
        const pnlColorClass = t.pnl >= 0 ? "text-green" : "text-red";
        const pnlSign = t.pnl >= 0 ? "+" : "";

        // Reason pill styling
        let reasonBadge = `<span style="background-color: rgba(33, 150, 243, 0.15); color: var(--color-blue); padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 700; border: 1px solid rgba(33, 150, 243, 0.2);">${t.exit_reason}</span>`;
        if (t.exit_reason === "SL") {
            reasonBadge = `<span style="background-color: rgba(239, 83, 80, 0.15); color: var(--color-red); padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 700; border: 1px solid rgba(239, 83, 80, 0.2);">${t.exit_reason}</span>`;
        } else if (t.exit_reason === "TP") {
            reasonBadge = `<span style="background-color: rgba(38, 166, 154, 0.15); color: var(--color-green); padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 700; border: 1px solid rgba(38, 166, 154, 0.2);">${t.exit_reason}</span>`;
        }

        row.innerHTML = `
            <td><strong>${t.trade_id}</strong></td>
            <td><span class="${t.direction === "LONG" ? "text-green" : "text-red"}">${t.direction}</span></td>
            <td>${t.quantity.toFixed(4)}</td>
            <td>${t.entry_date}</td>
            <td>₹${t.entry_price.toFixed(2)}</td>
            <td>${t.exit_date || "OPEN"}</td>
            <td>${t.exit_price ? "₹" + t.exit_price.toFixed(2) : "OPEN"}</td>
            <td class="${pnlColorClass}">${pnlSign}₹${t.pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td class="${pnlColorClass}">${pnlSign}${t.pnl_pct.toFixed(2)}%</td>
            <td>${reasonBadge}</td>
        `;
        tbody.appendChild(row);
    });
}

// Client-side quick filter / search table
tradeSearchInput.addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase();
    const rows = document.querySelectorAll("#trades-table tbody tr");

    rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        if (text.includes(query)) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
});

// ----------------------------------------------------
// 7. EXPORT CSV UTILITY
// ----------------------------------------------------
exportCsvBtn.addEventListener("click", () => {
    if (currentTradesData.length === 0) {
        alert("No transaction logs available for export.");
        return;
    }

    let csvContent = "Trade ID,Ticker,Direction,Quantity,Entry Date,Entry Price,Exit Date,Exit Price,Realized PnL,Return (%),Exit Reason\n";

    currentTradesData.forEach(t => {
        csvContent += `${t.trade_id},${t.ticker},${t.direction},${t.quantity},${t.entry_date},${t.entry_price},${t.exit_date || "OPEN"},${t.exit_price || ""},${t.pnl},${t.pnl_pct.toFixed(4)},${t.exit_reason || "OPEN"}\n`;
    });

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `trades_${document.getElementById("hud-ticker").innerText}_${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});

// Trigger initial submit on startup
window.addEventListener("DOMContentLoaded", () => {
    form.dispatchEvent(new Event("submit"));
});

// ----------------------------------------------------
// 8. RENDER STRATEGY COMPARISON DASHBOARD
// ----------------------------------------------------
function updateComparisonDashboard(data) {
    // 1. Update HUD Top Bar
    document.getElementById("hud-ticker").innerText = data.ticker;
    if (data.comparison_curve && data.comparison_curve.length > 0) {
        document.getElementById("hud-dates").innerText = `${data.comparison_curve[0].date} to ${data.comparison_curve[data.comparison_curve.length - 1].date}`;
    } else {
        document.getElementById("hud-dates").innerText = "No Data";
    }
    document.getElementById("hud-balance").innerText = "Comparison Loaded";

    // 2. Render MA Crossover Metrics
    renderCompMetrics("ma", data.ma_metrics);

    // 3. Render MACD Metrics
    renderCompMetrics("macd", data.macd_metrics);

    // 4. Render comparison chart
    renderComparisonChart(data.comparison_curve);
}

function renderCompMetrics(prefix, metrics) {
    const returnEl = document.getElementById(`comp-${prefix}-return`);
    const profitEl = document.getElementById(`comp-${prefix}-profit`);
    const ddEl = document.getElementById(`comp-${prefix}-drawdown`);
    const winrateEl = document.getElementById(`comp-${prefix}-winrate`);
    const tradesEl = document.getElementById(`comp-${prefix}-trades`);
    const sharpeEl = document.getElementById(`comp-${prefix}-sharpe`);

    const sign = metrics.total_pnl_pct >= 0 ? "+" : "";
    returnEl.innerText = `${sign}${metrics.total_pnl_pct.toFixed(2)}%`;
    profitEl.innerText = `${sign}₹${metrics.total_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const colorClass = metrics.total_pnl_pct >= 0 ? "text-green" : "text-red";
    returnEl.className = colorClass;
    profitEl.className = colorClass;

    ddEl.innerText = `${metrics.max_drawdown.toFixed(2)}%`;
    winrateEl.innerText = `${metrics.win_rate.toFixed(1)}%`;
    tradesEl.innerText = `${metrics.winning_trades} W / ${metrics.losing_trades} L`;
    sharpeEl.innerText = metrics.sharpe_ratio.toFixed(2);
}

function renderComparisonChart(comparisonCurve) {
    if (comparisonChartInstance) {
        comparisonChartInstance.destroy();
    }

    const labels = comparisonCurve.map(d => d.date);
    const maReturn = comparisonCurve.map(d => d.ma_return);
    const macdReturn = comparisonCurve.map(d => d.macd_return);
    const benchmarkReturn = comparisonCurve.map(d => d.benchmark_return);

    const ctx = document.getElementById("comparisonChart").getContext("2d");
    comparisonChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "MA Crossover Return (%)",
                    data: maReturn,
                    borderColor: "#00f2fe",
                    borderWidth: 2.5,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "MACD Return (%)",
                    data: macdReturn,
                    borderColor: "#9d4edd",
                    borderWidth: 2.5,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: "Benchmark (Buy & Hold) Return (%)",
                    data: benchmarkReturn,
                    borderColor: "#7a869a",
                    borderWidth: 1.5,
                    borderDash: [4, 4],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { labels: { color: "#f1f3f5", font: { family: "'Inter', sans-serif" } } }
            },
            scales: {
                x: {
                    type: "time",
                    time: { unit: "month", displayFormats: { month: "MMM yyyy" } },
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: { color: "#7a869a" }
                },
                y: {
                    grid: { color: "rgba(255, 255, 255, 0.04)" },
                    ticks: {
                        color: "#7a869a",
                        callback: function (value) { return (value >= 0 ? "+" : "") + value.toFixed(1) + "%"; }
                    }
                }
            }
        }
    });
}
