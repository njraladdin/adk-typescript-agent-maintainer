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
from .git_cli_utils import reset_repo_to_clean_state, pull_latest_changes
from .github_api_utils import fetch_commit_diff_data, fetch_repo_structure, fetch_file_content

def setup_agent_workspace(callback_context: CallbackContext) -> Optional[Any]:
    """
    A before-agent callback that sets up the agent workspace with the TypeScript repository.
    This function ensures we always start with a fresh, clean repository state by:
    1. Checking if workspace setup has already been completed in this session
    2. Resetting to main branch and cleaning any uncommitted changes if repo exists
    3. Pulling latest changes from remote
    4. Checking what setup steps have been completed and performing necessary steps
    5. Storing setup completion status in callback context state
    
    Note: Commit context gathering is now handled by the gather_commit_context tool.
    
    If any step in the setup process fails, it will print an error message and return.
    """
    print("[setup_agent_workspace]: Setting up TypeScript repository workspace")
    
    # Check if workspace setup has already been completed in this session
    if callback_context.state.get('workspace_setup_completed', False):
        print("[setup_agent_workspace]: Workspace already set up in this session, skipping setup")
        typescript_repo_path = callback_context.state.get('typescript_repo_path')
        if typescript_repo_path and Path(typescript_repo_path).exists():
            print(f"[setup_agent_workspace]: Using existing repository at {typescript_repo_path}")
            return None
        else:
            print("[setup_agent_workspace]: Stored path invalid, proceeding with fresh setup")
            # Clear the invalid state
            callback_context.state['workspace_setup_completed'] = False
    
    try:
        # Create workspace directory if it doesn't exist
        workspace_path = create_workspace_directory()
        typescript_repo_path = workspace_path / TYPESCRIPT_REPO_DIR
        
        # Step 1: Handle repository cloning or reset to fresh state
        if typescript_repo_path.exists() and (typescript_repo_path / ".git").exists():
            print("[setup_agent_workspace]: Repository exists, resetting to clean state...")
            # Reset to clean state (main branch, no uncommitted changes, no untracked files)
            reset_success, reset_message = reset_repo_to_clean_state(typescript_repo_path, target_branch="main")
            if not reset_success:
                print(f"[setup_agent_workspace] ERROR: Failed to reset repository to clean state: {reset_message}")
                return None
            print(f"[setup_agent_workspace]: {reset_message}")
            
            # Pull latest changes from remote
            print("[setup_agent_workspace]: Pulling latest changes from remote...")
            pull_success, pull_message = pull_latest_changes(typescript_repo_path, remote="origin", branch="main")
            if not pull_success:
                print(f"[setup_agent_workspace] ERROR: Failed to pull latest changes: {pull_message}")
                return None
            print(f"[setup_agent_workspace]: {pull_message}")
            
        else:
            print("[setup_agent_workspace]: Repository not found, cloning fresh copy...")
            clone_success, clone_message = clone_repo(TYPESCRIPT_REPO_URL, typescript_repo_path)
            if not clone_success:
                print(f"[setup_agent_workspace] ERROR: Repository setup failed: {clone_message}")
                return None
            print(f"[setup_agent_workspace]: {clone_message}")
        
        # Check the status of remaining setup steps
        print("[setup_agent_workspace]: Checking workspace setup status...")
        setup_status = check_workspace_setup_status(workspace_path)
        
        # Step 2: Install dependencies if not already installed
        if not setup_status["dependencies_installed"]:
            print("[setup_agent_workspace]: Installing dependencies...")
            install_success, install_message = install_dependencies(typescript_repo_path)
            if not install_success:
                print(f"[setup_agent_workspace] ERROR: Dependency installation failed: {install_message}")
                # Store partial setup state
                callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
                callback_context.state['workspace_setup_completed'] = False
                return None
            print(f"[setup_agent_workspace]: {install_message}")
        else:
            print("[setup_agent_workspace]: Dependencies already installed, skipping...")
        
        # Step 3: Build the project if not already built
        if not setup_status["project_built"]:
            print("[setup_agent_workspace]: Building project...")
            build_result = build_project(typescript_repo_path)
            if not build_result["success"]:
                print(f"[setup_agent_workspace] ERROR: Project build failed: {build_result['message']}")
                # Store partial setup state
                callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
                callback_context.state['workspace_setup_completed'] = False
                return None
            print(f"[setup_agent_workspace]: {build_result['message']}")
        else:
            print("[setup_agent_workspace]: Project already built, skipping...")
        
        # Step 4: Setup repository environment if not already set up
        if not setup_status["env_setup"]:
            print("[setup_agent_workspace]: Setting up repository environment...")
            env_success, env_message = setup_typescript_repository_environment(typescript_repo_path)
            if not env_success:
                print(f"[setup_agent_workspace] ERROR: Environment setup failed: {env_message}")
                # Store partial setup state
                callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
                callback_context.state['workspace_setup_completed'] = False
                return None
            print(f"[setup_agent_workspace]: {env_message}")
        else:
            print("[setup_agent_workspace]: Environment already set up, skipping...")
        
        # Store the repository path and completion status in the session state
        callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
        callback_context.state['workspace_setup_completed'] = True
        
        print("[setup_agent_workspace]: TypeScript repository setup completed successfully")
        print(f"[setup_agent_workspace]: Repository path: {typescript_repo_path.absolute()}")
        return None
        
    except Exception as e:
        print(f"[setup_agent_workspace] ERROR: Unexpected error during setup: {str(e)}")
        # Ensure we don't mark setup as completed on error
        callback_context.state['workspace_setup_completed'] = False
        return None

