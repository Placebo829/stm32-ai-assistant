import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent import run_agent

st.set_page_config(
    page_title="STM32 AI Assistant",
    page_icon="🔧",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

* { box-sizing: border-box; }

html, body, .stApp {
    background: #1a1a1a !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #ececec;
}

[data-testid="stHeader"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebar"],
#MainMenu, footer { display: none !important; }

[data-testid="stMainBlockContainer"],
[data-testid="block-container"] {
    max-width: 760px !important;
    margin: 0 auto !important;
    padding: 0 16px !important;
    background: transparent !important;
}

h1 { display: none !important; }
h2, h3 { color: #ececec !important; font-weight: 500 !important; }
p, li   { color: #c9c9c9 !important; line-height: 1.7 !important; }

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 16px 0 !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stMarkdownContainer"] p {
    background: #2f2f2f !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 10px 16px !important;
    display: inline-block !important;
    max-width: 80% !important;
    color: #ececec !important;
    float: right !important;
}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 16px 0 !important;
    box-shadow: none !important;
}

[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
    background: #2f2f2f !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 50% !important;
}

code {
    background: rgba(255,255,255,0.08) !important;
    border: none !important;
    border-radius: 5px !important;
    color: #89b4fa !important;
    font-size: 0.87em !important;
    padding: 2px 6px !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}

pre {
    background: #111 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    margin: 12px 0 !important;
}
pre code {
    background: transparent !important;
    color: #cdd6f4 !important;
    border: none !important;
    padding: 0 !important;
    font-size: 0.88rem !important;
    line-height: 1.6 !important;
}

[data-testid="stChatInput"] { background: transparent !important; }
[data-testid="stChatInput"] textarea {
    background: #2a2a2a !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 16px !important;
    color: #ececec !important;
    font-size: 0.95rem !important;
    padding: 14px 18px !important;
    resize: none !important;
    transition: border-color 0.2s !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(255,255,255,0.28) !important;
    outline: none !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: rgba(255,255,255,0.3) !important;
}

[data-testid="stExpander"] {
    background: #222 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    color: #888 !important;
    font-size: 0.85rem !important;
}

[data-testid="stSelectbox"] > div > div {
    background: #2a2a2a !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #ececec !important;
    font-size: 0.88rem !important;
}

.stButton > button {
    background: #2a2a2a !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #ececec !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    font-weight: 400 !important;
    transition: background 0.15s ease !important;
    padding: 6px 14px !important;
}
.stButton > button:hover {
    background: #333 !important;
    border-color: rgba(255,255,255,0.2) !important;
}

hr { border-color: rgba(255,255,255,0.07) !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
.stSpinner > div { border-top-color: #888 !important; }
.navbar-spacer { height: 56px; }
</style>
""", unsafe_allow_html=True)

# ── 初始化 ──
if "history" not in st.session_state:
    st.session_state.history = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "_quick_q" not in st.session_state:
    st.session_state._quick_q = None
if "total_iterations" not in st.session_state:
    st.session_state.total_iterations = 0

# ── Navbar ──
st.markdown("""
<nav style="
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 52px;
    background: #1a1a1a;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    z-index: 9999;
">
    <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:1.2rem;">🔧</span>
        <span style="color:#ececec;font-size:0.95rem;font-weight:500;letter-spacing:-0.2px;">STM32 AI Assistant</span>
    </div>
    <div style="color:rgba(255,255,255,0.3);font-size:0.75rem;letter-spacing:0.2px;">
        自動查詢文件 · 生成程式碼 · 解釋 Register
    </div>
</nav>
<div class="navbar-spacer"></div>
""", unsafe_allow_html=True)

# ── 頂部控制列 ──
col_model, col_clear = st.columns([3, 1])
with col_model:
    stm32_model = st.selectbox(
        "型號",
        ["STM32F103", "STM32F401", "STM32F407", "STM32L4", "STM32H7", "STM32F0", "STM32F3"],
        index=0,
        label_visibility="collapsed"
    )
with col_clear:
    if st.button("🗑️ 清除", use_container_width=True):
        st.session_state.history = []
        st.session_state.messages = []
        st.session_state.total_iterations = 0
        st.rerun()

# ── 快速問題 ──
quick_questions = [
    ("🔌", "UART with DMA"),
    ("⏱️", "TIM2 PWM registers"),
    ("📊", "ADC configuration"),
    ("🔄", "SPI master init code"),
    ("💡", "GPIO as output"),
]
cols = st.columns(len(quick_questions))
for col, (icon, q) in zip(cols, quick_questions):
    with col:
        if st.button(f"{icon} {q}", use_container_width=True):
            st.session_state._quick_q = q

st.divider()
st.title("STM32 AI Assistant")


def handle_question(q, model):
    st.session_state.messages.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                answer, steps, updated_history, sources, iterations = run_agent(
                    q, st.session_state.history, model
                )
                st.session_state.total_iterations += iterations
                error = None
            except Exception as e:
                answer = f"⚠️ 發生錯誤，請稍後再試。\n\n詳細資訊：`{str(e)}`"
                steps, sources, iterations = [], [], 0
                updated_history = st.session_state.history
                error = str(e)

        # ── 推理過程（預設展開）──
        if steps:
            with st.expander(f"🔍 推理過程（共 {iterations} 輪）", expanded=True):
                for step in steps:
                    st.markdown(step)
                st.markdown(
                    f"<div style='color:rgba(255,255,255,0.3);font-size:0.78rem;margin-top:8px;'>"
                    f"本次 Agent 思考了 <b>{iterations}</b> 輪迴圈</div>",
                    unsafe_allow_html=True
                )

        st.markdown(answer)

        # ── 參考來源 ──
        if sources:
            with st.expander("📚 參考來源", expanded=False):
                for i, src in enumerate(sources[:3], 1):
                    st.markdown(
                        f"<div style='color:#666;font-size:0.82rem;padding:4px 0;'>"
                        f"片段 {i}：{src}...</div>",
                        unsafe_allow_html=True
                    )

    st.session_state.history = updated_history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "steps": steps,
        "sources": sources,
        "iterations": iterations if not error else 0
    })


# ── 顯示歷史對話 ──
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            steps = msg.get("steps", [])
            sources = msg.get("sources", [])
            iters = msg.get("iterations", 0)
            if steps:
                with st.expander(f"🔍 推理過程（共 {iters} 輪）", expanded=False):
                    for step in steps:
                        st.markdown(step)
            if sources:
                with st.expander("📚 參考來源", expanded=False):
                    for i, src in enumerate(sources[:3], 1):
                        st.markdown(
                            f"<div style='color:#666;font-size:0.82rem;padding:4px 0;'>"
                            f"片段 {i}：{src}...</div>",
                            unsafe_allow_html=True
                        )

# ── 快速問題處理 ──
if st.session_state._quick_q:
    q = st.session_state._quick_q
    st.session_state._quick_q = None
    handle_question(q, stm32_model)
    st.rerun()

# ── 輸入框 ──
if question := st.chat_input(f"傳訊息給 {stm32_model} 助手..."):
    handle_question(question, stm32_model)

# ── 底部統計 ──
turns = len(st.session_state.history) // 2
if turns > 0:
    st.markdown(
        f"<div style='text-align:center;color:rgba(255,255,255,0.2);font-size:0.75rem;padding:16px 0;'>"
        f"{turns} 輪對話 · 累計 Agent 思考 {st.session_state.total_iterations} 次迴圈"
        f"</div>",
        unsafe_allow_html=True
    )