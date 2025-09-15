import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from database import get_db, log_audit_trail
from sqlalchemy import text

def show():
    st.title("🏭 Production Log")
    
    tab1, tab2, tab3 = st.tabs(["📋 Production Records", "➕ Add Production Entry", "📊 Analytics"])
    
    with tab1:
        show_production_records()
    
    with tab2:
        add_production_entry_form()
    
    with tab3:
        show_production_analytics()

def show_production_records():
    st.subheader("Production Records")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Date range filter
        start_date = st.date_input("From Date", value=date.today() - timedelta(days=30), key="prod_start_date")
        
    with col2:
        end_date = st.date_input("To Date", value=date.today(), key="prod_end_date")
    
    with col3:
        # Get projects for filter
        db = get_db()
        projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
        project_options = ["All"] + [f"{p[1]} (ID: {p[0]})" for p in projects]
        project_filter = st.selectbox("Filter by Project", options=project_options, key="prod_project_filter")
        db.close()
    
    with col4:
        # Get operators for filter
        db = get_db()
        operators = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
        operator_options = ["All"] + [f"{u[1]} (ID: {u[0]})" for u in operators]
        operator_filter = st.selectbox("Filter by Operator", options=operator_options, key="prod_operator_filter")
        db.close()
    
    # Additional filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        shift_filter = st.selectbox("Filter by Shift", 
                                  options=["All", "Morning", "Afternoon", "Night"],
                                  key="prod_shift_filter")
    
    with col2:
        # Get machines for filter
        db = get_db()
        machines = db.execute(text("SELECT DISTINCT machine_used FROM production_log WHERE machine_used IS NOT NULL")).fetchall()
        machine_options = ["All"] + [machine[0] for machine in machines]
        machine_filter = st.selectbox("Filter by Machine", options=machine_options, key="prod_machine_filter")
        db.close()
    
    with col3:
        search_term = st.text_input("Search", placeholder="WO number or notes...", key="prod_search")
    
    # Build query with filters
    query = """
        SELECT 
            pl.id,
            pl.wo_number,
            p.name as project_name,
            u.username as operator_name,
            pl.machine_used,
            pl.produced_quantity,
            pl.production_date,
            pl.shift,
            pl.notes,
            creator.username as created_by,
            pl.created_at
        FROM production_log pl
        LEFT JOIN projects p ON pl.project_id = p.id
        LEFT JOIN users u ON pl.operator_id = u.id
        LEFT JOIN users creator ON pl.created_by = creator.id
        WHERE pl.production_date >= :start_date AND pl.production_date <= :end_date
    """
    params = {
        "start_date": start_date,
        "end_date": end_date
    }
    
    if project_filter != "All":
        project_id = project_filter.split("ID: ")[1].split(")")[0]
        query += " AND pl.project_id = :project_id"
        params["project_id"] = int(project_id)
    
    if operator_filter != "All":
        operator_id = operator_filter.split("ID: ")[1].split(")")[0]
        query += " AND pl.operator_id = :operator_id"
        params["operator_id"] = int(operator_id)
    
    if shift_filter != "All":
        query += " AND pl.shift = :shift"
        params["shift"] = shift_filter
    
    if machine_filter != "All":
        query += " AND pl.machine_used = :machine"
        params["machine"] = machine_filter
    
    if search_term:
        query += " AND (LOWER(pl.wo_number) LIKE LOWER(:search) OR LOWER(pl.notes) LIKE LOWER(:search))"
        params["search"] = f"%{search_term}%"
    
    query += " ORDER BY pl.production_date DESC, pl.created_at DESC"
    
    try:
        db = get_db()
        result = db.execute(text(query), params)
        production_records = result.fetchall()
        db.close()
        
        if production_records:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            total_records = len(production_records)
            total_quantity = sum([record[5] for record in production_records if record[5]])
            unique_operators = len(set([record[3] for record in production_records if record[3]]))
            date_range_days = (end_date - start_date).days + 1
            
            col1.metric("Total Records", total_records)
            col2.metric("Total Quantity", total_quantity)
            col3.metric("Operators", unique_operators)
            col4.metric("Avg Daily Production", f"{total_quantity // date_range_days if date_range_days > 0 else 0}")
            
            st.divider()
            
            # Display production records
            for record in production_records:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
                    
                    with col1:
                        st.write(f"**WO: {record[1]}**")
                        st.write(f"Project: {record[2] or 'N/A'}")
                        st.write(f"Operator: {record[3] or 'N/A'}")
                        st.write(f"Machine: {record[4] or 'N/A'}")
                    
                    with col2:
                        st.write(f"Quantity: **{record[5] or 0}**")
                        st.write(f"Date: {record[6]}")
                        st.write(f"Shift: {record[7] or 'N/A'}")
                        st.write(f"Created by: {record[9]}")
                    
                    with col3:
                        if record[8]:  # Notes
                            with st.expander("📝 Notes"):
                                st.write(record[8])
                        
                        # Performance indicator
                        if record[5] and record[5] > 0:
                            if record[5] >= 100:
                                st.success(f"🟢 High Output")
                            elif record[5] >= 50:
                                st.info(f"🟡 Medium Output")
                            else:
                                st.warning(f"🔴 Low Output")
                    
                    with col4:
                        if st.session_state.user_role in ["Admin", "Project Manager"]:
                            if st.button("📝 Edit", key=f"edit_prod_{record[0]}"):
                                st.session_state[f"edit_prod_{record[0]}"] = True
                            
                            if st.button("🗑️ Delete", key=f"delete_prod_{record[0]}"):
                                if delete_production_record(record[0]):
                                    st.success("Production record deleted!")
                                    st.rerun()
                        
                        # Quick duplicate entry
                        if st.button("📋 Duplicate", key=f"duplicate_prod_{record[0]}"):
                            duplicate_production_record(record)
                            st.success("Record duplicated! Check the add form.")
                            st.rerun()
                    
                    # Edit form
                    if st.session_state.get(f"edit_prod_{record[0]}", False):
                        edit_production_record_form(record)
                    
                    st.divider()
        else:
            st.info("No production records found for the selected criteria.")
            
    except Exception as e:
        st.error(f"Error loading production records: {str(e)}")

def edit_production_record_form(record):
    st.subheader(f"Edit Production Record: {record[1]}")
    
    # Get projects, operators for dropdowns
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    operators = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
    db.close()
    
    with st.form(f"edit_prod_form_{record[0]}"):
        col1, col2 = st.columns(2)
        
        with col1:
            wo_number = st.text_input("WO Number", value=record[1])
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            current_project = next((f"{record[2]} (ID: {i})" for i, name in [(p[0], p[1]) for p in projects] if name == record[2]), project_options[0] if project_options else "")
            project = st.selectbox("Project", options=project_options, 
                                 index=project_options.index(current_project) if current_project in project_options else 0)
            
            operator_options = [f"{u[1]} (ID: {u[0]})" for u in operators]
            current_operator = next((f"{record[3]} (ID: {i})" for i, name in [(u[0], u[1]) for u in operators] if name == record[3]), operator_options[0] if operator_options else "")
            operator = st.selectbox("Operator", options=operator_options,
                                  index=operator_options.index(current_operator) if current_operator in operator_options else 0)
            
            machine_used = st.text_input("Machine Used", value=record[4] or "")
        
        with col2:
            produced_quantity = st.number_input("Produced Quantity", value=record[5] if record[5] else 0, min_value=0)
            production_date = st.date_input("Production Date", value=record[6] if record[6] else date.today())
            shift = st.selectbox("Shift", options=["Morning", "Afternoon", "Night"], 
                               index=["Morning", "Afternoon", "Night"].index(record[7]) if record[7] in ["Morning", "Afternoon", "Night"] else 0)
        
        notes = st.text_area("Notes", value=record[8] or "", height=80)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("💾 Update Record"):
                project_id = int(project.split("ID: ")[1].split(")")[0])
                operator_id = int(operator.split("ID: ")[1].split(")")[0])
                
                if update_production_record(record[0], wo_number, project_id, operator_id, machine_used,
                                          produced_quantity, production_date, shift, notes):
                    st.success("Production record updated successfully!")
                    st.session_state[f"edit_prod_{record[0]}"] = False
                    st.rerun()
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state[f"edit_prod_{record[0]}"] = False
                st.rerun()

def add_production_entry_form():
    st.subheader("Add Production Entry")
    
    # Get projects and operators for dropdowns
    db = get_db()
    projects = db.execute(text("SELECT id, name FROM projects ORDER BY name")).fetchall()
    operators = db.execute(text("SELECT id, username FROM users ORDER BY username")).fetchall()
    db.close()
    
    if not projects:
        st.warning("No projects available. Please create a project first.")
        return
    
    # Check for duplicated record data
    duplicate_data = st.session_state.get("duplicate_production_data", None)
    
    with st.form("add_production_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            wo_number = st.text_input("WO Number*", 
                                    value=duplicate_data[1] if duplicate_data else "",
                                    placeholder="e.g., WO-001")
            
            project_options = [f"{p[1]} (ID: {p[0]})" for p in projects]
            default_project_idx = 0
            if duplicate_data and duplicate_data[2]:
                for i, option in enumerate(project_options):
                    if duplicate_data[2] in option:
                        default_project_idx = i
                        break
            
            project = st.selectbox("Project*", options=project_options, index=default_project_idx)
            
            operator_options = [f"{u[1]} (ID: {u[0]})" for u in operators]
            default_operator_idx = 0
            if duplicate_data and duplicate_data[3]:
                for i, option in enumerate(operator_options):
                    if duplicate_data[3] in option:
                        default_operator_idx = i
                        break
            
            operator = st.selectbox("Operator*", options=operator_options, index=default_operator_idx)
            machine_used = st.text_input("Machine Used", 
                                       value=duplicate_data[4] if duplicate_data else "",
                                       placeholder="e.g., CNC Machine 1")
        
        with col2:
            produced_quantity = st.number_input("Produced Quantity*", 
                                              value=duplicate_data[5] if duplicate_data else 1,
                                              min_value=1, step=1)
            production_date = st.date_input("Production Date", 
                                          value=duplicate_data[6] if duplicate_data else date.today())
            shift = st.selectbox("Shift", options=["Morning", "Afternoon", "Night"],
                               index=["Morning", "Afternoon", "Night"].index(duplicate_data[7]) if duplicate_data and duplicate_data[7] else 0)
        
        notes = st.text_area("Notes", 
                           value=duplicate_data[8] if duplicate_data else "",
                           placeholder="Production notes, issues, observations", height=80)
        
        submitted = st.form_submit_button("🏭 Add Production Entry")
        
        if submitted:
            if not wo_number.strip():
                st.error("WO Number is required!")
                return
            
            project_id = int(project.split("ID: ")[1].split(")")[0])
            operator_id = int(operator.split("ID: ")[1].split(")")[0])
            
            if create_production_record(wo_number, project_id, operator_id, machine_used, 
                                      produced_quantity, production_date, shift, notes):
                st.success("Production entry added successfully!")
                # Clear duplicate data
                if "duplicate_production_data" in st.session_state:
                    del st.session_state["duplicate_production_data"]
                st.rerun()

def show_production_analytics():
    st.subheader("📊 Production Analytics")
    
    # Date range for analytics
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Analysis From", value=date.today() - timedelta(days=30), key="analytics_start")
    with col2:
        end_date = st.date_input("Analysis To", value=date.today(), key="analytics_end")
    
    try:
        db = get_db()
        
        # Production trend over time
        st.subheader("📈 Production Trend")
        trend_data = db.execute(text("""
            SELECT 
                production_date,
                SUM(produced_quantity) as daily_total
            FROM production_log 
            WHERE production_date >= :start_date AND production_date <= :end_date
            GROUP BY production_date
            ORDER BY production_date
        """), {"start_date": start_date, "end_date": end_date}).fetchall()
        
        if trend_data:
            df_trend = pd.DataFrame(trend_data, columns=['Date', 'Total Produced'])
            fig_trend = px.line(df_trend, x='Date', y='Total Produced', 
                               title="Daily Production Trend",
                               markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No production data available for the selected period.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Production by operator
            st.subheader("👨‍💼 Production by Operator")
            operator_data = db.execute(text("""
                SELECT 
                    u.username,
                    SUM(pl.produced_quantity) as total_produced,
                    COUNT(pl.id) as records_count
                FROM production_log pl
                JOIN users u ON pl.operator_id = u.id
                WHERE pl.production_date >= :start_date AND pl.production_date <= :end_date
                GROUP BY u.username
                ORDER BY total_produced DESC
            """), {"start_date": start_date, "end_date": end_date}).fetchall()
            
            if operator_data:
                df_operator = pd.DataFrame(operator_data, columns=['Operator', 'Total Produced', 'Records'])
                fig_operator = px.bar(df_operator, x='Operator', y='Total Produced',
                                    title="Production by Operator")
                st.plotly_chart(fig_operator, use_container_width=True)
            else:
                st.info("No operator production data available.")
        
        with col2:
            # Production by shift
            st.subheader("🕐 Production by Shift")
            shift_data = db.execute(text("""
                SELECT 
                    shift,
                    SUM(produced_quantity) as total_produced
                FROM production_log 
                WHERE production_date >= :start_date AND production_date <= :end_date
                    AND shift IS NOT NULL
                GROUP BY shift
                ORDER BY total_produced DESC
            """), {"start_date": start_date, "end_date": end_date}).fetchall()
            
            if shift_data:
                df_shift = pd.DataFrame(shift_data, columns=['Shift', 'Total Produced'])
                fig_shift = px.pie(df_shift, values='Total Produced', names='Shift',
                                 title="Production Distribution by Shift")
                st.plotly_chart(fig_shift, use_container_width=True)
            else:
                st.info("No shift production data available.")
        
        # Machine utilization
        st.subheader("🔧 Machine Utilization")
        machine_data = db.execute(text("""
            SELECT 
                machine_used,
                SUM(produced_quantity) as total_produced,
                COUNT(DISTINCT production_date) as days_used
            FROM production_log 
            WHERE production_date >= :start_date AND production_date <= :end_date
                AND machine_used IS NOT NULL
            GROUP BY machine_used
            ORDER BY total_produced DESC
        """), {"start_date": start_date, "end_date": end_date}).fetchall()
        
        if machine_data:
            df_machine = pd.DataFrame(machine_data, columns=['Machine', 'Total Produced', 'Days Used'])
            st.dataframe(df_machine, use_container_width=True)
        else:
            st.info("No machine utilization data available.")
        
        db.close()
        
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")

def create_production_record(wo_number, project_id, operator_id, machine_used, produced_quantity, production_date, shift, notes):
    """Create a new production record"""
    try:
        db = get_db()
        
        result = db.execute(text("""
            INSERT INTO production_log (wo_number, project_id, operator_id, machine_used,
                                      produced_quantity, production_date, shift, notes, created_by)
            VALUES (:wo_number, :project_id, :operator_id, :machine_used,
                   :produced_quantity, :production_date, :shift, :notes, :created_by)
            RETURNING id
        """), {
            "wo_number": wo_number,
            "project_id": project_id,
            "operator_id": operator_id,
            "machine_used": machine_used if machine_used else None,
            "produced_quantity": produced_quantity,
            "production_date": production_date,
            "shift": shift,
            "notes": notes if notes else None,
            "created_by": st.session_state.user_id
        })
        
        record_id = result.fetchone()[0]
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("production_log", record_id, "CREATE")
        
        return True
        
    except Exception as e:
        st.error(f"Error creating production record: {str(e)}")
        return False

def update_production_record(record_id, wo_number, project_id, operator_id, machine_used, produced_quantity, production_date, shift, notes):
    """Update an existing production record"""
    try:
        db = get_db()
        
        # Get old values for audit
        old_result = db.execute(text("SELECT * FROM production_log WHERE id = :id"), {"id": record_id})
        old_record = old_result.fetchone()
        
        db.execute(text("""
            UPDATE production_log 
            SET wo_number = :wo_number, project_id = :project_id, operator_id = :operator_id,
                machine_used = :machine_used, produced_quantity = :produced_quantity,
                production_date = :production_date, shift = :shift, notes = :notes
            WHERE id = :id
        """), {
            "wo_number": wo_number,
            "project_id": project_id,
            "operator_id": operator_id,
            "machine_used": machine_used if machine_used else None,
            "produced_quantity": produced_quantity,
            "production_date": production_date,
            "shift": shift,
            "notes": notes if notes else None,
            "id": record_id
        })
        
        db.commit()
        db.close()
        
        # Log audit trail for changes
        if old_record:
            changes = [
                ("wo_number", old_record[1], wo_number),
                ("project_id", old_record[2], project_id),
                ("operator_id", old_record[3], operator_id),
                ("machine_used", old_record[4], machine_used),
                ("produced_quantity", old_record[5], produced_quantity),
                ("production_date", str(old_record[6]), str(production_date)),
                ("shift", old_record[7], shift),
                ("notes", old_record[8], notes)
            ]
            
            for field, old_val, new_val in changes:
                if str(old_val) != str(new_val):
                    log_audit_trail("production_log", record_id, "UPDATE", field, str(old_val), str(new_val))
        
        return True
        
    except Exception as e:
        st.error(f"Error updating production record: {str(e)}")
        return False

def delete_production_record(record_id):
    """Delete a production record"""
    try:
        db = get_db()
        
        db.execute(text("DELETE FROM production_log WHERE id = :id"), {"id": record_id})
        db.commit()
        db.close()
        
        # Log audit trail
        log_audit_trail("production_log", record_id, "DELETE")
        
        return True
        
    except Exception as e:
        st.error(f"Error deleting production record: {str(e)}")
        return False

def duplicate_production_record(record):
    """Store record data for duplication"""
    st.session_state["duplicate_production_data"] = record
