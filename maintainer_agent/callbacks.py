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
    1. Resetting to main branch and cleaning any uncommitted changes if repo exists
    2. Pulling latest changes from remote
    3. Checking what setup steps have been completed and performing necessary steps
    
    Note: Commit context gathering is now handled by the gather_commit_context tool.
    
    If any step in the setup process fails, it will print an error message and return.
    """
    print("[setup_agent_workspace]: Setting up TypeScript repository workspace")
    
    try:
        # Create workspace directory if it doesn't exist
        workspace_path = create_workspace_directory()
        typescript_repo_path = workspace_path / TYPESCRIPT_REPO_DIR
        
        # Step 1: Handle repository cloning or reset to fresh state
        if typescript_repo_path.exists() and (typescript_repo_path / ".git").exists():
            # Reset to clean state (main branch, no uncommitted changes, no untracked files)
            reset_success, reset_message = reset_repo_to_clean_state(typescript_repo_path, target_branch="main")
            if not reset_success:
                print(f"[setup_agent_workspace] ERROR: Failed to reset repository to clean state: {reset_message}")
                return None
            
            # Pull latest changes from remote
            pull_success, pull_message = pull_latest_changes(typescript_repo_path, remote="origin", branch="main")
            if not pull_success:
                print(f"[setup_agent_workspace] ERROR: Failed to pull latest changes: {pull_message}")
                return None
            
        else:
            clone_success, clone_message = clone_repo(TYPESCRIPT_REPO_URL, typescript_repo_path)
            if not clone_success:
                print(f"[setup_agent_workspace] ERROR: Repository setup failed: {clone_message}")
                return None
        
        # Check the status of remaining setup steps
        setup_status = check_workspace_setup_status(workspace_path)
        
        # Step 2: Install dependencies if not already installed
        if not setup_status["dependencies_installed"]:
            install_success, install_message = install_dependencies(typescript_repo_path)
            if not install_success:
                print(f"[setup_agent_workspace] ERROR: Dependency installation failed: {install_message}")
                callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
                return None
        
        # Step 3: Build the project if not already built
        if not setup_status["project_built"]:
            build_result = build_project(typescript_repo_path)
            if not build_result["success"]:
                print(f"[setup_agent_workspace] ERROR: Project build failed: {build_result['message']}")
                callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
                return None
        
        # Step 4: Setup repository environment if not already set up
        if not setup_status["env_setup"]:
            env_success, env_message = setup_typescript_repository_environment(typescript_repo_path)
            if not env_success:
                print(f"[setup_agent_workspace] ERROR: Environment setup failed: {env_message}")
                callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
                return None
        
        # Store the repository path in the session state
        callback_context.state['typescript_repo_path'] = str(typescript_repo_path.absolute())
        
        print("[setup_agent_workspace]: TypeScript repository setup completed successfully")
        return None
        
    except Exception as e:
        print(f"[setup_agent_workspace] ERROR: Unexpected error during setup: {str(e)}")
        return None

