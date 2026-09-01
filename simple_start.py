import os
import sys
import subprocess
import time

def main():
    print("Starting Tennis Court Booking System...")
    
    # Set environment variables
    os.environ["FLASK_APP"] = "app.py"
    os.environ["FLASK_ENV"] = "development"
    print("Environment variables set")
    
    # Create necessary directories
    os.makedirs("static/uploads/courts", exist_ok=True)
    os.makedirs("instance", exist_ok=True)
    print("Directories created")
    
    # Install dependencies
    print("Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Dependencies installed")
    
    # Initialize database
    print("Initializing database...")
    try:
        from app import app, init_db
        with app.app_context():
            init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
    
    # Start server
    print("\n===================================")
    print("System is starting")
    print("===================================")
    print("Access at: http://localhost:5000")
    print("Admin account: admin/admin123")
    print("\nPress Ctrl+C to stop the server")
    
    # Wait a moment
    time.sleep(2)
    
    # Run the Flask server
    subprocess.run([sys.executable, "-m", "flask", "run"])

if __name__ == "__main__":
    main()