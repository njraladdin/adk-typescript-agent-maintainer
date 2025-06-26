from typing import Optional, Dict, Any
from google.adk.tools import ToolContext
from ..github_api_utils import delete_issue as api_delete_issue

def delete_issue(
    username: str,
    repo: str,
    issue_number: int,
    reason: str,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Deletes a GitHub issue by adding a comment explaining the reason and then closing it.
    GitHub doesn't allow true deletion of issues for audit reasons, so we close with explanation.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        issue_number (int): The issue number to delete
        reason (str): Reason for deletion (e.g., "Coder agent failed after 5 retries")
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The updated issue data from GitHub API
    """
    # Log the start of the tool execution with main parameters
    print(f"[DELETE_ISSUE] username={username} repo={repo} issue_number={issue_number} reason='{reason[:50]}{'...' if len(reason) > 50 else ''}'")
    
    # Use the centralized API utility
    repo_full = f"{username}/{repo}"
    result = api_delete_issue(repo_full, issue_number, reason)
    
    # Add the reason to the result for backward compatibility
    if result.get('status') == 'success':
        result['reason'] = reason
        print(f"[DELETE_ISSUE] : output status=success, issue_number={issue_number}, reason='{reason}', html_url={result['html_url']}")
    else:
        print(f"[DELETE_ISSUE] : output status=error, message={result.get('message', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_issue_number = 1
        test_reason = "Coder agent failed after 5 retries - unable to port commit"
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        result = delete_issue(
            test_username,
            test_repo,
            test_issue_number,
            test_reason
        )
        print(f"Deleted issue #{test_issue_number}")
    except Exception as error:
        print(f"Test failed: {error}") 