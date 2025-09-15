import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_db, log_audit_trail
from sqlalchemy import text

def show():
    st.title("📋 Work Orders")
    
    tab1, tab2 = st.tabs(["📋 All Work Orders", "➕ Add Work Order"])
    
    with tab1:
        show_work_orders_list()
    
    with tab2:
        if st.session_state.user_role in ["Admin", "Project Manager"]:
            add_work_order_form()
        else:
            st.warning("You don't have permission to create work orders.")

def show_work_orders_list():
    st.subheader("All Work Orders")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   options=["All", "Pending", "In Progress", "Completed", "Dispatched"],
                                   key="wo_status_filter")
    
    with col2:
        type_filter = st.selectbox("Filter by Type",
                                 options=["All", "Cutting", "Production", "Procurement"],
                                 key="wo_type_filter")
    
    with col3:
        priority_filter = st.selectbox("Filter by Priority",
                                     options=["All", "High", "Medium", "Low"],
                                     key="wo_priority_filter")
    
    with col4:
        # Get projects for filter
        db = get_db()
        projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
        project_options = ["All"] + [f"{p[1]} (ID: {p[0]})" for p in projects]
        project_filter = st.selectbox("Filter by Project", options=project_options, key="wo_project_filter")
        db.close()
    
    # Search
    search_term = st.text_input("Search Work Orders", placeholder="Enter WO number or description...", key="wo_search")
    
    # Build query with filters
    query = """
        SELECT 
            wo.id,
            wo.wo_number,
            p.name as project_name,
            wo.floor,
            wo.description,
            wo.wo_type,
            wo.status,
            wo.priority,
            wo.due_date,
            u.username as assigned_to,
            creator.username as created_by,
            wo.created_at
        FROM work_orders wo
        LEFT JOIN projects p ON wo.project_id = p.id
        LEFT JOIN users u ON wo.assigned_to = u.id
        LEFT JOIN users creator ON wo.created_by = creator.id
        WHERE 1=1
    """
    params = {}
    
    if status_filter != "All":
        query += " AND wo.status = :status"
        params["status"] = status_filter
    
    if type_filter != "All":
        query += " AND wo.wo_type = :wo_type"
        params["wo_type"] = type_filter
    
    if priority_filter != "All":
        query += " AND wo.priority = :priority"
        params["priority"] = priority_filter
    
    if project_filter != "All":
        project_id = project_filter.split("ID: ")[1].split(")")[0]
        query += " AND wo.project_id = :project_id"
        params["project_id"] = int(project_id)
    
    if search_term:
        query += " AND (LOWER(wo.wo_number) LIKE LOWER(:search) OR LOWER(wo.description) LIKE LOWER(:search))"
        params["search"] = f"%{search_term}%"
    
    query += " ORDER BY wo.created_at DESC"
    
    try:
        db = get_db()
        result = db.execute(text(query), params)
        work_orders = result.fetchall()
        db.close()
        
        if work_orders:
            for wo in work_orders:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
                    
                    with col1:
                        st.write(f"**{wo[1]}** ({wo[5]})")  # WO Number and Type
                        st.write(f"Project: {wo[2] or 'N/A'}")
                        st.write(f"Floor: {wo[3] or 'N/A'}")
                        if wo[4]:  # Description
                            st.write(f"Description: {wo[4][:50]}{'...' if len(wo[4]) > 50 else ''}")
                    
                    with col2:
                        # Status with color coding
                        status_color = {
                            "Pending": "🔴",
                            "In Progress": "🟡", 
                            "Completed": "🟢",
                            "Dispatched": "🔵"
                        }
                        st.write(f"Status: {status_color.get(wo[6], '⚪')} **{wo[6]}**")
                        st.write(f"Priority: {wo[7]}")
                        st.write(f"Due: {wo[8] or 'Not set'}")
                        st.write(f"Assigned: {wo[9] or 'Unassigned'}")
                    
                    with col3:
                        # Status update (only for assigned users or managers)
                        if (st.session_state.user_role in ["Admin", "Project Manager"] or 
                            (wo[9] and st.session_state.username == wo[9])):
                            
                            new_status = st.selectbox(
                                "Update Status",
                                options=["Pending", "In Progress", "Completed", "Dispatched"],
                                index=["Pending", "In Progress", "Completed", "Dispatched"].index(wo[6]),
                                key=f"status_update_{wo[0]}"
                            )
                            
                            if new_status != wo[6]:
                                if st.button("Update", key=f"update_status_{wo[0]}"):
                                    if update_work_order_status(wo[0], new_status, wo[6]):
                                        st.success("Status updated!")
                                        st.rerun()
                    
                    with col4:
                        if st.session_state.user_role in ["Admin", "Project Manager"]:
                            if st.button("📝 Edit", key=f"edit_wo_{wo[0]}"):
                                st.session_state[f"edit_wo_{wo[0]}"] = True
                            
                            if st.button("🗑️ Delete", key=f"delete_wo_{wo[0]}"):
                                if delete_work_order(wo[0]):
                                    st.success("Work order deleted!")
                                    st.rerun()
                    
                    # Edit form
                    if st.session_state.get(f"edit_wo_{wo[0]}", False):
                        edit_work_order_form(wo)
                    
                    st.divider()
        else:
            st.info("No work orders found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error loading work orders: {str(e)}")

def edit_work_order_form(wo):
    st.subheader(f"Edit Work Order: {wo[1]}")
    
    # Get projects and users for dropdowns
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    users = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
    db.close()
    
    with st.form(f"edit_wo_form_{wo[0]}"):
        col1, col2 = st.columns(2)
        
        with col1:
            wo_number = st.text_input("WO Number", value=wo[1])
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            current_project = next((f"{wo[2]} (ID: {i})" for i, name in [(p[0], p[1]) for p in projects] if name == wo[2]), project_options[0] if project_options else "")
            project = st.selectbox("Project", options=project_options, 
                                 index=project_options.index(current_project) if current_project in project_options else 0)
            floor = st.text_input("Floor", value=wo[3] or "")
            wo_type = st.selectbox("Type", options=["Cutting", "Production", "Procurement"],
                                 index=["Cutting", "Production", "Procurement"].index(wo[5]))
        
        with col2:
            priority = st.selectbox("Priority", options=["High", "Medium", "Low"],
                                  index=["High", "Medium", "Low"].index(wo[7]))
            due_date = st.date_input("Due Date", value=wo[8] if wo[8] else date.today())
            
            user_options = ["Unassigned"] + [f"{u[1]} (ID: {u[0]})" for u in users]
            current_assigned = next((f"{wo[9]} (ID: {i})" for i, name in [(u[0], u[1]) for u in users] if name == wo[9]), "Unassigned")
            assigned_to = st.selectbox("Assigned To", options=user_options,
                                     index=user_options.index(current_assigned) if current_assigned in user_options else 0)
        
        description = st.text_area("Description", value=wo[4] or "", height=100)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Update Work Order"):
                project_id = int(project.split("ID: ")[1].split(")")[0])
                assigned_user_id = None if assigned_to == "Unassigned" else int(assigned_to.split("ID: ")[1].split(")")[0])
                
                if update_work_order(wo[0], wo_number, project_id, floor, description, wo_type, 
                                    priority, due_date, assigned_user_id):
                    st.success("Work order updated successfully!")
                    st.session_state[f"edit_wo_{wo[0]}"] = False
                    st.rerun()
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state[f"edit_wo_{wo[0]}"] = False
                st.rerun()

def add_work_order_form():
    st.subheader("Add New Work Order")
    
    # Get projects and users for dropdowns
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    users = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
    db.close()
    
    if not projects:
        st.warning("No projects available. Please create a project first.")
        return
    
    with st.form("add_wo_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            wo_number = st.text_input("WO Number*", placeholder="e.g., WO-001")
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            project = st.selectbox("Project*", options=project_options)
            floor = st.text_input("Floor", placeholder="e.g., Ground Floor")
            wo_type = st.selectbox("Type*", options=["Cutting", "Production", "Procurement"])
        
        with col2:
            priority = st.selectbox("Priority", options=["Medium", "High", "Low"])
            due_date = st.date_input("Due Date")
            
            user_options = ["Unassigned"] + [f"{u[1]} (ID: {u[0]})" for u in users]
            assigned_to = st.selectbox("Assigned To", options=user_options)
        
        description = st.text_area("Description", placeholder="Work order description and requirements", height=100)
        
        submitted = st.form_submit_button("📋 Create Work Order")
        
        if submitted:
            if not wo_number.strip():
                st.error("WO Number is required!")
                return
            
            project_id = int(project.split("ID: ")[1].split(")")[0])
            assigned_user_id = None if assigned_to == "Unassigned" else int(assigned_to.split("ID: ")[1].split(")")[0])
            
            if create_work_order(wo_number, project_id, floor, description, wo_type, priority, due_date, assigned_user_id):
                st.success("Work order created successfully!")
                st.rerun()

def create_work_order(wo_number, project_id, floor, description, wo_type, priority, due_date, assigned_to):
    """Create a new work order"""
    try:
        db = get_db()
        
        # Check if WO number already exists
        existing = db.execute(text("SELECT id FROM work_orders WHERE wo_number = :wo_number"), 
                            {"wo_number": wo_number}).fetchone()
        if existing:
            st.error("Work Order number already exists!")
            db.close()
            return False
        
        result = db.execute(text("""
            INSERT INTO work_orders (wo_number, project_id, floor, description, wo_type, 
                                   priority, due_date, assigned_to, created_by)
            VALUES (:wo_number, :project_id, :floor, :description, :wo_type, 
                   :priority, :due_date, :assigned_to, :created_by)
            RETURNING id
        """), {
            "wo_number": wo_number,
            "project_id": project_id,
            "floor": floor if floor else None,
            "description": description if description else None,
            "wo_type": wo_type,
            "priority": priority,
            "due_date": due_date,
            "assigned_to": assigned_to,
            "created_by": st.session_state.user_id
        })
        
        wo_id = result.fetchone()[0]
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("work_orders", wo_id, "CREATE")
        
        return True
        
    except Exception as e:
        st.error(f"Error creating work order: {str(e)}")
        return False

def update_work_order(wo_id, wo_number, project_id, floor, description, wo_type, priority, due_date, assigned_to):
    """Update an existing work order"""
    try:
        db = get_db()
        
        # Get old values for audit
        old_result = db.execute(text("SELECT * FROM work_orders WHERE id = :id"), {"id": wo_id})
        old_wo = old_result.fetchone()
        
        db.execute(text("""
            UPDATE work_orders 
            SET wo_number = :wo_number, project_id = :project_id, floor = :floor,
                description = :description, wo_type = :wo_type, priority = :priority,
                due_date = :due_date, assigned_to = :assigned_to, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "wo_number": wo_number,
            "project_id": project_id,
            "floor": floor if floor else None,
            "description": description if description else None,
            "wo_type": wo_type,
            "priority": priority,
            "due_date": due_date,
            "assigned_to": assigned_to,
            "id": wo_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail for changes
        if old_wo:
            changes = [
                ("wo_number", old_wo[1], wo_number),
                ("project_id", old_wo[2], project_id),
                ("floor", old_wo[3], floor),
                ("description", old_wo[4], description),
                ("wo_type", old_wo[5], wo_type),
                ("priority", old_wo[7], priority),
                ("due_date", str(old_wo[8]), str(due_date)),
                ("assigned_to", old_wo[6], assigned_to)
            ]
            
            for field, old_val, new_val in changes:
                if str(old_val) != str(new_val):
                    log_audit_trail("work_orders", wo_id, "UPDATE", field, str(old_val), str(new_val))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating work order: {str(e)}")
        return False

def update_work_order_status(wo_id, new_status, old_status):
    """Update work order status"""
    try:
        db = get_db()
        
        db.execute(text("""
            UPDATE work_orders 
            SET status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "status": new_status,
            "id": wo_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("work_orders", wo_id, "UPDATE", "status", old_status, new_status)
        
        return True
        
    except Exception as e:
        st.error(f"Error updating work order status: {str(e)}")
        return False

def delete_work_order(wo_id):
    """Delete a work order"""
    try:
        db = get_db()
        
        db.execute(text("DELETE FROM work_orders WHERE id = :id"), {"id": wo_id})
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("work_orders", wo_id, "DELETE")
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting work order: {str(e)}")
        return False
