"""
GitHub API utilities for interacting with GitHub repositories.

This module provides functions for GitHub API operations like fetching
commit data, repository structure, and file content from remote repositories.
"""

import os
import requests
import re
from typing import Optional, Dict, Any


def get_github_token() -> Optional[str]:
    """
    Get GitHub token from environment variables.
    
    Returns:
        Optional[str]: GitHub token if found, None otherwise
    """
    return os.getenv("GITHUB_TOKEN")


def fetch_commit_diff_data(commit_sha: str) -> Dict[str, Any]:
    """
    Fetch commit diff data from the Python repository.
    
    Args:
        commit_sha: The commit SHA to fetch diff for
        
    Returns:
        Dict containing commit info with diff and changed files
    """
    print(f"[FETCH_COMMIT_DIFF] Fetching commit {commit_sha} from google/adk-python")
    
    github_token = get_github_token()
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    headers["Accept"] = "application/vnd.github.v3.diff"
    
    try:
        response = requests.get(
            f"https://api.github.com/repos/google/adk-python/commits/{commit_sha}",
            headers=headers
        )
        response.raise_for_status()
        
        # Parse the diff to extract changed files
        diff_text = response.text
        changed_files = []
        
        # Extract file paths from diff headers
        for line in diff_text.split('\n'):
            if line.startswith('diff --git a/'):
                # Extract the file path after "a/"
                match = re.search(r'diff --git a/(.*?) b/', line)
                if match:
                    changed_files.append(match.group(1))
        
        return {
            'commit_sha': commit_sha,
            'diff': diff_text,
            'changed_files': changed_files
        }
    except Exception as e:
        print(f"[FETCH_COMMIT_DIFF] Error: {e}")
        return {
            'commit_sha': commit_sha,
            'diff': '',
            'changed_files': [],
            'error': str(e)
        }


def fetch_repo_structure(repo: str, branch: str = "main") -> str:
    """
    Fetch repository structure as a formatted string.
    
    Args:
        repo: Repository in format 'owner/repo'
        branch: Branch name (default: main)
        
    Returns:
        Formatted string representation of repo structure
    """
    print(f"[FETCH_REPO_STRUCTURE] Fetching structure for {repo}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        # Get commit SHA for branch
        branch_url = f"https://api.github.com/repos/{repo}/branches/{branch}"
        branch_response = requests.get(branch_url, headers=headers)
        branch_response.raise_for_status()
        commit_sha = branch_response.json()["commit"]["sha"]
        
        # Get full tree
        tree_url = f"https://api.github.com/repos/{repo}/git/trees/{commit_sha}?recursive=1"
        response = requests.get(tree_url, headers=headers)
        response.raise_for_status()
        tree_data = response.json()
        
        # Exclude patterns
        exclude_patterns = [
            "node_modules/", ".git/", "dist/", "build/", "__pycache__/",
            ".pytest_cache/", ".vscode/", ".idea/", "docs/"
        ]
        
        # Format as string
        lines = []
        directories = []
        files = []
        
        for item in tree_data["tree"]:
            item_path = item["path"]
            
            # Skip excluded patterns
            skip = any(pattern in item_path for pattern in exclude_patterns)
            if skip:
                continue
            
            if item["type"] == "tree":
                directories.append(item_path + "/")
            elif item["type"] == "blob":
                size_kb = round(item.get("size", 0) / 1024, 1) if item.get("size", 0) > 0 else 0
                files.append(f"{item_path} ({size_kb}KB)")
        
        directories.sort()
        files.sort()
        
        if directories:
            lines.append("DIRECTORIES:")
            for directory in directories:
                lines.append(f"  {directory}")
            lines.append("")
        
        if files:
            lines.append("FILES:")
            for file in files:
                lines.append(f"  {file}")
        
        return "\n".join(lines)
        
    except Exception as e:
        print(f"[FETCH_REPO_STRUCTURE] Error for {repo}: {e}")
        return f"Error fetching structure for {repo}: {e}"


def fetch_file_content(repo: str, file_path: str, branch: str = "main") -> str:
    """
    Fetch file content from a GitHub repository.
    
    Args:
        repo: Repository in format 'owner/repo'
        file_path: Path to the file
        branch: Branch name (default: main)
        
    Returns:
        File content as string
    """
    print(f"[FETCH_FILE_CONTENT] Fetching {file_path} from {repo}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3.raw"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        if branch != "main":
            url += f"?ref={branch}"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
        
    except Exception as e:
        print(f"[FETCH_FILE_CONTENT] Error fetching {file_path} from {repo}: {e}")
        return f"Error fetching file: {e}" 