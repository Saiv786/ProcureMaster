from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Decimal, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(50), default="Operator")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))
    client = Column(String(200))
    location = Column(String(300))
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(50), default="Active")
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkOrder(Base):
    __tablename__ = "work_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    wo_number = Column(String(100), unique=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    floor = Column(String(100))
    description = Column(Text)
    wo_type = Column(String(50))
    status = Column(String(50), default="Pending")
    assigned_to = Column(Integer, ForeignKey("users.id"))
    priority = Column(String(20), default="Medium")
    due_date = Column(Date)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CuttingList(Base):
    __tablename__ = "cutting_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(100))
    project_id = Column(Integer, ForeignKey("projects.id"))
    floor = Column(String(100))
    description = Column(Text)
    width = Column(Decimal(10, 2))
    height = Column(Decimal(10, 2))
    quantity = Column(Integer)
    color = Column(String(100))
    status = Column(String(50), default="Pending")
    cut_date = Column(Date)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BalanceOrder(Base):
    __tablename__ = "balance_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    wo_number = Column(String(100))
    project_id = Column(Integer, ForeignKey("projects.id"))
    floor = Column(String(100))
    priority = Column(String(20), default="Medium")
    specifications = Column(Text)
    required_qty = Column(Integer)
    fulfilled_qty = Column(Integer, default=0)
    total_qty = Column(Integer)
    due_date = Column(Date)
    status = Column(String(50), default="Pending")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProductionLog(Base):
    __tablename__ = "production_log"
    
    id = Column(Integer, primary_key=True, index=True)
    wo_number = Column(String(100))
    project_id = Column(Integer, ForeignKey("projects.id"))
    operator_id = Column(Integer, ForeignKey("users.id"))
    machine_used = Column(String(200))
    produced_quantity = Column(Integer)
    production_date = Column(Date)
    shift = Column(String(20))
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class DailyTarget(Base):
    __tablename__ = "daily_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(100))
    project_id = Column(Integer, ForeignKey("projects.id"))
    description = Column(Text)
    target_quantity = Column(Integer)
    target_date = Column(Date)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    status = Column(String(50), default="Not Started")
    actual_quantity = Column(Integer, default=0)
    completion_date = Column(Date)
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Dispatch(Base):
    __tablename__ = "dispatch"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    order_number = Column(String(100))
    vehicle_number = Column(String(100))
    driver_name = Column(String(200))
    dispatch_date = Column(Date)
    delivery_date = Column(Date)
    status = Column(String(50), default="Dispatched")
    responsible_person = Column(Integer, ForeignKey("users.id"))
    challan_number = Column(String(100))
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditTrail(Base):
    __tablename__ = "audit_trail"
    
    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100))
    record_id = Column(Integer)
    action = Column(String(50))
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
