# agent/knowledge_builder.py (導師-學徒 最終版)

import google.generativeai as genai
from . import browser_tools
from . import knowledge_base
import json

def _consolidate_knowledge(socketio, new_findings: dict) -> dict:
    """
    【AI 導師】
    審查「學徒」提交的新發現，進行智慧的語意聚類、比對和決策。
    """
    existing_intents = knowledge_base.get_all_intents()
    
    if not existing_intents:
        socketio.emit('update_log', {'data': '🧠 **知識庫為空，跳過審查步驟，直接採用學徒的新發現。**'})
        return new_findings

    consolidation_model = genai.GenerativeModel('gemini-2.5-pro')
    
    # --- vvv 最終版的「導師」思考框架 Prompt vvv ---
    consolidation_prompt = (
        "你是一位經驗豐富的 AI 知識庫總編輯，負責審查由初級 AI (學徒) 提交的新意圖（intent）。你的職責是確保知識庫的精煉、無重複且高度結構化。\n\n"
        "【現有知識庫分類】:\n"
        f"`{', '.join(existing_intents)}`\n\n"
        "【學徒提交的新發現報告】:\n"
        f"```json\n{json.dumps(new_findings, indent=2, ensure_ascii=False)}\n```\n\n"
        "## 你的審查流程與決策原則 (極度重要):\n"
        "1.  **語意聚類**: 首先，審視【新發現報告】中的所有意圖，將語意上完全相同的概念（例如 `'搜尋列'`, `'搜尋新聞'`）在內部先合併，並選出一個最具代表性的名稱（例如 `'搜尋框'`）。\n"
        "2.  **比對與合併**: 拿著聚類後的每一個概念，去和【現有知識庫分類】進行比對。如果發現語意匹配的分類（例如，新發現的 `'登入'` 匹配到現有的 `'登入按鈕'`），就必須將其 CSS 選擇器合併到現有的分類中。**這是你的首要任務**。\n"
        "3.  **謹慎創建**: 只有當一個新概念，例如 `'即時客服聊天按鈕'`，在現有分類中完全找不到任何相關概念時，你才被授權為它「創建」一個新的分類。\n\n"
        "## 輸出格式要求:\n"
        "請回傳一個經過你深思熟慮後，最終整合完畢的 JSON 物件。這個 JSON 的鍵(key)必須是整理後的最終意圖名稱。\n"
        "**嚴格禁止**回傳任何 Markdown 標籤 (```json) 或額外解釋。\n\n"
        "請開始你嚴謹的審查與整理工作，並回傳最終的 JSON 物件："
    )
    # --- ^^^ Prompt 修改結束 ^^^ ---

    socketio.emit('update_log', {'data': '🤖 **AI 導師啟動：正在對學徒的發現進行語意審查與整合...**'})
    response = consolidation_model.generate_content(consolidation_prompt)
    
    try:
        raw_text = response.text
        start_index = raw_text.find('{')
        end_index = raw_text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_string = raw_text[start_index : end_index + 1]
            consolidated_knowledge = json.loads(json_string)
            socketio.emit('update_log', {'data': '🧠 **知識審查完畢！**'})
            return consolidated_knowledge
        else:
            raise ValueError("AI 導師回傳的內容中找不到有效的 JSON 物件。")
    except Exception as e:
        socketio.emit('update_log', {'data': f'❌ **錯誤：AI 知識審查失敗，將跳過此步驟。**\n<pre>錯誤細節: {e}</pre>'})
        return new_findings


def _analyze_and_update(socketio, file_path: str):
    analysis_model = genai.GenerativeModel('gemini-2.5-pro')

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            full_page_html = f.read()
    except Exception as e:
        socketio.emit('update_log', {'data': f'❌ **錯誤：無法讀取已儲存的頁面快照檔案：** {e}'})
        return 0
    
    # --- vvv 注入「穩定選擇器」思想的 Prompt vvv ---
    analysis_prompt = (
        "你是一位頂尖的前端工程師，專門為自動化測試撰寫最穩定、最可靠的 CSS 選擇器。\n\n"
        "## 你的核心原則:\n"
        "1.  **穩定性優先**: 尋找那些最不可能改變的屬性來定位元素。優先順序是：獨特的 `id` > 描述功能的 `role` 或 `aria-label` > 語意清晰的 `class` 名稱 > 穩定的父子結構關係。\n"
        "2.  **避免脆弱性**: 「絕對不要」使用由程式碼自動生成的、沒有語意、看起來像亂碼的 class 名稱 (例如: `jss31`, `css-1dbjc4n`, `ekqMKf`)。這些是導致不穩定的主要原因。\n"
        "3.  **人類可讀**: 盡可能創造人類可讀的意圖名稱，例如從 `aria-label` 或元素的文字內容中提煉。\n\n"
        "## 你的任務:\n"
        "全面分析我提供的 HTML，找出所有具備明確意圖的互動元素，並為它們創造一個初步的意圖名稱和一個極度穩定的 CSS 選擇器。\n\n"
        "## 輸出格式要求 (極度重要):\n"
        "回傳一個合法的 JSON 物件。鍵(key)是你初步創造的意圖名稱，值(value)是只包含「一個」你認為最穩定的 CSS 選擇器的列表。\n"
        "**嚴格禁止**回傳任何 Markdown 標籤或額外解釋。\n\n"
        f"## 以下是待分析的完整 HTML:\n{full_page_html}\n\n"
        "請開始分析，並回傳你所有發現的 JSON 物件："
    )
    # --- ^^^ Prompt 修改結束 ^^^ ---
    
    socketio.emit('update_log', {'data': '🤖 **AI 學徒啟動：正在分析完整頁面，尋找穩定元素特徵...**'})
    response = analysis_model.generate_content(analysis_prompt)
    
    try:
        raw_text = response.text
        start_index = raw_text.find('{')
        end_index = raw_text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_string = raw_text[start_index : end_index + 1]
            new_findings = json.loads(json_string)
            socketio.emit('update_log', {'data': f'🧠 **AI 學徒探索完成，共提交 {len(new_findings)} 項新發現供導師審查。**'})
        else:
            raise ValueError("AI 學徒回傳的內容中找不到有效的 JSON 物件。")
    except Exception as e:
        socketio.emit('update_log', {'data': f'❌ **錯誤：AI 學徒回傳的 JSON 格式解析失敗。**\n<pre>錯誤細節: {e}</pre>'})
        return 0

    final_knowledge_to_add = _consolidate_knowledge(socketio, new_findings)

    added_count = 0
    for intent, selectors in final_knowledge_to_add.items():
        if isinstance(selectors, list) and selectors:
            for selector in selectors:
                if knowledge_base.add_selector(intent, selector):
                    socketio.emit('update_log', {'data': f'✍️ **知識庫更新：** [{intent}] -> `{selector}`'})
                    added_count += 1
    return added_count

# ... (檔案中其他的函式 build_knowledge_from_url 和 learn_from_current_page 維持不變) ...
def build_knowledge_from_url(socketio, url: str):
    """【手動觸發】從一個給定的 URL 自動分析並擴充知識庫。"""
    try:
        socketio.emit('update_log', {'data': f'🚀 **開始擴充知識庫，目標網址：** {url}'})
        
        socketio.emit('update_log', {'data': '🔗 正在啟動瀏覽器並前往目標網址...'})
        nav_result = browser_tools.navigate_to_url(url)
        if "失敗" in nav_result:
            socketio.emit('update_log', {'data': f'❌ **錯誤：** 無法導航至 {url}。 {nav_result}'})
            return

        file_path = browser_tools.save_full_page_content()
        if not file_path:
            return

        added_count = _analyze_and_update(socketio, file_path)
        
        if added_count > 0:
            socketio.emit('update_log', {'data': f'✅ **知識庫擴充成功！** 共更新了 {added_count} 條元素策略。'})
        else:
            socketio.emit('update_log', {'data': '🤔 **知識庫未變更。** AI 分析的元素可能已存在於知識庫中或未找到可擴充項目。'})

    except Exception as e:
        socketio.emit('update_log', {'data': f'❌ **擴充知識庫時發生嚴重錯誤：** {e}'})
    finally:
        if browser_tools.driver:
            browser_tools.driver.quit()
            browser_tools.driver = None
        socketio.emit('task_complete', {'data': '✨ **知識庫擴充流程結束。**'})

def learn_from_current_page(socketio):
    """
    【自動觸發】從瀏覽器當前頁面學習，不關閉瀏覽器。
    """
    try:
        file_path = browser_tools.save_full_page_content()
        if not file_path:
            return False
        
        added_count = _analyze_and_update(socketio, file_path)

        if added_count > 0:
            socketio.emit('update_log', {'data': f'✅ **自動學習成功！** 更新了 {added_count} 條策略。'})
            return True
        else:
            socketio.emit('update_log', {'data': '🤔 **自動學習未發現新知識。**'})
            return False
    except Exception as e:
        socketio.emit('update_log', {'data': f'❌ **自動學習時發生嚴重錯誤：** {e}'})
        return False