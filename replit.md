# Overview

This is a Project & Procurement Management System built with Streamlit that replaces manual Excel workflows for construction project management. The system manages multiple projects, tracks procurement, cutting, dispatch, and production activities, maintains historical records with audit trails, and provides role-based access control for different user types (Admin, Project Manager, Operator).

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit web application with multi-page architecture
- **UI Structure**: Tab-based interface for different modules within each page
- **State Management**: Streamlit session state for authentication and user context
- **Authentication Flow**: Login-based access with role-based permissions

## Backend Architecture
- **Database Layer**: SQLAlchemy ORM with raw SQL queries for complex operations
- **Authentication**: SHA256 password hashing with session-based authentication
- **Data Models**: Relational database design with foreign key relationships between projects, work orders, cutting lists, and other entities
- **Audit Trail**: Comprehensive logging system for all CRUD operations

## Core Modules
- **Project Management**: CRUD operations for project lifecycle management
- **Work Orders**: Task management system with status tracking and assignments
- **Cutting Lists**: Material cutting specifications with dimensions and quantities
- **Balance Orders**: Order balancing and inventory management
- **Production Log**: Production activity tracking with operator assignments
- **Daily Targets**: Goal setting and performance tracking
- **Dispatch & Delivery**: Shipping and delivery management with challan generation
- **User Management**: Role-based user administration (Admin only)
- **Dashboard**: Real-time metrics and data visualization using Plotly
- **Audit Trail**: Historical change tracking for compliance

## Permission System
- **Admin**: Full system access including user management
- **Project Manager**: Project and work order management capabilities
- **Operator**: Limited access to assigned tasks and data entry

## Data Architecture
- **Primary Entities**: Users, Projects, Work Orders, Cutting Lists, Balance Orders, Production Log, Daily Targets, Dispatch Records
- **Relationships**: Hierarchical structure with projects as parent entities linked to work orders and other operational records
- **Data Integrity**: Foreign key constraints and referential integrity maintained through SQLAlchemy

# External Dependencies

## Database
- **PostgreSQL**: Primary data storage with connection string configuration via environment variables
- **SQLAlchemy**: ORM and database abstraction layer for connection management and query execution

## Frontend Libraries
- **Streamlit**: Web application framework for UI components and page routing
- **Pandas**: Data manipulation and tabular data handling
- **Plotly**: Interactive charts and data visualization for dashboard analytics

## Utility Libraries
- **hashlib**: Password hashing for authentication security
- **datetime**: Date and time handling across the application
- **os**: Environment variable management for configuration

## Reporting System
- **Text-based Reports**: Delivery challan generation with formatted text output
- **Data Export**: CSV/Excel export capabilities through Pandas integration