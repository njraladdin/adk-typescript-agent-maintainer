from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException

def create_issue(
    username: str,
    repo: str,
    title: str,
    body: str,
    labels: Optional[list[str]] = None,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new issue in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        title (str): Issue title
        body (str): Issue body/description
        labels (Optional[list[str]]): List of labels to apply to the issue
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Dict[str, Any]: The created issue data from GitHub API

    Raises:
        RequestException: If there's an error creating the issue
    """
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/issues"
        
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    except RequestException as error:
        print(f"Error creating issue: {error}")
        raise

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