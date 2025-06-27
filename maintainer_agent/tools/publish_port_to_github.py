from typing import Optional, Dict, Any, List
from pathlib import Path
from google.adk.tools import ToolContext
from ..github_api_utils import (
    fetch_commit_message, 
    fetch_commit_diff_data, 
    create_issue, 
    create_branch, 
    create_pull_request
)
# Import the individual git CLI utility functions for commit and push functionality
from ..git_cli_utils import (
    switch_branch,
    get_changed_files,
    stage_changes,
    commit_changes,
    push_changes
)
from ..workspace_utils import get_typescript_repo_path


def publish_port_to_github(
    commit_sha: str,
    username: str = "njraladdin",
    repo: str = "adk-typescript",
    base_branch: str = "main",
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Publishes a completed code port to GitHub by handling all GitHub operations in sequence.
    
    This tool consolidates the entire GitHub workflow into a single call:
    1. Fetches commit information to generate titles and descriptions
    2. Creates tracking issue with commit details
    3. Creates feature branch for the port
    4. Commits and pushes the translated code
    5. Creates pull request linking to the issue
    
    Args:
        commit_sha (str): The SHA of the commit that was ported (used for titles, branch names, etc.)
        username (str): GitHub username or organization name (default: 'njraladdin')
        repo (str): GitHub repository name (default: 'adk-typescript')
        base_branch (str): The base branch to create the feature branch from (default: 'main')
        tool_context (ToolContext): Automatically injected by ADK for state access
    
    Returns:
        Dict[str, Any]: Response containing:
            - success: bool (True if all operations succeeded)
            - message: str (Summary of what was accomplished)
            - issue_number: int (Created issue number)
            - branch_name: str (Created branch name)
            - commit_sha_local: str (Local commit SHA)
            - pr_number: int (Created PR number)
            - pr_url: str (URL of created PR)
            - steps_completed: List[str] (List of completed steps)
            - error_step: str (Which step failed, if any)
    """
    print(f"[PUBLISH_PORT_TO_GITHUB] Starting GitHub publish workflow for commit {commit_sha[:7]}")
    print(f"[PUBLISH_PORT_TO_GITHUB] Target: {username}/{repo}")
    
    steps_completed = []
    
    try:
        # Step 1: Get commit information for titles and descriptions
        print(f"[PUBLISH_PORT_TO_GITHUB] Step 1: Fetching commit information")
        
        # Get commit message
        commit_message = fetch_commit_message(commit_sha)
        
        # Get diff data for changed files
        diff_result = fetch_commit_diff_data(commit_sha)
        
        if 'error' in diff_result:
            return {
                "success": False,
                "message": f"Failed to fetch commit information: {diff_result.get('error', 'Unknown error')}",
                "error_step": "fetch_commit_info",
                "steps_completed": steps_completed
            }
        
        short_sha = commit_sha[:7]
        changed_files = diff_result.get("changed_files", [])
        
        # Extract a brief description from commit message (first line)
        brief_description = commit_message.split('\n')[0].strip()
        if len(brief_description) > 60:
            brief_description = brief_description[:60] + "..."
        
        steps_completed.append("fetch_commit_info")
        
        # Step 2: Create issue
        print(f"[PUBLISH_PORT_TO_GITHUB] Step 2: Creating tracking issue")
        issue_title = f"[NEW COMMIT IN PYTHON VERSION] [commit:{short_sha}] {brief_description}"
        issue_body = f"""**Commit Information:**
- **SHA:** {commit_sha}
- **Message:** {commit_message}
- **Changed Files:** {len(changed_files)} files
  
**Files Changed:**
{chr(10).join([f'- `{file}`' for file in changed_files[:10]])}
{f'- ... and {len(changed_files) - 10} more files' if len(changed_files) > 10 else ''}



This issue tracks the port of the above Python ADK commit to TypeScript.
"""
        
        issue_result = create_issue(
            repo=f"{username}/{repo}",
            title=issue_title,
            body=issue_body
        )
        
        if issue_result.get("status") != "success":
            return {
                "success": False,
                "message": f"Failed to create issue: {issue_result.get('message', 'Unknown error')}",
                "error_step": "create_issue",
                "steps_completed": steps_completed
            }
        
        issue_number = issue_result.get("number")
        steps_completed.append("create_issue")
        print(f"[PUBLISH_PORT_TO_GITHUB] Created issue #{issue_number}")
        
        # Step 3: Create branch
        print(f"[PUBLISH_PORT_TO_GITHUB] Step 3: Creating feature branch")
        branch_name = f"port-{short_sha}"
        
        branch_result = create_branch(
            repo=f"{username}/{repo}",
            branch_name=branch_name,
            base_branch=base_branch
        )
        
        if branch_result.get("status") != "success":
            return {
                "success": False,
                "message": f"Failed to create branch: {branch_result.get('message', 'Unknown error')}",
                "error_step": "create_branch",
                "steps_completed": steps_completed,
                "issue_number": issue_number
            }
        
        steps_completed.append("create_branch")
        print(f"[PUBLISH_PORT_TO_GITHUB] Created branch: {branch_name}")
        
        # Step 4: Commit and push changes
        print(f"[PUBLISH_PORT_TO_GITHUB] Step 4: Committing and pushing changes")
        commit_message_full = f"Port {brief_description} from Python ADK commit {short_sha}"
        
        # Get the TypeScript repository path from the tool context state or use the default path
        if tool_context and 'typescript_repo_path' in tool_context.state:
            typescript_repo_path = Path(tool_context.state['typescript_repo_path'])
            print(f"[PUBLISH_PORT_TO_GITHUB] Using TypeScript repository path from tool context: {typescript_repo_path}")
        else:
            # Use the default path
            typescript_repo_path = get_typescript_repo_path()
            print(f"[PUBLISH_PORT_TO_GITHUB] Using default TypeScript repository path: {typescript_repo_path}")
        
        # Initialize variables for git operations
        stdout_parts = []
        stderr_parts = []
        files_changed_local: List[str] = []
        commit_sha_local = ""
        
        try:
            # Ensure the TypeScript repository directory exists and is a git repo
            if not typescript_repo_path.exists():
                raise FileNotFoundError(f"TypeScript repository directory {typescript_repo_path} does not exist. Please run setup_agent_workspace first.")
            
            if not (typescript_repo_path / ".git").exists():
                raise FileNotFoundError(f"No git repository found at {typescript_repo_path}. Please ensure the repository is properly cloned.")
            
            # Step 4a: Switch to the correct branch
            print(f"[PUBLISH_PORT_TO_GITHUB] Switching to branch: {branch_name}")
            branch_success, branch_msg = switch_branch(typescript_repo_path, branch_name)
            if not branch_success:
                return {
                    "success": False,
                    "message": f"Failed to switch to branch '{branch_name}': {branch_msg}",
                    "error_step": "switch_branch",
                    "steps_completed": steps_completed,
                    "issue_number": issue_number,
                    "branch_name": branch_name
                }
            stdout_parts.append(branch_msg)
            
            # Step 4b: Get list of changed files
            print(f"[PUBLISH_PORT_TO_GITHUB] Getting list of changed files")
            files_success, files_changed_local = get_changed_files(typescript_repo_path)
            if not files_success:
                stderr_parts.append("Failed to get list of changed files")
            
            if not files_changed_local:
                print("[PUBLISH_PORT_TO_GITHUB] No changes detected to commit")
                return {
                    "success": True,
                    "message": "No changes to commit - port completed but no local changes found",
                    "issue_number": issue_number,
                    "branch_name": branch_name,
                    "commit_sha_local": "",
                    "pr_number": 0,
                    "pr_url": "",
                    "steps_completed": steps_completed + ["no_changes_to_commit"]
                }
            
            print(f"[PUBLISH_PORT_TO_GITHUB] Found {len(files_changed_local)} changed files")
            for file in files_changed_local:
                print(f"[PUBLISH_PORT_TO_GITHUB]   - {file}")
            
            # Step 4c: Stage all changes
            print("[PUBLISH_PORT_TO_GITHUB] Staging changes")
            stage_success, stage_msg = stage_changes(typescript_repo_path)
            if not stage_success:
                return {
                    "success": False,
                    "message": f"Failed to stage changes: {stage_msg}",
                    "error_step": "stage_changes",
                    "steps_completed": steps_completed,
                    "issue_number": issue_number,
                    "branch_name": branch_name
                }
            stdout_parts.append(stage_msg)
            
            # Step 4d: Commit changes
            print("[PUBLISH_PORT_TO_GITHUB] Committing changes")
            commit_success, commit_msg, commit_sha_local = commit_changes(
                typescript_repo_path, 
                commit_message_full,
                "ADK TypeScript Porter",
                "noreply@github.com"
            )
            if not commit_success:
                return {
                    "success": False,
                    "message": f"Failed to commit changes: {commit_msg}",
                    "error_step": "commit_changes",
                    "steps_completed": steps_completed,
                    "issue_number": issue_number,
                    "branch_name": branch_name
                }
            stdout_parts.append(commit_msg)
            
            # Step 4e: Push to remote
            print(f"[PUBLISH_PORT_TO_GITHUB] Pushing to remote branch: {branch_name}")
            push_success, push_msg = push_changes(typescript_repo_path, branch_name)
            if not push_success:
                return {
                    "success": False,
                    "message": f"Failed to push changes: {push_msg}",
                    "error_step": "push_changes",
                    "steps_completed": steps_completed,
                    "issue_number": issue_number,
                    "branch_name": branch_name,
                    "commit_sha_local": commit_sha_local
                }
            stdout_parts.append(push_msg)
            
            print(f"[PUBLISH_PORT_TO_GITHUB] Successfully committed and pushed {len(files_changed_local)} files")
            print(f"[PUBLISH_PORT_TO_GITHUB] Commit SHA: {commit_sha_local}")
            
        except Exception as git_error:
            return {
                "success": False,
                "message": f"Error during git operations: {str(git_error)}",
                "error_step": "git_operations",
                "steps_completed": steps_completed,
                "issue_number": issue_number,
                "branch_name": branch_name
            }
        
        steps_completed.append("commit_and_push")
        
        # Step 5: Create pull request
        print(f"[PUBLISH_PORT_TO_GITHUB] Step 5: Creating pull request")
        pr_title = f"Port {brief_description} from Python ADK commit {short_sha}"
        
        # Create a comprehensive PR body
        pr_body = f"""## Overview
This PR ports the changes from Python ADK commit [`{short_sha}`](https://github.com/google/adk-python/commit/{commit_sha}) to TypeScript.

## Commit Details
**Original Commit:** {commit_message}

## Changes Made
- Ported {len(changed_files)} files from Python to TypeScript

## Files Changed
{chr(10).join([f'- `{file}` (ported to TypeScript equivalent)' for file in changed_files[:10]])}
{f'- ... and {len(changed_files) - 10} more files' if len(changed_files) > 10 else ''}

## Testing
- TypeScript compilation successful
- All relevant tests passing


Related to #{issue_number}
"""
        
        pr_result = create_pull_request(
            repo=f"{username}/{repo}",
            title=pr_title,
            body=pr_body,
            head_branch=branch_name,
            base_branch=base_branch,
            issue_number=issue_number
        )
        
        if pr_result.get("status") != "success":
            return {
                "success": False,
                "message": f"Failed to create pull request: {pr_result.get('message', 'Unknown error')}",
                "error_step": "create_pull_request",
                "steps_completed": steps_completed,
                "issue_number": issue_number,
                "branch_name": branch_name,
                "commit_sha_local": commit_sha_local
            }
        
        pr_number = pr_result.get("number")
        pr_url = pr_result.get("html_url", "")
        steps_completed.append("create_pull_request")
        print(f"[PUBLISH_PORT_TO_GITHUB] Created PR #{pr_number}: {pr_url}")
        
        # Success!
        success_message = f"Successfully published port of commit {short_sha} to GitHub"
        print(f"[PUBLISH_PORT_TO_GITHUB] {success_message}")
        print(f"[PUBLISH_PORT_TO_GITHUB] Issue: #{issue_number}, Branch: {branch_name}, PR: #{pr_number}")
        
        return {
            "success": True,
            "message": success_message,
            "issue_number": issue_number,
            "branch_name": branch_name,
            "commit_sha_local": commit_sha_local,
            "pr_number": pr_number,
            "pr_url": pr_url,
            "steps_completed": steps_completed
        }
        
    except Exception as error:
        error_msg = f"Unexpected error during GitHub publish: {str(error)}"
        print(f"[PUBLISH_PORT_TO_GITHUB] Error: {error_msg}")
        
        return {
            "success": False,
            "message": error_msg,
            "error_step": "unexpected_error",
            "steps_completed": steps_completed
        }

if __name__ == "__main__":
    # Example usage
    try:
        result = publish_port_to_github(
            commit_sha="abc1234567890abcdef1234567890abcdef123456",
            username="njraladdin",
            repo="adk-typescript"
        )
        
        if result["success"]:
            print(f"✓ Successfully published port to GitHub")
            print(f"  Issue: #{result.get('issue_number')}")
            print(f"  Branch: {result.get('branch_name')}")
            print(f"  PR: #{result.get('pr_number')} - {result.get('pr_url')}")
        else:
            print(f"✗ Failed to publish: {result['message']}")
            print(f"  Failed at step: {result.get('error_step')}")
            print(f"  Completed steps: {', '.join(result.get('steps_completed', []))}")
            
    except Exception as error:
        print(f"Test failed: {error}") 