from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException

def create_branch(
    username: str,
    repo: str,
    branch_name: str,
    base_branch: str = "main",
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new branch in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        branch_name (str): Name of the new branch to create
        base_branch (str): Name of the branch to base the new branch on (default: 'main')
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Dict[str, Any]: The created reference data from GitHub API

    Raises:
        RequestException: If there's an error creating the branch
    """
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_BRANCH] username={username} repo={repo} branch_name={branch_name} base_branch={base_branch}")
    
    try:
        # First, get the SHA of the base branch
        base_url = f"https://api.github.com/repos/{username}/{repo}"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # Get the SHA of the base branch
        base_ref_url = f"{base_url}/git/ref/heads/{base_branch}"
        base_response = requests.get(base_ref_url, headers=headers)
        base_response.raise_for_status()
        base_sha = base_response.json()["object"]["sha"]
        
        # Create the new branch
        refs_url = f"{base_url}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }
        
        response = requests.post(refs_url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        # Log the success output
        print(f"[CREATE_BRANCH] : output status=success, created branch={branch_name} from base_sha={base_sha[:7]}")
        return result
    
    except RequestException as error:
        # Log the error output
        print(f"[CREATE_BRANCH] : output status=error, message={str(error)}")
        print(f"Error creating branch: {error}")
        raise

def branch_exists(
    username: str,
    repo: str,
    branch_name: str,
    github_token: Optional[str] = None
) -> bool:
    """
    Checks if a branch exists in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        branch_name (str): Name of the branch to check
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        bool: True if the branch exists, False otherwise
    """
    # Log the start of the tool execution with main parameters
    print(f"[BRANCH_EXISTS] username={username} repo={repo} branch_name={branch_name}")
    
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/git/ref/heads/{branch_name}"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        response = requests.get(url, headers=headers)
        exists = response.status_code == 200
        
        # Log the output
        print(f"[BRANCH_EXISTS] : output exists={exists}")
        return exists
    
    except RequestException as error:
        # Log the error output
        print(f"[BRANCH_EXISTS] : output status=error, message={str(error)}")
        return False

def create_branch_if_not_exists(
    username: str,
    repo: str,
    branch_name: str,
    base_branch: str = "main",
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a new branch if it doesn't already exist.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        branch_name (str): Name of the branch to create
        base_branch (str): Name of the branch to base the new branch on (default: 'main')
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Dict[str, Any]: The branch reference data from GitHub API

    Raises:
        RequestException: If there's an error checking or creating the branch
    """
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_BRANCH_IF_NOT_EXISTS] username={username} repo={repo} branch_name={branch_name} base_branch={base_branch}")
    
    if not branch_exists(username, repo, branch_name, github_token):
        result = create_branch(username, repo, branch_name, base_branch, github_token)
        # Log the success output
        print(f"[CREATE_BRANCH_IF_NOT_EXISTS] : output status=success, created new branch={branch_name}")
        return result
    else:
        error_msg = f"Branch '{branch_name}' already exists"
        # Log the error output
        print(f"[CREATE_BRANCH_IF_NOT_EXISTS] : output status=error, message={error_msg}")
        raise ValueError(error_msg)

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_branch = "feature/test-branch"
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        result = create_branch_if_not_exists(
            test_username,
            test_repo,
            test_branch,
            "main",
            github_token
        )
        print(f"Created branch: {test_branch}")
    except Exception as error:
        print(f"Test failed: {error}") 