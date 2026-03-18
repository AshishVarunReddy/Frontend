# components/sidebar.py
import streamlit as st
from streamlit_option_menu import option_menu

def sidebar(menu_items, key="app_sidebar_menu"):
    base_icons = [
        "grid-1x2",
        "activity",
        "flask",
        "capsule",
        "building",
        "credit-card",
        "people",
        "shield",
        "truck",
        "bar-chart",
        "gear",
        "clipboard-data",
    ]
    icons = (base_icons + ["circle"] * len(menu_items))[: len(menu_items)]
    selected_state_key = f"{key}_selected"
    if menu_items:
        st.session_state.setdefault(selected_state_key, menu_items[0])
        default_index = menu_items.index(st.session_state[selected_state_key]) if st.session_state[selected_state_key] in menu_items else 0
    else:
        default_index = 0

    with st.sidebar:
        st.markdown("## 🏥 MediCare")
        selected = option_menu(
            "",
            menu_items,
            icons=icons,
            default_index=default_index,
            key=key,
        )
        st.session_state[selected_state_key] = selected

        st.divider()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.page = "login"
            st.session_state.role = None
            st.session_state.view = "main"
            st.session_state.selected_category = None
            st.session_state.selected_module = None
            st.rerun()

    return selected