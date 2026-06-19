import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.agent import run_agent

st.set_page_config(
    page_title="STM32 AI Assistant",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

QUICK_QUESTIONS = [
    "UART with DMA",
    "TIM2 PWM registers",
    "ADC configuration",
    "SPI master init code",
    "GPIO as output",
]
MODEL_LIST = [
    "STM32F103", "STM32F401", "STM32F407",
    "STM32L4",   "STM32H7",   "STM32F0",  "STM32F3",
]

if "history"          not in st.session_state: st.session_state.history          = []
if "messages"         not in st.session_state: st.session_state.messages         = []
if "_quick_q"         not in st.session_state: st.session_state._quick_q         = None
if "total_iterations" not in st.session_state: st.session_state.total_iterations = 0
if "stm32_model"      not in st.session_state: st.session_state.stm32_model      = "STM32F103"

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔧 STM32 AI")

    st.session_state.stm32_model = st.selectbox(
        "Target MCU", MODEL_LIST,
        index=MODEL_LIST.index(st.session_state.stm32_model),
    )

    st.markdown("---")
    st.markdown("**Quick Questions**")
    for q in QUICK_QUESTIONS:
        if st.button(q, key="qq_" + q):
            st.session_state._quick_q = q
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear chat"):
        st.session_state.history          = []
        st.session_state.messages         = []
        st.session_state.total_iterations = 0
        st.rerun()

# ── MAIN ─────────────────────────────────────────────────────────────────────
model = st.session_state.stm32_model

st.markdown(
    "<style>"
    "[data-testid='stHeader']{display:none}"
    "footer{display:none}"
    ".block-container{max-width:800px;margin:0 auto;padding-top:1rem}"
    "</style>",
    unsafe_allow_html=True,
)

def handle_question(q, mdl):
    st.session_state.messages.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            try:
                answer, steps, updated_history, sources, iterations = run_agent(
                    q, st.session_state.history, mdl
                )
                st.session_state.total_iterations += iterations
                error = None
            except Exception as exc:
                answer          = f"Error: `{exc}`"
                steps           = []
                sources         = []
                iterations      = 0
                updated_history = st.session_state.history
                error           = str(exc)

        if steps:
            with st.expander(f"Reasoning ({iterations} rounds)", expanded=True):
                for s in steps:
                    st.markdown(s)

        st.markdown(answer)

        if sources:
            with st.expander("References", expanded=False):
                for i, src in enumerate(sources[:3], 1):
                    st.markdown(f"**{i}.** {src}")

    st.session_state.history = updated_history
    st.session_state.messages.append({
        "role": "assistant", "content": answer,
        "steps": steps, "sources": sources,
        "iterations": iterations if not error else 0,
    })

if st.session_state._quick_q:
    q = st.session_state._quick_q
    st.session_state._quick_q = None
    handle_question(q, model)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            if msg.get("steps"):
                with st.expander(f"Reasoning ({msg.get('iterations',0)} rounds)", expanded=False):
                    for s in msg["steps"]:
                        st.markdown(s)
            if msg.get("sources"):
                with st.expander("References", expanded=False):
                    for i, src in enumerate(msg["sources"][:3], 1):
                        st.markdown(f"**{i}.** {src}")

if question := st.chat_input(f"Message {model} assistant..."):
    handle_question(question, model)

turns = len(st.session_state.history) // 2
if turns > 0:
    st.caption(f"{turns} turns · {st.session_state.total_iterations} reasoning rounds")