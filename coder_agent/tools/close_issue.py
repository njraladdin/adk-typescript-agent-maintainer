from typing import Optional, Dict, Any
from google.adk.tools import ToolContext
from ..git_api_utils import close_issue as api_close_issue

def close_issue(
    username: str,
    repo: str,
    issue_number: int,
    comment: Optional[str] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Closes a GitHub issue and optionally adds a closing comment.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        issue_number (int): The issue number to close
        comment (Optional[str]): Optional comment to add before closing
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The updated issue data from GitHub API
    """
    # Log the start of the tool execution with main parameters
    print(f"[CLOSE_ISSUE] username={username} repo={repo} issue_number={issue_number} has_comment={comment is not None}")
    
    # Use the centralized API utility
    repo_full = f"{username}/{repo}"
    result = api_close_issue(repo_full, issue_number, comment)
    
    # Log the output
    if result.get('status') == 'success':
        print(f"[CLOSE_ISSUE] : output status=success, issue_number={issue_number}, html_url={result['html_url']}")
    else:
        print(f"[CLOSE_ISSUE] : output status=error, message={result.get('message', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_issue_number = 1
        test_comment = "Closing this issue as it is no longer relevant."
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        result = close_issue(
            test_username,
            test_repo,
            test_issue_number,
            test_comment
        )
        print(f"Closed issue #{test_issue_number}")
    except Exception as error:
        print(f"Test failed: {error}") 