"""
GitHub API utilities for interacting with GitHub repositories.

This module provides functions for GitHub API operations like fetching
commit data, repository structure, and file content from remote repositories.
"""

import os
import requests
import re
from typing import Optional, Dict, Any, List


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


def create_issue(repo: str, title: str, body: str) -> Dict[str, Any]:
    """
    Create a new issue in a GitHub repository.
    
    Args:
        repo: Repository in format 'owner/repo'
        title: Issue title
        body: Issue body/description
        
    Returns:
        Dict containing issue data or error info
    """
    print(f"[CREATE_ISSUE] Creating issue in {repo}: {title[:50]}{'...' if len(title) > 50 else ''}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        url = f"https://api.github.com/repos/{repo}/issues"
        data = {
            "title": title,
            "body": body
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            'status': 'success',
            'data': result,
            'html_url': result.get('html_url'),
            'number': result.get('number')
        }
        
    except Exception as e:
        print(f"[CREATE_ISSUE] Error creating issue in {repo}: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def close_issue(repo: str, issue_number: int, comment: Optional[str] = None) -> Dict[str, Any]:
    """
    Close a GitHub issue with optional comment.
    
    Args:
        repo: Repository in format 'owner/repo'
        issue_number: Issue number to close
        comment: Optional comment to add before closing
        
    Returns:
        Dict containing issue data or error info
    """
    print(f"[CLOSE_ISSUE] Closing issue #{issue_number} in {repo}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        base_url = f"https://api.github.com/repos/{repo}"
        
        # Add comment if provided
        if comment:
            comment_url = f"{base_url}/issues/{issue_number}/comments"
            comment_data = {"body": comment}
            comment_response = requests.post(comment_url, headers=headers, json=comment_data)
            comment_response.raise_for_status()
        
        # Close the issue
        issue_url = f"{base_url}/issues/{issue_number}"
        close_data = {"state": "closed"}
        response = requests.patch(issue_url, headers=headers, json=close_data)
        response.raise_for_status()
        
        result = response.json()
        return {
            'status': 'success',
            'data': result,
            'html_url': result.get('html_url'),
            'number': issue_number
        }
        
    except Exception as e:
        print(f"[CLOSE_ISSUE] Error closing issue #{issue_number} in {repo}: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def delete_issue(repo: str, issue_number: int, reason: str) -> Dict[str, Any]:
    """
    Delete a GitHub issue (actually closes it with a deletion comment).
    GitHub doesn't allow true deletion, so we close with explanation.
    
    Args:
        repo: Repository in format 'owner/repo'
        issue_number: Issue number to delete
        reason: Reason for deletion
        
    Returns:
        Dict containing issue data or error info
    """
    print(f"[DELETE_ISSUE] Deleting issue #{issue_number} in {repo}: {reason[:50]}{'...' if len(reason) > 50 else ''}")
    
    deletion_comment = f"**[AUTOMATED DELETION]**\n\nThis issue is being closed and deleted due to: {reason}\n\nNo further action is required."
    return close_issue(repo, issue_number, deletion_comment)


def create_pull_request(
    repo: str, 
    title: str, 
    body: str, 
    head_branch: str, 
    base_branch: str = "main",
    draft: bool = False,
    issue_number: Optional[int] = None,
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a new pull request in a GitHub repository.
    
    Args:
        repo: Repository in format 'owner/repo'
        title: Pull request title
        body: Pull request description
        head_branch: Branch with changes
        base_branch: Target branch (default: main)
        draft: Whether to create as draft
        issue_number: Optional issue to link
        
    Returns:
        Dict containing PR data or error info
    """
    print(f"[CREATE_PULL_REQUEST] Creating PR in {repo}: {head_branch} -> {base_branch}")
    
    # Add issue linking to body if provided
    if issue_number:
        body = f"{body}\n\nRelated to #{issue_number}"
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        url = f"https://api.github.com/repos/{repo}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        pr_data = response.json()
        
        # Add labels if provided
        if labels and len(labels) > 0:
            labels_url = f"https://api.github.com/repos/{repo}/issues/{pr_data['number']}/labels"
            labels_response = requests.post(labels_url, headers=headers, json=labels)
            labels_response.raise_for_status()
        
        # Get the updated PR data
        pr_url = pr_data["url"]
        updated_response = requests.get(pr_url, headers=headers)
        updated_response.raise_for_status()
        result = updated_response.json()
        
        return {
            'status': 'success',
            'data': result,
            'html_url': result.get('html_url'),
            'number': result.get('number')
        }
        
    except Exception as e:
        print(f"[CREATE_PULL_REQUEST] Error creating PR in {repo}: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def pull_request_exists(repo: str, head_branch: str, base_branch: str = "main") -> bool:
    """
    Check if a pull request exists for the given branches.
    
    Args:
        repo: Repository in format 'owner/repo'
        head_branch: Branch with changes
        base_branch: Target branch
        
    Returns:
        True if PR exists, False otherwise
    """
    print(f"[PULL_REQUEST_EXISTS] Checking if PR exists in {repo}: {head_branch} -> {base_branch}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        url = f"https://api.github.com/repos/{repo}/pulls"
        owner = repo.split('/')[0]
        params = {
            "head": f"{owner}:{head_branch}",
            "base": base_branch,
            "state": "open"
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        exists = len(response.json()) > 0
        print(f"[PULL_REQUEST_EXISTS] PR exists: {exists}")
        return exists
        
    except Exception as e:
        print(f"[PULL_REQUEST_EXISTS] Error checking PR in {repo}: {e}")
        return False


def create_branch(repo: str, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
    """
    Create a new branch in a GitHub repository.
    
    Args:
        repo: Repository in format 'owner/repo'
        branch_name: Name of new branch
        base_branch: Branch to base from (default: main)
        
    Returns:
        Dict containing branch data or error info
    """
    print(f"[CREATE_BRANCH] Creating branch {branch_name} in {repo} from {base_branch}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        base_url = f"https://api.github.com/repos/{repo}"
        
        # Get SHA of base branch
        base_ref_url = f"{base_url}/git/refs/heads/{base_branch}"
        base_response = requests.get(base_ref_url, headers=headers)
        base_response.raise_for_status()
        base_sha = base_response.json()["object"]["sha"]
        
        # Create new branch
        refs_url = f"{base_url}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }
        
        response = requests.post(refs_url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            'status': 'success',
            'data': result,
            'branch_name': branch_name,
            'base_sha': base_sha
        }
        
    except Exception as e:
        print(f"[CREATE_BRANCH] Error creating branch {branch_name} in {repo}: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def branch_exists(repo: str, branch_name: str) -> bool:
    """
    Check if a branch exists in a GitHub repository.
    
    Args:
        repo: Repository in format 'owner/repo'
        branch_name: Name of branch to check
        
    Returns:
        True if branch exists, False otherwise
    """
    print(f"[BRANCH_EXISTS] Checking if branch {branch_name} exists in {repo}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        url = f"https://api.github.com/repos/{repo}/git/refs/heads/{branch_name}"
        response = requests.get(url, headers=headers)
        exists = response.status_code == 200
        print(f"[BRANCH_EXISTS] Branch exists: {exists}")
        return exists
        
    except Exception as e:
        print(f"[BRANCH_EXISTS] Error checking branch {branch_name} in {repo}: {e}")
        return False 