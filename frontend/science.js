// SocialPulse Science Portal Application Logic

const API_BASE = 'http://127.0.0.1:8000/api';
let scienceForecastChart = null;

document.addEventListener('DOMContentLoaded', () => {
    initSciencePortal();
    
    // Refresh button event
    document.getElementById('refresh-btn').addEventListener('click', handlePipelineSync);
});

async function initSciencePortal() {
    console.log("Initializing Science Portal...");
    await loadScienceNews();
    await loadScienceTrending();
    await loadScienceForecast();
}

// 1. Load Science & Tech News
async function loadScienceNews() {
    const feedContainer = document.getElementById('science-news-feed');
    feedContainer.innerHTML = '<div class="loading-placeholder"><i class="fa-solid fa-spinner fa-spin"></i> Aggregating research headlines...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/trends/science/news`);
        if (!res.ok) throw new Error("Failed to load science news");
        const articles = await res.json();
        
        feedContainer.innerHTML = '';
        
        if (articles.length === 0) {
            feedContainer.innerHTML = '<div class="loading-placeholder">No articles found. Sync the trends pipeline first.</div>';
            document.getElementById('kpi-science-news-count').textContent = '0';
            document.getElementById('kpi-science-sentiment').textContent = '0.00';
            return;
        }
        
        // Update news count KPI
        document.getElementById('kpi-science-news-count').textContent = articles.length.toString();
        
        // Compute average sentiment
        let sumSentiment = 0.0;
        articles.forEach(a => sumSentiment += a.sentiment_score);
        const avgSentiment = sumSentiment / articles.length;
        
        const sentimentEl = document.getElementById('kpi-science-sentiment');
        sentimentEl.textContent = (avgSentiment >= 0 ? '+' : '') + avgSentiment.toFixed(2);
        
        // Color KPI sentiment based on positive/negative
        if (avgSentiment > 0.05) {
            sentimentEl.style.color = '#00e676';
        } else if (avgSentiment < -0.05) {
            sentimentEl.style.color = '#ff2a6d';
        } else {
            sentimentEl.style.color = '#9ca3af';
        }
        
        // Render Article Cards
        articles.forEach(article => {
            const card = document.createElement('a');
            card.href = article.link;
            card.target = '_blank';
            card.className = 'discussion-card glass';
            card.style.textDecoration = 'none';
            card.style.cursor = 'pointer';
            card.style.display = 'block';
            
            const date = new Date(article.published_date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            card.innerHTML = `
                <div class="card-top">
                    <div class="author-info">
                        <span class="author-name" style="color: var(--cyan);"><i class="fa-solid fa-newspaper"></i> ${article.source}</span>
                    </div>
                    <span class="sentiment-badge ${article.sentiment_label.toLowerCase()}">
                        ${article.sentiment_label} (${article.sentiment_score >= 0 ? '+' : ''}${article.sentiment_score.toFixed(1)})
                    </span>
                </div>
                <p class="discussion-text" style="margin-top: 0.5rem; font-weight: 500; font-size: 1rem; line-height: 1.4; color: var(--text-main);">
                    ${article.title}
                </p>
                <div class="discussion-meta" style="margin-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 0.5rem;">
                    <span></span>
                    <span class="discussion-date" style="font-size: 0.8rem; color: var(--text-dark);">${date}</span>
                </div>
            `;
            feedContainer.appendChild(card);
        });
    } catch (err) {
        console.error("Science News Feed Error:", err);
        feedContainer.innerHTML = '<div class="loading-placeholder" style="color: var(--rose);">Failed to load science news feed</div>';
    }
}

// 2. Load Trending Science Keywords
async function loadScienceTrending() {
    const tbody = document.getElementById('science-trending-tbody');
    tbody.innerHTML = '<tr><td colspan="2" style="text-align: center; padding: 1.5rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</td></tr>';
    
    try {
        // Fetch trending searches in United States specifically for category 'Science'
        const url = `${API_BASE}/trends/categories/trending?country=United%20States&category=Science`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to load science trends");
        const data = await res.json();
        
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" style="text-align: center; padding: 1rem; color: var(--text-muted); font-style: italic;">No specific science queries trending</td></tr>';
            return;
        }
        
        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid var(--border-glass)';
            tr.innerHTML = `
                <td style="padding: 0.5rem 0.25rem; font-weight: 700; color: var(--cyan);">#${item.rank}</td>
                <td style="padding: 0.5rem 0.25rem; font-weight: 500; color: var(--text-main);">${item.search_term}</td>
            `;
            tbody.appendChild(tr);
        });
        
        // Update top trend KPI card with rank #1 term
        if (data.length > 0) {
            document.getElementById('kpi-science-top-trend').textContent = data[0].search_term;
        }
    } catch (err) {
        console.error("Science Trending Table Error:", err);
        tbody.innerHTML = '<tr><td colspan="2" style="text-align: center; padding: 1rem; color: var(--rose);">Failed to load queries</td></tr>';
    }
}

// 3. Load Science Predictions Chart
async function loadScienceForecast() {
    try {
        const res = await fetch(`${API_BASE}/trends/science/predictions?keyword=Science`);
        if (!res.ok) throw new Error("Failed to load science forecast");
        const payload = await res.json();
        
        const dataPoints = payload.data || [];
        if (dataPoints.length === 0) return;
        
        const forecastIndex = dataPoints.findIndex(d => d.is_forecast);
        
        const histData = dataPoints.map((d, idx) => {
            if (d.is_forecast) return null;
            return d.count;
        });
        
        const forecastData = dataPoints.map((d, idx) => {
            if (!d.is_forecast) {
                return (idx === forecastIndex - 1) ? d.count : null;
            }
            return d.count;
        });
        
        const dates = dataPoints.map(d => {
            const date = new Date(d.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        const options = {
            series: [
                {
                    name: 'Historical index',
                    data: histData
                },
                {
                    name: '5-Day Predicted index',
                    data: forecastData
                }
            ],
            chart: {
                type: 'line',
                height: 230,
                toolbar: { show: false },
                background: 'transparent',
                dropShadow: {
                    enabled: true,
                    top: 10,
                    left: 0,
                    blur: 10,
                    opacity: 0.2,
                    color: '#bf55ec'
                }
            },
            theme: { mode: 'dark' },
            stroke: {
                curve: 'smooth',
                width: [4, 4],
                dashArray: [0, 5]
            },
            colors: ['#bf55ec', '#00f0ff'], // Purple for history, Cyan for prediction
            xaxis: {
                categories: dates,
                labels: { style: { colors: '#9ca3af', fontFamily: 'Outfit' } }
            },
            yaxis: {
                min: 0,
                max: 100,
                labels: { style: { colors: '#9ca3af', fontFamily: 'Outfit' } }
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

        if (scienceForecastChart) {
            scienceForecastChart.updateOptions(options);
        } else {
            scienceForecastChart = new ApexCharts(document.querySelector("#science-forecast-chart"), options);
            scienceForecastChart.render();
        }
    } catch (err) {
        console.error("Science Forecast Chart Error:", err);
    }
}

// 4. Ingest Pipeline trigger
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
        
        // Reload Science portal
        await initSciencePortal();
        
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
