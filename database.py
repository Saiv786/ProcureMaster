import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import streamlit as st

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/ppms")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

def init_database():
    """Initialize database tables"""
    try:
        with engine.connect() as conn:
            # Create tables if they don't exist
            
            # Users table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'Operator',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Projects table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    client VARCHAR(200),
                    location VARCHAR(300),
                    start_date DATE,
                    end_date DATE,
                    status VARCHAR(50) DEFAULT 'Active',
                    description TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Work Orders table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS work_orders (
                    id SERIAL PRIMARY KEY,
                    wo_number VARCHAR(100) UNIQUE NOT NULL,
                    project_id INTEGER REFERENCES projects(id),
                    floor VARCHAR(100),
                    description TEXT,
                    wo_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) DEFAULT 'Pending',
                    assigned_to INTEGER REFERENCES users(id),
                    priority VARCHAR(20) DEFAULT 'Medium',
                    due_date DATE,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Cutting Lists table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cutting_lists (
                    id SERIAL PRIMARY KEY,
                    order_number VARCHAR(100) NOT NULL,
                    project_id INTEGER REFERENCES projects(id),
                    floor VARCHAR(100),
                    description TEXT,
                    width DECIMAL(10,2),
                    height DECIMAL(10,2),
                    quantity INTEGER,
                    color VARCHAR(100),
                    status VARCHAR(50) DEFAULT 'Pending',
                    cut_date DATE,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Balance Orders table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS balance_orders (
                    id SERIAL PRIMARY KEY,
                    wo_number VARCHAR(100) NOT NULL,
                    project_id INTEGER REFERENCES projects(id),
                    floor VARCHAR(100),
                    priority VARCHAR(20) DEFAULT 'Medium',
                    specifications TEXT,
                    required_qty INTEGER,
                    fulfilled_qty INTEGER DEFAULT 0,
                    total_qty INTEGER,
                    due_date DATE,
                    status VARCHAR(50) DEFAULT 'Pending',
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Production Log table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS production_log (
                    id SERIAL PRIMARY KEY,
                    wo_number VARCHAR(100) NOT NULL,
                    project_id INTEGER REFERENCES projects(id),
                    operator_id INTEGER REFERENCES users(id),
                    machine_used VARCHAR(200),
                    produced_quantity INTEGER,
                    production_date DATE DEFAULT CURRENT_DATE,
                    shift VARCHAR(20),
                    notes TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Daily Targets table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_targets (
                    id SERIAL PRIMARY KEY,
                    order_number VARCHAR(100) NOT NULL,
                    project_id INTEGER REFERENCES projects(id),
                    description TEXT,
                    target_quantity INTEGER,
                    target_date DATE,
                    assigned_to INTEGER REFERENCES users(id),
                    status VARCHAR(50) DEFAULT 'Not Started',
                    actual_quantity INTEGER DEFAULT 0,
                    completion_date DATE,
                    notes TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Dispatch table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dispatch (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER REFERENCES projects(id),
                    order_number VARCHAR(100) NOT NULL,
                    vehicle_number VARCHAR(100),
                    driver_name VARCHAR(200),
                    dispatch_date DATE DEFAULT CURRENT_DATE,
                    delivery_date DATE,
                    status VARCHAR(50) DEFAULT 'Dispatched',
                    responsible_person INTEGER REFERENCES users(id),
                    challan_number VARCHAR(100),
                    notes TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Audit Trail table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id SERIAL PRIMARY KEY,
                    table_name VARCHAR(100) NOT NULL,
                    record_id INTEGER NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    field_name VARCHAR(100),
                    old_value TEXT,
                    new_value TEXT,
                    user_id INTEGER REFERENCES users(id),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create default admin user if not exists
            conn.execute(text("""
                INSERT INTO users (username, password_hash, role)
                SELECT 'admin', 'admin123', 'Admin'
                WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin')
            """))
            
            conn.commit()
            
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")

def log_audit_trail(table_name, record_id, action, field_name=None, old_value=None, new_value=None, user_id=None):
    """Log changes to audit trail"""
    try:
        db = get_db()
        db.execute(text("""
            INSERT INTO audit_trail (table_name, record_id, action, field_name, old_value, new_value, user_id)
            VALUES (:table_name, :record_id, :action, :field_name, :old_value, :new_value, :user_id)
        """), {
            "table_name": table_name,
            "record_id": record_id,
            "action": action,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
            "user_id": user_id or st.session_state.get('user_id')
        })
        db.commit()
        db.close()
    except Exception as e:
        print(f"Audit trail logging error: {str(e)}")
