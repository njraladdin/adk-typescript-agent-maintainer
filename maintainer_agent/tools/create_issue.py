from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

TOKEN_CACHE_KEY = "github_token"

def create_issue(
    username: str,
    repo: str,
    title: str,
    body: str,
    labels: Optional[list[str]] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Creates a new issue in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        title (str): Issue title
        body (str): Issue body/description
        labels (Optional[list[str]]): List of labels to apply to the issue
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The created issue data from GitHub API
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

        # Step 2: Make authenticated API call
        url = f"https://api.github.com/repos/{username}/{repo}/issues"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        # Step 3: Return success response
        result = response.json()
        return {
            "status": "success",
            "data": result,
            "html_url": result.get("html_url"),
            "number": result.get("number")
        }
    
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403):
            tool_context.state[TOKEN_CACHE_KEY] = None
            return {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        print(f"Error creating issue: {error}")
        return {'status': 'error', 'message': str(error)}

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_title = "Test Issue"
        test_body = "This is a test issue created via the API"
        test_labels = ["test", "automated"]
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        issue = create_issue(
            test_username,
            test_repo,
            test_title,
            test_body,
            test_labels,
            github_token
        )
        print("Created issue:", issue["html_url"])
    except Exception as error:
        print(f"Test failed: {error}") 