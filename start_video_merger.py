#!/usr/bin/env python3
"""
Video Merger Quick Start Script
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

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    print("🔍 Checking FFmpeg...")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ FFmpeg is installed")
            return True
        else:
            print("❌ FFmpeg not working properly")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found")
        print("Please install FFmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/")
        return False
    except Exception as e:
        print(f"❌ Error checking FFmpeg: {e}")
        return False

def run_tests():
    """Run tests"""
    print("\n🧪 Running video merger tests...")
    
    try:
        result = subprocess.run([sys.executable, "test_video_merger.py"], 
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
    print("\n🚀 Starting MediaCraft with Video Merger...")
    
    try:
        # Start Flask application
        print("Server starting at http://localhost:50001")
        print("Video Watermark Removal: http://localhost:50001/")
        print("Video Merger: http://localhost:50001/video-merger.html")
        print("\nPress Ctrl+C to stop the server")
        
        # Delay browser opening
        def open_browser():
            time.sleep(2)
            webbrowser.open("http://localhost:50001/video-merger.html")
        
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Start Flask application
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run([sys.executable, "app.py"])
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def main():
    """Main function"""
    print("🎬 MediaCraft Video Merger Launcher")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Check FFmpeg
    if not check_ffmpeg():
        print("\n⚠️  FFmpeg is required for video merging")
        response = input("Continue without FFmpeg? Video merging will not work. (y/N): ")
        if response.lower() != 'y':
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