import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_db, log_audit_trail
from sqlalchemy import text

def show():
    st.title("⚖️ Balance Orders")
    
    tab1, tab2 = st.tabs(["📋 All Balance Orders", "➕ Add Balance Order"])
    
    with tab1:
        show_balance_orders()
    
    with tab2:
        add_balance_order_form()

def show_balance_orders():
    st.subheader("All Balance Orders")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   options=["All", "Pending", "In Progress", "Completed"],
                                   key="balance_status_filter")
    
    with col2:
        priority_filter = st.selectbox("Filter by Priority",
                                     options=["All", "High", "Medium", "Low"],
                                     key="balance_priority_filter")
    
    with col3:
        # Get projects for filter
        db = get_db()
        projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
        project_options = ["All"] + [f"{p[1]} (ID: {p[0]})" for p in projects]
        project_filter = st.selectbox("Filter by Project", options=project_options, key="balance_project_filter")
        db.close()
    
    with col4:
        search_term = st.text_input("Search", placeholder="WO number or specifications...", key="balance_search")
    
    # Build query with filters
    query = """
        SELECT 
            bo.id,
            bo.wo_number,
            p.name as project_name,
            bo.floor,
            bo.priority,
            bo.specifications,
            bo.required_qty,
            bo.fulfilled_qty,
            bo.total_qty,
            bo.due_date,
            bo.status,
            u.username as created_by,
            bo.created_at
        FROM balance_orders bo
        LEFT JOIN projects p ON bo.project_id = p.id
        LEFT JOIN users u ON bo.created_by = u.id
        WHERE 1=1
    """
    params = {}
    
    if status_filter != "All":
        query += " AND bo.status = :status"
        params["status"] = status_filter
    
    if priority_filter != "All":
        query += " AND bo.priority = :priority"
        params["priority"] = priority_filter
    
    if project_filter != "All":
        project_id = project_filter.split("ID: ")[1].split(")")[0]
        query += " AND bo.project_id = :project_id"
        params["project_id"] = int(project_id)
    
    if search_term:
        query += " AND (LOWER(bo.wo_number) LIKE LOWER(:search) OR LOWER(bo.specifications) LIKE LOWER(:search))"
        params["search"] = f"%{search_term}%"
    
    query += " ORDER BY bo.due_date ASC, bo.priority DESC, bo.created_at DESC"
    
    try:
        db = get_db()
        result = db.execute(text(query), params)
        balance_orders = result.fetchall()
        db.close()
        
        if balance_orders:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_orders = len(balance_orders)
            pending_orders = len([order for order in balance_orders if order[10] == "Pending"])
            high_priority = len([order for order in balance_orders if order[4] == "High"])
            overdue_orders = len([order for order in balance_orders if order[9] and order[9] < date.today() and order[10] != "Completed"])
            
            col1.metric("Total Orders", total_orders)
            col2.metric("Pending", pending_orders)
            col3.metric("High Priority", high_priority)
            col4.metric("Overdue", overdue_orders)
            
            st.divider()
            
            # Display balance orders
            for order in balance_orders:
                with st.container():
                    # Check if overdue
                    is_overdue = order[9] and order[9] < date.today() and order[10] != "Completed"
                    
                    if is_overdue:
                        st.error("🚨 OVERDUE ORDER")
                    
                    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
                    
                    with col1:
                        st.write(f"**WO: {order[1]}**")
                        st.write(f"Project: {order[2] or 'N/A'}")
                        st.write(f"Floor: {order[3] or 'N/A'}")
                        if order[5]:  # Specifications
                            st.write(f"Specs: {order[5][:60]}{'...' if len(order[5]) > 60 else ''}")
                    
                    with col2:
                        # Priority with color coding
                        priority_color = {
                            "High": "🔴",
                            "Medium": "🟡",
                            "Low": "🟢"
                        }
                        st.write(f"Priority: {priority_color.get(order[4], '⚪')} **{order[4]}**")
                        
                        # Status with color coding
                        status_color = {
                            "Pending": "🔴",
                            "In Progress": "🟡",
                            "Completed": "🟢"
                        }
                        st.write(f"Status: {status_color.get(order[10], '⚪')} **{order[10]}**")
                        st.write(f"Due: {order[9] or 'Not set'}")
                    
                    with col3:
                        # Quantity tracking
                        required = order[6] or 0
                        fulfilled = order[7] or 0
                        total = order[8] or 0
                        
                        st.write(f"Required: {required}")
                        st.write(f"Fulfilled: {fulfilled}")
                        st.write(f"Total: {total}")
                        
                        # Progress bar
                        if required > 0:
                            progress = min(fulfilled / required, 1.0)
                            st.progress(progress)
                            st.write(f"{progress:.1%} Complete")
                        
                        # Quick fulfillment update
                        if st.session_state.user_role in ["Admin", "Project Manager", "Operator"]:
                            new_fulfilled = st.number_input(
                                "Update Fulfilled",
                                min_value=0,
                                value=fulfilled,
                                key=f"fulfilled_update_{order[0]}"
                            )
                            
                            if new_fulfilled != fulfilled:
                                if st.button("Update Qty", key=f"update_fulfilled_{order[0]}"):
                                    if update_fulfilled_quantity(order[0], new_fulfilled, fulfilled):
                                        st.success("Quantity updated!")
                                        st.rerun()
                    
                    with col4:
                        # Status update
                        if st.session_state.user_role in ["Admin", "Project Manager", "Operator"]:
                            new_status = st.selectbox(
                                "Status",
                                options=["Pending", "In Progress", "Completed"],
                                index=["Pending", "In Progress", "Completed"].index(order[10]),
                                key=f"balance_status_update_{order[0]}"
                            )
                            
                            if new_status != order[10]:
                                if st.button("Update", key=f"update_balance_status_{order[0]}"):
                                    if update_balance_status(order[0], new_status, order[10]):
                                        st.success("Status updated!")
                                        st.rerun()
                        
                        if st.session_state.user_role in ["Admin", "Project Manager"]:
                            if st.button("📝 Edit", key=f"edit_balance_{order[0]}"):
                                st.session_state[f"edit_balance_{order[0]}"] = True
                            
                            if st.button("🗑️ Delete", key=f"delete_balance_{order[0]}"):
                                if delete_balance_order(order[0]):
                                    st.success("Balance order deleted!")
                                    st.rerun()
                    
                    # Edit form
                    if st.session_state.get(f"edit_balance_{order[0]}", False):
                        edit_balance_order_form(order)
                    
                    st.divider()
        else:
            st.info("No balance orders found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error loading balance orders: {str(e)}")

def edit_balance_order_form(order):
    st.subheader(f"Edit Balance Order: {order[1]}")
    
    # Get projects for dropdown
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    db.close()
    
    with st.form(f"edit_balance_form_{order[0]}"):
        col1, col2 = st.columns(2)
        
        with col1:
            wo_number = st.text_input("WO Number", value=order[1])
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            current_project = next((f"{order[2]} (ID: {i})" for i, name in [(p[0], p[1]) for p in projects] if name == order[2]), project_options[0] if project_options else "")
            project = st.selectbox("Project", options=project_options, 
                                 index=project_options.index(current_project) if current_project in project_options else 0)
            floor = st.text_input("Floor", value=order[3] or "")
            priority = st.selectbox("Priority", options=["High", "Medium", "Low"],
                                  index=["High", "Medium", "Low"].index(order[4]))
        
        with col2:
            required_qty = st.number_input("Required Quantity", value=order[6] if order[6] else 0, min_value=0)
            fulfilled_qty = st.number_input("Fulfilled Quantity", value=order[7] if order[7] else 0, min_value=0)
            total_qty = st.number_input("Total Quantity", value=order[8] if order[8] else 0, min_value=0)
            due_date = st.date_input("Due Date", value=order[9] if order[9] else date.today())
        
        specifications = st.text_area("Specifications", value=order[5] or "", height=100)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Update Order"):
                project_id = int(project.split("ID: ")[1].split(")")[0])
                
                if update_balance_order(order[0], wo_number, project_id, floor, priority, 
                                      specifications, required_qty, fulfilled_qty, total_qty, due_date):
                    st.success("Balance order updated successfully!")
                    st.session_state[f"edit_balance_{order[0]}"] = False
                    st.rerun()
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state[f"edit_balance_{order[0]}"] = False
                st.rerun()

def add_balance_order_form():
    st.subheader("Add New Balance Order")
    
    # Get projects for dropdown
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    db.close()
    
    if not projects:
        st.warning("No projects available. Please create a project first.")
        return
    
    with st.form("add_balance_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            wo_number = st.text_input("WO Number*", placeholder="e.g., WO-001")
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            project = st.selectbox("Project*", options=project_options)
            floor = st.text_input("Floor", placeholder="e.g., Ground Floor")
            priority = st.selectbox("Priority", options=["Medium", "High", "Low"])
        
        with col2:
            required_qty = st.number_input("Required Quantity*", min_value=1, value=1)
            fulfilled_qty = st.number_input("Fulfilled Quantity", min_value=0, value=0)
            total_qty = st.number_input("Total Quantity", min_value=0, value=0)
            due_date = st.date_input("Due Date")
        
        specifications = st.text_area("Specifications", placeholder="Order specifications and requirements", height=100)
        
        submitted = st.form_submit_button("⚖️ Create Balance Order")
        
        if submitted:
            if not wo_number.strip():
                st.error("WO Number is required!")
                return
            
            project_id = int(project.split("ID: ")[1].split(")")[0])
            
            if create_balance_order(wo_number, project_id, floor, priority, specifications, 
                                  required_qty, fulfilled_qty, total_qty, due_date):
                st.success("Balance order created successfully!")
                st.rerun()

def create_balance_order(wo_number, project_id, floor, priority, specifications, required_qty, fulfilled_qty, total_qty, due_date):
    """Create a new balance order"""
    try:
        db = get_db()
        
        result = db.execute(text("""
            INSERT INTO balance_orders (wo_number, project_id, floor, priority, specifications,
                                      required_qty, fulfilled_qty, total_qty, due_date, created_by)
            VALUES (:wo_number, :project_id, :floor, :priority, :specifications,
                   :required_qty, :fulfilled_qty, :total_qty, :due_date, :created_by)
            RETURNING id
        """), {
            "wo_number": wo_number,
            "project_id": project_id,
            "floor": floor if floor else None,
            "priority": priority,
            "specifications": specifications if specifications else None,
            "required_qty": required_qty,
            "fulfilled_qty": fulfilled_qty,
            "total_qty": total_qty,
            "due_date": due_date,
            "created_by": st.session_state.user_id
        })
        
        order_id = result.fetchone()[0]
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("balance_orders", order_id, "CREATE")
        
        return True
        
    except Exception as e:
        st.error(f"Error creating balance order: {str(e)}")
        return False

def update_balance_order(order_id, wo_number, project_id, floor, priority, specifications, required_qty, fulfilled_qty, total_qty, due_date):
    """Update an existing balance order"""
    try:
        db = get_db()
        
        # Get old values for audit
        old_result = db.execute(text("SELECT * FROM balance_orders WHERE id = :id"), {"id": order_id})
        old_order = old_result.fetchone()
        
        db.execute(text("""
            UPDATE balance_orders 
            SET wo_number = :wo_number, project_id = :project_id, floor = :floor,
                priority = :priority, specifications = :specifications, required_qty = :required_qty,
                fulfilled_qty = :fulfilled_qty, total_qty = :total_qty, due_date = :due_date,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "wo_number": wo_number,
            "project_id": project_id,
            "floor": floor if floor else None,
            "priority": priority,
            "specifications": specifications if specifications else None,
            "required_qty": required_qty,
            "fulfilled_qty": fulfilled_qty,
            "total_qty": total_qty,
            "due_date": due_date,
            "id": order_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail for changes
        if old_order:
            changes = [
                ("wo_number", old_order[1], wo_number),
                ("project_id", old_order[2], project_id),
                ("floor", old_order[3], floor),
                ("priority", old_order[4], priority),
                ("specifications", old_order[5], specifications),
                ("required_qty", old_order[6], required_qty),
                ("fulfilled_qty", old_order[7], fulfilled_qty),
                ("total_qty", old_order[8], total_qty),
                ("due_date", str(old_order[9]), str(due_date))
            ]
            
            for field, old_val, new_val in changes:
                if str(old_val) != str(new_val):
                    log_audit_trail("balance_orders", order_id, "UPDATE", field, str(old_val), str(new_val))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating balance order: {str(e)}")
        return False

def update_balance_status(order_id, new_status, old_status):
    """Update balance order status"""
    try:
        db = get_db()
        
        db.execute(text("""
            UPDATE balance_orders 
            SET status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "status": new_status,
            "id": order_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("balance_orders", order_id, "UPDATE", "status", old_status, new_status)
        
        return True
        
    except Exception as e:
        st.error(f"Error updating balance order status: {str(e)}")
        return False

def update_fulfilled_quantity(order_id, new_quantity, old_quantity):
    """Update fulfilled quantity"""
    try:
        db = get_db()
        
        db.execute(text("""
            UPDATE balance_orders 
            SET fulfilled_qty = :quantity, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "quantity": new_quantity,
            "id": order_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("balance_orders", order_id, "UPDATE", "fulfilled_qty", str(old_quantity), str(new_quantity))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating fulfilled quantity: {str(e)}")
        return False

def delete_balance_order(order_id):
    """Delete a balance order"""
    try:
        db = get_db()
        
        db.execute(text("DELETE FROM balance_orders WHERE id = :id"), {"id": order_id})
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("balance_orders", order_id, "DELETE")
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting balance order: {str(e)}")
        return False
