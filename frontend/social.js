// Social Media Portal Logic

const API_BASE = 'http://127.0.0.1:8000/api';

document.addEventListener('DOMContentLoaded', () => {
    initSocialPortal();
    
    document.getElementById('refresh-social-btn').addEventListener('click', handleSocialSync);
    document.getElementById('news-category-select').addEventListener('change', renderNewsGrid);
});

let cachedNewsData = null;

async function initSocialPortal() {
    console.log("Initializing Social Portal...");
    await Promise.allSettled([
        loadRedditData(),
        loadYouTubeData(),
        loadNewsData()
    ]);
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function showSimIndicator(show) {
    const el = document.getElementById('sim-mode-indicator');
    if (show) {
        el.style.display = 'inline-block';
    }
}

// 1. Reddit Data
async function loadRedditData() {
    const tbody = document.getElementById('reddit-tbody');
    const trackedEl = document.getElementById('reddit-tracked-count');
    const volumeEl = document.getElementById('reddit-comment-volume');
    
    try {
        const res = await fetch(`${API_BASE}/social/reddit`);
        if (!res.ok) throw new Error('Reddit fetch failed');
        const data = await res.json();
        
        if (data.is_fallback_data) showSimIndicator(true);

        const trackedCount = (data.tracked_subreddits || []).length;
        const totalVolume = Object.values(data.comment_volume || {}).reduce((a, b) => a + (Number(b) || 0), 0);
        
        trackedEl.textContent = trackedCount;
        volumeEl.textContent = formatNumber(totalVolume);

        const posts = data.trending_posts || [];
        tbody.innerHTML = '';
        
        if (posts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No active Reddit discussions found.</td></tr>';
            return;
        }

        posts.forEach(post => {
            const tr = document.createElement('tr');
            const url = post.url || `https://reddit.com/r/${post.subreddit}/`;
            tr.innerHTML = `
                <td style="font-weight: 600; color: var(--reddit);">r/${post.subreddit}</td>
                <td style="color: var(--text-main); font-weight: 500;">${post.title}</td>
                <td style="color: var(--emerald);"><i class="fa-solid fa-arrow-up"></i> ${formatNumber(post.score)}</td>
                <td style="color: var(--cyan);"><i class="fa-regular fa-comment"></i> ${formatNumber(post.num_comments)}</td>
                <td><a href="${url}" target="_blank" class="source-link"><i class="fa-solid fa-external-link-alt"></i> View</a></td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        console.error('Reddit Load Error:', err);
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state" style="color: var(--rose);">Failed to load Reddit data.</td></tr>';
    }
}

// 2. YouTube Data
async function loadYouTubeData() {
    const gridEl = document.getElementById('youtube-grid');
    const topViralityEl = document.getElementById('youtube-top-virality');
    const avgEngagementEl = document.getElementById('youtube-avg-engagement');
    
    try {
        const res = await fetch(`${API_BASE}/social/youtube?region=US&limit=12`);
        if (!res.ok) throw new Error('YouTube fetch failed');
        const data = await res.json();
        
        if (data.is_fallback_data) showSimIndicator(true);

        const videos = data.videos || [];
        
        const topVirality = videos.length ? Math.max(...videos.map(v => Number(v.virality_score) || 0)) : 0;
        const avgEngagement = videos.length
            ? (videos.reduce((acc, v) => acc + (Number(v.engagement_score) || 0), 0) / videos.length)
            : 0;
            
        topViralityEl.textContent = topVirality.toFixed(2);
        avgEngagementEl.textContent = `${avgEngagement.toFixed(2)}%`;

        gridEl.innerHTML = '';
        if (videos.length === 0) {
            gridEl.innerHTML = '<div class="empty-state">No YouTube trends found.</div>';
            return;
        }

        videos.forEach(video => {
            const card = document.createElement('div');
            card.className = 'yt-card glass';
            const url = video.url || 'https://youtube.com/';
            card.innerHTML = `
                <div class="yt-card-header">
                    <span class="yt-category">${video.category}</span>
                    <a href="${url}" target="_blank" class="yt-link" title="Watch on YouTube"><i class="fa-brands fa-youtube"></i></a>
                </div>
                <h3 class="yt-title">${video.title}</h3>
                <div class="yt-channel">${video.channel || 'YouTube Creator'}</div>
                <div class="yt-metrics">
                    <div class="yt-metric"><i class="fa-solid fa-eye"></i> ${formatNumber(video.view_count)}</div>
                    <div class="yt-metric"><i class="fa-solid fa-thumbs-up"></i> ${formatNumber(video.like_count)}</div>
                    <div class="yt-metric"><i class="fa-solid fa-comment"></i> ${formatNumber(video.comment_count)}</div>
                </div>
                <div class="yt-scores">
                    <span class="score-badge virality">Virality: ${video.virality_score}</span>
                    <span class="score-badge engagement">Eng: ${video.engagement_score}%</span>
                </div>
            `;
            gridEl.appendChild(card);
        });

    } catch (err) {
        console.error('YouTube Load Error:', err);
        gridEl.innerHTML = '<div class="empty-state" style="color: var(--rose);">Failed to load YouTube data.</div>';
    }
}

// 3. News Data
async function loadNewsData() {
    try {
        const res = await fetch(`${API_BASE}/social/news?country=us`);
        if (!res.ok) throw new Error('News fetch failed');
        const data = await res.json();
        
        if (data.is_fallback_data) showSimIndicator(true);
        
        cachedNewsData = data;
        renderNewsGrid();
    } catch (err) {
        console.error('News Load Error:', err);
        const gridEl = document.getElementById('news-grid');
        gridEl.innerHTML = '<div class="empty-state" style="color: var(--rose);">Failed to load News data.</div>';
    }
}

function renderNewsGrid() {
    const gridEl = document.getElementById('news-grid');
    if (!cachedNewsData) return;
    
    const category = document.getElementById('news-category-select').value;
    let articles = [];
    
    if (category === 'breaking') {
        articles = cachedNewsData.breaking_news || [];
    } else {
        articles = (cachedNewsData.category_wise_news || {})[category] || [];
    }
    
    gridEl.innerHTML = '';
    
    if (articles.length === 0) {
        gridEl.innerHTML = '<div class="empty-state">No news found for this category today.</div>';
        return;
    }
    
    articles.forEach(article => {
        const card = document.createElement('div');
        card.className = 'news-card glass';
        const url = article.url || 'https://news.google.com/';
        card.innerHTML = `
            <div class="news-source"><i class="fa-solid fa-rss"></i> ${article.source}</div>
            <h3 class="news-title">${article.title}</h3>
            <a href="${url}" target="_blank" class="news-link-btn">Read Article <i class="fa-solid fa-arrow-right"></i></a>
        `;
        gridEl.appendChild(card);
    });
}

// Sync Trigger
async function handleSocialSync() {
    const btn = document.getElementById('refresh-social-btn');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing...';
    
    // Simulate delay for fetching APIs
    await new Promise(r => setTimeout(r, 1000));
    await initSocialPortal();
    
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Synced';
    btn.style.background = 'linear-gradient(135deg, #00e676 0%, #00b4d8 100%)';
    
    setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = originalText;
        btn.style.background = '';
    }, 2000);
}
