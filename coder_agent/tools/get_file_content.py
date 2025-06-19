from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

TOKEN_CACHE_KEY = "github_token"
GATHERED_CONTEXT_KEY = "gathered_context"

def get_file_content(
    username: str,
    repo: str,
    file_path: str,
    branch: Optional[str] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Gets the content and metadata of a file from a GitHub repository and automatically
    stores it in the session state.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
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
    try:
        # Step 1: Check for cached token
        github_token = tool_context.state.get(TOKEN_CACHE_KEY) if tool_context else None
        
        # If no token, we need to get it from environment or request it
        if not github_token:
            # For now, let's try to get it from environment as a fallback
            import os
            github_token = os.getenv("GITHUB_TOKEN")
            
            if github_token and tool_context:
                # Cache the token for future use
                tool_context.state[TOKEN_CACHE_KEY] = github_token
            elif not github_token:
                return {
                    'status': 'error', 
                    'message': 'GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.'
                }

        url = f"https://api.github.com/repos/{username}/{repo}/contents/{file_path}"
        if branch:
            url += f"?ref={branch}"
            
        headers = {
            "Accept": "application/vnd.github.v3.raw",
            "Authorization": f"token {github_token}"
        }
        
        # First get the metadata with regular API call
        meta_headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
        meta_response = requests.get(url, headers=meta_headers)
        meta_response.raise_for_status()
        metadata = meta_response.json()
        
        if isinstance(metadata, list):
            return {
                'status': 'error',
                'message': f"Path '{file_path}' points to a directory, not a file"
            }
        
        # Then get the raw content
        content_response = requests.get(url, headers=headers)
        content_response.raise_for_status()
        content = content_response.text
        
        # Store file content in session state
        if tool_context:
            # Initialize gathered_context if it doesn't exist
            if GATHERED_CONTEXT_KEY not in tool_context.state:
                tool_context.state[GATHERED_CONTEXT_KEY] = {}
            
            # Determine which category this file belongs to based on repository
            repo_key = f"{username}/{repo}"
            
            if "adk-python" in repo_key or "google" in username:
                # This is a Python file (either source or additional context)
                if 'python_context_files' not in tool_context.state[GATHERED_CONTEXT_KEY]:
                    tool_context.state[GATHERED_CONTEXT_KEY]['python_context_files'] = {}
                tool_context.state[GATHERED_CONTEXT_KEY]['python_context_files'][file_path] = content
                
            else:
                # Default to TypeScript files for all other repositories
                # This simplifies our implementation to focus on just Python and TypeScript
                if 'typescript_context_files' not in tool_context.state[GATHERED_CONTEXT_KEY]:
                    tool_context.state[GATHERED_CONTEXT_KEY]['typescript_context_files'] = {}
                tool_context.state[GATHERED_CONTEXT_KEY]['typescript_context_files'][file_path] = content
        
        return {
            'status': 'success',
            'content': content,
            'metadata': metadata
        }
    
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403) and tool_context:
            tool_context.state[TOKEN_CACHE_KEY] = None
            return {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        print(f"Error fetching file content: {error}")
        return {'status': 'error', 'message': str(error)}

def file_exists(
    username: str,
    repo: str,
    file_path: str,
    branch: Optional[str] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Checks if a file exists in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        file_path (str): Path to the file within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - exists: bool (True if the file exists, False otherwise)
            - message: str (Error message if status is 'error')
    """
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
                return {
                    'status': 'error', 
                    'message': 'GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.'
                }

        url = f"https://api.github.com/repos/{username}/{repo}/contents/{file_path}"
        if branch:
            url += f"?ref={branch}"
            
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json()
            # Make sure it's a file, not a directory
            return {
                'status': 'success',
                'exists': not isinstance(content, list)
            }
        return {
            'status': 'success',
            'exists': False
        }
    
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403):
            tool_context.state[TOKEN_CACHE_KEY] = None
            return {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        print(f"Error checking file existence: {error}")
        return {'status': 'error', 'message': str(error)}

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_file = "README.md"
        test_branch = "main"
        
        # Check if file exists
        exists_result = file_exists(
            test_username,
            test_repo,
            test_file,
            test_branch
        )
        
        if exists_result["status"] == "success":
            if exists_result["exists"]:
                print(f"Fetching content of {test_file} from {test_username}/{test_repo}:")
                result = get_file_content(
                    test_username,
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