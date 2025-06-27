from typing import Dict, Any
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

# Import from the parent module's utils
from ..github_api_utils import parse_diff, FileDiff, CommitDiffResponse, fetch_commit_diff_raw

TOKEN_CACHE_KEY = "github_token"
GATHERED_CONTEXT_KEY = "gathered_context"

def get_commit_diff(
    username: str,
    repo: str,
    commit_sha: str,
    max_excerpt_lines: int = 10,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Gets the diff for a specific commit and automatically stores it in the session state.
    
    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        commit_sha (str): The commit hash to get the diff for
        max_excerpt_lines (int): Maximum number of lines to include in the excerpt (default: 10)
        tool_context (ToolContext): Automatically injected by ADK for auth handling
    
    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - diff: CommitDiffResponse (Structured diff object containing file diffs and stats)
            - message: str (Error message if status is 'error')
    """
    # Log the start of the tool execution with main parameters
    print(f"[GET_COMMIT_DIFF] username={username} repo={repo} commit_sha={commit_sha}")
    
    try:        
        # Use the utility function to fetch raw diff
        repo_path = f"{username}/{repo}"
        raw_diff = fetch_commit_diff_raw(repo_path, commit_sha)
        
        diff_data = parse_diff(raw_diff, max_excerpt_lines)
        
        # Store commit info in session state
        if tool_context:
            # Initialize gathered_context if it doesn't exist
            if GATHERED_CONTEXT_KEY not in tool_context.state:
                tool_context.state[GATHERED_CONTEXT_KEY] = {}
            
            # Store commit info - this structure remains the same
            # Other tools will store files in python_context_files and typescript_context_files
            tool_context.state[GATHERED_CONTEXT_KEY]['commit_info'] = {
                'commit_sha': commit_sha,
                'diff': raw_diff,  # Store raw diff
                'changed_files': [file_info['file'] for file_info in diff_data['files']]
            }
        
        success_result = {
            'status': 'success',
            'diff': diff_data
        }
        
        # Log the output of the tool execution
        print(f"[GET_COMMIT_DIFF] : output status=success, files_changed={diff_data['total_files_changed']}, additions={diff_data['total_additions']}, deletions={diff_data['total_deletions']}")
        
        return success_result
    except RequestException as error:
        error_result = {'status': 'error', 'message': f'Request failed: {str(error)}'}
        
        # Log the error output
        print(f"[GET_COMMIT_DIFF] : output status=error, message={error_result['message']}")
        return error_result
    except Exception as error:
        error_result = {'status': 'error', 'message': str(error)}
        
        # Log the error output
        print(f"[GET_COMMIT_DIFF] : output status=error, message={error_result['message']}")
        return error_result

if __name__ == "__main__":
    # Example usage
    try:
        # Example values for testing
        test_username = "google"
        test_repo = "adk-python"
        test_commit_sha = "6dec235c13f42f1a6f69048b30fb78f48831cdbd"  # Example commit SHA
        
        print(f"Fetching diff for commit {test_commit_sha} from {test_username}/{test_repo} repo:")
        diff_data = get_commit_diff(test_username, test_repo, test_commit_sha, 10)
        import json
        print(json.dumps(diff_data, indent=2))
    except Exception as error:
        print(f"Test failed: {error}") 