import json
import os
import glob
import subprocess
from pathlib import Path
from google.adk.agents.callback_context import CallbackContext
from typing import Optional, Any

# Define the output directory at a single, clear location
ARTIFACTS_DIR = "debug_output"  
AGENT_WORKSPACE_DIR = "agent_workspace"
TYPESCRIPT_REPO_DIR = "adk-typescript"

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
            
            # Store the path to the saved file in the session state
            callback_context.state['context_artifact_path'] = output_path
            
        except Exception as e:
            print(f"CALLBACK: Error saving context artifact: {e}")
            
    # This callback doesn't need to alter the agent's flow, so it returns None.
    return None 

def load_gathered_context(callback_context: CallbackContext) -> Optional[Any]:
    """
    A before-agent callback that checks if 'gathered_context' is in the session state.
    If not, it finds the latest context JSON file in the debug_output directory and loads it.
    """
    # Only proceed if 'gathered_context' is not already in the state
    if 'gathered_context' not in callback_context.state:
        print("CALLBACK: 'gathered_context' not found in session state. Attempting to load from file...")
        
        try:
            # Ensure the artifacts directory exists
            if not os.path.exists(ARTIFACTS_DIR):
                print(f"CALLBACK: Directory {ARTIFACTS_DIR} does not exist. No context files to load.")
                return None
                
            # Find all context files
            context_files = glob.glob(os.path.join(ARTIFACTS_DIR, "context__*.json"))
            
            if not context_files:
                print(f"CALLBACK: No context files found in {ARTIFACTS_DIR}.")
                return None
                
            # Sort by modification time (newest first)
            latest_file = max(context_files, key=os.path.getmtime)
            
            print(f"CALLBACK: Found latest context file: {latest_file}")
            
            # Load the JSON data
            with open(latest_file, "r", encoding="utf-8") as f:
                context_data = json.load(f)
            
            # Create a properly structured gathered_context object
            gathered_context = {
                'commit_info': context_data.get('commit_info', {}),
                'python_repo_structure': context_data.get('python_repo_structure', {}),
                'typescript_repo_structure': context_data.get('typescript_repo_structure', {}),
                'python_context_files': context_data.get('python_context_files', {}),
                'typescript_context_files': context_data.get('typescript_context_files', {})
            }
                
            # Store the loaded context in the session state
            callback_context.state['gathered_context'] = gathered_context
            print(f"CALLBACK: Successfully loaded context from {latest_file}")
            
            # Also store the path to the loaded file
            callback_context.state['context_artifact_path'] = latest_file
            
        except Exception as e:
            print(f"CALLBACK: Error loading context from file: {e}")
    
    # This callback doesn't need to alter the agent's flow, so it returns None.
    return None

def setup_agent_workspace(callback_context: CallbackContext) -> Optional[Any]:
    """
    A before-agent callback that sets up the agent workspace with the TypeScript repository.
    If any step in the setup process fails (clone, install dependencies, or build),
    it will print an error message and return.
    """
    # Create base workspace directory
    workspace_path = Path(AGENT_WORKSPACE_DIR)
    workspace_path.mkdir(exist_ok=True, parents=True)
    
    # Set up the TypeScript repository in a subdirectory
    typescript_repo_path = workspace_path / TYPESCRIPT_REPO_DIR
    repo_url = "https://github.com/njraladdin/adk-typescript.git"
    
    # Check if repository already exists
    if typescript_repo_path.exists() and (typescript_repo_path / ".git").exists():
        print(f"CALLBACK: TypeScript repository already exists at {typescript_repo_path}.")
        
        # Store the repository path in the session state
        callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
        return None
    
    print(f"CALLBACK: Setting up TypeScript repository at {typescript_repo_path}...")
    
    # Determine npm command based on platform
    import platform
    is_windows = platform.system().lower() == 'windows'
    npm_cmd = "npm.cmd" if is_windows else "npm"
    
    # Step 1: Clone the repository
    try:
        print(f"CALLBACK: Cloning repository {repo_url}...")
        subprocess.run(
            ["git", "clone", repo_url, str(typescript_repo_path)],
            check=True,
            capture_output=True,
            text=True,
            shell=is_windows
        )
        
        # Get the absolute path of the TypeScript repository
        typescript_repo_abs_path = typescript_repo_path.absolute()
        print(f"CALLBACK: Repository cloned to {typescript_repo_abs_path}")
    except Exception as e:
        print(f"CALLBACK ERROR: Failed to clone repository: {e}")
        return None
    
    # Store the repository path in the session state
    callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
    
    # Step 2: Install dependencies
    try:
        print(f"CALLBACK: Installing dependencies using {npm_cmd}...")
        subprocess.run(
            [npm_cmd, "install", "--ignore-scripts"],
            cwd=str(typescript_repo_abs_path),
            check=True,
            capture_output=True,
            text=True,
            shell=is_windows
        )
        print("CALLBACK: Dependencies installed successfully")
    except Exception as e:
        print(f"CALLBACK ERROR: Failed to install dependencies: {e}")
        return None
    
    # Step 3: Build the project
    try:
        print("CALLBACK: Building TypeScript project...")
        result = subprocess.run(
            [npm_cmd, "run", "build"],
            cwd=str(typescript_repo_abs_path),
            check=True,
            capture_output=True,
            text=True,
            shell=is_windows
        )
        print("CALLBACK: TypeScript project built successfully")
    except subprocess.CalledProcessError as e:
        print(f"CALLBACK ERROR: Failed to build project (exit code {e.returncode})")
        if e.stdout:
            print("CALLBACK: Build stdout:")
            print(e.stdout)
        if e.stderr:
            print("CALLBACK: Build stderr:")
            print(e.stderr)
        return None
    except Exception as e:
        print(f"CALLBACK ERROR: Failed to build project: {e}")
        return None
    
    print("CALLBACK: TypeScript repository setup completed successfully")
    return None

