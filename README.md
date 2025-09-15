# ProcureMaster

ProcureMaster is a **Project & Procurement Management System** built with **Python** and **Streamlit**.  
It helps manage construction projects, procurement, cutting, dispatch, and production workflows.

---

## Features
- Web interface powered by **Streamlit**
- PostgreSQL-backed database
- Authentication & role-based access
- Project, procurement, and production management
- Default admin login created on first run

---

## Requirements
- **Python** 3.11 or higher (tested with 3.12+)
- **PostgreSQL** 16+
- **[uv](https://github.com/astral-sh/uv)** package manager
- Build tools (`libpq-dev`, `build-essential`)

---

## Installation

1. **Clone the repository**
   ```bash
   git clone <your_repo_url>
   cd ProcureMaster
   ```

2. **Install system dependencies** (Ubuntu/Debian example)
   ```bash
   sudo apt update
   sudo apt install -y libpq-dev build-essential
   ```

3. **Set up PostgreSQL**
   ```bash
   sudo -u postgres psql -c "CREATE DATABASE ppms;"
   sudo -u postgres psql -c "CREATE USER ppms_user WITH PASSWORD 'strongpassword';"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ppms TO ppms_user;"
   ```

4. **Configure environment variable**
   ```bash
   export DATABASE_URL="postgresql://ppms_user:strongpassword@localhost/ppms"
   ```
   Add this line to your `~/.bashrc` or `~/.zshrc` to persist.

5. **Install Python dependencies with uv**
   ```bash
   uv pip install -r <(uv pip compile pyproject.toml)
   ```

---

## Database Initialization

Run the database initialization script to create tables and insert the default admin user:

```bash
python -c "from database import init_database; init_database()"
```

This will create:
- Default user: **admin**
- Default password: **admin123**

---

## Running the Application

Start the Streamlit server:

```bash
streamlit run app.py --server.port 5000
```

Then open in your browser:

```
http://localhost:5000
```

Login with the default credentials above.

---

## Production Deployment

- Use **systemd** or Docker to keep the app running in production
- Ensure `DATABASE_URL` is set in the environment
- Configure backups for the `ppms` PostgreSQL database
- Monitor application and database logs

---

## Default Login

| Username | Password  |
|----------|-----------|
| admin    | admin123  |

It is strongly recommended to change the default credentials after first login.

---

## License

This project is licensed under your chosen license.  
(Replace this section with the actual license you plan to use.)