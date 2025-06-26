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
# Import git utilities for fresh repository setup
from .git_utils import reset_repo_to_clean_state, pull_latest_changes, fetch_commit_diff_data, fetch_repo_structure, fetch_file_content

def gather_commit_context(callback_context: CallbackContext) -> Optional[Any]:
    """
    A before-agent callback that gathers basic commit information and files.
    This does the mechanical work of fetching commit diff, repo structures, and Python files.
    """
    print("CALLBACK: Gathering commit context...")
    
    # Check if we have a commit_id in the invocation input
    if hasattr(callback_context, 'invocation_input') and callback_context.invocation_input:
        commit_id = callback_context.invocation_input.get('commit_id')
        if not commit_id:
            print("CALLBACK ERROR: No commit_id found in invocation input")
            return None
    else:
        print("CALLBACK ERROR: No invocation input available")
        return None
    
    print(f"CALLBACK: Processing commit {commit_id}")
    
    # Step 1: Get commit diff and changed files
    print("CALLBACK: Fetching commit diff...")
    commit_info = fetch_commit_diff_data(commit_id)
    
    # Step 2: Get content of each changed Python file and add to commit_info
    print("CALLBACK: Fetching Python file contents...")
    changed_files_with_content = []
    for file_path in commit_info.get('changed_files', []):
        content = fetch_file_content('google/adk-python', file_path)
        changed_files_with_content.append({
            'path': file_path,
            'content': content
        })
    
    # Enhanced commit context with file contents
    commit_context = {
        'commit_sha': commit_info['commit_sha'],
        'diff': commit_info['diff'],
        'changed_files': changed_files_with_content
    }
    callback_context.state['commit_context'] = commit_context
    
    # Step 3: Get TypeScript repository structure  
    print("CALLBACK: Fetching TypeScript repository structure...")
    typescript_structure = fetch_repo_structure('njraladdin/adk-typescript')
    callback_context.state['typescript_repo_structure'] = typescript_structure
    
    # Step 4: Initialize empty TypeScript files (to be filled by the agent)
    callback_context.state['typescript_files'] = {}
    
    print(f"CALLBACK: Successfully gathered context for commit {commit_id}")
    print(f"CALLBACK: Found {len(changed_files_with_content)} changed Python files")
    
    return None

def save_gathered_context(callback_context: CallbackContext) -> Optional[Any]:
    """
    An after-agent callback that collects all context from separate session state items
    and saves it to a JSON file for debugging and inspection.
    """
    # Check if we have the context items in the state
    if 'commit_context' not in callback_context.state:
        print("CALLBACK: No commit_context found in session state. Skipping save.")
        return None
        
    # Collect all context data from separate session state items
    commit_context = callback_context.state.get('commit_context', {})
    
    # Convert changed_files_with_content back to the expected format for compatibility
    python_context_files = {}
    for file_info in commit_context.get('changed_files', []):
        if isinstance(file_info, dict) and 'path' in file_info and 'content' in file_info:
            python_context_files[file_info['path']] = file_info['content']
    
    context_data = {
        'commit_info': {
            'commit_sha': commit_context.get('commit_sha', ''),
            'diff': commit_context.get('diff', ''),
            'changed_files': [f['path'] for f in commit_context.get('changed_files', [])]
        },
        'python_repo_structure': '',  # We don't fetch this anymore, focus on TypeScript
        'typescript_repo_structure': callback_context.state.get('typescript_repo_structure', ''),
        'python_context_files': python_context_files,
        'typescript_context_files': callback_context.state.get('typescript_files', {})
    }
    
    # Use the invocation_id to give each run a unique filename.
    run_id = callback_context.invocation_id
    commit_sha = commit_context.get('commit_sha', 'unknown_commit')
    
    # Construct a descriptive filename
    filename = f"context__{run_id}__{commit_sha}.json"
    
    # Ensure the artifacts directory exists
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    output_path = os.path.join(ARTIFACTS_DIR, filename)
    
    print(f"CALLBACK: Saving gathered context to '{output_path}'...")
    
    # Create a serializable version of the context data
    serializable_context = {
        'commit_info': context_data.get('commit_info', {}),
        'python_repo_structure': context_data.get('python_repo_structure', ''),
        'typescript_repo_structure': context_data.get('typescript_repo_structure', ''),
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
    A before-agent callback that checks if context is in the session state.
    If not, it finds the latest context JSON file and loads it into separate session state items.
    """
    # Only proceed if context is not already in the state
    if 'commit_context' not in callback_context.state:
        print("CALLBACK: Context not found in session state. Attempting to load from file...")
        
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
            
            # Reconstruct commit_context with file contents
            commit_info = context_data.get('commit_info', {})
            python_files = context_data.get('python_context_files', {})
            
            changed_files_with_content = []
            for file_path in commit_info.get('changed_files', []):
                changed_files_with_content.append({
                    'path': file_path,
                    'content': python_files.get(file_path, '')
                })
            
            commit_context = {
                'commit_sha': commit_info.get('commit_sha', ''),
                'diff': commit_info.get('diff', ''),
                'changed_files': changed_files_with_content
            }
            
            # Load data into separate session state items
            callback_context.state['commit_context'] = commit_context
            callback_context.state['typescript_repo_structure'] = context_data.get('typescript_repo_structure', '')
            callback_context.state['typescript_files'] = context_data.get('typescript_context_files', {})
                
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
    This function ensures we always start with a fresh, clean repository state by:
    1. Resetting to main branch and cleaning any uncommitted changes if repo exists
    2. Pulling latest changes from remote
    3. Checking what setup steps have been completed and performing necessary steps
    
    If any step in the setup process fails, it will print an error message and return.
    """
    print("CALLBACK: Setting up TypeScript repository workspace...")
    
    # Create workspace directory if it doesn't exist
    workspace_path = create_workspace_directory()
    typescript_repo_path = workspace_path / TYPESCRIPT_REPO_DIR
    
    # Step 1: Handle repository cloning or reset to fresh state
    if typescript_repo_path.exists() and (typescript_repo_path / ".git").exists():
        print("CALLBACK: Repository already exists. Resetting to fresh state...")
        
        # Reset to clean state (main branch, no uncommitted changes, no untracked files)
        reset_success, reset_message = reset_repo_to_clean_state(typescript_repo_path, target_branch="main")
        if not reset_success:
            print(f"CALLBACK ERROR: Failed to reset repository to clean state: {reset_message}")
            return None
        print(f"CALLBACK: ✓ {reset_message}")
        
        # Pull latest changes from remote
        pull_success, pull_message = pull_latest_changes(typescript_repo_path, remote="origin", branch="main")
        if not pull_success:
            print(f"CALLBACK ERROR: Failed to pull latest changes: {pull_message}")
            return None
        print(f"CALLBACK: ✓ {pull_message}")
        
    else:
        print("CALLBACK: Repository not found. Cloning fresh repository...")
        clone_success, clone_message = clone_repo(TYPESCRIPT_REPO_URL, typescript_repo_path)
        if not clone_success:
            print(f"CALLBACK ERROR: Repository setup failed: {clone_message}")
            return None
        print(f"CALLBACK: ✓ {clone_message}")
    
    # Check the status of remaining setup steps
    setup_status = check_workspace_setup_status(workspace_path)
    
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
    
    print("CALLBACK: TypeScript repository setup completed successfully with fresh state")
    
    # Store the repository path in the session state
    callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
    
    return None

