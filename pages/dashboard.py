import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_db
from sqlalchemy import text

def show():
    st.title("📊 Dashboard")
    
    # Fetch dashboard data
    db = get_db()
    
    try:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Total Projects
            result = db.execute(text("SELECT COUNT(*) FROM projects WHERE status = 'Active'"))
            active_projects = result.fetchone()[0]
            st.metric("Active Projects", active_projects)
        
        with col2:
            # Pending Work Orders
            result = db.execute(text("SELECT COUNT(*) FROM work_orders WHERE status = 'Pending'"))
            pending_wo = result.fetchone()[0]
            st.metric("Pending Work Orders", pending_wo)
        
        with col3:
            # Today's Targets
            result = db.execute(text("""
                SELECT COUNT(*) FROM daily_targets 
                WHERE target_date = CURRENT_DATE AND status != 'Completed'
            """))
            todays_targets = result.fetchone()[0]
            st.metric("Today's Pending Targets", todays_targets)
        
        with col4:
            # Balance Orders
            result = db.execute(text("SELECT COUNT(*) FROM balance_orders WHERE status = 'Pending'"))
            balance_orders = result.fetchone()[0]
            st.metric("Pending Balance Orders", balance_orders)
        
        st.divider()
        
        # Charts and visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Work Orders by Status")
            wo_status_data = db.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM work_orders 
                GROUP BY status
            """)).fetchall()
            
            if wo_status_data:
                df_wo = pd.DataFrame(wo_status_data, columns=['Status', 'Count'])
                fig_wo = px.pie(df_wo, values='Count', names='Status', 
                               title="Work Orders Distribution")
                st.plotly_chart(fig_wo, use_container_width=True)
            else:
                st.info("No work orders data available")
        
        with col2:
            st.subheader("Production by Week")
            production_data = db.execute(text("""
                SELECT 
                    DATE_TRUNC('week', production_date) as week,
                    SUM(produced_quantity) as total_produced
                FROM production_log 
                WHERE production_date >= CURRENT_DATE - INTERVAL '8 weeks'
                GROUP BY week
                ORDER BY week
            """)).fetchall()
            
            if production_data:
                df_prod = pd.DataFrame(production_data, columns=['Week', 'Total Produced'])
                fig_prod = px.bar(df_prod, x='Week', y='Total Produced',
                                 title="Weekly Production Trend")
                st.plotly_chart(fig_prod, use_container_width=True)
            else:
                st.info("No production data available")
        
        # Recent activity
        st.subheader("📋 Recent Work Orders")
        recent_wo = db.execute(text("""
            SELECT 
                wo.wo_number,
                p.name as project_name,
                wo.wo_type,
                wo.status,
                wo.priority,
                u.username as assigned_to,
                wo.created_at
            FROM work_orders wo
            LEFT JOIN projects p ON wo.project_id = p.id
            LEFT JOIN users u ON wo.assigned_to = u.id
            ORDER BY wo.created_at DESC
            LIMIT 10
        """)).fetchall()
        
        if recent_wo:
            df_recent = pd.DataFrame(recent_wo, columns=[
                'WO Number', 'Project', 'Type', 'Status', 'Priority', 'Assigned To', 'Created At'
            ])
            st.dataframe(df_recent, use_container_width=True)
        else:
            st.info("No recent work orders")
        
        # Today's targets
        st.subheader("🎯 Today's Targets")
        todays_targets_data = db.execute(text("""
            SELECT 
                dt.order_number,
                p.name as project_name,
                dt.description,
                dt.target_quantity,
                dt.actual_quantity,
                dt.status,
                u.username as assigned_to
            FROM daily_targets dt
            LEFT JOIN projects p ON dt.project_id = p.id
            LEFT JOIN users u ON dt.assigned_to = u.id
            WHERE dt.target_date = CURRENT_DATE
            ORDER BY dt.status ASC
        """)).fetchall()
        
        if todays_targets_data:
            df_targets = pd.DataFrame(todays_targets_data, columns=[
                'Order Number', 'Project', 'Description', 'Target Qty', 'Actual Qty', 'Status', 'Assigned To'
            ])
            st.dataframe(df_targets, use_container_width=True)
        else:
            st.info("No targets for today")
            
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
    finally:
        db.close()
