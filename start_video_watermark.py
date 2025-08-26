#!/usr/bin/env python3
"""
Video Watermark Removal Quick Start Script
"""

import os
import sys
import subprocess
import webbrowser
import time

def check_dependencies():
    """Check dependencies"""
    print("🔍 Checking dependencies...")
    
    try:
        import cv2
        import numpy
        import flask
        print("✅ All dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip3 install -r requirements.txt")
        return False

def run_tests():
    """Run tests"""
    print("\n🧪 Running functional tests...")
    
    try:
        result = subprocess.run([sys.executable, "test_video_watermark.py"], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Some tests failed")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def start_server():
    """Start server"""
    print("\n🚀 Starting Video Watermark Removal service...")
    
    try:
        # Start Flask application
        print("Server starting at http://localhost:50001")
        print("Video Watermark Removal page: http://localhost:50001/")
        print("\nPress Ctrl+C to stop the server")
        
        # Delay browser opening
        def open_browser():
            time.sleep(2)
            webbrowser.open("http://localhost:50001/")
        
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Start Flask application
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run([sys.executable, "app/routes.py"])
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def main():
    """Main function"""
    print("🎬 Video Watermark Removal Launcher")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Run tests
    if not run_tests():
        print("\n⚠️  Tests failed, but you can still try to start the server")
        response = input("Continue starting the server? (y/N): ")
        if response.lower() != 'y':
            return
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()