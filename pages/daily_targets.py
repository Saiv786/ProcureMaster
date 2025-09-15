import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from database import get_db, log_audit_trail
from sqlalchemy import text

def show():
    st.title("🎯 Daily Targets")
    
    tab1, tab2, tab3 = st.tabs(["📋 All Targets", "➕ Add Target", "📊 Performance"])
    
    with tab1:
        show_daily_targets()
    
    with tab2:
        add_daily_target_form()
    
    with tab3:
        show_target_performance()

def show_daily_targets():
    st.subheader("Daily Targets")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   options=["All", "Not Started", "In Progress", "Completed"],
                                   key="target_status_filter")
    
    with col2:
        # Date filter
        date_filter = st.selectbox("Filter by Date",
                                 options=["All", "Today", "This Week", "Overdue"],
                                 key="target_date_filter")
    
    with col3:
        # Get projects for filter
        db = get_db()
        projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
        project_options = ["All"] + [f"{p[1]} (ID: {p[0]})" for p in projects]
        project_filter = st.selectbox("Filter by Project", options=project_options, key="target_project_filter")
        db.close()
    
    with col4:
        # Get assigned users for filter
        db = get_db()
        users = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
        user_options = ["All"] + [f"{u[1]} (ID: {u[0]})" for u in users]
        assigned_filter = st.selectbox("Filter by Assigned", options=user_options, key="target_assigned_filter")
        db.close()
    
    # Search
    search_term = st.text_input("Search Targets", placeholder="Order number or description...", key="target_search")
    
    # Build query with filters
    query = """
        SELECT 
            dt.id,
            dt.order_number,
            p.name as project_name,
            dt.description,
            dt.target_quantity,
            dt.target_date,
            u.username as assigned_to,
            dt.status,
            dt.actual_quantity,
            dt.completion_date,
            dt.notes,
            creator.username as created_by,
            dt.created_at
        FROM daily_targets dt
        LEFT JOIN projects p ON dt.project_id = p.id
        LEFT JOIN users u ON dt.assigned_to = u.id
        LEFT JOIN users creator ON dt.created_by = creator.id
        WHERE 1=1
    """
    params = {}
    
    if status_filter != "All":
        query += " AND dt.status = :status"
        params["status"] = status_filter
    
    if date_filter == "Today":
        query += " AND dt.target_date = CURRENT_DATE"
    elif date_filter == "This Week":
        query += " AND dt.target_date >= CURRENT_DATE AND dt.target_date < CURRENT_DATE + INTERVAL '7 days'"
    elif date_filter == "Overdue":
        query += " AND dt.target_date < CURRENT_DATE AND dt.status != 'Completed'"
    
    if project_filter != "All":
        project_id = project_filter.split("ID: ")[1].split(")")[0]
        query += " AND dt.project_id = :project_id"
        params["project_id"] = int(project_id)
    
    if assigned_filter != "All":
        assigned_id = assigned_filter.split("ID: ")[1].split(")")[0]
        query += " AND dt.assigned_to = :assigned_to"
        params["assigned_to"] = int(assigned_id)
    
    if search_term:
        query += " AND (LOWER(dt.order_number) LIKE LOWER(:search) OR LOWER(dt.description) LIKE LOWER(:search))"
        params["search"] = f"%{search_term}%"
    
    query += " ORDER BY dt.target_date ASC, dt.status ASC, dt.created_at DESC"
    
    try:
        db = get_db()
        result = db.execute(text(query), params)
        targets = result.fetchall()
        db.close()
        
        if targets:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_targets = len(targets)
            completed_targets = len([t for t in targets if t[7] == "Completed"])
            overdue_targets = len([t for t in targets if t[5] and t[5] < date.today() and t[7] != "Completed"])
            today_targets = len([t for t in targets if t[5] == date.today()])
            
            col1.metric("Total Targets", total_targets)
            col2.metric("Completed", completed_targets)
            col3.metric("Overdue", overdue_targets, delta=f"-{overdue_targets}" if overdue_targets > 0 else "0")
            col4.metric("Due Today", today_targets)
            
            st.divider()
            
            # Display targets
            for target in targets:
                with st.container():
                    # Check if overdue
                    is_overdue = target[5] and target[5] < date.today() and target[7] != "Completed"
                    is_today = target[5] == date.today()
                    
                    if is_overdue:
                        st.error("🚨 OVERDUE TARGET")
                    elif is_today:
                        st.warning("⏰ DUE TODAY")
                    
                    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
                    
                    with col1:
                        st.write(f"**Order: {target[1]}**")
                        st.write(f"Project: {target[2] or 'N/A'}")
                        if target[3]:  # Description
                            st.write(f"Description: {target[3][:50]}{'...' if len(target[3]) > 50 else ''}")
                        st.write(f"Assigned to: {target[6] or 'Unassigned'}")
                    
                    with col2:
                        # Status with color coding
                        status_color = {
                            "Not Started": "🔴",
                            "In Progress": "🟡",
                            "Completed": "🟢"
                        }
                        st.write(f"Status: {status_color.get(target[7], '⚪')} **{target[7]}**")
                        st.write(f"Target Date: {target[5]}")
                        st.write(f"Target Qty: {target[4] or 0}")
                        st.write(f"Actual Qty: {target[8] or 0}")
                        
                        # Progress calculation
                        if target[4] and target[4] > 0:
                            progress = min((target[8] or 0) / target[4], 1.0)
                            st.progress(progress)
                            st.write(f"{progress:.1%} Complete")
                    
                    with col3:
                        # Quick status and quantity update
                        if (st.session_state.user_role in ["Admin", "Project Manager"] or 
                            (target[6] and st.session_state.username == target[6])):
                            
                            # Status update
                            new_status = st.selectbox(
                                "Update Status",
                                options=["Not Started", "In Progress", "Completed"],
                                index=["Not Started", "In Progress", "Completed"].index(target[7]),
                                key=f"target_status_update_{target[0]}"
                            )
                            
                            # Actual quantity update
                            new_actual_qty = st.number_input(
                                "Actual Qty",
                                min_value=0,
                                value=target[8] or 0,
                                key=f"actual_qty_update_{target[0]}"
                            )
                            
                            if new_status != target[7] or new_actual_qty != (target[8] or 0):
                                if st.button("Update Progress", key=f"update_target_progress_{target[0]}"):
                                    if update_target_progress(target[0], new_status, new_actual_qty, target[7], target[8] or 0):
                                        st.success("Target updated!")
                                        st.rerun()
                    
                    with col4:
                        if st.session_state.user_role in ["Admin", "Project Manager"]:
                            if st.button("📝 Edit", key=f"edit_target_{target[0]}"):
                                st.session_state[f"edit_target_{target[0]}"] = True
                            
                            if st.button("🗑️ Delete", key=f"delete_target_{target[0]}"):
                                if delete_target(target[0]):
                                    st.success("Target deleted!")
                                    st.rerun()
                        
                        # Notes display
                        if target[10]:  # Notes
                            with st.expander("📝 Notes"):
                                st.write(target[10])
                    
                    # Edit form
                    if st.session_state.get(f"edit_target_{target[0]}", False):
                        edit_target_form(target)
                    
                    st.divider()
        else:
            st.info("No targets found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error loading targets: {str(e)}")

def edit_target_form(target):
    st.subheader(f"Edit Target: {target[1]}")
    
    # Get projects and users for dropdowns
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    users = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
    db.close()
    
    with st.form(f"edit_target_form_{target[0]}"):
        col1, col2 = st.columns(2)
        
        with col1:
            order_number = st.text_input("Order Number", value=target[1])
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            current_project = next((f"{target[2]} (ID: {i})" for i, name in [(p[0], p[1]) for p in projects] if name == target[2]), project_options[0] if project_options else "")
            project = st.selectbox("Project", options=project_options, 
                                 index=project_options.index(current_project) if current_project in project_options else 0)
            
            description = st.text_area("Description", value=target[3] or "", height=80)
            target_quantity = st.number_input("Target Quantity", value=target[4] if target[4] else 1, min_value=1)
        
        with col2:
            target_date = st.date_input("Target Date", value=target[5] if target[5] else date.today())
            
            user_options = ["Unassigned"] + [f"{u[1]} (ID: {u[0]})" for u in users]
            current_assigned = next((f"{target[6]} (ID: {i})" for i, name in [(u[0], u[1]) for u in users] if name == target[6]), "Unassigned")
            assigned_to = st.selectbox("Assigned To", options=user_options,
                                     index=user_options.index(current_assigned) if current_assigned in user_options else 0)
            
            status = st.selectbox("Status", options=["Not Started", "In Progress", "Completed"],
                                index=["Not Started", "In Progress", "Completed"].index(target[7]))
            actual_quantity = st.number_input("Actual Quantity", value=target[8] if target[8] else 0, min_value=0)
        
        notes = st.text_area("Notes", value=target[10] or "", height=60)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Update Target"):
                project_id = int(project.split("ID: ")[1].split(")")[0])
                assigned_user_id = None if assigned_to == "Unassigned" else int(assigned_to.split("ID: ")[1].split(")")[0])
                
                if update_target(target[0], order_number, project_id, description, target_quantity,
                               target_date, assigned_user_id, status, actual_quantity, notes):
                    st.success("Target updated successfully!")
                    st.session_state[f"edit_target_{target[0]}"] = False
                    st.rerun()
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state[f"edit_target_{target[0]}"] = False
                st.rerun()

def add_daily_target_form():
    st.subheader("Add New Daily Target")
    
    # Get projects and users for dropdowns
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    users = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
    db.close()
    
    if not projects:
        st.warning("No projects available. Please create a project first.")
        return
    
    with st.form("add_target_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            order_number = st.text_input("Order Number*", placeholder="e.g., ORD-001")
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            project = st.selectbox("Project*", options=project_options)
            description = st.text_area("Description", placeholder="Target description and specifications", height=80)
            target_quantity = st.number_input("Target Quantity*", min_value=1, value=1)
        
        with col2:
            target_date = st.date_input("Target Date*", value=date.today())
            
            user_options = ["Unassigned"] + [f"{u[1]} (ID: {u[0]})" for u in users]
            assigned_to = st.selectbox("Assigned To", options=user_options)
            
            status = st.selectbox("Status", options=["Not Started", "In Progress", "Completed"])
            actual_quantity = st.number_input("Actual Quantity", min_value=0, value=0)
        
        notes = st.text_area("Notes", placeholder="Additional notes and comments", height=60)
        
        submitted = st.form_submit_button("🎯 Create Target")
        
        if submitted:
            if not order_number.strip():
                st.error("Order Number is required!")
                return
            
            project_id = int(project.split("ID: ")[1].split(")")[0])
            assigned_user_id = None if assigned_to == "Unassigned" else int(assigned_to.split("ID: ")[1].split(")")[0])
            
            if create_target(order_number, project_id, description, target_quantity, target_date, 
                           assigned_user_id, status, actual_quantity, notes):
                st.success("Target created successfully!")
                st.rerun()

def show_target_performance():
    st.subheader("📊 Target Performance Analytics")
    
    # Date range for analytics
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Analysis From", value=date.today() - timedelta(days=30), key="perf_start")
    with col2:
        end_date = st.date_input("Analysis To", value=date.today(), key="perf_end")
    
    try:
        db = get_db()
        
        # Overall performance metrics
        col1, col2, col3, col4 = st.columns(4)
        
        # Total targets in period
        total_targets = db.execute(text("""
            SELECT COUNT(*) FROM daily_targets 
            WHERE target_date >= :start_date AND target_date <= :end_date
        """), {"start_date": start_date, "end_date": end_date}).fetchone()[0]
        
        # Completed targets
        completed_targets = db.execute(text("""
            SELECT COUNT(*) FROM daily_targets 
            WHERE target_date >= :start_date AND target_date <= :end_date AND status = 'Completed'
        """), {"start_date": start_date, "end_date": end_date}).fetchone()[0]
        
        # On-time completion rate
        on_time_completed = db.execute(text("""
            SELECT COUNT(*) FROM daily_targets 
            WHERE target_date >= :start_date AND target_date <= :end_date 
                AND status = 'Completed' 
                AND (completion_date IS NULL OR completion_date <= target_date)
        """), {"start_date": start_date, "end_date": end_date}).fetchone()[0]
        
        # Average completion rate
        completion_data = db.execute(text("""
            SELECT AVG(CASE WHEN target_quantity > 0 THEN (actual_quantity * 100.0 / target_quantity) ELSE 0 END) 
            FROM daily_targets 
            WHERE target_date >= :start_date AND target_date <= :end_date AND target_quantity > 0
        """), {"start_date": start_date, "end_date": end_date}).fetchone()[0]
        
        col1.metric("Total Targets", total_targets)
        col2.metric("Completed", completed_targets, f"{(completed_targets/total_targets*100):.1f}%" if total_targets > 0 else "0%")
        col3.metric("On-Time Rate", f"{(on_time_completed/completed_targets*100):.1f}%" if completed_targets > 0 else "0%")
        col4.metric("Avg Completion", f"{completion_data:.1f}%" if completion_data else "0%")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Targets completion trend
            st.subheader("📈 Daily Completion Trend")
            trend_data = db.execute(text("""
                SELECT 
                    target_date,
                    COUNT(*) as total_targets,
                    COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_targets
                FROM daily_targets 
                WHERE target_date >= :start_date AND target_date <= :end_date
                GROUP BY target_date
                ORDER BY target_date
            """), {"start_date": start_date, "end_date": end_date}).fetchall()
            
            if trend_data:
                df_trend = pd.DataFrame(trend_data, columns=['Date', 'Total Targets', 'Completed Targets'])
                df_trend['Completion Rate'] = (df_trend['Completed Targets'] / df_trend['Total Targets'] * 100).round(1)
                
                fig_trend = px.line(df_trend, x='Date', y='Completion Rate',
                                   title="Daily Completion Rate (%)",
                                   markers=True)
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No trend data available.")
        
        with col2:
            # Performance by team member
            st.subheader("👥 Performance by Team Member")
            member_data = db.execute(text("""
                SELECT 
                    u.username,
                    COUNT(dt.id) as total_assigned,
                    COUNT(CASE WHEN dt.status = 'Completed' THEN 1 END) as completed,
                    AVG(CASE WHEN dt.target_quantity > 0 THEN (dt.actual_quantity * 100.0 / dt.target_quantity) ELSE 0 END) as avg_completion_rate
                FROM daily_targets dt
                JOIN users u ON dt.assigned_to = u.id
                WHERE dt.target_date >= :start_date AND dt.target_date <= :end_date
                GROUP BY u.username
                ORDER BY completed DESC
            """), {"start_date": start_date, "end_date": end_date}).fetchall()
            
            if member_data:
                df_member = pd.DataFrame(member_data, columns=['Team Member', 'Total Assigned', 'Completed', 'Avg Completion %'])
                df_member['Completion Rate %'] = (df_member['Completed'] / df_member['Total Assigned'] * 100).round(1)
                st.dataframe(df_member, use_container_width=True)
            else:
                st.info("No team member performance data available.")
        
        # Status distribution
        st.subheader("📊 Target Status Distribution")
        status_data = db.execute(text("""
            SELECT 
                status,
                COUNT(*) as count
            FROM daily_targets 
            WHERE target_date >= :start_date AND target_date <= :end_date
            GROUP BY status
        """), {"start_date": start_date, "end_date": end_date}).fetchall()
        
        if status_data:
            df_status = pd.DataFrame(status_data, columns=['Status', 'Count'])
            fig_status = px.pie(df_status, values='Count', names='Status',
                               title="Target Status Distribution")
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("No status distribution data available.")
        
        db.close()
        
    except Exception as e:
        st.error(f"Error loading performance analytics: {str(e)}")

def create_target(order_number, project_id, description, target_quantity, target_date, assigned_to, status, actual_quantity, notes):
    """Create a new daily target"""
    try:
        db = get_db()
        
        result = db.execute(text("""
            INSERT INTO daily_targets (order_number, project_id, description, target_quantity,
                                     target_date, assigned_to, status, actual_quantity, notes, created_by)
            VALUES (:order_number, :project_id, :description, :target_quantity,
                   :target_date, :assigned_to, :status, :actual_quantity, :notes, :created_by)
            RETURNING id
        """), {
            "order_number": order_number,
            "project_id": project_id,
            "description": description if description else None,
            "target_quantity": target_quantity,
            "target_date": target_date,
            "assigned_to": assigned_to,
            "status": status,
            "actual_quantity": actual_quantity,
            "notes": notes if notes else None,
            "created_by": st.session_state.user_id
        })
        
        target_id = result.fetchone()[0]
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("daily_targets", target_id, "CREATE")
        
        return True
        
    except Exception as e:
        st.error(f"Error creating target: {str(e)}")
        return False

def update_target(target_id, order_number, project_id, description, target_quantity, target_date, assigned_to, status, actual_quantity, notes):
    """Update an existing target"""
    try:
        db = get_db()
        
        # Get old values for audit
        old_result = db.execute(text("SELECT * FROM daily_targets WHERE id = :id"), {"id": target_id})
        old_target = old_result.fetchone()
        
        # Set completion date if status changed to Completed
        completion_date = None
        if status == "Completed" and old_target and old_target[7] != "Completed":
            completion_date = date.today()
        
        update_query = """
            UPDATE daily_targets 
            SET order_number = :order_number, project_id = :project_id, description = :description,
                target_quantity = :target_quantity, target_date = :target_date, assigned_to = :assigned_to,
                status = :status, actual_quantity = :actual_quantity, notes = :notes,
                updated_at = CURRENT_TIMESTAMP
        """
        
        update_params = {
            "order_number": order_number,
            "project_id": project_id,
            "description": description if description else None,
            "target_quantity": target_quantity,
            "target_date": target_date,
            "assigned_to": assigned_to,
            "status": status,
            "actual_quantity": actual_quantity,
            "notes": notes if notes else None,
            "id": target_id
        }
        
        if completion_date:
            update_query += ", completion_date = :completion_date"
            update_params["completion_date"] = completion_date
        
        update_query += " WHERE id = :id"
        
        db.execute(text(update_query), update_params)
        db.commit()
        db.close()
        
        # Log audit trail for changes
        if old_target:
            changes = [
                ("order_number", old_target[1], order_number),
                ("project_id", old_target[2], project_id),
                ("description", old_target[3], description),
                ("target_quantity", old_target[4], target_quantity),
                ("target_date", str(old_target[5]), str(target_date)),
                ("assigned_to", old_target[6], assigned_to),
                ("status", old_target[7], status),
                ("actual_quantity", old_target[8], actual_quantity),
                ("notes", old_target[10], notes)
            ]
            
            for field, old_val, new_val in changes:
                if str(old_val) != str(new_val):
                    log_audit_trail("daily_targets", target_id, "UPDATE", field, str(old_val), str(new_val))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating target: {str(e)}")
        return False

def update_target_progress(target_id, new_status, new_actual_qty, old_status, old_actual_qty):
    """Update target progress (status and actual quantity)"""
    try:
        db = get_db()
        
        # Set completion date if status changed to Completed
        update_query = """
            UPDATE daily_targets 
            SET status = :status, actual_quantity = :actual_quantity, updated_at = CURRENT_TIMESTAMP
        """
        
        update_params = {
            "status": new_status,
            "actual_quantity": new_actual_qty,
            "id": target_id
        }
        
        if new_status == "Completed" and old_status != "Completed":
            update_query += ", completion_date = :completion_date"
            update_params["completion_date"] = date.today()
        
        update_query += " WHERE id = :id"
        
        db.execute(text(update_query), update_params)
        db.commit()
        db.close()
        
        # Log audit trail for changes
        if new_status != old_status:
            log_audit_trail("daily_targets", target_id, "UPDATE", "status", old_status, new_status)
        
        if new_actual_qty != old_actual_qty:
            log_audit_trail("daily_targets", target_id, "UPDATE", "actual_quantity", str(old_actual_qty), str(new_actual_qty))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating target progress: {str(e)}")
        return False

def delete_target(target_id):
    """Delete a target"""
    try:
        db = get_db()
        
        db.execute(text("DELETE FROM daily_targets WHERE id = :id"), {"id": target_id})
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("daily_targets", target_id, "DELETE")
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting target: {str(e)}")
        return False
