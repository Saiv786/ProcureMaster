import streamlit as st
from database import get_db
from sqlalchemy import text
import hashlib

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    """Authenticate user credentials"""
    try:
        db = get_db()
        result = db.execute(text("""
            SELECT id, username, role 
            FROM users 
            WHERE username = :username AND password_hash = :password_hash
        """), {
            "username": username,
            "password_hash": hash_password(password)
        })
        
        user = result.fetchone()
        db.close()
        
        if user:
            return {
                "id": user[0],
                "username": user[1], 
                "role": user[2]
            }
        return None
        
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return None

def get_user_role(user_id):
    """Get user role by user ID"""
    try:
        db = get_db()
        result = db.execute(text("""
            SELECT role FROM users WHERE id = :user_id
        """), {"user_id": user_id})
        
        role = result.fetchone()
        db.close()
        
        return role[0] if role else None
        
    except Exception as e:
        return None

def logout_user():
    """Clear session state for logout"""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.user_role = None
    st.session_state.current_page = "dashboard"

def create_user(username, password, role):
    """Create a new user"""
    try:
        db = get_db()
        
        # Check if username already exists
        result = db.execute(text("""
            SELECT id FROM users WHERE username = :username
        """), {"username": username})
        
        if result.fetchone():
            db.close()
            return False, "Username already exists"
        
        # Create user
        db.execute(text("""
            INSERT INTO users (username, password_hash, role)
            VALUES (:username, :password_hash, :role)
        """), {
            "username": username,
            "password_hash": hash_password(password),
            "role": role
        })
        
        db.commit()
        db.close()
        return True, "User created successfully"
        
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

def get_all_users():
    """Get all users"""
    try:
        db = get_db()
        result = db.execute(text("""
            SELECT id, username, role, created_at
            FROM users
            ORDER BY created_at DESC
        """))
        
        users = result.fetchall()
        db.close()
        
        return [{"id": user[0], "username": user[1], "role": user[2], "created_at": user[3]} for user in users]
        
    except Exception as e:
        st.error(f"Error fetching users: {str(e)}")
        return []

def update_user_role(user_id, new_role):
    """Update user role"""
    try:
        db = get_db()
        db.execute(text("""
            UPDATE users 
            SET role = :role, updated_at = CURRENT_TIMESTAMP
            WHERE id = :user_id
        """), {
            "role": new_role,
            "user_id": user_id
        })
        
        db.commit()
        db.close()
        return True, "User role updated successfully"
        
    except Exception as e:
        return False, f"Error updating user role: {str(e)}"

def delete_user(user_id):
    """Delete user"""
    try:
        db = get_db()
        db.execute(text("""
            DELETE FROM users WHERE id = :user_id
        """), {"user_id": user_id})
        
        db.commit()
        db.close()
        return True, "User deleted successfully"
        
    except Exception as e:
        return False, f"Error deleting user: {str(e)}"
