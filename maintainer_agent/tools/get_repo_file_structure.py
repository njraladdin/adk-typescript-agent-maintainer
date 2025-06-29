from typing import Optional, Dict, Any, List
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

TOKEN_CACHE_KEY = "github_token"
GATHERED_CONTEXT_KEY = "gathered_context"

class MockToolContext:
    """Mock ToolContext for direct script execution"""
    def __init__(self):
        self._state = {}
    
    @property
    def state(self):
        return self._state

def format_repo_structure_as_string(tree_items: List[Dict[str, Any]], exclude_patterns: List[str]) -> str:
    """
    Format the repository tree structure as a simple string representation.
    This makes it much easier for LLMs to understand the repository structure.
    """
    lines = []
    
    # Group items by type and sort them
    directories = []
    files = []
    
    for item in tree_items:
        item_path = item["path"]
        
        # Skip excluded patterns
        should_skip = False
        for pattern in exclude_patterns:
            if pattern in item_path:
                should_skip = True
                break
        if should_skip:
            continue
            
        if item["type"] == "tree":
            directories.append(item_path + "/")
        elif item["type"] == "blob":
            size_kb = round(item.get("size", 0) / 1024, 1) if item.get("size", 0) > 0 else 0
            files.append(f"{item_path} ({size_kb}KB)")
    
    # Sort directories and files
    directories.sort()
    files.sort()
    
    # Add directories first
    if directories:
        lines.append("DIRECTORIES:")
        for directory in directories:
            lines.append(f"  {directory}")
        lines.append("")
    
    # Add files
    if files:
        lines.append("FILES:")
        for file in files:
            lines.append(f"  {file}")
    
    return "\n".join(lines)

def get_repo_file_structure(
    repo: str = 'njraladdin/adk-typescript',
    path: str = "",
    branch: str = "main",
    exclude_patterns: Optional[List[str]] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Gets the complete file and directory structure of a GitHub repository using the Git Tree API
    and automatically stores it in the session state.
    
    Args:
        repo (str): GitHub repository in the format "username/repo" (e.g. "google/adk-python")
        path (str): Path within the repository to start from (default: root)
        branch (str): Branch to get structure from (default: 'main')
        exclude_patterns (Optional[List[str]]): List of patterns to exclude (e.g., ["node_modules/", ".git/"])
        tool_context (ToolContext): Automatically injected by ADK for auth handling
        
    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - data: List[Dict[str, Any]] List of file/directory objects
            - message: str (Error message if status is 'error')
    """
    # Log the start of the tool execution with main parameters
    print(f"[GET_REPO_FILE_STRUCTURE] repo={repo} branch={branch} path={path}")
    
    try:
        # Get token from context
        github_token = tool_context.state.get(TOKEN_CACHE_KEY) if tool_context else None
        if not github_token:
            import os
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token and tool_context:
                tool_context.state[TOKEN_CACHE_KEY] = github_token

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {github_token}" if github_token else None
        }

        # First, get the commit SHA for the branch
        print(f"Fetching latest commit SHA for branch: {branch}")
        branch_url = f"https://api.github.com/repos/{repo}/branches/{branch}"
        branch_response = requests.get(branch_url, headers=headers)
        branch_response.raise_for_status()
        commit_sha = branch_response.json()["commit"]["sha"]

        # Get the full tree with recursive=1
        print(f"Fetching complete repository tree...")
        tree_url = f"https://api.github.com/repos/{repo}/git/trees/{commit_sha}?recursive=1"
        response = requests.get(tree_url, headers=headers)
        response.raise_for_status()
        tree_data = response.json()

        if tree_data.get("truncated", False):
            print("Warning: Repository tree was truncated due to size!")

        # Initialize exclude patterns if not provided
        if exclude_patterns is None:
            exclude_patterns = [
                "node_modules/",
                ".git/",
                "dist/",
                "build/",
                "__pycache__/",
                ".pytest_cache/",
                ".vscode/",
                ".idea/", "docs/"
            ]

        # Process the tree into our desired structure
        print("Processing repository tree...")
        path_dict = {}
        result = []

        # First pass: Create all directory entries
        for item in tree_data["tree"]:
            item_path = item["path"]
            
            # Skip excluded patterns
            should_skip = False
            for pattern in exclude_patterns:
                if pattern in item_path:
                    should_skip = True
                    break
            if should_skip:
                #print(f"Skipping excluded path: {item_path}")
                continue

            # Split path into components
            components = item_path.split("/")
            current_path = ""
            
            # Create directory entries for each path component
            for i, component in enumerate(components[:-1]):
                parent_path = "/".join(components[:i]) if i > 0 else ""
                current_path = "/".join(components[:i+1])
                
                if current_path not in path_dict:
                    dir_entry = {
                        "path": current_path,
                        "type": "dir",
                        "size": 0,
                        "name": component,
                        "contents": []
                    }
                    path_dict[current_path] = dir_entry
                    
                    # Add to parent's contents or root result
                    if parent_path:
                        path_dict[parent_path]["contents"].append(dir_entry)
                    elif i == 0:  # Root level directory
                        result.append(dir_entry)

        # Second pass: Add all files
        for item in tree_data["tree"]:
            if item["type"] != "blob":  # Skip non-file entries
                continue
                
            item_path = item["path"]
            
            # Skip if path was excluded
            if item_path not in path_dict:
                components = item_path.split("/")
                parent_path = "/".join(components[:-1])
                file_name = components[-1]
                
                file_entry = {
                    "path": item_path,
                    "type": "file",
                    "size": item["size"],
                    "name": file_name
                }
                
                # Add to parent's contents or root result
                if parent_path:
                    if parent_path in path_dict:
                        path_dict[parent_path]["contents"].append(file_entry)
                else:  # Root level file
                    result.append(file_entry)

        # Store repo structure in session state
        if tool_context:
            # Initialize gathered_context if it doesn't exist
            if GATHERED_CONTEXT_KEY not in tool_context.state:
                tool_context.state[GATHERED_CONTEXT_KEY] = {}
            
            # Create a simple formatted string representation instead of complex nested structure
            formatted_structure = format_repo_structure_as_string(tree_data["tree"], exclude_patterns)
            
            # Determine which repo this is and store accordingly
            if "adk-python" in repo or "google" in repo.split('/')[0]:
                tool_context.state[GATHERED_CONTEXT_KEY]['python_repo_structure'] = formatted_structure
            else:
                # Default to TypeScript for all other repositories
                tool_context.state[GATHERED_CONTEXT_KEY]['typescript_repo_structure'] = formatted_structure

        # Format and print the tree data in a more readable way
        formatted_tree = []
        for item in tree_data['tree']:
            entry = {
                'path': item['path'],
                'type': item['type'],
                'size': item.get('size', 0) if item['type'] == 'blob' else None
            }
            formatted_tree.append(entry)

        # Skip the flat list output and only use the hierarchical tree structure
        # that's already implemented in print_repo_file_structure()
        result_data = {
            "status": "success",
            "data": result
        }
        
        # Log the output of the tool execution
        print(f"[GET_REPO_FILE_STRUCTURE] : output status={result_data['status']}, found {len(result)} top-level items")
        
        return result_data

    except RequestException as error:
        if hasattr(error, 'response') and error.response.status_code in (401, 403) and tool_context:
            tool_context.state[TOKEN_CACHE_KEY] = None
            error_result = {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        else:
            print(f"Error fetching repository file structure: {error}")
            error_result = {'status': 'error', 'message': str(error)}
        
        # Log the error output
        print(f"[GET_REPO_FILE_STRUCTURE] : output status=error, message={error_result['message']}")
        return error_result

def print_repo_file_structure(structure: List[Dict[str, Any]], indent: int = 0) -> None:
    """Helper function to print the repository file structure in a tree-like format."""
    for item in structure:
        prefix = "  " * indent + "- "
        size_info = f" ({item['size']} bytes)" if item.get('size') else ""
        print(f"{prefix}{item['name']}{size_info}")
        if item["type"] == "dir" and "contents" in item:
            print_repo_file_structure(item["contents"], indent + 1)

if __name__ == "__main__":
    # Example usage
    try:
        test_repo = "njraladdin/adk-typescript"
        test_branch = "main"
        
        # Custom exclude patterns
        exclude = [
            "node_modules/",
            ".git/",
            "dist/",
            "__pycache__/"
        ]
        
        # Create mock context for direct script execution
        mock_context = MockToolContext()
        
        print(f"Fetching repository file structure for {test_repo}:")
        result = get_repo_file_structure(
            test_repo,
            branch=test_branch,
            exclude_patterns=exclude,
            tool_context=mock_context
        )
        
        if result["status"] == "success":
            # Print the structure in a tree-like format
            print("\nRepository file structure:")
            print_repo_file_structure(result["data"])
        else:
            print(f"Error: {result['message']}")
        
    except Exception as error:
        print(f"Test failed: {error}") 