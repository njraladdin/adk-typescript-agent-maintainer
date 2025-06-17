from typing import Optional, Dict, Any, List
import requests
from requests.exceptions import RequestException

def get_repo_file_structure(
    username: str,
    repo: str,
    path: str = "",
    branch: str = "main",
    github_token: Optional[str] = None,
    exclude_patterns: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Gets the complete file and directory structure of a GitHub repository recursively.
    
    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        path (str): Path within the repository to start from (default: root)
        branch (str): Branch to get structure from (default: 'main')
        github_token (Optional[str]): GitHub personal access token for authentication
        exclude_patterns (Optional[List[str]]): List of patterns to exclude (e.g., ["node_modules/", ".git/"])
        
    Returns:
        List[Dict[str, Any]]: List of file/directory objects with structure:
            - path: str (Full path to the file/directory)
            - type: str ('file' or 'dir')
            - size: int (file size in bytes, 0 for directories)
            - name: str (Name of the file/directory)
            For directories, also includes:
            - contents: List[Dict[str, Any]] (Recursive structure for subdirectories)
    
    Raises:
        RequestException: If there's an error fetching the repository structure
    """
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/contents/{path}"
        if branch:
            url += f"?ref={branch}"
            
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        items = response.json()
        
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
                ".idea/"
            ]
        
        result = []
        for item in items:
            # Skip excluded patterns
            should_skip = False
            for pattern in exclude_patterns:
                if pattern in item["path"]:
                    should_skip = True
                    break
            if should_skip:
                continue
            
            entry = {
                "path": item["path"],
                "type": "dir" if item["type"] == "dir" else "file",
                "size": item["size"],
                "name": item["name"]
            }
            
            # Recursively get contents of directories
            if item["type"] == "dir":
                entry["contents"] = get_repo_file_structure(
                    username,
                    repo,
                    item["path"],
                    branch,
                    github_token,
                    exclude_patterns
                )
            
            result.append(entry)
        
        return result
    
    except RequestException as error:
        print(f"Error fetching repository file structure: {error}")
        raise

def print_repo_file_structure(structure: List[Dict[str, Any]], indent: int = 0) -> None:
    """Helper function to print the repository file structure in a tree-like format."""
    for item in structure:
        print("  " * indent + "├── " + item["name"])
        if item["type"] == "dir" and "contents" in item:
            print_repo_file_structure(item["contents"], indent + 1)

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_branch = "main"
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        # Custom exclude patterns
        exclude = [
            "node_modules/",
            ".git/",
            "dist/",
            "__pycache__/"
        ]
        
        print(f"Fetching repository file structure for {test_username}/{test_repo}:")
        structure = get_repo_file_structure(
            test_username,
            test_repo,
            branch=test_branch,
            github_token=github_token,
            exclude_patterns=exclude
        )
        
        # Print the structure in a tree-like format
        print("\nRepository file structure:")
        print_repo_file_structure(structure)
        
    except Exception as error:
        print(f"Test failed: {error}") 