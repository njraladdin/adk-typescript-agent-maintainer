from typing import Optional, Dict, Any, List
from google.adk.tools import ToolContext
from requests.exceptions import RequestException
from ..github_api_utils import fetch_file_content, get_github_token

GATHERED_CONTEXT_KEY = "gathered_context"
TOKEN_CACHE_KEY = "github_token"

def get_file_content(
    repo: str,
    file_path: str,
    branch: Optional[str] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Gets the content and metadata of a file from a GitHub repository and automatically
    stores it in the session state.

    Args:
        repo (str): GitHub repository in the format "username/repo" (e.g. "google/adk-python")
        file_path (str): Path to the file within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - content: str (The file content as a string)
            - metadata: Dict[str, Any] File metadata including:
                - sha: str (File's SHA hash)
                - size: int (File size in bytes)
                - encoding: str (File encoding, usually 'base64' or 'utf-8')
                - url: str (API URL for the file)
                - html_url: str (Web URL for the file)
                - git_url: str (Git URL for the file)
                - download_url: str (Raw content URL)
                - type: str (Usually 'file')
                - content: str (Raw content from API)
                - name: str (File name)
                - path: str (File path)
            - message: str (Error message if status is 'error')
    """
    # Log the start of the tool execution with main parameters
    print(f"[GET_FILE_CONTENT] repo={repo} file_path={file_path} branch={branch or 'default'}")
    
    try:
        # Check if GitHub token is available
        github_token = get_github_token()
        if not github_token:
            error_result = {
                'status': 'error', 
                'message': 'GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.'
            }
            # Log the error output
            print(f"[GET_FILE_CONTENT] : output status=error, message={error_result['message']}")
            return error_result
        
        # Use the centralized API utility
        content = fetch_file_content(repo, file_path, branch or "main")
        
        # Check if it's an error response
        if content.startswith("Error fetching file:"):
            error_result = {
                'status': 'error',
                'message': content
            }
            # Log the error output
            print(f"[GET_FILE_CONTENT] : output status=error, message={error_result['message']}")
            return error_result
        
        # Create a minimal metadata structure (since the utility only returns content)
        metadata = {
            'name': file_path.split('/')[-1],
            'path': file_path,
            'size': len(content.encode('utf-8')),
            'type': 'file'
        }
        
        # Store file content in session state
        if tool_context:
            # Only store TypeScript files - Python files are handled by the callback
            if not ("adk-python" in repo or "google" in repo.split('/')[0]):
                # Default to TypeScript files for all other repositories
                if 'typescript_files' not in tool_context.state:
                    tool_context.state['typescript_files'] = {}
                tool_context.state['typescript_files'][file_path] = content
        
        success_result = {
            'status': 'success',
            'content': content,
            'metadata': metadata
        }
        
        # Log the output of the tool execution
        print(f"[GET_FILE_CONTENT] : output status=success, file_size={metadata.get('size')} bytes, name={metadata.get('name')}")
        
        return success_result
    
    except Exception as error:
        print(f"Error fetching file content: {error}")
        error_result = {'status': 'error', 'message': str(error)}
        
        # Log the error output
        print(f"[GET_FILE_CONTENT] : output status=error, message={error_result['message']}")
        return error_result

def file_exists(
    repo: str,
    file_path: str,
    branch: Optional[str] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Checks if a file exists in a GitHub repository.

    Args:
        repo (str): GitHub repository in the format "username/repo" (e.g. "google/adk-python")
        file_path (str): Path to the file within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - exists: bool (True if the file exists, False otherwise)
            - message: str (Error message if status is 'error')
    """
    # Log the start of the tool execution with main parameters
    print(f"[FILE_EXISTS] repo={repo} file_path={file_path} branch={branch or 'default'}")
    
    try:
        # Check if GitHub token is available
        github_token = get_github_token()
        if not github_token:
            error_result = {
                'status': 'error', 
                'message': 'GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.'
            }
            # Log the error output
            print(f"[FILE_EXISTS] : output status=error, message={error_result['message']}")
            return error_result

        # Try to fetch the file content using our utility
        content = fetch_file_content(repo, file_path, branch or "main")
        
        # If it's an error, the file doesn't exist
        if content.startswith("Error fetching file:"):
            exists = False
        else:
            exists = True
            
        success_result = {
            'status': 'success',
            'exists': exists
        }
        # Log the output of the tool execution
        print(f"[FILE_EXISTS] : output status=success, exists={exists}")
        return success_result
        
        success_result = {
            'status': 'success',
            'exists': False
        }
        # Log the output of the tool execution
        print(f"[FILE_EXISTS] : output status=success, exists=False")
        return success_result
    
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403):
            tool_context.state[TOKEN_CACHE_KEY] = None
            error_result = {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        else:
            print(f"Error checking file existence: {error}")
            error_result = {'status': 'error', 'message': str(error)}
        
        # Log the error output
        print(f"[FILE_EXISTS] : output status=error, message={error_result['message']}")
        return error_result



if __name__ == "__main__":
    # Example usage
    try:
        test_repo = "njraladdin/adk-typescript"
        test_file = "README.md"
        test_branch = "main"
        
        # Check if file exists
        exists_result = file_exists(
            test_repo,
            test_file,
            test_branch
        )
        
        if exists_result["status"] == "success":
            if exists_result["exists"]:
                print(f"Fetching content of {test_file} from {test_repo}:")
                result = get_file_content(
                    test_repo,
                    test_file,
                    test_branch
                )
                
                if result["status"] == "success":
                    metadata = result["metadata"]
                    content = result["content"]
                    print("\nFile metadata:")
                    print(f"Name: {metadata['name']}")
                    print(f"Size: {metadata['size']} bytes")
                    print(f"SHA: {metadata['sha']}")
                    print("\nContent preview (first 200 chars):")
                    print(content[:200] + "..." if len(content) > 200 else content)
                else:
                    print(f"Error: {result['message']}")
            else:
                print(f"File {test_file} not found")
        else:
            print(f"Error: {exists_result['message']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 