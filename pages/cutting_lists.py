import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_db, log_audit_trail
from sqlalchemy import text

def show():
    st.title("✂️ Cutting Lists")
    
    tab1, tab2 = st.tabs(["📋 All Cutting Lists", "➕ Add Cutting Item"])
    
    with tab1:
        show_cutting_lists()
    
    with tab2:
        add_cutting_item_form()

def show_cutting_lists():
    st.subheader("All Cutting Lists")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   options=["All", "Pending", "Cut", "Re-cut"],
                                   key="cutting_status_filter")
    
    with col2:
        # Get projects for filter
        db = get_db()
        projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
        project_options = ["All"] + [f"{p[1]} (ID: {p[0]})" for p in projects]
        project_filter = st.selectbox("Filter by Project", options=project_options, key="cutting_project_filter")
        db.close()
    
    with col3:
        # Color filter
        db = get_db()
        colors = db.execute(text("SELECT DISTINCT color FROM cutting_lists WHERE color IS NOT NULL")).fetchall()
        color_options = ["All"] + [color[0] for color in colors]
        color_filter = st.selectbox("Filter by Color", options=color_options, key="cutting_color_filter")
        db.close()
    
    with col4:
        search_term = st.text_input("Search", placeholder="Order number or description...", key="cutting_search")
    
    # Build query with filters
    query = """
        SELECT 
            cl.id,
            cl.order_number,
            p.name as project_name,
            cl.floor,
            cl.description,
            cl.width,
            cl.height,
            cl.quantity,
            cl.color,
            cl.status,
            cl.cut_date,
            u.username as created_by,
            cl.created_at
        FROM cutting_lists cl
        LEFT JOIN projects p ON cl.project_id = p.id
        LEFT JOIN users u ON cl.created_by = u.id
        WHERE 1=1
    """
    params = {}
    
    if status_filter != "All":
        query += " AND cl.status = :status"
        params["status"] = status_filter
    
    if project_filter != "All":
        project_id = project_filter.split("ID: ")[1].split(")")[0]
        query += " AND cl.project_id = :project_id"
        params["project_id"] = int(project_id)
    
    if color_filter != "All":
        query += " AND cl.color = :color"
        params["color"] = color_filter
    
    if search_term:
        query += " AND (LOWER(cl.order_number) LIKE LOWER(:search) OR LOWER(cl.description) LIKE LOWER(:search))"
        params["search"] = f"%{search_term}%"
    
    query += " ORDER BY cl.created_at DESC"
    
    try:
        db = get_db()
        result = db.execute(text(query), params)
        cutting_items = result.fetchall()
        db.close()
        
        if cutting_items:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_items = len(cutting_items)
            pending_items = len([item for item in cutting_items if item[9] == "Pending"])
            cut_items = len([item for item in cutting_items if item[9] == "Cut"])
            total_quantity = sum([item[7] for item in cutting_items if item[7]])
            
            col1.metric("Total Items", total_items)
            col2.metric("Pending", pending_items)
            col3.metric("Cut", cut_items)
            col4.metric("Total Quantity", total_quantity)
            
            st.divider()
            
            # Display cutting items
            for item in cutting_items:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
                    
                    with col1:
                        st.write(f"**Order: {item[1]}**")
                        st.write(f"Project: {item[2] or 'N/A'}")
                        st.write(f"Floor: {item[3] or 'N/A'}")
                        if item[4]:  # Description
                            st.write(f"Description: {item[4][:50]}{'...' if len(item[4]) > 50 else ''}")
                    
                    with col2:
                        st.write(f"Dimensions: {item[5]} x {item[6]}" if item[5] and item[6] else "Dimensions: N/A")
                        st.write(f"Quantity: {item[7] or 'N/A'}")
                        st.write(f"Color: {item[8] or 'N/A'}")
                        
                        # Status with color coding
                        status_color = {
                            "Pending": "🔴",
                            "Cut": "🟢",
                            "Re-cut": "🟡"
                        }
                        st.write(f"Status: {status_color.get(item[9], '⚪')} **{item[9]}**")
                    
                    with col3:
                        # Status update
                        if st.session_state.user_role in ["Admin", "Project Manager", "Operator"]:
                            new_status = st.selectbox(
                                "Update Status",
                                options=["Pending", "Cut", "Re-cut"],
                                index=["Pending", "Cut", "Re-cut"].index(item[9]),
                                key=f"cutting_status_update_{item[0]}"
                            )
                            
                            if new_status != item[9]:
                                if st.button("Update", key=f"update_cutting_status_{item[0]}"):
                                    if update_cutting_status(item[0], new_status, item[9]):
                                        st.success("Status updated!")
                                        st.rerun()
                            
                            # Cut date update
                            if new_status == "Cut" and not item[10]:
                                cut_date = st.date_input("Cut Date", value=date.today(), key=f"cut_date_{item[0]}")
                                if st.button("Set Cut Date", key=f"set_cut_date_{item[0]}"):
                                    if update_cut_date(item[0], cut_date):
                                        st.success("Cut date updated!")
                                        st.rerun()
                    
                    with col4:
                        if st.session_state.user_role in ["Admin", "Project Manager"]:
                            if st.button("📝 Edit", key=f"edit_cutting_{item[0]}"):
                                st.session_state[f"edit_cutting_{item[0]}"] = True
                            
                            if st.button("🗑️ Delete", key=f"delete_cutting_{item[0]}"):
                                if delete_cutting_item(item[0]):
                                    st.success("Cutting item deleted!")
                                    st.rerun()
                    
                    # Edit form
                    if st.session_state.get(f"edit_cutting_{item[0]}", False):
                        edit_cutting_item_form(item)
                    
                    st.divider()
        else:
            st.info("No cutting items found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error loading cutting lists: {str(e)}")

def edit_cutting_item_form(item):
    st.subheader(f"Edit Cutting Item: {item[1]}")
    
    # Get projects for dropdown
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    db.close()
    
    with st.form(f"edit_cutting_form_{item[0]}"):
        col1, col2 = st.columns(2)
        
        with col1:
            order_number = st.text_input("Order Number", value=item[1])
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            current_project = next((f"{item[2]} (ID: {i})" for i, name in [(p[0], p[1]) for p in projects] if name == item[2]), project_options[0] if project_options else "")
            project = st.selectbox("Project", options=project_options, 
                                 index=project_options.index(current_project) if current_project in project_options else 0)
            floor = st.text_input("Floor", value=item[3] or "")
            description = st.text_area("Description", value=item[4] or "", height=80)
        
        with col2:
            width = st.number_input("Width", value=float(item[5]) if item[5] else 0.0, min_value=0.0, step=0.1)
            height = st.number_input("Height", value=float(item[6]) if item[6] else 0.0, min_value=0.0, step=0.1)
            quantity = st.number_input("Quantity", value=item[7] if item[7] else 0, min_value=0, step=1)
            color = st.text_input("Color", value=item[8] or "")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Update Item"):
                project_id = int(project.split("ID: ")[1].split(")")[0])
                
                if update_cutting_item(item[0], order_number, project_id, floor, description, 
                                     width, height, quantity, color):
                    st.success("Cutting item updated successfully!")
                    st.session_state[f"edit_cutting_{item[0]}"] = False
                    st.rerun()
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state[f"edit_cutting_{item[0]}"] = False
                st.rerun()

def add_cutting_item_form():
    st.subheader("Add New Cutting Item")
    
    # Get projects for dropdown
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    db.close()
    
    if not projects:
        st.warning("No projects available. Please create a project first.")
        return
    
    with st.form("add_cutting_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            order_number = st.text_input("Order Number*", placeholder="e.g., ORD-001")
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            project = st.selectbox("Project*", options=project_options)
            floor = st.text_input("Floor", placeholder="e.g., Ground Floor")
            description = st.text_area("Description", placeholder="Item description and specifications", height=80)
        
        with col2:
            width = st.number_input("Width*", min_value=0.0, step=0.1, placeholder="Enter width")
            height = st.number_input("Height*", min_value=0.0, step=0.1, placeholder="Enter height")
            quantity = st.number_input("Quantity*", min_value=1, step=1, value=1)
            color = st.text_input("Color", placeholder="e.g., Blue, Red")
        
        submitted = st.form_submit_button("✂️ Add Cutting Item")
        
        if submitted:
            if not order_number.strip():
                st.error("Order Number is required!")
                return
            
            if width <= 0 or height <= 0:
                st.error("Width and Height must be greater than 0!")
                return
            
            project_id = int(project.split("ID: ")[1].split(")")[0])
            
            if create_cutting_item(order_number, project_id, floor, description, width, height, quantity, color):
                st.success("Cutting item created successfully!")
                st.rerun()

def create_cutting_item(order_number, project_id, floor, description, width, height, quantity, color):
    """Create a new cutting item"""
    try:
        db = get_db()
        
        result = db.execute(text("""
            INSERT INTO cutting_lists (order_number, project_id, floor, description, width, height, 
                                     quantity, color, created_by)
            VALUES (:order_number, :project_id, :floor, :description, :width, :height, 
                   :quantity, :color, :created_by)
            RETURNING id
        """), {
            "order_number": order_number,
            "project_id": project_id,
            "floor": floor if floor else None,
            "description": description if description else None,
            "width": width,
            "height": height,
            "quantity": quantity,
            "color": color if color else None,
            "created_by": st.session_state.user_id
        })
        
        item_id = result.fetchone()[0]
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("cutting_lists", item_id, "CREATE")
        
        return True
        
    except Exception as e:
        st.error(f"Error creating cutting item: {str(e)}")
        return False

def update_cutting_item(item_id, order_number, project_id, floor, description, width, height, quantity, color):
    """Update an existing cutting item"""
    try:
        db = get_db()
        
        # Get old values for audit
        old_result = db.execute(text("SELECT * FROM cutting_lists WHERE id = :id"), {"id": item_id})
        old_item = old_result.fetchone()
        
        db.execute(text("""
            UPDATE cutting_lists 
            SET order_number = :order_number, project_id = :project_id, floor = :floor,
                description = :description, width = :width, height = :height,
                quantity = :quantity, color = :color, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "order_number": order_number,
            "project_id": project_id,
            "floor": floor if floor else None,
            "description": description if description else None,
            "width": width,
            "height": height,
            "quantity": quantity,
            "color": color if color else None,
            "id": item_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail for changes
        if old_item:
            changes = [
                ("order_number", old_item[1], order_number),
                ("project_id", old_item[2], project_id),
                ("floor", old_item[3], floor),
                ("description", old_item[4], description),
                ("width", str(old_item[5]), str(width)),
                ("height", str(old_item[6]), str(height)),
                ("quantity", old_item[7], quantity),
                ("color", old_item[8], color)
            ]
            
            for field, old_val, new_val in changes:
                if str(old_val) != str(new_val):
                    log_audit_trail("cutting_lists", item_id, "UPDATE", field, str(old_val), str(new_val))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating cutting item: {str(e)}")
        return False

def update_cutting_status(item_id, new_status, old_status):
    """Update cutting item status"""
    try:
        db = get_db()
        
        update_data = {
            "status": new_status,
            "id": item_id
        }
        
        # Set cut date if status is "Cut" and no date is set
        if new_status == "Cut":
            update_data["cut_date"] = date.today()
            query = """
                UPDATE cutting_lists 
                SET status = :status, cut_date = COALESCE(cut_date, :cut_date), updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """
        else:
            query = """
                UPDATE cutting_lists 
                SET status = :status, updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """
        
        db.execute(text(query), update_data)
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("cutting_lists", item_id, "UPDATE", "status", old_status, new_status)
        
        return True
        
    except Exception as e:
        st.error(f"Error updating cutting status: {str(e)}")
        return False

def update_cut_date(item_id, cut_date):
    """Update cut date for an item"""
    try:
        db = get_db()
        
        db.execute(text("""
            UPDATE cutting_lists 
            SET cut_date = :cut_date, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "cut_date": cut_date,
            "id": item_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("cutting_lists", item_id, "UPDATE", "cut_date", None, str(cut_date))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating cut date: {str(e)}")
        return False

def delete_cutting_item(item_id):
    """Delete a cutting item"""
    try:
        db = get_db()
        
        db.execute(text("DELETE FROM cutting_lists WHERE id = :id"), {"id": item_id})
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("cutting_lists", item_id, "DELETE")
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting cutting item: {str(e)}")
        return False
