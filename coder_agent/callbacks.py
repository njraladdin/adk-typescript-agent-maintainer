import json
import os
import glob
from pathlib import Path
from google.adk.agents.callback_context import CallbackContext
from typing import Optional, Any

# Import constants from the centralized constants module
from .constants import ARTIFACTS_DIR, AGENT_WORKSPACE_DIR, TYPESCRIPT_REPO_DIR, TYPESCRIPT_REPO_URL
# Import workspace utilities
from .workspace_utils import (
    create_workspace_directory, 
    clone_repo, 
    install_dependencies, 
    build_project,
    setup_typescript_repository_environment,
    check_workspace_setup_status
)

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
    This function checks what steps have already been completed and only performs the necessary steps.
    If any step in the setup process fails, it will print an error message and return.
    """
    print("CALLBACK: Setting up TypeScript repository workspace...")
    
    # Create workspace directory if it doesn't exist
    workspace_path = create_workspace_directory()
    typescript_repo_path = workspace_path / TYPESCRIPT_REPO_DIR
    
    # Check the status of each setup step
    setup_status = check_workspace_setup_status(workspace_path)
    
    # Step 1: Clone the repository if not already cloned
    if not setup_status["repo_cloned"]:
        print("CALLBACK: Repository not cloned. Cloning now...")
        clone_success, clone_message = clone_repo(TYPESCRIPT_REPO_URL, typescript_repo_path)
        if not clone_success:
            print(f"CALLBACK ERROR: Repository setup failed: {clone_message}")
            return None
        print(f"CALLBACK: ✓ {clone_message}")
    else:
        print("CALLBACK: ✓ Repository already cloned")
    
    # Step 2: Install dependencies if not already installed
    if not setup_status["dependencies_installed"]:
        print("CALLBACK: Dependencies not installed. Installing now...")
        install_success, install_message = install_dependencies(typescript_repo_path)
        if not install_success:
            print(f"CALLBACK ERROR: Dependency installation failed: {install_message}")
            # Store partial path even if failed
            callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
            return None
        print(f"CALLBACK: ✓ {install_message}")
    else:
        print("CALLBACK: ✓ Dependencies already installed")
    
    # Step 3: Build the project if not already built
    if not setup_status["project_built"]:
        print("CALLBACK: Project not built. Building now...")
        build_result = build_project(typescript_repo_path)
        if not build_result["success"]:
            print(f"CALLBACK ERROR: Project build failed: {build_result['message']}")
            if build_result["stderr"]:
                print(f"CALLBACK ERROR: Build stderr: {build_result['stderr']}")
            # Store partial path even if failed
            callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
            return None
        print(f"CALLBACK: ✓ {build_result['message']}")
        if build_result["stdout"]:
            print(f"CALLBACK: Build output:\n{build_result['stdout']}")
    else:
        print("CALLBACK: ✓ Project already built")
    
    # Step 4: Setup repository environment if not already set up
    if not setup_status["env_setup"]:
        print("CALLBACK: Environment not set up. Setting up now...")
        env_success, env_message = setup_typescript_repository_environment(typescript_repo_path)
        if not env_success:
            print(f"CALLBACK ERROR: Environment setup failed: {env_message}")
            # Store partial path even if failed
            callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
            return None
        print(f"CALLBACK: ✓ {env_message}")
    else:
        print("CALLBACK: ✓ Environment already set up")
    
    if setup_status["all_steps_completed"]:
        print("CALLBACK: All setup steps were already completed")
    else:
        print("CALLBACK: TypeScript repository setup completed successfully")
    
    # Store the repository path in the session state
    callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
    
    return None

