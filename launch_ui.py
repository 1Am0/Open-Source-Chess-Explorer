#!/usr/bin/env python3
"""Launch script for Chess Explorer GUI - opens browser automatically."""

import os
import sys
import time
import webbrowser
from pathlib import Path
from threading import Timer

# Add the package to path if running as frozen exe
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    bundle_dir = Path(sys._MEIPASS)
else:
    # Running as normal script
    bundle_dir = Path(__file__).parent

# Set working directory to bundle directory for games folder access
os.chdir(bundle_dir)

def print_banner():
    """Print startup banner immediately."""
    print("\n" + "=" * 60)
    print("   ♟️  CHESS EXPLORER  ♟️")
    print("   Opening Explorer for Chess.com Games")
    print("=" * 60)
    print("\n⏳ Loading application...")
    print("   This may take a few seconds on first launch...")
    sys.stdout.flush()

def open_browser():
    """Open browser after short delay to ensure server is ready."""
    time.sleep(1.5)
    webbrowser.open('http://localhost:8000')
    print("\n✅ Browser opened! Chess Explorer is running.")
    print("   URL: http://localhost:8000")
    print("\n💡 TIP: Keep this window open while using the app.")
    print("   Press Ctrl+C to stop the server when done.\n")
    sys.stdout.flush()

if __name__ == "__main__":
    # Show banner immediately so user knows something is happening
    print_banner()
    
    # Open browser in background after delay
    Timer(1.5, open_browser).start()
    
    # Import and run the server
    try:
        from serve_frontend import main
        sys.argv = ['serve_frontend.py', '--port', '8000', '--games-dir', 'games', '--frontend', 'frontend']
        main()
    except KeyboardInterrupt:
        print("\n\nShutting down Chess Explorer. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError starting server: {e}")
        print("\nIf this is your first time, you may need to import games first.")
        print("Run this from command line: chess-explore-import your_username --player your_username")
        input("\nPress Enter to exit...")
        sys.exit(1)
