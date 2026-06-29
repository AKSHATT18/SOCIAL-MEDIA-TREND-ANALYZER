// SocialPulse Overview Dashboard Application Logic

const API_BASE = 'http://127.0.0.1:8000/api';

// Chart instances
let categoryChart = null;
let categoryForecastChart = null;

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    
    // Event listeners
    document.getElementById('refresh-btn').addEventListener('click', handlePipelineSync);
    
    document.getElementById('country-select').addEventListener('change', loadTrendingQueries);
    document.getElementById('category-select').addEventListener('change', loadTrendingQueries);
    
    document.getElementById('forecast-category-select').addEventListener('change', (e) => {
        if (e.target.value) {
            loadForecastData(e.target.value);
        }
    });
});

async function initDashboard() {
    console.log("Initializing Overview Dashboard...");
    await loadKPIs();
    await loadCategoryComparison();
    await loadTrendingQueries();
    
    // Initial forecast load
    const initialForecastCat = document.getElementById('forecast-category-select').value || 'AI';
    await loadForecastData(initialForecastCat);
}

// Format numbers
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

// 1. Load KPIs
async function loadKPIs() {
    try {
        const res = await fetch(`${API_BASE}/summary`);
        if (!res.ok) throw new Error("Failed to load summary statistics");
        const data = await res.json();
        
        document.getElementById('kpi-top-category').textContent = data.top_google_category || 'AI';
        
        const topSearchEl = document.getElementById('kpi-top-search');
        topSearchEl.textContent = data.top_google_search || 'N/A';
        topSearchEl.title = data.top_google_search || 'N/A'; // tooltip
        
        document.getElementById('kpi-engagement').textContent = formatNumber(data.total_engagement);
    } catch (err) {
        console.error("KPI Error:", err);
    }
}

// 2. Load Category Interest Comparison (Line chart comparing categories)
async function loadCategoryComparison() {
    try {
        const res = await fetch(`${API_BASE}/trends/categories`);
        if (!res.ok) throw new Error("Failed to load category comparisons");
        const categoriesData = await res.json();
        
        const categoryNames = Object.keys(categoriesData);
        if (categoryNames.length === 0) return;
        
        // Pick a subset of categories to plot so the chart isn't overcrowded
        // We will plot AI, Technology, Medical, Sports, Finance, Science
        const focusCats = ["AI", "Technology", "Medical", "Sports", "Finance", "Science"];
        const series = [];
        
        // Find distinct dates (use the dates of the first category found)
        const sampleCat = categoryNames[0];
        const dates = categoriesData[sampleCat]
            .filter(d => !d.is_forecast) // Only plot historical comparison
            .map(d => {
                const dt = new Date(d.date);
                return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            });
            
        focusCats.forEach(c => {
            if (categoriesData[c]) {
                series.push({
                    name: c,
                    data: categoriesData[c]
                        .filter(d => !d.is_forecast)
                        .map(d => parseFloat(d.score.toFixed(1)))
                });
            }
        });

        // If categories aren't in database, fallback to empty check
        if (series.length === 0) {
            // Fallback: load whatever categories are available
            categoryNames.slice(0, 5).forEach(c => {
                series.push({
                    name: c,
                    data: categoriesData[c].filter(d => !d.is_forecast).map(d => parseFloat(d.score.toFixed(1)))
                });
            });
        }

        const options = {
            series: series,
            chart: {
                type: 'line',
                height: 340,
                toolbar: { show: false },
                background: 'transparent'
            },
            theme: { mode: 'dark' },
            stroke: {
                curve: 'smooth',
                width: 3
            },
            colors: ['#00f0ff', '#bf55ec', '#00e676', '#ff2a6d', '#ff8c00', '#ffd700'],
            xaxis: {
                categories: dates,
                labels: {
                    style: {
                        colors: '#9ca3af',
                        fontFamily: 'Outfit'
                    }
                }
            },
            yaxis: {
                min: 0,
                max: 100,
                labels: {
                    style: {
                        colors: '#9ca3af',
                        fontFamily: 'Outfit'
                    }
                },
                title: {
                    text: 'Google Search Index',
                    style: {
                        color: '#9ca3af',
                        fontFamily: 'Outfit'
                    }
                }
            },
            grid: {
                borderColor: 'rgba(255,255,255,0.06)',
                yaxis: { lines: { show: true } }
            },
            legend: {
                position: 'top',
                horizontalAlign: 'right',
                labels: { colors: '#9ca3af' },
                fontFamily: 'Outfit'
            },
            tooltip: { theme: 'dark' }
        };

        if (categoryChart) {
            categoryChart.updateOptions(options);
        } else {
            categoryChart = new ApexCharts(document.querySelector("#category-chart"), options);
            categoryChart.render();
        }
    } catch (err) {
        console.error("Category Comparison Error:", err);
    }
}

// 3. Load Trending Queries Table
async function loadTrendingQueries() {
    const country = document.getElementById('country-select').value;
    const category = document.getElementById('category-select').value;
    const tbody = document.getElementById('trending-queries-tbody');
    
    tbody.innerHTML = '<tr><td colspan="2" style="text-align: center; padding: 1.5rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading live queries...</td></tr>';
    
    try {
        const url = `${API_BASE}/trends/google/realtime?country=${encodeURIComponent(country)}&category=${encodeURIComponent(category)}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to fetch trending queries");
        const data = await res.json();
        
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" style="text-align: center; padding: 1.5rem; color: var(--text-muted); font-style: italic;">No queries trending in this category</td></tr>';
            return;
        }
        
        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid var(--border-glass)';
            tr.innerHTML = `
                <td style="padding: 0.6rem 0.25rem; font-weight: 700; color: var(--cyan); width: 60px;">#${item.rank}</td>
                <td style="padding: 0.6rem 0.25rem; font-weight: 500; color: var(--text-main);">${item.search_term}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Trending queries table error:", err);
        tbody.innerHTML = '<tr><td colspan="2" style="text-align: center; padding: 1.5rem; color: var(--rose);">Failed to load trending queries</td></tr>';
    }
}

// 4. Load Forecast Data for Selected Category
async function loadForecastData(category) {
    try {
        const res = await fetch(`${API_BASE}/trends/categories?category=${encodeURIComponent(category)}`);
        if (!res.ok) throw new Error("Failed to load forecast category data");
        const categoryDict = await res.json();
        
        // The endpoint returns {"CategoryName": [points]}
        const dataPoints = categoryDict[category] || [];
        if (dataPoints.length === 0) return;
        
        const forecastIndex = dataPoints.findIndex(d => d.is_forecast);
        
        const histData = dataPoints.map((d, idx) => {
            if (d.is_forecast) return null;
            return d.score;
        });
        
        const forecastData = dataPoints.map((d, idx) => {
            if (!d.is_forecast) {
                return (idx === forecastIndex - 1) ? d.score : null;
            }
            return d.score;
        });
        
        const categories = dataPoints.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        const options = {
            series: [
                {
                    name: 'Historical search index',
                    data: histData
                },
                {
                    name: '5-Day Predicted search index',
                    data: forecastData
                }
            ],
            chart: {
                type: 'line',
                height: 320,
                toolbar: { show: false },
                background: 'transparent',
                dropShadow: {
                    enabled: true,
                    top: 10,
                    left: 0,
                    blur: 10,
                    opacity: 0.2,
                    color: '#00f0ff'
                }
            },
            theme: { mode: 'dark' },
            stroke: {
                curve: 'smooth',
                width: [4, 4],
                dashArray: [0, 5]
            },
            colors: ['#00f0ff', '#bf55ec'],
            xaxis: {
                categories: categories,
                labels: { style: { colors: '#9ca3af', fontFamily: 'Outfit' } }
            },
            yaxis: {
                min: 0,
                max: 100,
                labels: { style: { colors: '#9ca3af', fontFamily: 'Outfit' } },
                title: {
                    text: 'Google Trends Score (0-100)',
                    style: { color: '#9ca3af', fontFamily: 'Outfit' }
                }
            },
            grid: {
                borderColor: 'rgba(255,255,255,0.06)',
                yaxis: { lines: { show: true } }
            },
            markers: {
                size: [4, 4],
                strokeWidth: 2,
                hover: { size: 6 }
            },
            legend: {
                position: 'top',
                horizontalAlign: 'right',
                labels: { colors: '#9ca3af' },
                fontFamily: 'Outfit'
            },
            tooltip: { theme: 'dark' }
        };

        if (categoryForecastChart) {
            categoryForecastChart.updateOptions(options);
        } else {
            categoryForecastChart = new ApexCharts(document.querySelector("#category-forecast-chart"), options);
            categoryForecastChart.render();
        }
    } catch (err) {
        console.error("Category Forecast Error:", err);
    }
}

// 5. Trigger Pipeline Ingest Trigger
async function handlePipelineSync() {
    const btn = document.getElementById('refresh-btn');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing ETL...';
    
    try {
        const res = await fetch(`${API_BASE}/pipeline/run`, {
            method: 'POST'
        });
        
        if (!res.ok) throw new Error("Pipeline trigger failed");
        
        const data = await res.json();
        console.log("Pipeline sync finished:", data);
        
        btn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Sync Finished';
        btn.style.background = 'linear-gradient(135deg, #00e676 0%, #00b4d8 100%)';
        
        // Reload dashboard
        await initDashboard();
        
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = originalText;
            btn.style.background = '';
        }, 2000);
        
    } catch (err) {
        console.error("Pipeline run error:", err);
        btn.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Sync Failed';
        btn.style.background = 'linear-gradient(135deg, #ff2a6d 0%, #ff007f 100%)';
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = originalText;
            btn.style.background = '';
        }, 3000);
    }
}


