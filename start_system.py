#!/usr/bin/env python3
"""
Simple startup script for the Multi-Agent System
"""

import sys
import webbrowser
import time
import threading
from app import app, socketio

def main():
    """Start the multi-agent system."""
    print("🤖 Multi-Agent System")
    print("=" * 40)
    print("Starting the system...")
    print("🌐 Web Interface: http://localhost:5000")
    print("📊 System Status: http://localhost:5000/api/health")
    print("=" * 40)
    print("Press Ctrl+C to stop the system")
    print("=" * 40)
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(3)
        try:
            webbrowser.open("http://localhost:5000")
            print("✅ Browser opened to http://localhost:5000")
        except Exception as e:
            print(f"⚠️  Could not open browser automatically: {e}")
            print("   Please open http://localhost:5000 in your browser")
    
    # Start browser in background
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the Flask app
    try:
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 System stopped by user")
    except Exception as e:
        print(f"❌ Error starting system: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
