"""
00_home.py — プロジェクト管理ページ
app.py（Project Hub）にリダイレクトする。
"""
import streamlit as st

st.set_page_config(page_title="Consulting OS", page_icon="◆",
    initial_sidebar_state="expanded")

st.switch_page("app.py")
