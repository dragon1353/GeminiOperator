# agent/browser_tools.py (新增頁面儲存功能)

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time, os
from . import knowledge_base
from urllib.parse import urlparse
from datetime import datetime

driver = None
socketio_instance = None

_LAST_SUCCESSFUL_SELECTORS = {}

def set_socketio(sio):
    global socketio_instance
    socketio_instance = sio

def _log(message):
    if socketio_instance:
        socketio_instance.emit('update_log', {'data': message})

# --- vvv 新增的函式 vvv ---
def save_full_page_content() -> str:
    """
    【全新功能】獲取完整頁面原始碼，儲存至本地檔案，並回傳檔案路徑。
    """
    if driver is None:
        _log("❌ **錯誤：無法儲存頁面，瀏覽器未啟動。**")
        return None
    try:
        page_html = driver.page_source
        
        # 建立儲存資料夾 (如果不存在)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.join(current_dir, 'page_captures')
        os.makedirs(save_dir, exist_ok=True)
        
        # 產生檔案名稱
        hostname = urlparse(driver.current_url).hostname or "local_page"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{hostname}_{timestamp}.html"
        file_path = os.path.join(save_dir, filename)
        
        # 儲存檔案
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(page_html)
            
        _log(f"📄 **頁面快照已儲存至：** `{file_path}`")
        return file_path
        
    except Exception as e:
        _log(f"❌ **錯誤：儲存頁面快照失敗：** {e}")
        return None
# --- ^^^ 新增結束 ^^^ ---

# ... (檔案中其他的函式 _find_element_with_knowledge, verify_selector 等維持不變) ...
def is_browser_alive() -> bool:
    if driver is None:
        return False
    try:
        _ = driver.title
        return True
    except Exception:
        return False

def _find_element_with_knowledge(intent: str):
    """
    【效能優化版】
    1. 優先嘗試域名快取中最後成功的選擇器。
    2. 如果快取失敗或不存在，才遍歷完整知識庫。
    3. 遍歷時使用較短的超時時間，以提升速度。
    4. 成功後，將結果更新回快取。
    """
    if not driver: return None

    # 1. 獲取當前域名
    try:
        current_url = driver.current_url
        hostname = urlparse(current_url).hostname
    except Exception:
        hostname = None # 如果獲取失敗，則不使用快取

    # 2. 優先嘗試快取
    if hostname and hostname in _LAST_SUCCESSFUL_SELECTORS and intent in _LAST_SUCCESSFUL_SELECTORS[hostname]:
        cached_selector = _LAST_SUCCESSFUL_SELECTORS[hostname][intent]
        _log(f"🧠 **快取命中：** 正在為意圖 '{intent}' 優先嘗試策略 `{cached_selector}`")
        try:
            # 使用一個較短的超時來驗證快取
            element = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, cached_selector))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            _log("✅ **快取策略成功！**")
            return element
        except Exception:
            _log(f"⚠️ **快取策略 `{cached_selector}` 已失效。**")
            # 從快取中移除失效的策略
            del _LAST_SUCCESSFUL_SELECTORS[hostname][intent]

    # 3. 如果快取失敗或不存在，遍歷完整知識庫
    selectors = knowledge_base.get_selectors(intent)
    if not selectors:
        _log(f"📚 知識庫中找不到意圖 '{intent}' 的任何策略。")
        return None 
    
    _log(f"📚 知識庫查詢: '{intent}', 正在嘗試所有 {len(selectors)} 個可用策略。")
    for selector in selectors:
        try:
            # 【參數調整】將超時從 5 秒縮短為 2 秒，大幅減少每次嘗試的延遲
            element = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)

            # 4. 成功後，更新快取
            if hostname:
                if hostname not in _LAST_SUCCESSFUL_SELECTORS:
                    _LAST_SUCCESSFUL_SELECTORS[hostname] = {}
                _LAST_SUCCESSFUL_SELECTORS[hostname][intent] = selector
                _log(f"✍️ **快取已更新：** 意圖 '{intent}' -> `{selector}`")
            
            return element
        except Exception:
            continue
            
    return None

def verify_selector(selector: str) -> bool:
    if driver is None: return False
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        return True
    except TimeoutException:
        return False
    except Exception as e:
        _log(f"❌ 驗證選擇器時發生錯誤: {e}")
        return False

def perform_search(text: str, search_box_intent: str = "搜尋框", search_button_intent: str = "搜尋按鈕") -> str:
    if driver is None: return "錯誤：瀏覽器未啟動。"
    
    _log(f"🔍 開始執行搜尋: '{text}'")
    initial_url = driver.current_url
    
    search_box = _find_element_with_knowledge(search_box_intent)
    if not search_box:
        # 【修正】確保使用全形冒號
        return f"操作失敗：找不到意圖為 '{search_box_intent}' 的輸入框。"
    
    try:
        search_box.clear()
        search_box.send_keys(text)
        _log(f"✅ 已在 '{search_box_intent}' 中輸入文字: '{text}'")
    except Exception as e:
        return f"在 '{search_box_intent}' 輸入文字時失敗: {e}"

    search_button = _find_element_with_knowledge(search_button_intent)
    if search_button:
        try:
            driver.execute_script("arguments[0].click();", search_button)
            _log(f"✅ 已成功點擊 '{search_button_intent}'。")
        except Exception as e:
            _log(f"⚠️ 點擊 '{search_button_intent}' 失敗: {e}。嘗試使用 ENTER。")
            try:
                search_box.send_keys(Keys.RETURN)
            except Exception as e_enter:
                 return f"操作失敗：點擊按鈕及按下 ENTER 均失敗。"
    else:
        _log(f"⚠️ 未找到 '{search_button_intent}'，直接在搜尋框上按下 ENTER。")
        try:
            search_box.send_keys(Keys.RETURN)
        except Exception as e:
            return f"在搜尋框上按下 ENTER 鍵時失敗: {e}"

    time.sleep(3)
    final_url = driver.current_url
    if initial_url == final_url:
        # 【修正】確保使用全形冒號
        return f"操作失敗：搜尋動作已執行，但頁面沒有跳轉。"

    return f"搜尋 '{text}' 的操作已成功完成。"


def click_element(intent: str) -> str:
    if driver is None: return "錯誤：瀏覽器未啟動。"
    _log(f"🖱️ 嘗試根據意圖點擊元素: '{intent}'")
    element_to_click = _find_element_with_knowledge(intent)
    if not element_to_click:
        # 【修正】確保使用全形冒號
        return f"操作失敗：找不到意圖為 '{intent}' 的可點擊元素。"
    try:
        driver.execute_script("arguments[0].click();", element_to_click)
        _log(f"✅ 已成功點擊意圖為 '{intent}' 的元素。")
        time.sleep(3)
        return f"已成功點擊 '{intent}'。"
    except Exception as e:
        _log(f"⚠️ 點擊意圖為 '{intent}' 的元素時失敗: {e}")
        return f"點擊意圖為 '{intent}' 的元素時失敗: {e}"

def navigate_to_url(url: str) -> str:
    global driver
    if driver is None:
        try:
            options = Options(); options.add_argument("--start-maximized")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            service = Service(ChromeDriverManager().install()); driver = webdriver.Chrome(service=service, options=options)
        except Exception as e: return f"瀏覽器初始化失敗: {e}"
    
    try:
        driver.get(url); time.sleep(3)
        return f"已成功導航至: {url}"
    except Exception as e: return f"導航失敗: {e}"

def get_page_content() -> str:
    if driver is None: return "錯誤：瀏覽器未啟動。"
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        return driver.page_source
    except Exception as e: return f"獲取頁面內容失敗: {e}"

def get_current_url() -> str:
    if driver is None: return "錯誤：瀏覽器未啟動。"
    try:
        return driver.current_url
    except Exception as e:
        return f"獲取當前網址失敗: {e}"

def take_screenshot(filename: str = "screenshot.png") -> str:
    if driver is None: return "錯誤：瀏覽器未啟動。"
    try:
        save_path = os.path.join(os.getcwd(), filename)
        driver.save_screenshot(save_path)
        return f"已截圖至 {save_path}"
    except Exception as e: return f"截圖失敗: {e}"