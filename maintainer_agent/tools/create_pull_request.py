from typing import Optional, Dict, Any, List
import requests
from requests.exceptions import RequestException

def create_pull_request(
    username: str,
    repo: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
    labels: Optional[List[str]] = None,
    draft: bool = False,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new pull request in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        title (str): Pull request title
        body (str): Pull request description
        head_branch (str): The name of the branch where your changes are implemented
        base_branch (str): The name of the branch you want the changes pulled into (default: 'main')
        labels (Optional[List[str]]): List of labels to apply to the pull request
        draft (bool): Whether to create the pull request as a draft (default: False)
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Dict[str, Any]: The created pull request data from GitHub API

    Raises:
        RequestException: If there's an error creating the pull request
    """
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/pulls"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft
        }
        
        # Create the pull request
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        pr_data = response.json()
        
        # Add labels if provided
        if labels and len(labels) > 0:
            labels_url = f"https://api.github.com/repos/{username}/{repo}/issues/{pr_data['number']}/labels"
            labels_response = requests.post(labels_url, headers=headers, json=labels)
            labels_response.raise_for_status()
        
        # Get the updated PR data
        pr_url = pr_data["url"]
        updated_response = requests.get(pr_url, headers=headers)
        updated_response.raise_for_status()
        
        return updated_response.json()
    
    except RequestException as error:
        print(f"Error creating pull request: {error}")
        raise

def pull_request_exists(
    username: str,
    repo: str,
    head_branch: str,
    base_branch: str = "main",
    github_token: Optional[str] = None
) -> bool:
    """
    Checks if a pull request already exists for the given branches.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        head_branch (str): The name of the branch where your changes are implemented
        base_branch (str): The name of the branch you want the changes pulled into
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        bool: True if a pull request exists, False otherwise
    """
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/pulls"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        params = {
            "head": f"{username}:{head_branch}",
            "base": base_branch,
            "state": "open"
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return len(response.json()) > 0
    
    except RequestException:
        return False

def create_pull_request_if_not_exists(
    username: str,
    repo: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
    labels: Optional[List[str]] = None,
    draft: bool = False,
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new pull request if one doesn't already exist for the given branches.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        title (str): Pull request title
        body (str): Pull request description
        head_branch (str): The name of the branch where your changes are implemented
        base_branch (str): The name of the branch you want the changes pulled into (default: 'main')
        labels (Optional[List[str]]): List of labels to apply to the pull request
        draft (bool): Whether to create the pull request as a draft (default: False)
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Dict[str, Any]: The created pull request data from GitHub API

    Raises:
        ValueError: If a pull request already exists
        RequestException: If there's an error checking or creating the pull request
    """
    if not pull_request_exists(username, repo, head_branch, base_branch, github_token):
        return create_pull_request(
            username,
            repo,
            title,
            body,
            head_branch,
            base_branch,
            labels,
            draft,
            github_token
        )
    else:
        raise ValueError(f"Pull request already exists for {head_branch} into {base_branch}")

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_title = "Test Pull Request"
        test_body = "This is a test pull request created via the API"
        test_head_branch = "feature/test-branch"
        test_labels = ["test", "automated"]
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        result = create_pull_request_if_not_exists(
            test_username,
            test_repo,
            test_title,
            test_body,
            test_head_branch,
            "main",
            test_labels,
            False,
            github_token
        )
        print("Created pull request:", result["html_url"])
    except Exception as error:
        print(f"Test failed: {error}") 