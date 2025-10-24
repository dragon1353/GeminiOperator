# agent/agent_core.py (情境感知 AI 最終版)

import google.generativeai as genai
from . import browser_tools
from . import knowledge_base
from . import knowledge_builder
import time
import json
import re
from typing import Tuple

def parse_tool_call(call_string: str) -> Tuple[str, dict]:
    try:
        match = re.match(r"(\w+)\s*\((.*)\)", call_string)
        if not match: return None, {}
        tool_name = match.group(1)
        args_str = match.group(2).strip()
        if not args_str: return tool_name, {}
        tool_args = eval(f"dict({args_str})", {"__builtins__": None}, {"dict": dict})
        return tool_name, tool_args
    except Exception as e:
        print(f"無法解析工具呼叫 '{call_string}': {e}")
        return None, {}

def run_agent_task_internal(socketio, api_key: str, user_task: str, attempt=1):
    if attempt > 3:
        socketio.emit('update_log', {'data': '❌ **已達最大重試次數，任務中止。**'})
        return

    # ================= STAGE 1: PLANNING =================
    socketio.emit('update_log', {'data': '🤖 **AI 策略家啟動：正在進行情境分析與意圖推斷...**'})
    planning_model = genai.GenerativeModel('gemini-2.5-pro')

    # --- vvv 最終版的「策略家」思考框架 Prompt vvv ---
    planning_prompt = (
        "你是一位頂尖的通用網頁自動化策略家。你的核心能力是「情境感知」與「意圖推斷」。你的任務是將使用者指令分解為一個精確、高效、且絕對符合當前情境的執行計畫。\n\n"
        "## 核心思考流程 (極度重要):\n"
        "1.  **分析情境**: 首先，判斷任務的當前階段。我是在一個需要「搜尋」的入口頁面，還是在一個需要「點擊導航」的內容頁面？\n"
        "2.  **推斷意圖**: 根據使用者指令的動詞和名詞，推斷出最核心的操作意圖。\n"
        "3.  **選擇正確工具**: 根據情境和意圖，選擇最合適的工具。**這是你最重要的職責**。\n\n"
        "## 工具選擇的黃金法則:\n"
        "   - **`perform_search(text: str)`**: 「只在」使用者明確表示要「搜尋」、「查詢」，或者當前頁面是搜尋引擎首頁時使用。例如：`'到 PChome 網站搜尋「筆電」'`。\n"
        "   - **`click_element(intent: str)`**: 「在所有其他情況下」都應優先使用此工具。這是最常用的工具。你需要根據使用者指令，動態創造一個合理的意圖名稱。例如：\n"
        "     - 指令: `'點擊國際分類'` -> `click_element(intent='國際分類連結')`\n"
        "     - 指令: `'找到關於川普的第一條新聞'` -> `click_element(intent='川普相關新聞')`\n"
        "     - 指令: `'點進那個筆電的商品頁'` -> `click_element(intent='項目連結')` (這是一個通用意圖)\n\n"
        "## 輸出格式要求:\n"
        "你「必須」且「只能」以一個 Python 的 JSON 列表 (list of strings) 格式回傳計畫。\n"
        "**嚴格禁止**在回傳的 JSON 中添加任何 Markdown 標籤、註解或解釋性文字。\n\n"
        "## 範例分析:\n"
        "使用者任務: `'開啟 Google 新聞，點擊國際分類，然後找到關於川普的第一條新聞'`\n"
        "你的思考過程:\n"
        "1.  `'開啟 Google 新聞'` -> 明確的導航指令 -> `Maps_to_url`\n"
        "2.  `'點擊國際分類'` -> 我已經在新聞網站內，這是一個內容導航 -> `click_element`，意圖是 `'國際分類'`\n"
        "3.  `'找到關於川普的第一條新聞'` -> 我已經在國際分類頁，這是在頁面上尋找一個連結，而不是使用搜尋框 -> `click_element`，意圖是 `'川普相關新聞'`\n"
        "你的最終回傳:\n"
        "[\n"
        "  \"navigate_to_url(url='https://news.google.com/')\",\n"
        "  \"click_element(intent='國際分類')\",\n"
        "  \"click_element(intent='川普相關新聞')\"\n"
        "]\n\n"
        "---\n\n"
        f"**使用者總任務**: '{user_task}'\n\n"
        "請開始你嚴謹的策略規劃，並生成一個完美符合情境的 JSON 執行計畫:"
    )
    # --- ^^^ Prompt 修改結束 ^^^ ---
    
    response = planning_model.generate_content(planning_prompt)
    plan_text = response.text

    try:
        start_index = plan_text.find('[')
        end_index = plan_text.rfind(']')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_string = plan_text[start_index : end_index + 1]
            action_plan = json.loads(json_string)
        else:
            raise ValueError("在 AI 回傳中找不到有效的 JSON 列表。")

    except Exception as e:
        socketio.emit('update_log', {'data': f'❌ **AI 生成計畫失敗，無法解析回傳內容。**\n<pre>錯誤: {e}</pre>\n<pre>AI回傳: {plan_text}</pre>'})
        return

    plan_html = json.dumps(action_plan, indent=2, ensure_ascii=False)
    socketio.emit('update_log', {'data': f'✅ **AI 已生成計畫:**\n<pre>{plan_html}</pre>'})
    time.sleep(2)

    # ... (STAGE 2: EXECUTION & SELF-HEALING 的程式碼維持不變) ...
    for i, step in enumerate(action_plan):
        socketio.emit('update_log', {'data': f'▶️ **執行步驟 {i+1}/{len(action_plan)}:** `{step}`'})
        tool_name, tool_args = parse_tool_call(step)

        if not tool_name: continue
        tool_function = getattr(browser_tools, tool_name, None)
        if not tool_function: continue

        try:
            result = tool_function(**tool_args)

            if "操作失敗：" in result:
                failed_intent = None
                if tool_name == 'perform_search':
                    if "輸入框" in result:
                        failed_intent = "搜尋框"
                    elif "頁面沒有跳轉" in result:
                        failed_intent = "搜尋按鈕"
                elif tool_name == 'click_element':
                    failed_intent = tool_args.get('intent')

                if failed_intent:
                    socketio.emit('update_log', {'data': f'⚠️ **操作失敗，意圖「{failed_intent}」。正在檢查瀏覽器狀態...**'})

                    if not browser_tools.is_browser_alive():
                        socketio.emit('update_log', {'data': '🚨 **偵測到瀏覽器已無回應或已關閉！**'})
                        socketio.emit('update_log', {'data': '🔄 **正在嘗試重置瀏覽器並從頭重新執行任務...**'})
                        browser_tools.driver = None
                        run_agent_task_internal(socketio, api_key, user_task, attempt + 1)
                        return

                    socketio.emit('update_log', {'data': '✅ **瀏覽器狀態正常。開始執行自我修復流程...**'})

                    page_html = browser_tools.get_page_content()
                    if "錯誤：" in page_html or len(page_html) < 200:
                        socketio.emit('update_log', {'data': '❌ **無法獲取頁面內容，中止擴增流程。**'})
                        continue

                    analysis_prompt = (
                        "你是一位 CSS 選擇器專家，專門為自動化測試撰寫最穩定、最可靠的選擇器。\n"
                        "我的自動化腳本在嘗試尋找一個重要元素時失敗了。\n\n"
                        "## 核心原則:\n"
                        "1.  **優先級**: `id` > `aria-label`, `role` > 描述性 `class` > 結構路徑。\n"
                        "2.  **避免脆弱性**: 「絕對不要」使用由程式碼自動生成的、沒有語意、看起來像亂碼的 class 名稱 (例如: `jss31`, `css-1dbjc4n`, `ekqMKf`)。\n\n"
                        f"我的目標意圖是：「{failed_intent}」。\n"
                        f"使用者的原始任務是：「{user_task}」。\n"
                        "請仔細分析以下 HTML 原始碼，並找出一個最能夠精準代表上述意圖的、最穩定的 CSS 選擇器。\n"
                        f"--- HTML 內容 ---\n{page_html[:7000]}...\n--- HTML 內容結束 ---\n"
                        "你的回覆「只能」包含一個 CSS 選擇器字串，不要有任何其他文字、解釋或程式碼標籤。"
                    )

                    socketio.emit('update_log', {'data': '🤖 **AI 正在分析頁面結構以尋找新的【穩定】元素策略...**'})
                    analysis_model = genai.GenerativeModel('gemini-2.5-pro')
                    analysis_response = analysis_model.generate_content(analysis_prompt)
                    suggested_selector = analysis_response.text.strip().replace("`", "")

                    if not suggested_selector or len(suggested_selector) < 2:
                        socketio.emit('update_log', {'data': '❌ **AI 未能生成有效的選擇器，跳過此步驟。**'})
                        continue

                    socketio.emit('update_log', {'data': f'🧠 **AI 建議使用新的選擇器:** `{suggested_selector}`'})

                    is_valid = browser_tools.verify_selector(suggested_selector)

                    if is_valid:
                        socketio.emit('update_log', {'data': '✅ **驗證成功！選擇器可在頁面上找到元素。**'})
                        
                        add_result = knowledge_base.add_selector(failed_intent, suggested_selector)
                        
                        if add_result:
                            socketio.emit('update_log', {'data': f'✍️ **知識庫已成功擴增意圖「{failed_intent}」！準備重新規劃與執行任務...**'})
                            
                            browser_tools.driver.quit()
                            browser_tools.driver = None
                            run_agent_task_internal(socketio, api_key, user_task, attempt + 1)
                            return
                        else:
                            socketio.emit('update_log', {'data': '⚠️ **寫入知識庫失敗或選擇器已存在，任務中止以避免無限循環。**'})
                    else:
                        socketio.emit('update_log', {'data': f'❌ **驗證失敗！AI 建議的選擇器 `{suggested_selector}` 無法在頁面上找到元素。**'})

                        file_path = browser_tools.save_full_page_content()
                        if not file_path:
                            return False
                        
                        learned_something_new = knowledge_builder.learn_from_current_page(socketio)

                        if learned_something_new:
                            socketio.emit('update_log', {'data': '🎓 **學習完畢！準備從頭開始，以全新的知識重新執行任務...**'})
                        else:
                            socketio.emit('update_log', {'data': '🤔 **深度學習未發現新知識。將再次嘗試重新執行任務...**'})

                        browser_tools.driver.quit()
                        browser_tools.driver = None
                        run_agent_task_internal(socketio, api_key, user_task, attempt + 1)
                        return

                    socketio.emit('update_log', {'data': '❌ **因操作失敗，目前執行計畫已中止。**'})
                    return

            socketio.emit('update_log', {'data': f'✔️ <strong>步驟 {i+1} 結果:</strong> {result}'})

        except Exception as e:
            socketio.emit('update_log', {'data': f'❌ <strong>步驟 {i+1} 執行失敗:</strong> {e}'})
            break

        time.sleep(1)

def run_agent_task(socketio, api_key: str, user_task: str):
    try:
        genai.configure(api_key=api_key)
        browser_tools.set_socketio(socketio)
        run_agent_task_internal(socketio, api_key, user_task)
    except Exception as e:
        socketio.emit('update_log', {'data': f'❌ **發生嚴重錯誤: {e}**'})
        import traceback
        traceback.print_exc()
    finally:
        socketio.emit('task_complete', {'data': '✅ **任務流程結束。瀏覽器將保持開啟以供檢視。**'})