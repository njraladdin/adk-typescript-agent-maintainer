#!/usr/bin/env python3
"""
Launch the Commit Processor Web UI
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commit_processor.app import app

if __name__ == "__main__":
    print("🚀 Starting ADK TypeScript Commit Processor Web UI...")
    print("📍 Open your browser to: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000) 