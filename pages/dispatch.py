import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database import get_db, log_audit_trail
from sqlalchemy import text
from utils.reports import generate_delivery_challan

def show():
    st.title("🚚 Dispatch & Delivery")
    
    tab1, tab2 = st.tabs(["📋 Dispatch Records", "➕ Add Dispatch"])
    
    with tab1:
        show_dispatch_records()
    
    with tab2:
        add_dispatch_form()

def show_dispatch_records():
    st.subheader("Dispatch Records")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   options=["All", "Dispatched", "In Transit", "Delivered", "Delayed"],
                                   key="dispatch_status_filter")
    
    with col2:
        # Date range filter
        date_range = st.selectbox("Filter by Date",
                                options=["All", "Today", "This Week", "This Month"],
                                key="dispatch_date_filter")
    
    with col3:
        # Get projects for filter
        db = get_db()
        projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
        project_options = ["All"] + [f"{p[1]} (ID: {p[0]})" for p in projects]
        project_filter = st.selectbox("Filter by Project", options=project_options, key="dispatch_project_filter")
        db.close()
    
    with col4:
        search_term = st.text_input("Search", placeholder="Order number, vehicle, or challan...", key="dispatch_search")
    
    # Build query with filters
    query = """
        SELECT 
            d.id,
            p.name as project_name,
            d.order_number,
            d.vehicle_number,
            d.driver_name,
            d.dispatch_date,
            d.delivery_date,
            d.status,
            u.username as responsible_person,
            d.challan_number,
            d.notes,
            creator.username as created_by,
            d.created_at
        FROM dispatch d
        LEFT JOIN projects p ON d.project_id = p.id
        LEFT JOIN users u ON d.responsible_person = u.id
        LEFT JOIN users creator ON d.created_by = creator.id
        WHERE 1=1
    """
    params = {}
    
    if status_filter != "All":
        query += " AND d.status = :status"
        params["status"] = status_filter
    
    if date_range == "Today":
        query += " AND d.dispatch_date = CURRENT_DATE"
    elif date_range == "This Week":
        query += " AND d.dispatch_date >= CURRENT_DATE - INTERVAL '7 days'"
    elif date_range == "This Month":
        query += " AND d.dispatch_date >= CURRENT_DATE - INTERVAL '30 days'"
    
    if project_filter != "All":
        project_id = project_filter.split("ID: ")[1].split(")")[0]
        query += " AND d.project_id = :project_id"
        params["project_id"] = int(project_id)
    
    if search_term:
        query += " AND (LOWER(d.order_number) LIKE LOWER(:search) OR LOWER(d.vehicle_number) LIKE LOWER(:search) OR LOWER(d.challan_number) LIKE LOWER(:search))"
        params["search"] = f"%{search_term}%"
    
    query += " ORDER BY d.dispatch_date DESC, d.created_at DESC"
    
    try:
        db = get_db()
        result = db.execute(text(query), params)
        dispatch_records = result.fetchall()
        db.close()
        
        if dispatch_records:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_dispatches = len(dispatch_records)
            delivered_count = len([d for d in dispatch_records if d[7] == "Delivered"])
            in_transit_count = len([d for d in dispatch_records if d[7] == "In Transit"])
            delayed_count = len([d for d in dispatch_records if d[7] == "Delayed"])
            
            col1.metric("Total Dispatches", total_dispatches)
            col2.metric("Delivered", delivered_count)
            col3.metric("In Transit", in_transit_count)
            col4.metric("Delayed", delayed_count, delta=f"+{delayed_count}" if delayed_count > 0 else "0")
            
            st.divider()
            
            # Display dispatch records
            for dispatch in dispatch_records:
                with st.container():
                    # Highlight delayed or overdue deliveries
                    is_delayed = dispatch[7] == "Delayed"
                    is_overdue = dispatch[6] and dispatch[6] < date.today() and dispatch[7] not in ["Delivered"]
                    
                    if is_delayed:
                        st.error("🚨 DELAYED DISPATCH")
                    elif is_overdue:
                        st.warning("⏰ OVERDUE DELIVERY")
                    
                    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
                    
                    with col1:
                        st.write(f"**Order: {dispatch[2]}**")
                        st.write(f"Project: {dispatch[1] or 'N/A'}")
                        st.write(f"Vehicle: {dispatch[3] or 'N/A'}")
                        st.write(f"Driver: {dispatch[4] or 'N/A'}")
                        if dispatch[9]:  # Challan number
                            st.write(f"Challan: {dispatch[9]}")
                    
                    with col2:
                        # Status with color coding
                        status_color = {
                            "Dispatched": "🟡",
                            "In Transit": "🔵",
                            "Delivered": "🟢",
                            "Delayed": "🔴"
                        }
                        st.write(f"Status: {status_color.get(dispatch[7], '⚪')} **{dispatch[7]}**")
                        st.write(f"Dispatch Date: {dispatch[5]}")
                        st.write(f"Expected Delivery: {dispatch[6] or 'Not set'}")
                        st.write(f"Responsible: {dispatch[8] or 'N/A'}")
                    
                    with col3:
                        # Status update
                        if st.session_state.user_role in ["Admin", "Project Manager", "Operator"]:
                            new_status = st.selectbox(
                                "Update Status",
                                options=["Dispatched", "In Transit", "Delivered", "Delayed"],
                                index=["Dispatched", "In Transit", "Delivered", "Delayed"].index(dispatch[7]),
                                key=f"dispatch_status_update_{dispatch[0]}"
                            )
                            
                            if new_status != dispatch[7]:
                                if st.button("Update Status", key=f"update_dispatch_status_{dispatch[0]}"):
                                    if update_dispatch_status(dispatch[0], new_status, dispatch[7]):
                                        st.success("Status updated!")
                                        st.rerun()
                        
                        # Quick delivery date update
                        if dispatch[7] == "Delivered" and not dispatch[6]:
                            if st.button("Set Delivery Date", key=f"set_delivery_date_{dispatch[0]}"):
                                if update_delivery_date(dispatch[0], date.today()):
                                    st.success("Delivery date set!")
                                    st.rerun()
                    
                    with col4:
                        # Generate challan
                        if st.button("📄 Challan", key=f"generate_challan_{dispatch[0]}"):
                            challan_content = generate_delivery_challan(dispatch)
                            st.download_button(
                                "📥 Download Challan",
                                data=challan_content,
                                file_name=f"challan_{dispatch[2]}_{dispatch[5]}.txt",
                                mime="text/plain",
                                key=f"download_challan_{dispatch[0]}"
                            )
                        
                        if st.session_state.user_role in ["Admin", "Project Manager"]:
                            if st.button("📝 Edit", key=f"edit_dispatch_{dispatch[0]}"):
                                st.session_state[f"edit_dispatch_{dispatch[0]}"] = True
                            
                            if st.button("🗑️ Delete", key=f"delete_dispatch_{dispatch[0]}"):
                                if delete_dispatch_record(dispatch[0]):
                                    st.success("Dispatch record deleted!")
                                    st.rerun()
                        
                        # Notes display
                        if dispatch[10]:  # Notes
                            with st.expander("📝 Notes"):
                                st.write(dispatch[10])
                    
                    # Edit form
                    if st.session_state.get(f"edit_dispatch_{dispatch[0]}", False):
                        edit_dispatch_form(dispatch)
                    
                    st.divider()
        else:
            st.info("No dispatch records found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error loading dispatch records: {str(e)}")

def edit_dispatch_form(dispatch):
    st.subheader(f"Edit Dispatch: {dispatch[2]}")
    
    # Get projects and users for dropdowns
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    users = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
    db.close()
    
    with st.form(f"edit_dispatch_form_{dispatch[0]}"):
        col1, col2 = st.columns(2)
        
        with col1:
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            current_project = next((f"{dispatch[1]} (ID: {i})" for i, name in [(p[0], p[1]) for p in projects] if name == dispatch[1]), project_options[0] if project_options else "")
            project = st.selectbox("Project", options=project_options, 
                                 index=project_options.index(current_project) if current_project in project_options else 0)
            
            order_number = st.text_input("Order Number", value=dispatch[2])
            vehicle_number = st.text_input("Vehicle Number", value=dispatch[3] or "")
            driver_name = st.text_input("Driver Name", value=dispatch[4] or "")
            challan_number = st.text_input("Challan Number", value=dispatch[9] or "")
        
        with col2:
            dispatch_date = st.date_input("Dispatch Date", value=dispatch[5] if dispatch[5] else date.today())
            delivery_date = st.date_input("Expected Delivery Date", value=dispatch[6] if dispatch[6] else None)
            status = st.selectbox("Status", options=["Dispatched", "In Transit", "Delivered", "Delayed"],
                                index=["Dispatched", "In Transit", "Delivered", "Delayed"].index(dispatch[7]))
            
            user_options = ["Not Assigned"] + [f"{u[1]} (ID: {u[0]})" for u in users]
            current_responsible = next((f"{dispatch[8]} (ID: {i})" for i, name in [(u[0], u[1]) for u in users] if name == dispatch[8]), "Not Assigned")
            responsible_person = st.selectbox("Responsible Person", options=user_options,
                                            index=user_options.index(current_responsible) if current_responsible in user_options else 0)
        
        notes = st.text_area("Notes", value=dispatch[10] or "", height=80)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Update Dispatch"):
                project_id = int(project.split("ID: ")[1].split(")")[0])
                responsible_id = None if responsible_person == "Not Assigned" else int(responsible_person.split("ID: ")[1].split(")")[0])
                
                if update_dispatch_record(dispatch[0], project_id, order_number, vehicle_number, driver_name,
                                        dispatch_date, delivery_date, status, responsible_id, challan_number, notes):
                    st.success("Dispatch record updated successfully!")
                    st.session_state[f"edit_dispatch_{dispatch[0]}"] = False
                    st.rerun()
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state[f"edit_dispatch_{dispatch[0]}"] = False
                st.rerun()

def add_dispatch_form():
    st.subheader("Add New Dispatch")
    
    # Get projects and users for dropdowns
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    users = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
    db.close()
    
    if not projects:
        st.warning("No projects available. Please create a project first.")
        return
    
    with st.form("add_dispatch_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            project = st.selectbox("Project*", options=project_options)
            order_number = st.text_input("Order Number*", placeholder="e.g., ORD-001")
            vehicle_number = st.text_input("Vehicle Number*", placeholder="e.g., ABC-123")
            driver_name = st.text_input("Driver Name", placeholder="Driver's full name")
            
            # Auto-generate challan number
            import random
            import string
            default_challan = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            challan_number = st.text_input("Challan Number", value=f"CH-{default_challan}")
        
        with col2:
            dispatch_date = st.date_input("Dispatch Date*", value=date.today())
            delivery_date = st.date_input("Expected Delivery Date")
            status = st.selectbox("Status", options=["Dispatched", "In Transit", "Delivered", "Delayed"])
            
            user_options = ["Not Assigned"] + [f"{u[1]} (ID: {u[0]})" for u in users]
            responsible_person = st.selectbox("Responsible Person", options=user_options)
        
        notes = st.text_area("Notes", placeholder="Dispatch notes, special instructions, etc.", height=80)
        
        submitted = st.form_submit_button("🚚 Create Dispatch Record")
        
        if submitted:
            if not order_number.strip():
                st.error("Order Number is required!")
                return
            
            if not vehicle_number.strip():
                st.error("Vehicle Number is required!")
                return
            
            project_id = int(project.split("ID: ")[1].split(")")[0])
            responsible_id = None if responsible_person == "Not Assigned" else int(responsible_person.split("ID: ")[1].split(")")[0])
            
            if create_dispatch_record(project_id, order_number, vehicle_number, driver_name, dispatch_date,
                                    delivery_date, status, responsible_id, challan_number, notes):
                st.success("Dispatch record created successfully!")
                st.rerun()

def create_dispatch_record(project_id, order_number, vehicle_number, driver_name, dispatch_date, delivery_date, status, responsible_person, challan_number, notes):
    """Create a new dispatch record"""
    try:
        db = get_db()
        
        result = db.execute(text("""
            INSERT INTO dispatch (project_id, order_number, vehicle_number, driver_name,
                                dispatch_date, delivery_date, status, responsible_person,
                                challan_number, notes, created_by)
            VALUES (:project_id, :order_number, :vehicle_number, :driver_name,
                   :dispatch_date, :delivery_date, :status, :responsible_person,
                   :challan_number, :notes, :created_by)
            RETURNING id
        """), {
            "project_id": project_id,
            "order_number": order_number,
            "vehicle_number": vehicle_number,
            "driver_name": driver_name if driver_name else None,
            "dispatch_date": dispatch_date,
            "delivery_date": delivery_date if delivery_date else None,
            "status": status,
            "responsible_person": responsible_person,
            "challan_number": challan_number if challan_number else None,
            "notes": notes if notes else None,
            "created_by": st.session_state.user_id
        })
        
        dispatch_id = result.fetchone()[0]
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("dispatch", dispatch_id, "CREATE")
        
        return True
        
    except Exception as e:
        st.error(f"Error creating dispatch record: {str(e)}")
        return False

def update_dispatch_record(dispatch_id, project_id, order_number, vehicle_number, driver_name, dispatch_date, delivery_date, status, responsible_person, challan_number, notes):
    """Update an existing dispatch record"""
    try:
        db = get_db()
        
        # Get old values for audit
        old_result = db.execute(text("SELECT * FROM dispatch WHERE id = :id"), {"id": dispatch_id})
        old_dispatch = old_result.fetchone()
        
        db.execute(text("""
            UPDATE dispatch 
            SET project_id = :project_id, order_number = :order_number, vehicle_number = :vehicle_number,
                driver_name = :driver_name, dispatch_date = :dispatch_date, delivery_date = :delivery_date,
                status = :status, responsible_person = :responsible_person, challan_number = :challan_number,
                notes = :notes, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "project_id": project_id,
            "order_number": order_number,
            "vehicle_number": vehicle_number,
            "driver_name": driver_name if driver_name else None,
            "dispatch_date": dispatch_date,
            "delivery_date": delivery_date if delivery_date else None,
            "status": status,
            "responsible_person": responsible_person,
            "challan_number": challan_number if challan_number else None,
            "notes": notes if notes else None,
            "id": dispatch_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail for changes
        if old_dispatch:
            changes = [
                ("project_id", old_dispatch[1], project_id),
                ("order_number", old_dispatch[2], order_number),
                ("vehicle_number", old_dispatch[3], vehicle_number),
                ("driver_name", old_dispatch[4], driver_name),
                ("dispatch_date", str(old_dispatch[5]), str(dispatch_date)),
                ("delivery_date", str(old_dispatch[6]), str(delivery_date)),
                ("status", old_dispatch[7], status),
                ("responsible_person", old_dispatch[8], responsible_person),
                ("challan_number", old_dispatch[9], challan_number),
                ("notes", old_dispatch[10], notes)
            ]
            
            for field, old_val, new_val in changes:
                if str(old_val) != str(new_val):
                    log_audit_trail("dispatch", dispatch_id, "UPDATE", field, str(old_val), str(new_val))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating dispatch record: {str(e)}")
        return False

def update_dispatch_status(dispatch_id, new_status, old_status):
    """Update dispatch status"""
    try:
        db = get_db()
        
        db.execute(text("""
            UPDATE dispatch 
            SET status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "status": new_status,
            "id": dispatch_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("dispatch", dispatch_id, "UPDATE", "status", old_status, new_status)
        
        return True
        
    except Exception as e:
        st.error(f"Error updating dispatch status: {str(e)}")
        return False

def update_delivery_date(dispatch_id, delivery_date):
    """Update delivery date"""
    try:
        db = get_db()
        
        db.execute(text("""
            UPDATE dispatch 
            SET delivery_date = :delivery_date, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "delivery_date": delivery_date,
            "id": dispatch_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("dispatch", dispatch_id, "UPDATE", "delivery_date", None, str(delivery_date))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating delivery date: {str(e)}")
        return False

def delete_dispatch_record(dispatch_id):
    """Delete a dispatch record"""
    try:
        db = get_db()
        
        db.execute(text("DELETE FROM dispatch WHERE id = :id"), {"id": dispatch_id})
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("dispatch", dispatch_id, "DELETE")
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting dispatch record: {str(e)}")
        return False
