import os
import sys
import requests
import json
import re
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from typing import Dict, Any

# Add parent directory to Python path to allow imports from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# ADK configuration
ADK_APP_NAME = "maintainer_agent"
ADK_API_URL = "http://127.0.0.1:8000"

# ==============================================================================
# FLASK APP SETUP
# ==============================================================================

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def validate_commit_hash(commit_hash: str):
    """Validate commit hash format."""
    if not re.match(r'^[a-f0-9]{7,40}$', commit_hash.lower()):
        return {"valid": False, "error": "Invalid commit hash format"}
    return {"valid": True}

# ==============================================================================
# WEB ROUTES
# ==============================================================================

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html', adk_api_url=ADK_API_URL)

@app.route('/api/trace/<session_id>')
def api_get_trace(session_id):
    """
    Proxy route to get trace data from ADK server.
    This avoids CORS issues by making the request server-side.
    """
    try:
        response = requests.get(
            f"{ADK_API_URL}/debug/trace/session/{session_id}",
            timeout=10
        )
        print(response.json())
        if response.status_code == 200:
            return jsonify(response.json())
        elif response.status_code == 404:
            return jsonify([]), 404
        else:
            return jsonify({"error": f"ADK server returned {response.status_code}"}), response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to ADK server: {e}"}), 500

@app.route('/api/start_processing', methods=['POST'])
def api_start_processing():
    """
    Creates the ADK session and triggers the agent run in a fire-and-forget way.
    Returns the session_id for the client to poll the trace endpoint directly.
    """
    data = request.get_json()
    commit_hash = data.get('commit_hash', '').strip()
    
    if not commit_hash:
        return jsonify({"success": False, "error": "Commit hash is required"}), 400
    
    # Validate commit hash format
    validation = validate_commit_hash(commit_hash)
    if not validation['valid']:
        return jsonify({"success": False, "error": validation['error']}), 400
    
    # Generate unique IDs for this run
    user_id = f"web-ui-user-{commit_hash[:7]}"
    
    try:
        # Step 1: Create the session
        session_payload = {
            "state": {
                "commit_hash": commit_hash
            }
        }
        
        session_response = requests.post(
            f"{ADK_API_URL}/apps/{ADK_APP_NAME}/users/{user_id}/sessions",
            json=session_payload,
            timeout=10
        )
        
        if session_response.status_code != 200:
            error_msg = f"Failed to create session: {session_response.status_code} - {session_response.text}"
            return jsonify({"success": False, "error": error_msg}), 500
            
        session_data = session_response.json()
        session_id = session_data.get('id')
        
        if not session_id:
            return jsonify({"success": False, "error": "No session ID returned from ADK server"}), 500
        
        # Step 2: Trigger the agent run (fire-and-forget with short timeout)
        run_payload = {
            "app_name": ADK_APP_NAME,
            "user_id": user_id,
            "session_id": session_id,
            "streaming": False,
            "new_message": {
                "role": "user",
                "parts": [{"text": json.dumps({"commit_id": commit_hash})}]
            }
        }
        
        # Make the request with a very short timeout - we don't wait for completion
        # The ADK server will start processing in the background
        try:
            requests.post(
                f"{ADK_API_URL}/run",
                json=run_payload,
                timeout=2  # Very short timeout - just to send the request
            )
        except requests.exceptions.Timeout:
            # This is expected and OK - we don't want to wait for completion
            pass
        except requests.exceptions.RequestException as e:
            # Only fail if we can't send the request at all
            return jsonify({"success": False, "error": f"Failed to start agent: {e}"}), 500
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "user_id": user_id,
            "commit_hash": commit_hash
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "error": f"Failed to communicate with ADK server: {e}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": f"Unexpected error: {e}"}), 500

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000) 