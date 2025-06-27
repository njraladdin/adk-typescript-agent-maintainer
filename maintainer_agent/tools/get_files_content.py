from typing import Optional, Dict, Any, List
from google.adk.tools import ToolContext
from ..github_api_utils import fetch_multiple_files_content, get_github_token

def get_files_content(
    repo: str,
    file_paths: List[str],
    branch: Optional[str] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Gets the content and metadata of multiple files from a GitHub repository concurrently
    and automatically stores them in the session state.

    Args:
        repo (str): GitHub repository in the format "username/repo" (e.g. "google/adk-python")
        file_paths (List[str]): List of file paths within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'partial' or 'error')
            - files: Dict[str, Dict] Dictionary mapping file paths to their content and metadata
            - successful_files: List[str] List of successfully fetched file paths
            - failed_files: Dict[str, str] Dictionary mapping failed file paths to error messages
            - message: str (Summary message)
    """
    # Log the start of the tool execution with main parameters
    print(f"[GET_FILES_CONTENT] repo={repo} file_count={len(file_paths)} branch={branch or 'default'}")
    print(f"[GET_FILES_CONTENT] files={file_paths}")
    
    try:
        # Check if GitHub token is available
        github_token = get_github_token()
        if not github_token:
            error_result = {
                'status': 'error', 
                'message': 'GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.',
                'files': {},
                'successful_files': [],
                'failed_files': {}
            }
            print(f"[GET_FILES_CONTENT] : output status=error, message={error_result['message']}")
            return error_result
        
        # Use the centralized GitHub API utility for concurrent fetching
        print(f"[GET_FILES_CONTENT] Starting concurrent fetch of {len(file_paths)} files...")
        
        # Fetch all files using the centralized utility
        file_results = fetch_multiple_files_content(repo, file_paths, branch or "main")
        
        # Process results
        files = {}
        successful_files = []
        failed_files = {}
        
        for file_path, result in file_results.items():
            if result['status'] == 'success':
                files[file_path] = {
                    'content': result['content'],
                    'metadata': result['metadata']
                }
                successful_files.append(file_path)
                
                # Store file content in session state
                if tool_context:
                    # Only store TypeScript files - Python files are handled by the callback
                    if not ("adk-python" in repo or "google" in repo.split('/')[0]):
                        # Default to TypeScript files for all other repositories
                        if 'typescript_files' not in tool_context.state:
                            tool_context.state['typescript_files'] = {}
                        tool_context.state['typescript_files'][file_path] = result['content']
                
                
            else:
                failed_files[file_path] = result['message']
                print(f"[GET_FILES_CONTENT] Failed to fetch {file_path}: {result['message']}")
        
        # Determine overall status
        if len(successful_files) == len(file_paths):
            status = 'success'
            message = f"Successfully fetched all {len(file_paths)} files concurrently"
        elif len(successful_files) > 0:
            status = 'partial'
            message = f"Fetched {len(successful_files)}/{len(file_paths)} files successfully"
        else:
            status = 'error'
            message = f"Failed to fetch any files"
        
        result = {
            'status': status,
            'files': files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'message': message
        }
        
        # Log the output
        print(f"[GET_FILES_CONTENT] : output status={status}, successful={len(successful_files)}, failed={len(failed_files)}")
        print(f"[GET_FILES_CONTENT] Concurrent fetch completed using centralized GitHub API utilities")
        
        return result
    
    except Exception as error:
        print(f"Error in get_files_content: {error}")
        error_result = {
            'status': 'error', 
            'message': str(error),
            'files': {},
            'successful_files': [],
            'failed_files': {}
        }
        
        # Log the error output
        print(f"[GET_FILES_CONTENT] : output status=error, message={error_result['message']}")
        return error_result

if __name__ == "__main__":
    # Example usage
    try:
        test_repo = "njraladdin/adk-typescript"
        test_files = ["README.md", "package.json", "src/agents/BaseAgent.ts"]
        test_branch = "main"
        
        print(f"Testing concurrent fetch of {len(test_files)} files from {test_repo}:")
        result = get_files_content(
            test_repo,
            test_files,
            test_branch
        )
        
        if result["status"] in ["success", "partial"]:
            print(f"\nFetched {len(result['successful_files'])} files successfully:")
            for file_path in result['successful_files']:
                metadata = result['files'][file_path]['metadata']
                content_preview = result['files'][file_path]['content'][:100]
                print(f"- {file_path}: {metadata['size']} bytes")
                print(f"  Preview: {content_preview}...")
            
            if result['failed_files']:
                print(f"\nFailed to fetch {len(result['failed_files'])} files:")
                for file_path, error in result['failed_files'].items():
                    print(f"- {file_path}: {error}")
        else:
            print(f"Error: {result['message']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 