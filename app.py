import streamlit as st
import json
import os
import re
import urllib.parse
from PIL import Image

# Set up page config
st.set_page_config(
    page_title="人物誌設計師 Persona Designer | AI 品牌行銷工具",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

# Helper: Clean Markdown Code Fences from JSON Strings
def clean_json_string(text):
    if not text:
        return ""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

# Initialize Session State
session_vars = {
    "step": 1,
    "api_key": "",
    "api_key_valid": False,
    "model_name": "gemini-2.0-flash",
    "available_models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-flash", "gemini-pro"],
    "brand_name": "",
    "brand_desc": "",
    "audience_desc": "",
    "audience_pain": "",
    "num_personas": 2,
    "focus_preference": "自動分配特徵（多元化均衡）",
    "personas": None,
    "suggested_audiences": None,
    "api_error": None
}

for var, default in session_vars.items():
    if var not in st.session_state:
        st.session_state[var] = default

# Helper: Initialize Gemini Client
def get_gemini_client(api_key):
    try:
        from google import genai
        clean_key = api_key.strip().strip("'").strip('"')
        return genai.Client(api_key=clean_key)
    except Exception as e:
        st.session_state.api_error = f"載入 Google GenAI SDK 失敗: {str(e)}"
        return None

# Helper: Validate API Key with Multi-Model Fallback
def validate_api_key(api_key):
    if not api_key:
        return False
    clean_key = api_key.strip().strip("'").strip('"')
    if not clean_key:
        st.session_state.api_error = "金鑰不可為空白或全空格"
        return False
        
    client = get_gemini_client(clean_key)
    if not client:
        return False
        
    # List of universal models to test in priority order
    test_models = [
        st.session_state.model_name,
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-flash"
    ]
    
    # Remove duplicates preserving order
    unique_test_models = []
    for m in test_models:
        if m not in unique_test_models:
            unique_test_models.append(m)
            
    last_err = None
    for model in unique_test_models:
        try:
            client.models.generate_content(
                model=model,
                contents="PING"
            )
            st.session_state.model_name = model
            st.session_state.api_error = None
            return True
        except Exception as e:
            last_err = e
            continue
            
    # If all test models fail, format a helpful error message
    err_str = str(last_err)
    if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
        st.session_state.api_error = "API Key 無效，請檢查是否複製完整或包含多餘字元。"
    elif "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
        st.session_state.api_error = "此 API Key 配額已滿或觸發 Rate Limit，請稍後重試。"
    else:
        st.session_state.api_error = f"驗證失敗: {err_str}"
    return False

# Header Component
st.markdown("<h1 class='main-title'>👤 人物誌設計師 Persona Designer</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>專為行銷人與 AI 新手打造的視覺化人物誌生成工具。按部就班，打造精準客群畫像！</p>", unsafe_allow_html=True)

# --- SIDEBAR: API KEY & SETTINGS (BYOK) ---
with st.sidebar:
    st.markdown("### 🔑 金鑰與設定 (BYOK)")
    
    # API Key Input
    api_key_input = st.text_input(
        "輸入您的 Google Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        help="此 Key 僅儲存於您當前的瀏覽器會話中，絕不傳送到第三方伺服器。"
    )
    
    # Validate API Key if changed
    clean_input = api_key_input.strip().strip("'").strip('"')
    if clean_input != st.session_state.api_key.strip():
        st.session_state.api_key = clean_input
        st.session_state.api_error = None
        if clean_input:
            with st.spinner("驗證金鑰中..."):
                is_valid = validate_api_key(clean_input)
                st.session_state.api_key_valid = is_valid
                if is_valid:
                    st.success("✅ 金鑰驗證成功！")
                else:
                    st.error("❌ 金鑰驗證失敗，請檢查輸入。")
        else:
            st.session_state.api_key_valid = False

    # Model Selection
    model_options = st.session_state.available_models
    curr_index = model_options.index(st.session_state.model_name) if st.session_state.model_name in model_options else 0
    selected_model = st.selectbox(
        "選擇 AI 模型版本 (已啟用動態備援機制)",
        options=model_options,
        index=curr_index,
        help="預設使用相容性最高、最穩定的模型。若遇模型限制會自動升降級。"
    )
    st.session_state.model_name = selected_model

    # Status Display
    if st.session_state.api_key_valid:
        st.markdown("<div style='color:#10b981; font-weight:bold; margin-bottom:15px;'>● 服務狀態：已啟用 (Active)</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#ef4444; font-weight:bold; margin-bottom:15px;'>● 服務狀態：未啟用 (Key Required)</div>", unsafe_allow_html=True)
        if st.session_state.api_error:
            st.markdown(f"<div style='background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.4); border-radius:8px; padding:10px; font-size:0.85rem; color:#fca5a5; margin-bottom:15px;'><b>詳細原因：</b><br>{st.session_state.api_error}</div>", unsafe_allow_html=True)

    # Guide Accordion
    with st.expander("❓ 如何取得免費的 API 金鑰？"):
        st.markdown(
            """
            1. 前往 👉 [Google AI Studio](https://aistudio.google.com/)。
            2. 使用您的 **Google 帳號** 登入。
            3. 點選左上角的 **"Get API Key"** 按鈕。
            4. 點選 **"Create API Key"**，並選擇您的專案。
            5. **複製** 產生的 API Key，並貼到上方輸入框中。
            
            *註：請確保貼上時無多餘空格。個人免費配額即可完全免費使用！*
            """
        )
        
    st.markdown("---")
    st.caption("人物誌設計師 v1.2.1 | 增強型驗證版")

# --- CHECK FOR API KEY ON MAIN SCREEN ---
if not st.session_state.api_key_valid:
    st.markdown(
        """
        <div class="glass-card">
            <h3 style="color:#a78bfa; margin-top:0;">👋 歡迎使用人物誌設計師！</h3>
            <p>在開始規劃您的行銷人物誌之前，我們需要您提供自己的 <b>Google Gemini API Key</b>。這樣我們才能召喚 AI 助理為您服務！</p>
            <p>請在<b>左側選單</b>中輸入您的金鑰。如果您還沒有金鑰，可以點選左側下方摺疊選單中的指引前往免費申請。</p>
            <div style="background:rgba(236,72,153,0.1); border-radius:10px; padding:15px; border:1px solid rgba(236,72,153,0.3); margin-top:15px;">
                <b>🔒 隱私與安全保障：</b><br>
                本網頁是一個純前端/本地運行的 Streamlit 應用程式。您的 API 金鑰僅會存存在您的網頁會話中，直接發送給 Google 官方 API 節點，絕不會被上傳或分享到任何其他第三方伺服器，請放心使用。
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()

# --- STEP WIZARD PROGRESS BAR (HTML/CSS) ---
steps_html = f"""
<div class="wizard-container">
    <div class="wizard-line"></div>
    <div class="wizard-line-active" style="width: {((st.session_state.step - 1) / 3) * 80 + 10}%;"></div>
    
    <div class="wizard-step {'active' if st.session_state.step == 1 else 'completed' if st.session_state.step > 1 else ''}">
        <div class="wizard-circle">1</div>
        <div class="wizard-label">品牌與產品</div>
    </div>
    <div class="wizard-step {'active' if st.session_state.step == 2 else 'completed' if st.session_state.step > 2 else ''}">
        <div class="wizard-circle">2</div>
        <div class="wizard-label">目標客群</div>
    </div>
    <div class="wizard-step {'active' if st.session_state.step == 3 else 'completed' if st.session_state.step > 3 else ''}">
        <div class="wizard-circle">3</div>
        <div class="wizard-label">生成設定</div>
    </div>
    <div class="wizard-step {'active' if st.session_state.step == 4 else 'completed' if st.session_state.step > 4 else ''}">
        <div class="wizard-circle">4</div>
        <div class="wizard-label">結果展示</div>
    </div>
</div>
"""
st.markdown(steps_html, unsafe_allow_html=True)


# --- HELPER: ROBUST CONTENT GENERATION WITH AUTO-FALLBACK ---
def generate_content_with_fallback(prompt, config=None):
    client = get_gemini_client(st.session_state.api_key)
    if not client:
        raise Exception("Gemini Client 初始化失敗")
    
    candidate_models = [
        st.session_state.model_name,
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-flash"
    ]
    models_to_try = []
    for m in candidate_models:
        if m not in models_to_try:
            models_to_try.append(m)
            
    last_error = None
    for model_name in models_to_try:
        try:
            kwargs = {"model": model_name, "contents": prompt}
            if config:
                kwargs["config"] = config
            response = client.models.generate_content(**kwargs)
            return response.text
        except Exception as e:
            last_error = e
            continue
            
    raise last_error if last_error else Exception("全數備援模型均無法連線")


# --- AI HELPER FUNCTION: BRAND DESCRIPTION POLISH ---
def ai_polish_description(raw_desc):
    prompt = f"""
    你是一位資深的品牌顧問與文案大師。請將以下這段簡短的產品或品牌描述，擴充並潤飾成一段專業、有吸引力且具備獨特價值主張的品牌與產品介紹（約 150 字，以繁體中文撰寫）。
    
    原始描述：'{raw_desc}'
    """
    try:
        res_text = generate_content_with_fallback(prompt)
        return res_text.strip()
    except Exception as e:
        st.error(f"AI 潤飾失敗: {str(e)}")
        return raw_desc

# --- AI HELPER FUNCTION: TARGET AUDIENCE ARCHETYPES SUGGESTION ---
def ai_suggest_audiences(brand_name, brand_desc):
    prompt = f"""
    你是一位專業的行銷策略規劃師。根據以下品牌與產品介紹，為其推薦 3 個最合理且最具潛力的目標客群（人物誌原型）。
    請以繁體中文回應，並必須輸出為一個合法的 JSON 陣列，每個元素包含：
    - 'archetype': 客群原型稱號（4字以內，例如：忙碌白領、小資大專生、精緻媽媽）
    - 'description': 簡短特徵描述（約 30 字，說明他們是誰）
    - 'pain_point': 核心痛點與渴望（約 30 字，說明他們面臨什麼問題）
    
    品牌名稱：'{brand_name}'
    產品介紹：'{brand_desc}'
    """
    try:
        res_text = generate_content_with_fallback(prompt)
        cleaned_text = clean_json_string(res_text)
        return json.loads(cleaned_text)
    except Exception as e:
        st.error(f"AI 推薦失敗: {str(e)}")
        return []

# --- AI HELPER FUNCTION: GENERATE FULL PERSONAS ---
def ai_generate_personas():
    from google.genai import types
    
    prompt = f"""
    請為以下品牌及目標客群，生成 {st.session_state.num_personas} 個互不相同且互補的詳細人物誌原型。
    
    【品牌名稱】
    {st.session_state.brand_name}
    
    【產品/服務介紹】
    {st.session_state.brand_desc}
    
    【目標客群描述】
    {st.session_state.audience_desc}
    
    【核心痛點與渴望】
    {st.session_state.audience_pain}
    
    【人物誌屬性偏好】
    {st.session_state.focus_preference}
    
    請根據以上資訊，深入描繪消費者，創造出鮮明、立體且互不重複的個人檔案。
    你必須使用繁體中文（Taiwan）撰寫，並且輸出為一個合法的 JSON 陣列，每個元素代表一個人物誌，結構如下：
    
    [
      {{
        "name": "中文姓名（加上英文名，例如：林書豪 Leo）",
        "age": 數字（代表年齡）,
        "gender": "男性" 或 "女性" 或 "非二元",
        "occupation": "具體職業（例如：軟體工程師、自由工作者、高中老師）",
        "location": "居住城市與生活環境（例如：台中市，都會重劃區）",
        "archetype": "核心客群原型稱號（4-6字，例如：理性科技男、質感生活家、高標細節控）",
        "slogan": "代表其核心價值觀或消費心聲的一句話（例如：時間就是金錢，只選對的不選貴的）",
        "traits": {{
          "price_sensitivity": 1到100的整數（價格敏感度，值越高越在乎價格）,
          "tech_savviness": 1到100的整數（科技熟悉度，值越高越愛用新科技）,
          "brand_loyalty": 1到100的整數（品牌忠誠度，值越高越不易換品牌）,
          "decision_speed": 1到100的整數（決策速度，值越高代表買東西越衝動/越快決定）
        }},
        "bio": "約 120 字的個人背景故事，描述他的日常生活型態、個性細節以及與本產品可能產生的關聯性",
        "needs_and_goals": [
          "核心需求 1",
          "核心需求 2",
          "核心需求 3"
        ],
        "pain_points": [
          "面臨的痛點 1",
          "面臨的痛點 2",
          "面臨的痛點 3"
        ],
        "buying_behavior": [
          "購買習慣 1（例如：購買前必看 YouTube 開箱）",
          "購買習慣 2（例如：偏好線上網購，常在深夜下單）"
        ],
        "media_habits": [
          "媒體與社群偏好 1（例如：每日滑 Instagram 1.5小時）",
          "媒體與社群偏好 2（例如：通勤時聽 Podcast 商業類節目）"
        ],
        "marketing_tips": {{
          "channels": ["推薦行銷管道 1", "推薦行銷管道 2"],
          "hooks": ["對他最有效的溝通痛點或吸睛行銷切入點 1", "對他最有效的溝通痛點或吸睛行銷切入點 2"],
          "copy_example": "最能打動他的廣告文案範例（2-3句，以繁體中文撰寫）"
        }}
      }}
    ]
    """
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        system_instruction="你是一位資深的行銷策略總監與消費者心理學專家。你的工作是根據品牌、產品及目標客群資訊，生成極具洞察力、真實且可立即用於行銷規劃的「人物誌（Persona）」。你必須使用繁體中文（Taiwan）進行回應，且內容要具體、有商業可行性。"
    )
    
    try:
        res_text = generate_content_with_fallback(prompt, config=config)
        cleaned_text = clean_json_string(res_text)
        st.session_state.personas = json.loads(cleaned_text)
    except Exception as e:
        st.error(f"人物誌生成失敗: {str(e)}")
        st.session_state.personas = None


# ==========================================
# STEP 1: BRAND & PRODUCT PROFILE
# ==========================================
if st.session_state.step == 1:
    st.markdown(
        """
        <div class="guide-alert">
            <div class="guide-title">💡 小白行銷心法 1：從「你是誰」開始</div>
            <p class="guide-content">
                做行銷第一步，就是說清楚你的品牌和產品核心價值。AI 會根據這裡輸入的資訊，來判斷哪一種人最容易被你的產品吸引。
                <b>別擔心不會寫！</b> 隨意輸入幾個關鍵字，再點擊「✨ AI 幫我潤飾」按鈕，讓 AI 幫你寫出大師級的品牌文案！
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("### 📝 填寫品牌與產品資訊")
    
    brand_name = st.text_input(
        "品牌/店家名稱 (如：微光咖啡, FitLife 健身房)",
        value=st.session_state.brand_name,
        placeholder="請輸入品牌名稱..."
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        brand_desc = st.text_area(
            "產品或服務介紹 (如：主打自家烘焙的低酸冷萃咖啡，並提供安靜工作空間...)",
            value=st.session_state.brand_desc,
            placeholder="請詳細描述你的產品在賣什麼？有什麼特點或優勢？",
            height=180
        )
    with col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='ai-helper-btn'>", unsafe_allow_html=True)
        if st.button("✨ AI 幫我潤飾描述"):
            if not brand_desc.strip():
                st.warning("⚠️ 請先輸入一些簡單的產品描述關鍵字喔！")
            else:
                with st.spinner("AI 正在發揮文案魔力中..."):
                    polished = ai_polish_description(brand_desc)
                    st.session_state.brand_desc = polished
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("輸入關鍵字後，點選此按鈕可以讓 AI 將描述擴充為完整且吸引人的品牌簡介。")

    # Update states
    st.session_state.brand_name = brand_name
    st.session_state.brand_desc = brand_desc
    
    # Navigation
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    col_prev, col_next = st.columns([1, 1])
    with col_next:
        if st.button("下一步：描述目標客群 ➡️"):
            if not brand_name.strip() or not brand_desc.strip():
                st.warning("⚠️ 請務必填寫「品牌名稱」與「產品介紹」才能繼續喔！")
            else:
                st.session_state.step = 2
                st.rerun()


# ==========================================
# STEP 2: TARGET AUDIENCE PROFILE
# ==========================================
elif st.session_state.step == 2:
    st.markdown(
        """
        <div class="guide-alert">
            <div class="guide-title">💡 小白行銷心法 2：定位你的潛在顧客</div>
            <p class="guide-content">
                誰是你的消費者？他們有什麼苦惱（痛點）？例如：想喝咖啡但喝了會心悸、工作太忙沒空運動。
                <b>毫無頭緒嗎？</b> 點擊下方的「💡 AI 推薦客群原型」按鈕，AI 就會根據你第一步輸入的產品，自動推導出三個最合適的受眾群體。
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("### 👥 目標客群與痛點描述")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        audience_desc = st.text_area(
            "你想賣給誰？顧客的基本輪廓是？ (如：常加班的都會上班族、剛生小孩的媽媽)",
            value=st.session_state.audience_desc,
            placeholder="描述你腦海中的顧客樣貌。例如：年齡、生活習慣、或者是他們的職業...",
            height=120
        )
        
        audience_pain = st.text_area(
            "他們的核心痛點或渴望是什麼？ (如：工作累想放鬆、想減肥但討厭做有氧運動)",
            value=st.session_state.audience_pain,
            placeholder="他們生活中遇到了什麼不方便或煩惱，是你的產品可以幫忙解決的？",
            height=120
        )
    with col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='ai-helper-btn'>", unsafe_allow_html=True)
        if st.button("💡 AI 推薦客群原型"):
            with st.spinner("AI 正在分析市場定位中..."):
                suggestions = ai_suggest_audiences(
                    st.session_state.brand_name,
                    st.session_state.brand_desc
                )
                st.session_state.suggested_audiences = suggestions
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("AI 將分析您的品牌定位，並推薦三個高潛力的目標消費族群。")
        
    # Show recommendations if loaded
    if st.session_state.suggested_audiences:
        st.markdown("#### 🎯 AI 推薦的客群定位（可點選套用）：")
        rec_cols = st.columns(3)
        for idx, rec in enumerate(st.session_state.suggested_audiences):
            with rec_cols[idx]:
                st.markdown(
                    f"""
                    <div style="background:rgba(139,92,246,0.08); border: 1px dashed rgba(139,92,246,0.3); border-radius:15px; padding:15px; height:100%;">
                        <strong style="color:#a78bfa; font-size:1.05rem;">📍 {rec.get('archetype', '')}</strong>
                        <p style="font-size:0.85rem; margin-top:5px; color:#cbd5e1;"><b>特徵：</b>{rec.get('description', '')}</p>
                        <p style="font-size:0.85rem; margin-bottom:15px; color:#f472b6;"><b>痛點：</b>{rec.get('pain_point', '')}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"套用客群 {idx+1}", key=f"apply_rec_{idx}"):
                    st.session_state.audience_desc = rec.get('description', '')
                    st.session_state.audience_pain = rec.get('pain_point', '')
                    st.session_state.suggested_audiences = None
                    st.rerun()

    # Update states
    st.session_state.audience_desc = audience_desc
    st.session_state.audience_pain = audience_pain
    
    # Navigation
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("⬅️ 上一步：品牌與產品"):
            st.session_state.step = 1
            st.rerun()
    with col_next:
        if st.button("下一步：人物誌設定 ➡️"):
            if not audience_desc.strip() or not audience_pain.strip():
                st.warning("⚠️ 請務必填寫「客群輪廓」與「核心痛點」才能繼續喔！")
            else:
                st.session_state.step = 3
                st.rerun()


# ==========================================
# STEP 3: PERSONA CONFIGURATION
# ==========================================
elif st.session_state.step == 3:
    st.markdown(
        """
        <div class="guide-alert">
            <div class="guide-title">💡 小白行銷心法 3：細化設定</div>
            <p class="guide-content">
                在這裡，您可以選擇想要生成的人物誌數量。我們建議先生成 <b>2 個</b>，這樣可以讓您在設計行銷方案時，有兩個不同切入點（例如：一個重感性、一個重理性；一個重價格、一個重便利）進行對比。
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("### ⚙️ 人物誌產出偏好設定")
    
    num_personas = st.slider(
        "您想要生成幾個人物誌原型？",
        min_value=1,
        max_value=3,
        value=st.session_state.num_personas,
        help="生成多個人物誌可以看見不同受眾的購物決策流程差異。"
    )
    
    focus_preference = st.selectbox(
        "人物誌的屬性取向偏好",
        options=[
            "自動分配特徵（多元化均衡）",
            "價格敏感偏好（著重小資、划算、比價型顧客）",
            "數位科技偏好（著重熱愛新事物、線上網購、社群活躍型顧客）",
            "品牌忠誠偏好（著重重品質、不易更換品牌、重視口碑型顧客）"
        ],
        index=[
            "自動分配特徵（多元化均衡）",
            "價格敏感偏好（著重小資、划算、比價型顧客）",
            "數位科技偏好（著重熱愛新事物、線上網購、社群活躍型顧客）",
            "品牌忠誠偏好（著重重品質、不易更換品牌、重視口碑型顧客）"
        ].index(st.session_state.focus_preference)
    )
    
    # Save states
    st.session_state.num_personas = num_personas
    st.session_state.focus_preference = focus_preference
    
    # Navigation
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("⬅️ 上一步：目標客群"):
            st.session_state.step = 2
            st.rerun()
    with col_next:
        if st.button("🚀 開始分析並生成人物誌！"):
            st.session_state.step = 4
            st.session_state.personas = None # Clear previous personas to force new generation
            st.rerun()


# ==========================================
# STEP 4: AI GENERATION & DISPLAY
# ==========================================
elif st.session_state.step == 4:
    # Trigger generation if not exists
    if st.session_state.personas is None:
        with st.status("🔮 AI 腦力激盪中... 正在繪製人物誌...", expanded=True) as status:
            st.write("🔍 分析品牌及產品核心價值...")
            st.write("👥 拆解目標客群特徵與痛點...")
            st.write("⚡ 模擬人物誌性格、生活背景與決策模型...")
            ai_generate_personas()
            if st.session_state.personas:
                status.update(label="🎉 人物誌繪製完成！", state="complete", expanded=False)
            else:
                status.update(label="❌ 人物誌生成失敗，請查看下方錯誤。", state="error", expanded=True)
                st.session_state.step = 3
                if st.button("回到上一步重新設定"):
                    st.rerun()
                st.stop()
                
    # Display results
    if st.session_state.personas:
        st.markdown("### 🏆 AI 生成的人物誌結果")
        
        # Tabs for multiple personas
        persona_tabs = st.tabs([f"👤 人物誌 {idx+1}: {p.get('name', '未命名')}" for idx, p in enumerate(st.session_state.personas)])
        
        for idx, p in enumerate(st.session_state.personas):
            with persona_tabs[idx]:
                name = p.get('name', 'N/A')
                age = p.get('age', 'N/A')
                gender = p.get('gender', 'N/A')
                occupation = p.get('occupation', 'N/A')
                location = p.get('location', 'N/A')
                archetype = p.get('archetype', 'N/A')
                slogan = p.get('slogan', 'N/A')
                bio = p.get('bio', 'N/A')
                
                # Fetch avatar dynamically from DiceBear using URL encoding for seed with onerror fallback
                avatar_seed = urllib.parse.quote(name)
                avatar_url = f"https://api.dicebear.com/7.x/lorelei/svg?seed={avatar_seed}"
                fallback_avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={avatar_seed}"
                
                # Traits mapping
                traits = p.get('traits', {})
                price_sens = traits.get('price_sensitivity', 50)
                tech_sav = traits.get('tech_savviness', 50)
                brand_loy = traits.get('brand_loyalty', 50)
                dec_speed = traits.get('decision_speed', 50)
                
                # Display HTML Persona Card
                st.markdown(
                    f"""
                    <div class="persona-card">
                        <div class="persona-header">
                            <div class="persona-avatar-wrapper">
                                <img src="{avatar_url}" alt="Avatar" onerror="this.onerror=null; this.src='{fallback_avatar}';">
                            </div>
                            <div class="persona-meta">
                                <div class="persona-name-container">
                                    <h2 class="persona-name">{name}</h2>
                                    <span class="persona-tag">{archetype}</span>
                                </div>
                                <p class="persona-slogan">「{slogan}」</p>
                            </div>
                        </div>
                        <div class="persona-body">
                            <!-- Demographics Grid -->
                            <div class="demo-grid">
                                <div class="demo-item">
                                    <div class="demo-label">年齡</div>
                                    <div class="demo-value">{age} 歲</div>
                                </div>
                                <div class="demo-item">
                                    <div class="demo-label">性別</div>
                                    <div class="demo-value">{gender}</div>
                                </div>
                                <div class="demo-item">
                                    <div class="demo-label">職業</div>
                                    <div class="demo-value">{occupation}</div>
                                </div>
                                <div class="demo-item">
                                    <div class="demo-label">居住地</div>
                                    <div class="demo-value">{location}</div>
                                </div>
                            </div>
                            
                            <!-- Middle content: Traits & Bio -->
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 24px;">
                                <!-- Traits progress bars -->
                                <div class="content-box">
                                    <div class="content-box-title">📊 購物性格雷達</div>
                                    <div class="metric-row">
                                        <div class="metric-header">
                                            <span>價格敏感度 (越在意折扣/划算)</span>
                                            <span>{price_sens}%</span>
                                        </div>
                                        <div class="metric-bar-bg"><div class="metric-bar-fill" style="width: {price_sens}%;"></div></div>
                                    </div>
                                    <div class="metric-row">
                                        <div class="metric-header">
                                            <span>科技接受度 (越喜歡線上、智慧化)</span>
                                            <span>{tech_sav}%</span>
                                        </div>
                                        <div class="metric-bar-bg"><div class="metric-bar-fill" style="width: {tech_sav}%;"></div></div>
                                    </div>
                                    <div class="metric-row">
                                        <div class="metric-header">
                                            <span>品牌忠誠度 (越不容易轉移品牌)</span>
                                            <span>{brand_loy}%</span>
                                        </div>
                                        <div class="metric-bar-bg"><div class="metric-bar-fill" style="width: {brand_loy}%;"></div></div>
                                    </div>
                                    <div class="metric-row">
                                        <div class="metric-header">
                                            <span>決策速度 (越容易衝動或快買)</span>
                                            <span>{dec_speed}%</span>
                                        </div>
                                        <div class="metric-bar-bg"><div class="metric-bar-fill" style="width: {dec_speed}%;"></div></div>
                                    </div>
                                </div>
                                <!-- Bio story -->
                                <div class="content-box">
                                    <div class="content-box-title">📖 個人故事背景</div>
                                    <p style="font-size:0.92rem; color:#cbd5e1; line-height:1.6; font-family:'Noto Sans TC', sans-serif;">{bio}</p>
                                </div>
                            </div>
                            
                            <!-- Bottom detailed lists: Pain points & Needs -->
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 24px;">
                                <div class="content-box">
                                    <div class="content-box-title">🎯 核心需求與目標</div>
                                    <ul class="content-box-list">
                                        {"".join([f"<li>{item}</li>" for item in p.get('needs_and_goals', [])])}
                                    </ul>
                                </div>
                                <div class="content-box">
                                    <div class="content-box-title">⚠️ 生活與消費痛點</div>
                                    <ul class="content-box-list">
                                        {"".join([f"<li>{item}</li>" for item in p.get('pain_points', [])])}
                                    </ul>
                                </div>
                            </div>
                            
                            <!-- Habits: Buying & Media -->
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 24px;">
                                <div class="content-box">
                                    <div class="content-box-title">🛍️ 購買決策與管道偏好</div>
                                    <ul class="content-box-list">
                                        {"".join([f"<li>{item}</li>" for item in p.get('buying_behavior', [])])}
                                    </ul>
                                </div>
                                <div class="content-box">
                                    <div class="content-box-title">📱 每日媒體與社交習慣</div>
                                    <ul class="content-box-list">
                                        {"".join([f"<li>{item}</li>" for item in p.get('media_habits', [])])}
                                    </ul>
                                </div>
                            </div>
                            
                            <!-- Marketing Strategy (Callout box) -->
                            <div class="marketing-section">
                                <div class="marketing-title">🚀 針對該人物誌的行銷攻略心法</div>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                                    <div>
                                        <strong style="color:#ffffff; font-size:0.9rem;">📍 建議觸及管道：</strong>
                                        <div style="margin-top:5px;">
                                            {" ".join([f"<span class='persona-tag' style='background:rgba(236,72,153,0.15); border-color:rgba(236,72,153,0.4);'>{ch}</span>" for ch in p.get('marketing_tips', {}).get('channels', [])])}
                                        </div>
                                        <div style="height:15px;"></div>
                                        <strong style="color:#ffffff; font-size:0.9rem;">🎯 溝通切入點（Hooks）：</strong>
                                        <ul style="margin:5px 0 0 0; padding-left:18px; font-size:0.85rem; color:#cbd5e1; line-height:1.5;">
                                            {"".join([f"<li>{hk}</li>" for hk in p.get('marketing_tips', {}).get('hooks', [])])}
                                        </ul>
                                    </div>
                                    <div style="border-left: 1px solid rgba(255,255,255,0.08); padding-left:20px;">
                                        <strong style="color:#ffffff; font-size:0.9rem;">✍️ 推薦行銷文案範例：</strong>
                                        <div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:12px; border:1px solid rgba(255,255,255,0.05); margin-top:8px; font-style:italic; font-size:0.88rem; color:#f472b6; line-height:1.5;">
                                            「{p.get('marketing_tips', {}).get('copy_example', '無範例')}」
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # --- EXPORT TOOLS ---
        st.markdown("### 💾 匯出與分享報告")
        
        # Prepare markdown text
        md_report = f"# 《{st.session_state.brand_name}》消費者人物誌報告\n\n"
        md_report += f"**品牌產品說明**：{st.session_state.brand_desc}\n\n"
        md_report += f"**整體目標客群定位**：{st.session_state.audience_desc}\n\n"
        md_report += "---\n\n"
        
        for idx, p in enumerate(st.session_state.personas):
            md_report += f"## 人物誌 {idx+1}：{p.get('name')} - {p.get('archetype')}\n"
            md_report += f"> 「{p.get('slogan')}」\n\n"
            md_report += f"- **基本資料**：{p.get('age')}歲 / {p.get('gender')} / {p.get('occupation')} / 居住於 {p.get('location')}\n"
            md_report += f"- **購物性格指標**：\n"
            md_report += f"  - 價格敏感度：{p.get('traits', {}).get('price_sensitivity')}% | "
            md_report += f"科技接受度：{p.get('traits', {}).get('tech_savviness')}% | "
            md_report += f"品牌忠誠度：{p.get('traits', {}).get('brand_loyalty')}% | "
            md_report += f"決策速度：{p.get('traits', {}).get('decision_speed')}%\n"
            md_report += f"- **生活背景故事**：{p.get('bio')}\n\n"
            
            md_report += "### 🎯 核心需求與目標\n"
            for item in p.get('needs_and_goals', []):
                md_report += f"- {item}\n"
            md_report += "\n"
            
            md_report += "### ⚠️ 生活與消費痛點\n"
            for item in p.get('pain_points', []):
                md_report += f"- {item}\n"
            md_report += "\n"
            
            md_report += "### 🛍️ 購買決策與社交媒體習慣\n"
            md_report += "**購買決策偏好**：\n"
            for item in p.get('buying_behavior', []):
                md_report += f"- {item}\n"
            md_report += "**媒體習慣**：\n"
            for item in p.get('media_habits', []):
                md_report += f"- {item}\n"
            md_report += "\n"
            
            md_report += "### 🚀 專屬行銷攻略\n"
            md_report += f"- **推薦管道**：{', '.join(p.get('marketing_tips', {}).get('channels', []))}\n"
            md_report += f"- **溝通痛點切入點**：\n"
            for item in p.get('marketing_tips', {}).get('hooks', []):
                md_report += f"  - {item}\n"
            md_report += f"- **推薦廣告文案範例**：*{p.get('marketing_tips', {}).get('copy_example')}*\n\n"
            md_report += "---\n\n"
            
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        with col_dl1:
            st.download_button(
                label="📥 下載人物誌 Markdown 報告 (.md)",
                data=md_report,
                file_name=f"persona_report_{st.session_state.brand_name.replace(' ', '_')}.md",
                mime="text/markdown"
            )
        with col_dl2:
            st.download_button(
                label="📥 下載人物誌 JSON 數據 (.json)",
                data=json.dumps(st.session_state.personas, ensure_ascii=False, indent=2),
                file_name=f"persona_data_{st.session_state.brand_name.replace(' ', '_')}.json",
                mime="application/json"
            )
        with col_dl3:
            st.code(md_report[:500] + "\n... (以下省略，請點選下載或複製完整檔案) ...", language="markdown")

        # Go back / Reset
        st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)
        col_prev, col_next = st.columns([1, 1])
        with col_prev:
            if st.button("⬅️ 修改設定或重填"):
                st.session_state.step = 3
                st.rerun()
        with col_next:
            if st.button("🔄 重新生成人物誌"):
                st.session_state.personas = None
                st.rerun()
