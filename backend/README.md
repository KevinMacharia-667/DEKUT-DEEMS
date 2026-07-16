# DeKUT Event Management System - Backend

FastAPI backend application for the DeKUT Event Management Platform.

## Requirements
- Python 3.11+
- Pip (Python Package Installer)

## Setup & Running (Windows)

1. **Create Virtual Environment**:
   ```cmd
   python -m venv venv
   ```

2. **Activate Virtual Environment**:
   ```cmd
   venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

4. **Environment Variables Setup**:
   Copy the example environment file:
   ```cmd
   copy .env.example .env
   ```

5. **Start Development Server**:
   ```cmd
   uvicorn main:app --reload
   ```

6. **Verify API is running**:
   Open a browser or run the following PowerShell command:
   ```powershell
   Invoke-RestMethod -Uri http://127.0.0.1:8000/health
   ```
   Expected response:
   ```json
   {"status": "ok"}
   ```

## Development Features
- **Auto-reloading**: Uvicorn is set to reload when code changes are detected.
- **Interactive Documentation**: Swagger UI documentation is available at `http://127.0.0.1:8000/docs` once the server is running.
