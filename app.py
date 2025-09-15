import streamlit as st
import os
from database import init_database
from auth import authenticate_user, get_user_role, logout_user
from pages import dashboard, projects, work_orders, cutting_lists, balance_orders, production_log, daily_targets, dispatch, audit_trail, users

# Page configuration
st.set_page_config(
    page_title="Project & Procurement Management System",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_database()

# Authentication check
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.user_role = None

def main():
    if not st.session_state.authenticated:
        show_login()
    else:
        show_app()

def show_login():
    st.title("🏗️ Project & Procurement Management System")
    st.markdown("### Please login to continue")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", use_container_width=True):
            user = authenticate_user(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_id = user['id']
                st.session_state.username = user['username']
                st.session_state.user_role = user['role']
                st.rerun()
            else:
                st.error("Invalid username or password")

def show_app():
    # Sidebar navigation
    with st.sidebar:
        st.title("🏗️ PPMS")
        st.markdown(f"**Welcome, {st.session_state.username}**")
        st.markdown(f"*Role: {st.session_state.user_role}*")
        
        st.divider()
        
        # Navigation menu
        pages = {
            "📊 Dashboard": "dashboard",
            "🏗️ Projects": "projects",
            "📋 Work Orders": "work_orders",
            "✂️ Cutting Lists": "cutting_lists",
            "⚖️ Balance Orders": "balance_orders",
            "🏭 Production Log": "production_log",
            "🎯 Daily Targets": "daily_targets",
            "🚚 Dispatch": "dispatch",
            "📜 Audit Trail": "audit_trail"
        }
        
        # Add user management for admins
        if st.session_state.user_role == "Admin":
            pages["👥 Users"] = "users"
        
        # Page selection
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "dashboard"
        
        for page_name, page_key in pages.items():
            if st.button(page_name, use_container_width=True):
                st.session_state.current_page = page_key
                st.rerun()
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()
    
    # Main content
    if st.session_state.current_page == "dashboard":
        dashboard.show()
    elif st.session_state.current_page == "projects":
        projects.show()
    elif st.session_state.current_page == "work_orders":
        work_orders.show()
    elif st.session_state.current_page == "cutting_lists":
        cutting_lists.show()
    elif st.session_state.current_page == "balance_orders":
        balance_orders.show()
    elif st.session_state.current_page == "production_log":
        production_log.show()
    elif st.session_state.current_page == "daily_targets":
        daily_targets.show()
    elif st.session_state.current_page == "dispatch":
        dispatch.show()
    elif st.session_state.current_page == "audit_trail":
        audit_trail.show()
    elif st.session_state.current_page == "users" and st.session_state.user_role == "Admin":
        users.show()

if __name__ == "__main__":
    main()
