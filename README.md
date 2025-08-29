# Student Data Flask App

A simple Flask-based web application to manage student data using **SQLite** as the backend database.

## Features
- Add, update, and delete student records
- View stored student data in a clean interface
- Lightweight, uses SQLite (no external DB setup needed)

## Requirements
- Python 3.8+
- Virtual environment (recommended)

## Installation & Run
```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Start the Flask app
python app.py

# 5. Open in browser
# After running the above command, open:
http://localhost:5000
