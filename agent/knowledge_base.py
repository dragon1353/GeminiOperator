# agent/knowledge_base.py (引入安全的檔案讀寫機制)

import json
import os
from typing import List, Dict
import threading

# --- vvv 新增執行緒鎖 vvv ---
# 建立一個執行緒鎖，確保同一時間只有一個執行緒可以寫入 JSON 檔案
_db_lock = threading.Lock()
# --- ^^^ 新增結束 ^^^ ---

_KNOWLEDGE_BASE: Dict[str, List[str]] = None

def _get_json_path() -> str:
    """輔助函式：取得 knowledge_base.json 的絕對路徑"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'knowledge_base.json')

def _load_knowledge_base_from_json(force_reload: bool = False) -> Dict[str, List[str]]:
    """
    從 knowledge_base.json 檔案載入知識庫。
    新增 force_reload 參數以強制從檔案重新讀取。
    """
    global _KNOWLEDGE_BASE
    if _KNOWLEDGE_BASE is not None and not force_reload:
        return _KNOWLEDGE_BASE

    # 在讀取檔案時也加上鎖，避免讀取到寫入一半的髒資料
    with _db_lock:
        try:
            json_path = _get_json_path()
            with open(json_path, 'r', encoding='utf-8') as f:
                _KNOWLEDGE_BASE = json.load(f)
            return _KNOWLEDGE_BASE
        except (FileNotFoundError, json.JSONDecodeError):
            _KNOWLEDGE_BASE = {}
            return _KNOWLEDGE_BASE

# --- vvv 重構 add_selector 函式 vvv ---
def add_selector(intent: str, new_selector: str) -> bool:
    """
    【重構版】將一個新的選擇器新增到指定的意圖中，並安全地寫回 JSON 檔案。
    這個版本是執行緒安全的。
    """
    global _KNOWLEDGE_BASE
    
    # 使用鎖來確保整個「讀取-修改-寫入」過程的原子性
    with _db_lock:
        try:
            json_path = _get_json_path()
            # 1. 直接從檔案讀取最新的資料，忽略記憶體快取
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    kb_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                kb_data = {}

            # 2. 執行修改邏輯
            selectors = kb_data.get(intent, [])
            
            if new_selector in selectors:
                print(f"Selector '{new_selector}' already exists for intent '{intent}'. No update needed.")
                return False

            selectors.append(new_selector)
            kb_data[intent] = selectors
            
            # 3. 將更新後的完整資料寫回檔案
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(kb_data, f, indent=2, ensure_ascii=False)
            
            # 4. 清除全域快取，強制下次讀取時從檔案載入新資料
            _KNOWLEDGE_BASE = None
            
            print(f"Successfully added selector '{new_selector}' to intent '{intent}'.")
            return True

        except Exception as e:
            print(f"An unexpected error occurred while updating knowledge base: {e}")
            return False
# --- ^^^ 重構結束 ^^^ ---

def get_selectors(intent: str) -> List[str]:
    """
    根據操作意圖，從知識庫中獲取對應的 CSS 選擇器列表。
    """
    kb = _load_knowledge_base_from_json()
    return kb.get(intent, [])

def get_all_intents() -> List[str]:
    """
    讀取知識庫，並回傳所有意圖 (titles) 的列表。
    """
    kb = _load_knowledge_base_from_json(force_reload=True) # 強制重讀以獲取最新列表
    return list(kb.keys())