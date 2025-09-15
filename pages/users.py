import streamlit as st
import pandas as pd
from datetime import datetime
from auth import create_user, get_all_users, update_user_role, delete_user

def show():
    st.title("👥 User Management")
    
    # Permission check - only admins can manage users
    if st.session_state.user_role != "Admin":
        st.error("You don't have permission to manage users.")
        return
    
    tab1, tab2 = st.tabs(["👥 All Users", "➕ Add User"])
    
    with tab1:
        show_users_list()
    
    with tab2:
        add_user_form()

def show_users_list():
    st.subheader("All Users")
    
    # Search and filter
    col1, col2 = st.columns(2)
    
    with col1:
        role_filter = st.selectbox("Filter by Role", 
                                 options=["All", "Admin", "Project Manager", "Operator"],
                                 key="user_role_filter")
    
    with col2:
        search_term = st.text_input("Search Users", placeholder="Enter username...", key="user_search")
    
    try:
        users = get_all_users()
        
        # Apply filters
        if role_filter != "All":
            users = [user for user in users if user['role'] == role_filter]
        
        if search_term:
            users = [user for user in users if search_term.lower() in user['username'].lower()]
        
        if users:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_users = len(users)
            admin_count = len([u for u in users if u['role'] == 'Admin'])
            pm_count = len([u for u in users if u['role'] == 'Project Manager'])
            operator_count = len([u for u in users if u['role'] == 'Operator'])
            
            col1.metric("Total Users", total_users)
            col2.metric("Admins", admin_count)
            col3.metric("Project Managers", pm_count)
            col4.metric("Operators", operator_count)
            
            st.divider()
            
            # Display users
            for user in users:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                    
                    with col1:
                        st.write(f"**{user['username']}**")
                        # Role with color coding
                        role_color = {
                            "Admin": "🔴",
                            "Project Manager": "🟡",
                            "Operator": "🟢"
                        }
                        st.write(f"Role: {role_color.get(user['role'], '⚪')} **{user['role']}**")
                    
                    with col2:
                        st.write(f"User ID: {user['id']}")
                        st.write(f"Created: {user['created_at'].strftime('%Y-%m-%d') if user['created_at'] else 'N/A'}")
                    
                    with col3:
                        # Role update (can't change own role or demote last admin)
                        if user['id'] != st.session_state.user_id:
                            new_role = st.selectbox(
                                "Update Role",
                                options=["Admin", "Project Manager", "Operator"],
                                index=["Admin", "Project Manager", "Operator"].index(user['role']),
                                key=f"role_update_{user['id']}"
                            )
                            
                            if new_role != user['role']:
                                # Check if trying to remove last admin
                                if user['role'] == 'Admin' and admin_count == 1:
                                    st.warning("Cannot remove the last admin!")
                                else:
                                    if st.button("Update Role", key=f"update_role_{user['id']}"):
                                        success, message = update_user_role(user['id'], new_role)
                                        if success:
                                            st.success(message)
                                            st.rerun()
                                        else:
                                            st.error(message)
                        else:
                            st.info("You cannot change your own role")
                    
                    with col4:
                        # Delete user (can't delete self or last admin)
                        if user['id'] != st.session_state.user_id:
                            if user['role'] == 'Admin' and admin_count == 1:
                                st.warning("Cannot delete last admin")
                            else:
                                if st.button("🗑️ Delete User", key=f"delete_user_{user['id']}"):
                                    if st.session_state.get(f"confirm_delete_{user['id']}", False):
                                        success, message = delete_user(user['id'])
                                        if success:
                                            st.success(message)
                                            st.rerun()
                                        else:
                                            st.error(message)
                                    else:
                                        st.session_state[f"confirm_delete_{user['id']}"] = True
                                        st.warning("Click again to confirm deletion")
                        else:
                            st.info("Cannot delete yourself")
                        
                        # Activity summary
                        if st.button("📊 Activity", key=f"activity_{user['id']}"):
                            st.session_state[f"show_activity_{user['id']}"] = True
                    
                    # Activity details
                    if st.session_state.get(f"show_activity_{user['id']}", False):
                        show_user_activity(user)
                    
                    st.divider()
        else:
            st.info("No users found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error loading users: {str(e)}")

def show_user_activity(user):
    """Show user activity summary"""
    with st.expander(f"📊 Activity Summary for {user['username']}", expanded=True):
        try:
            from database import get_db
            from sqlalchemy import text
            
            db = get_db()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Projects created
                projects_created = db.execute(text("""
                    SELECT COUNT(*) FROM projects WHERE created_by = :user_id
                """), {"user_id": user['id']}).fetchone()[0]
                st.metric("Projects Created", projects_created)
                
                # Work orders created
                wo_created = db.execute(text("""
                    SELECT COUNT(*) FROM work_orders WHERE created_by = :user_id
                """), {"user_id": user['id']}).fetchone()[0]
                st.metric("Work Orders Created", wo_created)
            
            with col2:
                # Work orders assigned
                wo_assigned = db.execute(text("""
                    SELECT COUNT(*) FROM work_orders WHERE assigned_to = :user_id
                """), {"user_id": user['id']}).fetchone()[0]
                st.metric("Work Orders Assigned", wo_assigned)
                
                # Production entries
                production_entries = db.execute(text("""
                    SELECT COUNT(*) FROM production_log WHERE operator_id = :user_id OR created_by = :user_id
                """), {"user_id": user['id']}).fetchone()[0]
                st.metric("Production Entries", production_entries)
            
            with col3:
                # Targets assigned
                targets_assigned = db.execute(text("""
                    SELECT COUNT(*) FROM daily_targets WHERE assigned_to = :user_id
                """), {"user_id": user['id']}).fetchone()[0]
                st.metric("Targets Assigned", targets_assigned)
                
                # Audit trail entries
                audit_entries = db.execute(text("""
                    SELECT COUNT(*) FROM audit_trail WHERE user_id = :user_id
                """), {"user_id": user['id']}).fetchone()[0]
                st.metric("Total Actions", audit_entries)
            
            # Recent activity
            st.subheader("Recent Activity (Last 10)")
            recent_activity = db.execute(text("""
                SELECT 
                    table_name,
                    record_id,
                    action,
                    field_name,
                    timestamp
                FROM audit_trail 
                WHERE user_id = :user_id
                ORDER BY timestamp DESC 
                LIMIT 10
            """), {"user_id": user['id']}).fetchall()
            
            if recent_activity:
                df_activity = pd.DataFrame(recent_activity, columns=[
                    'Table', 'Record ID', 'Action', 'Field', 'Timestamp'
                ])
                st.dataframe(df_activity, use_container_width=True)
            else:
                st.info("No recent activity found.")
            
            db.close()
            
            if st.button("Close Activity", key=f"close_activity_{user['id']}"):
                st.session_state[f"show_activity_{user['id']}"] = False
                st.rerun()
                
        except Exception as e:
            st.error(f"Error loading user activity: {str(e)}")

def add_user_form():
    st.subheader("Add New User")
    
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username*", placeholder="Enter unique username")
            password = st.text_input("Password*", type="password", placeholder="Enter password")
        
        with col2:
            role = st.selectbox("Role*", options=["Operator", "Project Manager", "Admin"])
            confirm_password = st.text_input("Confirm Password*", type="password", placeholder="Confirm password")
        
        # Password strength indicator
        if password:
            strength = check_password_strength(password)
            if strength == "Weak":
                st.error("⚠️ Password is weak. Use at least 6 characters.")
            elif strength == "Medium":
                st.warning("⚡ Password is medium strength. Consider adding numbers or symbols.")
            else:
                st.success("✅ Password is strong.")
        
        submitted = st.form_submit_button("👥 Create User")
        
        if submitted:
            # Validation
            if not username.strip():
                st.error("Username is required!")
                return
            
            if not password:
                st.error("Password is required!")
                return
            
            if password != confirm_password:
                st.error("Passwords do not match!")
                return
            
            if len(password) < 6:
                st.error("Password must be at least 6 characters long!")
                return
            
            # Check username format
            if not username.isalnum() and '_' not in username:
                st.error("Username can only contain letters, numbers, and underscores!")
                return
            
            # Create user
            success, message = create_user(username, password, role)
            if success:
                st.success(message)
                st.info("User can now login with the provided credentials.")
                st.rerun()
            else:
                st.error(message)

def check_password_strength(password):
    """Check password strength"""
    if len(password) < 6:
        return "Weak"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    
    strength_score = sum([has_upper, has_lower, has_digit, has_symbol])
    
    if strength_score >= 3 and len(password) >= 8:
        return "Strong"
    elif strength_score >= 2 or len(password) >= 8:
        return "Medium"
    else:
        return "Weak"
