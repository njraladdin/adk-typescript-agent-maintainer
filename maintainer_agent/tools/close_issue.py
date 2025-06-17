from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException

def close_issue(
    username: str,
    repo: str,
    issue_number: int,
    comment: Optional[str] = None,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Closes a GitHub issue and optionally adds a closing comment.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        issue_number (int): The issue number to close
        comment (Optional[str]): Optional comment to add before closing
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Dict[str, Any]: The updated issue data from GitHub API

    Raises:
        RequestException: If there's an error closing the issue
    """
    try:
        base_url = f"https://api.github.com/repos/{username}/{repo}"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
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
        
        return response.json()
    
    except RequestException as error:
        print(f"Error closing issue: {error}")
        raise

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
            test_comment,
            github_token
        )
        print(f"Closed issue #{test_issue_number}")
    except Exception as error:
        print(f"Test failed: {error}") 