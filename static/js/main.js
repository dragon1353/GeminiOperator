// static/js/main.js (簡化任務提交流程版)

document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // 任務區塊的元素 (移除 urlInput)
    const taskInput = document.getElementById('taskInput');
    const submitBtn = document.getElementById('submitBtn');
    
    // 知識庫區塊的元素
    const knowledgeUrlInput = document.getElementById('knowledgeUrlInput');
    const expandBtn = document.getElementById('expandBtn');

    const logDiv = document.getElementById('log');

    // --- 通用函式 ---
    function disableAllInputs() {
        submitBtn.disabled = true;
        taskInput.disabled = true;
        expandBtn.disabled = true;
        knowledgeUrlInput.disabled = true;
    }

    function enableAllInputs() {
        submitBtn.disabled = false;
        taskInput.disabled = false;
        expandBtn.disabled = false;
        knowledgeUrlInput.disabled = false;
    }

    // --- 事件監聽 ---
    socket.on('connect', () => {
        console.log('成功連接到後端 WebSocket 伺服器！ ID:', socket.id);
    });

    // 1. 執行自動化任務 (簡化)
    function startTask() {
        const task = taskInput.value.trim();
        
        if (task) {
            logDiv.innerHTML = `<p><strong>任務開始：</strong> ${escapeHtml(task)}</p>`;
            logDiv.innerHTML += `<p>🤖 AI 知識大腦正在進行深度思考與規劃...</p>`;
            // 只發送 task，不再發送 url
            socket.emit('submit_task', { task: task });
            disableAllInputs();
        }
    }

    // 2. 擴充知識庫 (維持不變)
    function expandKnowledge() {
        const knowledgeUrl = knowledgeUrlInput.value.trim();
        if (knowledgeUrl) {
            logDiv.innerHTML = `<p><strong>知識庫擴充任務開始...</strong></p>`;
            socket.emit('expand_knowledge_base', { url: knowledgeUrl });
            disableAllInputs();
        } else {
            alert("請輸入要學習的網址！");
        }
    }

    // 綁定事件
    submitBtn.addEventListener('click', startTask);
    expandBtn.addEventListener('click', expandKnowledge);
    
    taskInput.addEventListener('keydown', (event) => { if (event.key === 'Enter') submitBtn.click(); });
    knowledgeUrlInput.addEventListener('keydown', (event) => { if (event.key === 'Enter') expandBtn.click(); });

    // --- Socket.IO 監聽器 ---
    socket.on('update_log', (msg) => {
        const p = document.createElement('p');
        p.innerHTML = msg.data;  
        logDiv.appendChild(p);
        logDiv.scrollTop = logDiv.scrollHeight;
    });

    socket.on('task_complete', (msg) => {
        const p = document.createElement('p');
        p.innerHTML = `<strong>${escapeHtml(msg.data)}</strong>`;
        p.style.color = 'green';
        p.style.fontWeight = 'bold';
        logDiv.appendChild(p);
        logDiv.scrollTop = logDiv.scrollHeight;
        enableAllInputs();
    });
    
    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
});