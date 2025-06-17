from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

TOKEN_CACHE_KEY = "github_token"

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
    try:
        # Step 1: Check for cached token
        github_token = tool_context.state.get(TOKEN_CACHE_KEY)
        
        # If no token, we need to get it from environment or request it
        if not github_token:
            # For now, let's try to get it from environment as a fallback
            import os
            github_token = os.getenv("GITHUB_TOKEN")
            
            if github_token:
                # Cache the token for future use
                tool_context.state[TOKEN_CACHE_KEY] = github_token
            else:
                return {
                    'status': 'error', 
                    'message': 'GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.'
                }

        base_url = f"https://api.github.com/repos/{username}/{repo}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
        # Add a comment if provided
        if comment:
            comment_url = f"{base_url}/issues/{issue_number}/comments"
            comment_data = {"body": comment}
            
            comment_response = requests.post(
                comment_url,
                headers=headers,
                json=comment_data
            )
            comment_response.raise_for_status()
        
        # Close the issue
        issue_url = f"{base_url}/issues/{issue_number}"
        close_data = {
            "state": "closed"
        }
        
        response = requests.patch(issue_url, headers=headers, json=close_data)
        response.raise_for_status()
        
        return {
            "status": "success",
            "data": response.json(),
            "html_url": response.json().get("html_url"),
            "number": issue_number
        }
    
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403):
            tool_context.state[TOKEN_CACHE_KEY] = None
            return {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        print(f"Error closing issue: {error}")
        return {'status': 'error', 'message': str(error)}

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