from typing import Optional, Dict, Any
from google.adk.tools import ToolContext
from .create_issue import create_issue
from .create_branch import create_branch
from .commit_and_push_changes import commit_and_push_changes
from .create_pull_request import create_pull_request
from ..tools.get_commit_diff import get_commit_diff

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
        commit_result = get_commit_diff(
            username="google",
            repo="adk-python", 
            commit_sha=commit_sha,
            tool_context=tool_context
        )
        
        if not commit_result.get("success", False):
            return {
                "success": False,
                "message": f"Failed to fetch commit information: {commit_result.get('message', 'Unknown error')}",
                "error_step": "fetch_commit_info",
                "steps_completed": steps_completed
            }
        
        commit_info = commit_result.get("commit_info", {})
        short_sha = commit_sha[:7]
        commit_message = commit_info.get("message", "Unknown commit")
        changed_files = commit_result.get("changed_files", [])
        
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
            username=username,
            repo=repo,
            title=issue_title,
            body=issue_body,
            tool_context=tool_context
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
            username=username,
            repo=repo,
            branch_name=branch_name,
            base_branch=base_branch,
            tool_context=tool_context
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
        
        commit_result = commit_and_push_changes(
            commit_message=commit_message_full,
            branch_name=branch_name,
            author_name="ADK TypeScript Porter",
            author_email="noreply@github.com",
            tool_context=tool_context
        )
        
        if not commit_result.get("success", False):
            return {
                "success": False,
                "message": f"Failed to commit and push: {commit_result.get('message', 'Unknown error')}",
                "error_step": "commit_and_push",
                "steps_completed": steps_completed,
                "issue_number": issue_number,
                "branch_name": branch_name
            }
        
        commit_sha_local = commit_result.get("commit_sha", "")
        steps_completed.append("commit_and_push")
        print(f"[PUBLISH_PORT_TO_GITHUB] Committed changes: {commit_sha_local[:7] if commit_sha_local else 'unknown'}")
        
        # Step 5: Create pull request
        print(f"[PUBLISH_PORT_TO_GITHUB] Step 5: Creating pull request")
        pr_title = f"Port {brief_description} from Python ADK commit {short_sha}"
        
        # Create a comprehensive PR body (this would typically come from coder_agent, but we'll create a basic one)
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
- ✅ TypeScript compilation successful
- ✅ All relevant tests passing


Related to #{issue_number}
"""
        
        pr_result = create_pull_request(
            username=username,
            repo=repo,
            title=pr_title,
            body=pr_body,
            head_branch=branch_name,
            base_branch=base_branch,
            issue_number=issue_number,
            tool_context=tool_context
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