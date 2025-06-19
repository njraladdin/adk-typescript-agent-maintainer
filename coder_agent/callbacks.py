import json
import os
from google.adk.agents.callback_context import CallbackContext
from typing import Optional, Any

# Define the output directory at a single, clear location
ARTIFACTS_DIR = "debug_output"

def save_gathered_context(callback_context: CallbackContext) -> Optional[Any]:
    """
    An after-agent callback that checks for the 'gathered_context' in the
    session state and saves it to a JSON file for debugging and inspection.
    """
    # Check if the context object exists in the state.
    # The 'state' property of the callback_context gives you read/write access.
    if 'gathered_context' in callback_context.state:
        
        context_data = callback_context.state['gathered_context']
        
        # Use the invocation_id to give each run a unique filename.
        run_id = callback_context.invocation_id
        commit_sha = context_data.get('commit_info', {}).get('commit_sha', 'unknown_commit')
        
        # Construct a descriptive filename
        filename = f"context__{run_id}__{commit_sha}.json"
        
        # Ensure the artifacts directory exists
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        
        output_path = os.path.join(ARTIFACTS_DIR, filename)
        
        print(f"CALLBACK: Found 'gathered_context'. Saving to '{output_path}'...")
        
        # Create a serializable version of the context data
        serializable_context = {
            'commit_info': context_data.get('commit_info', {}),
            'python_repo_structure': context_data.get('python_repo_structure', {}),
            'typescript_repo_structure': context_data.get('typescript_repo_structure', {}),
            'python_context_files': {
                path: content 
                for path, content in context_data.get('python_context_files', {}).items()
            },
            'typescript_context_files': {
                path: content 
                for path, content in context_data.get('typescript_context_files', {}).items()
            }
        }
        
        # Add summary statistics
        serializable_context['summary'] = {
            'commit_sha': commit_sha,
            'python_files_count': len(serializable_context['python_context_files']),
            'typescript_files_count': len(serializable_context['typescript_context_files']),
            'python_files': list(serializable_context['python_context_files'].keys()),
            'typescript_files': list(serializable_context['typescript_context_files'].keys())
        }
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # Use indent for readability
                json.dump(serializable_context, f, indent=2)
            print(f"CALLBACK: Successfully saved context artifact.")
        except Exception as e:
            print(f"CALLBACK: Error saving context artifact: {e}")
            
    # This callback doesn't need to alter the agent's flow, so it returns None.
    return None 