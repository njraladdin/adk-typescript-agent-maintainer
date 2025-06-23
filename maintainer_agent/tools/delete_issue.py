from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

TOKEN_CACHE_KEY = "github_token"

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
                error_result = {
                    'status': 'error', 
                    'message': 'GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.'
                }
                # Log the error output
                print(f"[DELETE_ISSUE] : output status=error, message={error_result['message']}")
                return error_result

        base_url = f"https://api.github.com/repos/{username}/{repo}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
        # Add a deletion comment with reason
        deletion_comment = f"**[AUTOMATED DELETION]**\n\nThis issue is being closed and deleted due to: {reason}\n\nNo further action is required."
        
        comment_url = f"{base_url}/issues/{issue_number}/comments"
        comment_data = {"body": deletion_comment}
        
        comment_response = requests.post(
            comment_url,
            headers=headers,
            json=comment_data
        )
        comment_response.raise_for_status()
        
        # Close the issue (GitHub doesn't allow true deletion)
        issue_url = f"{base_url}/issues/{issue_number}"
        close_data = {
            "state": "closed"
        }
        
        response = requests.patch(issue_url, headers=headers, json=close_data)
        response.raise_for_status()
        
        success_result = {
            "status": "success",
            "data": response.json(),
            "html_url": response.json().get("html_url"),
            "number": issue_number,
            "reason": reason
        }
        
        # Log the success output
        print(f"[DELETE_ISSUE] : output status=success, issue_number={issue_number}, reason='{reason}', html_url={success_result['html_url']}")
        return success_result
    
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403):
            tool_context.state[TOKEN_CACHE_KEY] = None
            error_result = {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        else:
            print(f"Error deleting issue: {error}")
            error_result = {'status': 'error', 'message': str(error)}
        
        # Log the error output
        print(f"[DELETE_ISSUE] : output status=error, message={error_result['message']}")
        return error_result

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