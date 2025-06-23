from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

TOKEN_CACHE_KEY = "github_token"

def create_branch(
    username: str,
    repo: str,
    branch_name: str,
    base_branch: str = "main",
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Creates a new branch in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        branch_name (str): Name of the new branch to create
        base_branch (str): Name of the branch to base the new branch on (default: 'main')
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The created reference data from GitHub API

    Raises:
        RequestException: If there's an error creating the branch
    """
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_BRANCH] username={username} repo={repo} branch_name={branch_name} base_branch={base_branch}")
    
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
                print(f"[CREATE_BRANCH] : output status=error, message={error_result['message']}")
                return error_result

        # First, get the SHA of the base branch
        base_url = f"https://api.github.com/repos/{username}/{repo}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
        # Get the SHA of the base branch
        base_ref_url = f"{base_url}/git/refs/heads/{base_branch}"
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
        success_result = {
            "status": "success",
            "data": result,
            "branch_name": branch_name,
            "base_sha": base_sha
        }
        
        # Log the success output
        print(f"[CREATE_BRANCH] : output status=success, created branch={branch_name} from base_sha={base_sha[:7]}")
        return success_result
    
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403):
            tool_context.state[TOKEN_CACHE_KEY] = None
            error_result = {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        else:
            print(f"Error creating branch: {error}")
            error_result = {'status': 'error', 'message': str(error)}
        
        # Log the error output
        print(f"[CREATE_BRANCH] : output status=error, message={error_result['message']}")
        return error_result

def branch_exists(
    username: str,
    repo: str,
    branch_name: str,
    tool_context: ToolContext = None
) -> bool:
    """
    Checks if a branch exists in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        branch_name (str): Name of the branch to check
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        bool: True if the branch exists, False otherwise
    """
    # Log the start of the tool execution with main parameters
    print(f"[BRANCH_EXISTS] username={username} repo={repo} branch_name={branch_name}")
    
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
                # Log the error output
                print(f"[BRANCH_EXISTS] : output status=error, message=GitHub token not found")
                return False

        url = f"https://api.github.com/repos/{username}/{repo}/git/refs/heads/{branch_name}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
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
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Creates a new branch if it doesn't already exist.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        branch_name (str): Name of the branch to create
        base_branch (str): Name of the branch to base the new branch on (default: 'main')
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The branch reference data from GitHub API

    Raises:
        RequestException: If there's an error checking or creating the branch
    """
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_BRANCH_IF_NOT_EXISTS] username={username} repo={repo} branch_name={branch_name} base_branch={base_branch}")
    
    if not branch_exists(username, repo, branch_name, tool_context):
        result = create_branch(username, repo, branch_name, base_branch, tool_context)
        # Log the success output
        print(f"[CREATE_BRANCH_IF_NOT_EXISTS] : output status=success, created new branch={branch_name}")
        return result
    else:
        error_msg = f"Branch '{branch_name}' already exists"
        # Log the error output
        print(f"[CREATE_BRANCH_IF_NOT_EXISTS] : output status=error, message={error_msg}")
        return {'status': 'error', 'message': error_msg}

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_branch = "feature/test-branch"
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        # In real usage, tool_context would be provided by ADK
        class MockToolContext:
            def __init__(self):
                self.state = {}
        
        mock_context = MockToolContext()
        
        result = create_branch_if_not_exists(
            test_username,
            test_repo,
            test_branch,
            "main",
            mock_context
        )
        print(f"Created branch: {test_branch}")
    except Exception as error:
        print(f"Test failed: {error}") 