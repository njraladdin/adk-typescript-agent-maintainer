from typing import Optional, Dict, Any, List
from pathlib import Path
from google.adk.tools import ToolContext

# Import the individual git CLI utility functions
from ..git_cli_utils import (
    switch_branch,
    get_changed_files,
    stage_changes,
    commit_changes,
    push_changes
)
from ..workspace_utils import get_typescript_repo_path
from ..constants import AGENT_WORKSPACE_DIR, TYPESCRIPT_REPO_DIR

def commit_and_push_changes(
    commit_message: str,
    branch_name: str,
    author_name: Optional[str] = None,
    author_email: Optional[str] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Commits all local changes made by the coder agent and pushes them to the specified branch.
    
    This tool should be called after all file translations are complete and the build/tests pass.
    It will stage all modified files, commit them with the provided message, and push to the branch.
    
    Args:
        commit_message (str): The commit message describing the changes made
        branch_name (str): The name of the branch to push changes to
        author_name (Optional[str]): Git author name (optional, uses git config if not provided)
        author_email (Optional[str]): Git author email (optional, uses git config if not provided)
        tool_context (ToolContext): Automatically injected by ADK for state access
    
    Returns:
        Dict[str, Any]: Response containing:
            - success: bool (True if commit and push succeeded)
            - message: str (Success/error message)
            - commit_sha: str (SHA of the created commit, empty if failed)
            - files_changed: List[str] (List of files that were committed)
            - stdout: str (Git command output)
            - stderr: str (Git command errors, if any)
    """
    # Log the start of the tool execution with main parameters
    print(f"[COMMIT_AND_PUSH_CHANGES] commit_message={commit_message[:50]}{'...' if len(commit_message) > 50 else ''}")
    print(f"[COMMIT_AND_PUSH_CHANGES] branch_name={branch_name}")
    
    stdout_parts = []
    stderr_parts = []
    files_changed: List[str] = []
    
    try:
        # Get the TypeScript repository path from the tool context state or use the default path
        if tool_context and 'typescript_repo_path' in tool_context.state:
            typescript_repo_path = Path(tool_context.state['typescript_repo_path'])
            print(f"[COMMIT_AND_PUSH_CHANGES] Using TypeScript repository path from tool context: {typescript_repo_path}")
        else:
            # Use the default path
            typescript_repo_path = get_typescript_repo_path()
            print(f"[COMMIT_AND_PUSH_CHANGES] Using default TypeScript repository path: {typescript_repo_path}")
        
        # Ensure the TypeScript repository directory exists and is a git repo
        if not typescript_repo_path.exists():
            raise FileNotFoundError(f"TypeScript repository directory {typescript_repo_path} does not exist. Please run setup_agent_workspace first.")
        
        if not (typescript_repo_path / ".git").exists():
            raise FileNotFoundError(f"No git repository found at {typescript_repo_path}. Please ensure the repository is properly cloned.")
        
        # Step 1: Switch to the correct branch
        print(f"[COMMIT_AND_PUSH_CHANGES] Switching to branch: {branch_name}")
        branch_success, branch_msg = switch_branch(typescript_repo_path, branch_name)
        if not branch_success:
            error_msg = f"Failed to switch to branch '{branch_name}': {branch_msg}"
            print(f"[COMMIT_AND_PUSH_CHANGES] Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "commit_sha": "",
                "files_changed": [],
                "stdout": "",
                "stderr": branch_msg
            }
        stdout_parts.append(branch_msg)
        
        # Step 2: Get list of changed files
        print(f"[COMMIT_AND_PUSH_CHANGES] Getting list of changed files")
        files_success, files_changed = get_changed_files(typescript_repo_path)
        if not files_success:
            stderr_parts.append("Failed to get list of changed files")
        
        if not files_changed:
            print("[COMMIT_AND_PUSH_CHANGES] No changes detected to commit")
            return {
                "success": True,
                "message": "No changes to commit",
                "commit_sha": "",
                "files_changed": [],
                "stdout": "No changes detected",
                "stderr": ""
            }
        
        print(f"[COMMIT_AND_PUSH_CHANGES] Found {len(files_changed)} changed files")
        for file in files_changed:
            print(f"[COMMIT_AND_PUSH_CHANGES]   - {file}")
        
        # Step 3: Stage all changes
        print("[COMMIT_AND_PUSH_CHANGES] Staging changes")
        stage_success, stage_msg = stage_changes(typescript_repo_path)
        if not stage_success:
            error_msg = f"Failed to stage changes: {stage_msg}"
            print(f"[COMMIT_AND_PUSH_CHANGES] Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "commit_sha": "",
                "files_changed": files_changed,
                "stdout": "\n".join(stdout_parts),
                "stderr": stage_msg
            }
        stdout_parts.append(stage_msg)
        
        # Step 4: Commit changes
        print("[COMMIT_AND_PUSH_CHANGES] Committing changes")
        commit_success, commit_msg, commit_sha = commit_changes(
            typescript_repo_path, 
            commit_message,
            author_name,
            author_email
        )
        if not commit_success:
            error_msg = f"Failed to commit changes: {commit_msg}"
            print(f"[COMMIT_AND_PUSH_CHANGES] Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "commit_sha": "",
                "files_changed": files_changed,
                "stdout": "\n".join(stdout_parts),
                "stderr": commit_msg
            }
        stdout_parts.append(commit_msg)
        
        # Step 5: Push to remote
        print(f"[COMMIT_AND_PUSH_CHANGES] Pushing to remote branch: {branch_name}")
        push_success, push_msg = push_changes(typescript_repo_path, branch_name)
        if not push_success:
            error_msg = f"Failed to push changes: {push_msg}"
            print(f"[COMMIT_AND_PUSH_CHANGES] Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "commit_sha": commit_sha,
                "files_changed": files_changed,
                "stdout": "\n".join(stdout_parts),
                "stderr": push_msg
            }
        stdout_parts.append(push_msg)
        
        # Success!
        success_message = f"Successfully committed and pushed {len(files_changed)} files to branch '{branch_name}'"
        print(f"[COMMIT_AND_PUSH_CHANGES] {success_message}")
        print(f"[COMMIT_AND_PUSH_CHANGES] Commit SHA: {commit_sha}")
        
        return {
            "success": True,
            "message": success_message,
            "commit_sha": commit_sha,
            "files_changed": files_changed,
            "stdout": "\n".join(stdout_parts),
            "stderr": "\n".join(stderr_parts)
        }
        
    except Exception as error:
        error_msg = f"Error during commit and push: {str(error)}"
        print(f"[COMMIT_AND_PUSH_CHANGES] Error: {error_msg}")
        
        error_result = {
            "success": False,
            "message": error_msg,
            "commit_sha": "",
            "files_changed": files_changed,
            "stdout": "\n".join(stdout_parts) if stdout_parts else "",
            "stderr": str(error)
        }
        
        return error_result

if __name__ == "__main__":
    # Example usage
    try:
        result = commit_and_push_changes(
            commit_message="Port feature from Python ADK commit abc1234",
            branch_name="port-abc1234",
            author_name="ADK TypeScript Agent",
            author_email="noreply@example.com"
        )
        
        if result["success"]:
            print(f"✓ Successfully committed and pushed changes")
            print(f"  Commit SHA: {result['commit_sha']}")
            print(f"  Files changed: {len(result['files_changed'])}")
            for file in result['files_changed']:
                print(f"    - {file}")
        else:
            print(f"✗ Failed to commit and push: {result['message']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 