from typing import Optional, Dict, Any
from google.adk.tools import ToolContext
from ..git_api_utils import create_issue as api_create_issue

def create_issue(
    username: str,
    repo: str,
    title: str,
    body: str,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Creates a new issue in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        title (str): Issue title
        body (str): Issue body/description
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The created issue data from GitHub API
    """
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_ISSUE] username={username} repo={repo} title='{title[:50]}{'...' if len(title) > 50 else ''}'")
    
    # Use the centralized API utility
    repo_full = f"{username}/{repo}"
    result = api_create_issue(repo_full, title, body)
    
    # Log the output
    if result.get('status') == 'success':
        print(f"[CREATE_ISSUE] : output status=success, issue_number={result['number']}, html_url={result['html_url']}")
    else:
        print(f"[CREATE_ISSUE] : output status=error, message={result.get('message', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_title = "Test Issue"
        test_body = "This is a test issue created via the API"
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        issue = create_issue(
            test_username,
            test_repo,
            test_title,
            test_body,
            github_token
        )
        print("Created issue:", issue["html_url"])
    except Exception as error:
        print(f"Test failed: {error}") 