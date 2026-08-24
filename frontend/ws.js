// WebSocket Logic for Real-Time Updates

const WS_URL = 'ws://127.0.0.1:8000/api/ws';
let ws;

function initWebSocket() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log("Connected to Real-Time Updates via WebSocket.");
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("WebSocket Event:", data.event, data);

        if (data.event === "pipeline_started") {
            showToast("Pipeline Run Started...", "info");
        } else if (data.event === "pipeline_completed") {
            showToast("Pipeline Run Completed! Refreshing data...", "success");
            // Trigger global refresh depending on which page we are on
            if (typeof initDashboard === "function") initDashboard();
            if (typeof initSciencePortal === "function") initSciencePortal();
            if (typeof initSocialPortal === "function") initSocialPortal();
        } else if (data.event === "pipeline_error") {
            showToast("Pipeline Error: " + data.error, "error");
        }
    };

    ws.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 5s...");
        setTimeout(initWebSocket, 5000);
    };
}

function showToast(message, type="info") {
    let toast = document.getElementById('ws-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'ws-toast';
        document.body.appendChild(toast);
        
        // Add basic styles for the toast
        const style = document.createElement('style');
        style.innerHTML = `
            #ws-toast {
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 15px 25px;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                z-index: 9999;
                opacity: 0;
                transition: opacity 0.3s, transform 0.3s;
                transform: translateY(20px);
                pointer-events: none;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            }
            #ws-toast.show {
                opacity: 1;
                transform: translateY(0);
            }
            #ws-toast.info { background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%); }
            #ws-toast.success { background: linear-gradient(135deg, #00e676 0%, #00c853 100%); }
            #ws-toast.error { background: linear-gradient(135deg, #ff5252 0%, #d50000 100%); }
        `;
        document.head.appendChild(style);
    }
    
    toast.className = type;
    toast.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
});
