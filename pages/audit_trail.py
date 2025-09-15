import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database import get_db
from sqlalchemy import text

def show():
    st.title("📜 Audit Trail")
    
    st.markdown("""
    The audit trail provides a complete history of all changes made to the system.
    Every create, update, and delete operation is recorded with timestamps and user information.
    """)
    
    # Permission check - only admins and project managers can view audit trail
    if st.session_state.user_role not in ["Admin", "Project Manager"]:
        st.warning("You don't have permission to view the audit trail.")
        return
    
    tab1, tab2 = st.tabs(["🔍 View Audit Trail", "📊 Audit Analytics"])
    
    with tab1:
        show_audit_trail()
    
    with tab2:
        show_audit_analytics()

def show_audit_trail():
    st.subheader("Audit Trail Records")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Date range filter
        start_date = st.date_input("From Date", value=date.today() - timedelta(days=7), key="audit_start_date")
    
    with col2:
        end_date = st.date_input("To Date", value=date.today(), key="audit_end_date")
    
    with col3:
        # Table filter
        table_options = ["All", "projects", "work_orders", "cutting_lists", "balance_orders", 
                        "production_log", "daily_targets", "dispatch", "users"]
        table_filter = st.selectbox("Filter by Table", options=table_options, key="audit_table_filter")
    
    with col4:
        # Action filter
        action_filter = st.selectbox("Filter by Action", 
                                   options=["All", "CREATE", "UPDATE", "DELETE"],
                                   key="audit_action_filter")
    
    # Additional filters
    col1, col2 = st.columns(2)
    
    with col1:
        # User filter
        db = get_db()
        users = db.execute(text("SELECT DISTINCT u.username FROM audit_trail at JOIN users u ON at.user_id = u.id ORDER BY u.username")).fetchall()
        user_options = ["All"] + [user[0] for user in users]
        user_filter = st.selectbox("Filter by User", options=user_options, key="audit_user_filter")
        db.close()
    
    with col2:
        search_term = st.text_input("Search", placeholder="Record ID, old value, or new value...", key="audit_search")
    
    # Build query with filters
    query = """
        SELECT 
            at.id,
            at.table_name,
            at.record_id,
            at.action,
            at.field_name,
            at.old_value,
            at.new_value,
            u.username as user_name,
            at.timestamp
        FROM audit_trail at
        LEFT JOIN users u ON at.user_id = u.id
        WHERE DATE(at.timestamp) >= :start_date AND DATE(at.timestamp) <= :end_date
    """
    params = {
        "start_date": start_date,
        "end_date": end_date
    }
    
    if table_filter != "All":
        query += " AND at.table_name = :table_name"
        params["table_name"] = table_filter
    
    if action_filter != "All":
        query += " AND at.action = :action"
        params["action"] = action_filter
    
    if user_filter != "All":
        query += " AND u.username = :username"
        params["username"] = user_filter
    
    if search_term:
        query += " AND (CAST(at.record_id AS TEXT) LIKE :search OR LOWER(at.old_value) LIKE LOWER(:search) OR LOWER(at.new_value) LIKE LOWER(:search))"
        params["search"] = f"%{search_term}%"
    
    query += " ORDER BY at.timestamp DESC LIMIT 1000"  # Limit for performance
    
    try:
        db = get_db()
        result = db.execute(text(query), params)
        audit_records = result.fetchall()
        db.close()
        
        if audit_records:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_records = len(audit_records)
            create_actions = len([r for r in audit_records if r[3] == "CREATE"])
            update_actions = len([r for r in audit_records if r[3] == "UPDATE"])
            delete_actions = len([r for r in audit_records if r[3] == "DELETE"])
            
            col1.metric("Total Records", total_records)
            col2.metric("Creates", create_actions)
            col3.metric("Updates", update_actions)
            col4.metric("Deletes", delete_actions)
            
            st.divider()
            
            # Display options
            col1, col2 = st.columns(2)
            with col1:
                show_details = st.checkbox("Show Field Details", value=True)
            with col2:
                records_per_page = st.selectbox("Records per page", options=[50, 100, 200], index=0)
            
            # Pagination
            total_pages = (total_records + records_per_page - 1) // records_per_page
            if total_pages > 1:
                page = st.selectbox("Page", options=list(range(1, total_pages + 1))) - 1
                start_idx = page * records_per_page
                end_idx = min(start_idx + records_per_page, total_records)
                display_records = audit_records[start_idx:end_idx]
            else:
                display_records = audit_records[:records_per_page]
            
            # Display audit records
            for record in display_records:
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        # Action with color coding
                        action_color = {
                            "CREATE": "🟢",
                            "UPDATE": "🟡",
                            "DELETE": "🔴"
                        }
                        st.write(f"{action_color.get(record[3], '⚪')} **{record[3]}** on {record[1]}")
                        st.write(f"Record ID: {record[2]}")
                        st.write(f"User: {record[7] or 'System'}")
                        st.write(f"Time: {record[8].strftime('%Y-%m-%d %H:%M:%S') if record[8] else 'N/A'}")
                    
                    with col2:
                        if show_details and record[3] == "UPDATE" and record[4]:  # Field-level changes
                            st.write(f"**Field:** {record[4]}")
                            
                            if record[5] and record[6]:  # Both old and new values
                                st.write(f"**Old Value:** `{record[5][:100]}{'...' if len(str(record[5])) > 100 else ''}`")
                                st.write(f"**New Value:** `{record[6][:100]}{'...' if len(str(record[6])) > 100 else ''}`")
                            elif record[6]:  # Only new value (creation)
                                st.write(f"**Value:** `{record[6][:100]}{'...' if len(str(record[6])) > 100 else ''}`")
                        elif record[3] in ["CREATE", "DELETE"]:
                            st.write(f"**Action:** {record[3]} operation")
                            if record[3] == "CREATE":
                                st.success("Record was created")
                            else:
                                st.error("Record was deleted")
                    
                    with col3:
                        # Additional actions
                        if st.button("📋 View Details", key=f"view_audit_{record[0]}"):
                            st.session_state[f"show_audit_details_{record[0]}"] = True
                    
                    # Detailed view
                    if st.session_state.get(f"show_audit_details_{record[0]}", False):
                        with st.expander(f"📋 Full Details - {record[1]} #{record[2]}", expanded=True):
                            details_col1, details_col2 = st.columns(2)
                            
                            with details_col1:
                                st.write(f"**Audit ID:** {record[0]}")
                                st.write(f"**Table:** {record[1]}")
                                st.write(f"**Record ID:** {record[2]}")
                                st.write(f"**Action:** {record[3]}")
                            
                            with details_col2:
                                st.write(f"**Field:** {record[4] or 'N/A'}")
                                st.write(f"**User:** {record[7] or 'System'}")
                                st.write(f"**Timestamp:** {record[8]}")
                            
                            if record[5]:
                                st.write(f"**Old Value:**")
                                st.code(record[5], language="text")
                            
                            if record[6]:
                                st.write(f"**New Value:**")
                                st.code(record[6], language="text")
                            
                            if st.button("Close Details", key=f"close_audit_{record[0]}"):
                                st.session_state[f"show_audit_details_{record[0]}"] = False
                                st.rerun()
                    
                    st.divider()
            
            # Export functionality
            if st.button("📥 Export Audit Trail"):
                df_audit = pd.DataFrame(audit_records, columns=[
                    'Audit ID', 'Table', 'Record ID', 'Action', 'Field', 'Old Value', 'New Value', 'User', 'Timestamp'
                ])
                
                csv = df_audit.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"audit_trail_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
                
        else:
            st.info("No audit records found for the selected criteria.")
            
    except Exception as e:
        st.error(f"Error loading audit trail: {str(e)}")

def show_audit_analytics():
    st.subheader("📊 Audit Analytics")
    
    # Date range for analytics
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Analysis From", value=date.today() - timedelta(days=30), key="analytics_audit_start")
    with col2:
        end_date = st.date_input("Analysis To", value=date.today(), key="analytics_audit_end")
    
    try:
        db = get_db()
        
        # Activity overview
        col1, col2, col3, col4 = st.columns(4)
        
        # Total activities
        total_activities = db.execute(text("""
            SELECT COUNT(*) FROM audit_trail 
            WHERE DATE(timestamp) >= :start_date AND DATE(timestamp) <= :end_date
        """), {"start_date": start_date, "end_date": end_date}).fetchone()[0]
        
        # Unique users
        unique_users = db.execute(text("""
            SELECT COUNT(DISTINCT user_id) FROM audit_trail 
            WHERE DATE(timestamp) >= :start_date AND DATE(timestamp) <= :end_date
        """), {"start_date": start_date, "end_date": end_date}).fetchone()[0]
        
        # Most active table
        most_active_table = db.execute(text("""
            SELECT table_name, COUNT(*) as activity_count 
            FROM audit_trail 
            WHERE DATE(timestamp) >= :start_date AND DATE(timestamp) <= :end_date
            GROUP BY table_name 
            ORDER BY activity_count DESC 
            LIMIT 1
        """), {"start_date": start_date, "end_date": end_date}).fetchone()
        
        # Peak activity day
        peak_day = db.execute(text("""
            SELECT DATE(timestamp) as activity_date, COUNT(*) as daily_count 
            FROM audit_trail 
            WHERE DATE(timestamp) >= :start_date AND DATE(timestamp) <= :end_date
            GROUP BY DATE(timestamp) 
            ORDER BY daily_count DESC 
            LIMIT 1
        """), {"start_date": start_date, "end_date": end_date}).fetchone()
        
        col1.metric("Total Activities", total_activities)
        col2.metric("Active Users", unique_users)
        col3.metric("Most Active Table", most_active_table[0] if most_active_table else "N/A")
        col4.metric("Peak Activity", f"{peak_day[1]} activities on {peak_day[0]}" if peak_day else "N/A")
        
        st.divider()
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Activity by action type
            st.subheader("Activity by Action Type")
            action_data = db.execute(text("""
                SELECT action, COUNT(*) as count 
                FROM audit_trail 
                WHERE DATE(timestamp) >= :start_date AND DATE(timestamp) <= :end_date
                GROUP BY action
                ORDER BY count DESC
            """), {"start_date": start_date, "end_date": end_date}).fetchall()
            
            if action_data:
                df_actions = pd.DataFrame(action_data, columns=['Action', 'Count'])
                st.bar_chart(df_actions.set_index('Action'))
            else:
                st.info("No activity data available.")
        
        with col2:
            # Activity by table
            st.subheader("Activity by Table")
            table_data = db.execute(text("""
                SELECT table_name, COUNT(*) as count 
                FROM audit_trail 
                WHERE DATE(timestamp) >= :start_date AND DATE(timestamp) <= :end_date
                GROUP BY table_name
                ORDER BY count DESC
                LIMIT 10
            """), {"start_date": start_date, "end_date": end_date}).fetchall()
            
            if table_data:
                df_tables = pd.DataFrame(table_data, columns=['Table', 'Count'])
                st.bar_chart(df_tables.set_index('Table'))
            else:
                st.info("No table activity data available.")
        
        # Daily activity trend
        st.subheader("📈 Daily Activity Trend")
        daily_data = db.execute(text("""
            SELECT 
                DATE(timestamp) as activity_date,
                COUNT(*) as total_activities,
                COUNT(CASE WHEN action = 'CREATE' THEN 1 END) as creates,
                COUNT(CASE WHEN action = 'UPDATE' THEN 1 END) as updates,
                COUNT(CASE WHEN action = 'DELETE' THEN 1 END) as deletes
            FROM audit_trail 
            WHERE DATE(timestamp) >= :start_date AND DATE(timestamp) <= :end_date
            GROUP BY DATE(timestamp)
            ORDER BY activity_date
        """), {"start_date": start_date, "end_date": end_date}).fetchall()
        
        if daily_data:
            df_daily = pd.DataFrame(daily_data, columns=['Date', 'Total', 'Creates', 'Updates', 'Deletes'])
            st.line_chart(df_daily.set_index('Date'))
        else:
            st.info("No daily activity data available.")
        
        # User activity ranking
        st.subheader("👥 Most Active Users")
        user_data = db.execute(text("""
            SELECT 
                u.username,
                COUNT(at.id) as total_actions,
                COUNT(CASE WHEN at.action = 'CREATE' THEN 1 END) as creates,
                COUNT(CASE WHEN at.action = 'UPDATE' THEN 1 END) as updates,
                COUNT(CASE WHEN at.action = 'DELETE' THEN 1 END) as deletes
            FROM audit_trail at
            JOIN users u ON at.user_id = u.id
            WHERE DATE(at.timestamp) >= :start_date AND DATE(at.timestamp) <= :end_date
            GROUP BY u.username
            ORDER BY total_actions DESC
            LIMIT 10
        """), {"start_date": start_date, "end_date": end_date}).fetchall()
        
        if user_data:
            df_users = pd.DataFrame(user_data, columns=['User', 'Total Actions', 'Creates', 'Updates', 'Deletes'])
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("No user activity data available.")
        
        # Recent high-impact changes
        st.subheader("🚨 Recent High-Impact Changes")
        high_impact_data = db.execute(text("""
            SELECT 
                at.table_name,
                at.record_id,
                at.action,
                u.username,
                at.timestamp
            FROM audit_trail at
            LEFT JOIN users u ON at.user_id = u.id
            WHERE DATE(at.timestamp) >= :start_date AND DATE(at.timestamp) <= :end_date
                AND (at.action = 'DELETE' OR at.table_name IN ('projects', 'work_orders'))
            ORDER BY at.timestamp DESC
            LIMIT 20
        """), {"start_date": start_date, "end_date": end_date}).fetchall()
        
        if high_impact_data:
            df_high_impact = pd.DataFrame(high_impact_data, columns=['Table', 'Record ID', 'Action', 'User', 'Timestamp'])
            st.dataframe(df_high_impact, use_container_width=True)
        else:
            st.info("No high-impact changes in the selected period.")
        
        db.close()
        
    except Exception as e:
        st.error(f"Error loading audit analytics: {str(e)}")
