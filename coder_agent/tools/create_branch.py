from typing import Optional, Dict, Any
from google.adk.tools import ToolContext
from ..git_api_utils import create_branch as api_create_branch, branch_exists as api_branch_exists

def create_branch(
    username: str,
    repo: str,
    branch_name: Optional[str] = None,
    issue_number: Optional[int] = None,
    base_branch: str = "main",
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Creates a new branch in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        branch_name (Optional[str]): Name of the new branch to create. If not provided, issue_number must be provided.
        issue_number (Optional[int]): Issue number to auto-generate branch name as 'port-issue-{number}'
        base_branch (str): Name of the branch to base the new branch on (default: 'main')
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The created reference data from GitHub API

    Raises:
        RequestException: If there's an error creating the branch
    """
    # Auto-generate branch name if issue_number is provided
    if branch_name is None and issue_number is not None:
        branch_name = f"port-issue-{issue_number}"
    elif branch_name is None and issue_number is None:
        error_result = {
            'status': 'error', 
            'message': 'Either branch_name or issue_number must be provided'
        }
        print(f"[CREATE_BRANCH] : output status=error, message={error_result['message']}")
        return error_result
    
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_BRANCH] username={username} repo={repo} branch_name={branch_name} base_branch={base_branch}")
    
    # Use the centralized API utility
    repo_full = f"{username}/{repo}"
    result = api_create_branch(repo_full, branch_name, base_branch)
    
    # Log the output
    if result.get('status') == 'success':
        base_sha = result.get('base_sha', '')
        print(f"[CREATE_BRANCH] : output status=success, created branch={branch_name} from base_sha={base_sha[:7] if base_sha else 'unknown'}")
    else:
        print(f"[CREATE_BRANCH] : output status=error, message={result.get('message', 'Unknown error')}")
    
    return result

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
    
    # Use the centralized API utility
    repo_full = f"{username}/{repo}"
    exists = api_branch_exists(repo_full, branch_name)
    
    # Log the output
    print(f"[BRANCH_EXISTS] : output exists={exists}")
    return exists

def create_branch_if_not_exists(
    username: str,
    repo: str,
    branch_name: Optional[str] = None,
    issue_number: Optional[int] = None,
    base_branch: str = "main",
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Creates a new branch if it doesn't already exist.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        branch_name (Optional[str]): Name of the branch to create. If not provided, issue_number must be provided.
        issue_number (Optional[int]): Issue number to auto-generate branch name as 'port-issue-{number}'
        base_branch (str): Name of the branch to base the new branch on (default: 'main')
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: The branch reference data from GitHub API

    Raises:
        RequestException: If there's an error checking or creating the branch
    """
    # Auto-generate branch name if issue_number is provided
    if branch_name is None and issue_number is not None:
        branch_name = f"port-issue-{issue_number}"
    elif branch_name is None and issue_number is None:
        error_result = {
            'status': 'error', 
            'message': 'Either branch_name or issue_number must be provided'
        }
        print(f"[CREATE_BRANCH_IF_NOT_EXISTS] : output status=error, message={error_result['message']}")
        return error_result
    
    # Log the start of the tool execution with main parameters
    print(f"[CREATE_BRANCH_IF_NOT_EXISTS] username={username} repo={repo} branch_name={branch_name} base_branch={base_branch}")
    
    if not branch_exists(username, repo, branch_name, tool_context):
        result = create_branch(username, repo, branch_name, None, base_branch, tool_context)
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