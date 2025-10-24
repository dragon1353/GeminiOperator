# app.py (簡化任務提交流程版)
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import Flask, render_template
from flask_socketio import SocketIO
from dotenv import load_dotenv
from agent.agent_core import run_agent_task
from agent.knowledge_builder import build_knowledge_from_url

load_dotenv()
app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

@app.route('/')
def index():
    return render_template('index.html')

def get_api_key():
    """輔助函式：讀取並驗證 API Key"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        socketio.emit('update_log', {'data': '❌ 錯誤：後端找不到 GOOGLE_API_KEY。請檢查 .env 檔案。'})
        return None
    return api_key

@socketio.on('submit_task')
def handle_task(json_data):
    """監聽自動化任務"""
    print("\n--- [偵錯] 收到前端 'submit_task' 請求 ---")
    # 不再接收 user_url
    user_task = json_data.get('task')
    print(f"[偵錯] 收到的任務內容: {user_task}")

    if user_task:
        api_key = get_api_key()
        if api_key:
            # 呼叫 run_agent_task 時不再傳遞 user_url
            socketio.start_background_task(run_agent_task, socketio, api_key, user_task)
    else:
        print("[偵錯] 錯誤：任務內容為空。")

@socketio.on('expand_knowledge_base')
def handle_knowledge_expansion(json_data):
    """監聽知識庫擴充任務 (維持不變)"""
    print("\n--- [偵錯] 收到前端 'expand_knowledge_base' 請求 ---")
    url = json_data.get('url')
    print(f"[偵錯] 收到要學習的網址: {url}")

    if url:
        api_key = get_api_key()
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            socketio.start_background_task(build_knowledge_from_url, socketio, url)
    else:
        print("[偵錯] 錯誤：學習網址為空。")

if __name__ == '__main__':
    print("伺服器啟動於 http://127.0.0.1:5000")
    socketio.run(app, debug=True)