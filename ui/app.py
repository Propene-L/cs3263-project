"""Thin optional Streamlit UI. Install `streamlit` separately.

It delegates all decisions to MuseumDialogue; no reasoning occurs in the UI.
Session data exists only in Streamlit's per-session memory.
"""
from __future__ import annotations

import streamlit as st
from museum_guide.dialogue import MuseumDialogue

st.set_page_config(page_title="Museum Logic Curator", page_icon="🏛️")
st.title("Museum Logic Curator")
mode = st.sidebar.selectbox("Reasoning mode", ["manual", "hybrid", "direct_llm"])
st.sidebar.caption("Manual is an offline command interface; hybrid and direct require provider configuration.")
if st.sidebar.button("Reset session"):
    for key in ["guide", "session", "messages", "mode", "last_audit"]:
        st.session_state.pop(key, None)
    st.rerun()

if st.session_state.get("mode") != mode:
    for key in ["guide", "session", "messages"]:
        st.session_state.pop(key, None)
    st.session_state.mode = mode

if "guide" not in st.session_state:
    try:
        st.session_state.guide = MuseumDialogue.from_repository(
            use_llm=mode != "manual", with_direct=mode == "direct_llm")
        st.session_state.session = st.session_state.guide.new_session("visitor_web")
        st.session_state.messages = []
    except Exception as exc:
        st.error(f"Unable to start museum engine: {type(exc).__name__}: {exc}")
        st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["text"])

incoming = st.chat_input("Describe an artwork or answer the current question")
if incoming:
    st.session_state.messages.append({"role": "user", "text": incoming})
    try:
        new_state, output = st.session_state.guide.run_turn(st.session_state.session, incoming, mode=mode)
    except Exception as exc:
        st.error(f"State unchanged: {type(exc).__name__}: {exc}")
    else:
        st.session_state.session = new_state
        st.session_state.messages.append({"role": "assistant", "text": output["text"]})
        st.session_state.last_audit = output
    st.rerun()

if "last_audit" in st.session_state:
    with st.expander("Last decision: provenance and state"):
        st.json(st.session_state.last_audit["audit"])
        st.json(st.session_state.last_audit["state"])
        for src in st.session_state.last_audit["sources"]:
            st.write(src)
