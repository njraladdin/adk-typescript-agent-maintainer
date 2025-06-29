import os
import sys
import requests
import json
import re
from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime
from typing import Dict, Any
import uuid

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

@app.route('/api/start_processing', methods=['POST'])
def api_start_processing():
    """
    Creates the ADK session and starts processing with SSE streaming.
    Returns a streaming response with session events.
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
    session_id = str(uuid.uuid4())
    
    def generate_events():
        try:
            # Step 1: Create the session
            session_payload = {
                "state": {
                    "commit_hash": commit_hash
                }
            }
            
            session_response = requests.post(
                f"{ADK_API_URL}/apps/{ADK_APP_NAME}/users/{user_id}/sessions/{session_id}",
                json=session_payload,
                timeout=10
            )
            
            if session_response.status_code != 200:
                error_msg = f"Failed to create session: {session_response.status_code} - {session_response.text}"
                yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
                return
                
            # Send session created event
            yield f"event: session_created\ndata: {json.dumps({'session_id': session_id, 'user_id': user_id, 'commit_hash': commit_hash})}\n\n"
            
            # Step 2: Start the agent run with SSE streaming
            run_payload = {
                "appName": ADK_APP_NAME,
                "userId": user_id,
                "sessionId": session_id,
                "streaming": False,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": json.dumps({"commit_id": commit_hash})}]
                }
            }
            
            # Make the streaming request to ADK
            response = requests.post(
                f"{ADK_API_URL}/run_sse",
                json=run_payload,
                stream=True,
                timeout=300  # 5 minute timeout for the entire operation
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to start agent: {response.status_code} - {response.text}"
                yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
                return
            
            # Stream the response from ADK to the client
            line_buffer = ""
            event_data_buffer = ""
            
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    line_buffer += chunk
                    
                    # Process complete lines
                    while '\n' in line_buffer:
                        line, line_buffer = line_buffer.split('\n', 1)
                        
                        if line.strip() == "":  # Empty line: dispatch event
                            if event_data_buffer.strip():
                                # Forward the event data to the client
                                yield f"data: {event_data_buffer.strip()}\n\n"
                                event_data_buffer = ""
                        elif line.startswith('data:'):
                            event_data_buffer += line[5:].strip() + '\n'
                        elif line.startswith(':'):
                            # Comment line, ignore
                            pass
                        # Other SSE fields can be handled here if needed
            
            # Handle any remaining data
            if event_data_buffer.strip():
                yield f"data: {event_data_buffer.strip()}\n\n"
                
            # Send completion event
            yield f"event: complete\ndata: {json.dumps({'status': 'completed'})}\n\n"
            
        except requests.exceptions.RequestException as e:
            yield f"event: error\ndata: {json.dumps({'error': f'Failed to communicate with ADK server: {e}'})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': f'Unexpected error: {e}'})}\n\n"

    return Response(
        generate_events(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )

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