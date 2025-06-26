from typing import Optional, Dict, Any, List
from google.adk.tools import ToolContext
from ..github_api_utils import create_pull_request as api_create_pull_request, pull_request_exists as api_pull_request_exists

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
    
    # Use the centralized API utility
    repo_full = f"{username}/{repo}"
    result = api_create_pull_request(
        repo_full, title, body, head_branch, base_branch, draft, issue_number, labels
    )
    
    # Log the output
    if result.get('status') == 'success':
        print(f"[CREATE_PULL_REQUEST] : output status=success, pr_number={result['number']}, html_url={result['html_url']}")
    else:
        print(f"[CREATE_PULL_REQUEST] : output status=error, message={result.get('message', 'Unknown error')}")
    
    return result

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
    
    # Use the centralized API utility
    repo_full = f"{username}/{repo}"
    exists = api_pull_request_exists(repo_full, head_branch, base_branch)
    
    # Log the output
    print(f"[PULL_REQUEST_EXISTS] : output exists={exists}")
    return exists

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