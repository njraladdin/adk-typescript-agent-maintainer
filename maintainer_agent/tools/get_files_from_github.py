from typing import Optional, Dict, Any, List
from google.adk.tools import ToolContext
from ..github_api_utils import fetch_multiple_files_content, get_github_token

def get_files_from_github(
    repo: str,
    file_paths: List[str],
    branch: Optional[str] = None,
    tool_context: ToolContext = None
) -> Dict[str, Dict[str, Any]]:
    """
    Gets the content and metadata of multiple files from a GitHub repository concurrently
    and automatically stores them in the session state.

    Args:
        repo (str): GitHub repository in the format "username/repo" (e.g. "google/adk-python")
        file_paths (List[str]): List of file paths within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)
        tool_context (ToolContext): Automatically injected by ADK for auth handling

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping file paths to their content and metadata.
                                  Only includes successfully fetched files.
    """
    try:
        # Check if GitHub token is available
        github_token = get_github_token()
        if not github_token:
            raise Exception('GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.')
        
        # Fetch all files using the centralized utility
        file_results = fetch_multiple_files_content(repo, file_paths, branch or "main")
        
        # Process results - only return successfully fetched files
        files = {}
        
        for file_path, result in file_results.items():
            if result['status'] == 'success':
                files[file_path] = {
                    'content': result['content'],
                    'metadata': result['metadata']
                }
                
                # Store file content in session state
                if tool_context:
                    # Only store TypeScript files - Python files are handled by the callback
                    if not ("adk-python" in repo or "google" in repo.split('/')[0]):
                        # Default to TypeScript files for all other repositories
                        if 'typescript_files' not in tool_context.state:
                            tool_context.state['typescript_files'] = {}
                        tool_context.state['typescript_files'][file_path] = result['content']
        
        return files
    
    except Exception as error:
        print(f"Error in get_files_from_github: {error}")
        return {}

if __name__ == "__main__":
    # Example usage
    try:
        test_repo = "njraladdin/adk-typescript"
        test_files = ["README.md", "package.json", "src/agents/BaseAgent.ts"]
        test_branch = "main"
        
        print(f"Testing concurrent fetch of {len(test_files)} files from {test_repo}:")
        files = get_files_from_github(
            test_repo,
            test_files,
            test_branch
        )
        
        if files:
            print(f"\nFetched {len(files)} files successfully:")
            for file_path, file_data in files.items():
                metadata = file_data['metadata']
                content_preview = file_data['content'][:100]
                print(f"- {file_path}: {metadata['size']} bytes")
                print(f"  Preview: {content_preview}...")
        else:
            print("No files were fetched successfully")
            
    except Exception as error:
        print(f"Test failed: {error}") 