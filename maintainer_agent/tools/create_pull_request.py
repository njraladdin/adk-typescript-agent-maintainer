from typing import Optional, Dict, Any, List
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

TOKEN_CACHE_KEY = "github_token"

def create_pull_request(
    username: str,
    repo: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
    issue_number: Optional[int] = None,
    labels: Optional[List[str]] = None,
    draft: bool = False,
    tool_context: ToolContext = None
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
        issue_number (Optional[int]): Issue number to automatically link and close when PR is merged
        labels (Optional[List[str]]): List of labels to apply to the pull request
        draft (bool): Whether to create the pull request as a draft (default: False)
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The created pull request data from GitHub API

    Raises:
        RequestException: If there's an error creating the pull request
    """
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_PULL_REQUEST] username={username} repo={repo} title='{title[:50]}{'...' if len(title) > 50 else ''}' head_branch={head_branch} base_branch={base_branch} issue={issue_number} draft={draft}")
    
    # Add issue linking to body if issue_number is provided
    if issue_number:
        body = f"{body}\n\nRelated to #{issue_number}"
    
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
                print(f"[CREATE_PULL_REQUEST] : output status=error, message={error_result['message']}")
                return error_result

        url = f"https://api.github.com/repos/{username}/{repo}/pulls"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
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
        
        result = updated_response.json()
        
        success_result = {
            "status": "success",
            "data": result,
            "html_url": result.get("html_url"),
            "number": result.get("number")
        }
        
        # Log the success output
        print(f"[CREATE_PULL_REQUEST] : output status=success, pr_number={success_result['number']}, html_url={success_result['html_url']}")
        return success_result
    
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403):
            tool_context.state[TOKEN_CACHE_KEY] = None
            error_result = {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        else:
            print(f"Error creating pull request: {error}")
            error_result = {'status': 'error', 'message': str(error)}
        
        # Log the error output
        print(f"[CREATE_PULL_REQUEST] : output status=error, message={error_result['message']}")
        return error_result

def pull_request_exists(
    username: str,
    repo: str,
    head_branch: str,
    base_branch: str = "main",
    tool_context: ToolContext = None
) -> bool:
    """
    Checks if a pull request already exists for the given branches.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        head_branch (str): The name of the branch where your changes are implemented
        base_branch (str): The name of the branch you want the changes pulled into
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        bool: True if a pull request exists, False otherwise
    """
    # Log the start of the tool execution with main parameters
    print(f"[PULL_REQUEST_EXISTS] username={username} repo={repo} head_branch={head_branch} base_branch={base_branch}")
    
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
                print(f"[PULL_REQUEST_EXISTS] : output status=error, message=GitHub token not found")
                return False

        url = f"https://api.github.com/repos/{username}/{repo}/pulls"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
        params = {
            "head": f"{username}:{head_branch}",
            "base": base_branch,
            "state": "open"
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        exists = len(response.json()) > 0
        
        # Log the output
        print(f"[PULL_REQUEST_EXISTS] : output exists={exists}")
        return exists
    
    except RequestException as error:
        # Log the error output
        print(f"[PULL_REQUEST_EXISTS] : output status=error, message={str(error)}")
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
    tool_context: ToolContext = None
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
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The created pull request data from GitHub API

    Raises:
        ValueError: If a pull request already exists
        RequestException: If there's an error checking or creating the pull request
    """
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_PULL_REQUEST_IF_NOT_EXISTS] username={username} repo={repo} title='{title[:50]}{'...' if len(title) > 50 else ''}' head_branch={head_branch} base_branch={base_branch}")
    
    if not pull_request_exists(username, repo, head_branch, base_branch, tool_context):
        result = create_pull_request(
            username,
            repo,
            title,
            body,
            head_branch,
            base_branch,
            labels,
            draft,
            tool_context
        )
        # Log the success output
        print(f"[CREATE_PULL_REQUEST_IF_NOT_EXISTS] : output status=success, created new pr_number={result.get('number')}")
        return result
    else:
        error_msg = f"Pull request already exists for {head_branch} into {base_branch}"
        # Log the error output
        print(f"[CREATE_PULL_REQUEST_IF_NOT_EXISTS] : output status=error, message={error_msg}")
        return {'status': 'error', 'message': error_msg}

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
            None
        )
        print("Created pull request:", result["html_url"])
    except Exception as error:
        print(f"Test failed: {error}") 