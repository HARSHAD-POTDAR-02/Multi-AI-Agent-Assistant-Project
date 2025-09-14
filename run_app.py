#!/usr/bin/env python3
"""
Simple script to run the Simi.ai application
"""
import subprocess
import sys
import os
import time
import threading

def run_backend():
    """Run the backend server"""
    print("Starting Backend Server...")
    try:
        subprocess.run([sys.executable, "backend.py"], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("Backend server stopped.")

def run_frontend():
    """Run the frontend server"""
    print("Starting Frontend Server...")
    time.sleep(3)  # Wait for backend to start
    try:
        subprocess.run(["npm", "start"], cwd="frontend")
    except KeyboardInterrupt:
        print("Frontend server stopped.")

def main():
    print("=" * 50)
    print("Starting Simi.ai Multi-Agent Assistant")
    print("=" * 50)
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend)
    backend_thread.daemon = True
    backend_thread.start()
    
    # Start frontend in main thread
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\nShutting down Simi.ai...")
        sys.exit(0)

if __name__ == "__main__":
    main()