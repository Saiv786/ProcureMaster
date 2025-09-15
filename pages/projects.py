import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_db, log_audit_trail
from sqlalchemy import text

def show():
    st.title("🏗️ Projects")
    
    # Permission check
    if st.session_state.user_role not in ["Admin", "Project Manager"]:
        st.warning("You don't have permission to manage projects.")
        return
    
    tab1, tab2 = st.tabs(["📋 All Projects", "➕ Add Project"])
    
    with tab1:
        show_projects_list()
    
    with tab2:
        add_project_form()

def show_projects_list():
    st.subheader("All Projects")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   options=["All", "Active", "Completed", "On Hold"],
                                   key="project_status_filter")
    
    with col2:
        # Get all clients for filter
        db = get_db()
        clients = db.execute(text("SELECT DISTINCT client FROM projects WHERE client IS NOT NULL")).fetchall()
        client_options = ["All"] + [client[0] for client in clients]
        client_filter = st.selectbox("Filter by Client", options=client_options, key="project_client_filter")
        db.close()
    
    with col3:
        search_term = st.text_input("Search Projects", placeholder="Enter project name...", key="project_search")
    
    # Build query with filters
    query = """
        SELECT 
            p.id,
            p.name,
            p.client,
            p.location,
            p.start_date,
            p.end_date,
            p.status,
            u.username as created_by,
            p.created_at
        FROM projects p
        LEFT JOIN users u ON p.created_by = u.id
        WHERE 1=1
    """
    params = {}
    
    if status_filter != "All":
        query += " AND p.status = :status"
        params["status"] = status_filter
    
    if client_filter != "All":
        query += " AND p.client = :client"
        params["client"] = client_filter
    
    if search_term:
        query += " AND LOWER(p.name) LIKE LOWER(:search)"
        params["search"] = f"%{search_term}%"
    
    query += " ORDER BY p.created_at DESC"
    
    try:
        db = get_db()
        result = db.execute(text(query), params)
        projects = result.fetchall()
        db.close()
        
        if projects:
            df = pd.DataFrame(projects, columns=[
                'ID', 'Name', 'Client', 'Location', 'Start Date', 'End Date', 'Status', 'Created By', 'Created At'
            ])
            
            # Display projects in a more interactive way
            for _, project in df.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    
                    with col1:
                        st.write(f"**{project['Name']}**")
                        st.write(f"Client: {project['Client'] or 'Not specified'}")
                        st.write(f"Location: {project['Location'] or 'Not specified'}")
                    
                    with col2:
                        st.write(f"Status: **{project['Status']}**")
                        st.write(f"Start: {project['Start Date']}")
                        st.write(f"End: {project['End Date']}")
                    
                    with col3:
                        if st.button("📝 Edit", key=f"edit_{project['ID']}"):
                            st.session_state[f"edit_project_{project['ID']}"] = True
                    
                    with col4:
                        if st.button("🗑️ Delete", key=f"delete_{project['ID']}"):
                            if delete_project(project['ID']):
                                st.success("Project deleted successfully!")
                                st.rerun()
                    
                    # Edit form
                    if st.session_state.get(f"edit_project_{project['ID']}", False):
                        edit_project_form(project)
                    
                    st.divider()
        else:
            st.info("No projects found matching the criteria.")
            
    except Exception as e:
        st.error(f"Error loading projects: {str(e)}")

def edit_project_form(project):
    st.subheader(f"Edit Project: {project['Name']}")
    
    with st.form(f"edit_project_form_{project['ID']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Project Name", value=project['Name'])
            client = st.text_input("Client", value=project['Client'] or "")
            location = st.text_input("Location", value=project['Location'] or "")
        
        with col2:
            start_date = st.date_input("Start Date", value=project['Start Date'])
            end_date = st.date_input("End Date", value=project['End Date'])
            status = st.selectbox("Status", 
                                options=["Active", "Completed", "On Hold"],
                                index=["Active", "Completed", "On Hold"].index(project['Status']))
        
        description = st.text_area("Description", height=100)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.form_submit_button("💾 Update Project"):
                if update_project(project['ID'], name, client, location, start_date, end_date, status, description):
                    st.success("Project updated successfully!")
                    st.session_state[f"edit_project_{project['ID']}"] = False
                    st.rerun()
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state[f"edit_project_{project['ID']}"] = False
                st.rerun()

def add_project_form():
    st.subheader("Add New Project")
    
    with st.form("add_project_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Project Name*", placeholder="e.g., HIBA Tower")
            client = st.text_input("Client", placeholder="Client name")
            location = st.text_input("Location", placeholder="Project location")
        
        with col2:
            start_date = st.date_input("Start Date", value=date.today())
            end_date = st.date_input("End Date")
            status = st.selectbox("Status", options=["Active", "Completed", "On Hold"], index=0)
        
        description = st.text_area("Description", placeholder="Project description and notes", height=100)
        
        submitted = st.form_submit_button("🏗️ Create Project")
        
        if submitted:
            if not name.strip():
                st.error("Project name is required!")
                return
            
            if create_project(name, client, location, start_date, end_date, status, description):
                st.success("Project created successfully!")
                st.rerun()

def create_project(name, client, location, start_date, end_date, status, description):
    """Create a new project"""
    try:
        db = get_db()
        
        result = db.execute(text("""
            INSERT INTO projects (name, client, location, start_date, end_date, status, description, created_by)
            VALUES (:name, :client, :location, :start_date, :end_date, :status, :description, :created_by)
            RETURNING id
        """), {
            "name": name,
            "client": client if client else None,
            "location": location if location else None,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "description": description if description else None,
            "created_by": st.session_state.user_id
        })
        
        project_id = result.fetchone()[0]
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("projects", project_id, "CREATE")
        
        return True
        
    except Exception as e:
        st.error(f"Error creating project: {str(e)}")
        return False

def update_project(project_id, name, client, location, start_date, end_date, status, description):
    """Update an existing project"""
    try:
        db = get_db()
        
        # Get old values for audit
        old_result = db.execute(text("SELECT * FROM projects WHERE id = :id"), {"id": project_id})
        old_project = old_result.fetchone()
        
        db.execute(text("""
            UPDATE projects 
            SET name = :name, client = :client, location = :location, 
                start_date = :start_date, end_date = :end_date, status = :status,
                description = :description, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """), {
            "name": name,
            "client": client if client else None,
            "location": location if location else None,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "description": description if description else None,
            "id": project_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail for changes
        if old_project:
            changes = [
                ("name", old_project[1], name),
                ("client", old_project[2], client),
                ("location", old_project[3], location),
                ("start_date", str(old_project[4]), str(start_date)),
                ("end_date", str(old_project[5]), str(end_date)),
                ("status", old_project[6], status),
                ("description", old_project[7], description)
            ]
            
            for field, old_val, new_val in changes:
                if str(old_val) != str(new_val):
                    log_audit_trail("projects", project_id, "UPDATE", field, str(old_val), str(new_val))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating project: {str(e)}")
        return False

def delete_project(project_id):
    """Delete a project"""
    try:
        db = get_db()
        
        # Check if project has associated records
        wo_count = db.execute(text("SELECT COUNT(*) FROM work_orders WHERE project_id = :id"), {"id": project_id}).fetchone()[0]
        
        if wo_count > 0:
            st.error(f"Cannot delete project: {wo_count} work orders are associated with this project.")
            db.close()
            return False
        
        db.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("projects", project_id, "DELETE")
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting project: {str(e)}")
        return False
