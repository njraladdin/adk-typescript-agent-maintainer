"""
GitHub API utilities for interacting with GitHub repositories.

This module provides functions for GitHub API operations like fetching
commit data, repository structure, and file content from remote repositories.
"""

import os
import requests
import re
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List, TypedDict, Literal


class FileDiff(TypedDict):
    """Represents a structured diff for a file"""
    file: str
    changed_lines: int
    excerpt: List[str]
    additions: int
    deletions: int
    is_binary: bool
    status: Literal['modified', 'added', 'deleted', 'renamed']


class CommitDiffResponse(TypedDict):
    """Represents a structured commit diff"""
    files: List[FileDiff]
    total_additions: int
    total_deletions: int
    total_files_changed: int


def parse_diff(raw_diff: str, max_excerpt_lines: int) -> CommitDiffResponse:
    """
    Parse a raw git diff into a structured format.
    
    Args:
        raw_diff: The raw diff string from GitHub API
        max_excerpt_lines: Maximum number of lines to include in the excerpt
    
    Returns:
        Structured diff object
    """
    files: List[FileDiff] = []
    total_additions = 0
    total_deletions = 0
    
    # Split the diff by file sections (diff --git lines)
    file_patterns = raw_diff.split('\ndiff --git ')
    
    # First element might be empty or contain some header information
    file_sections = ['diff --git ' + file_patterns[0]] if file_patterns[0].strip() else []
    
    # Add the rest of the file sections with the diff --git prefix restored
    file_sections.extend(f'diff --git {pattern}' for pattern in file_patterns[1:])
    
    for section in file_sections:
        if not section.startswith('diff --git'):
            continue
        
        # Extract filenames from the section
        file_name_match = re.search(r'diff --git a/(.*?) b/(.*?)(\n|$)', section)
        if not file_name_match:
            continue
        
        from_file = file_name_match.group(1)
        to_file = file_name_match.group(2)
        
        # Determine file status
        status: Literal['modified', 'added', 'deleted', 'renamed'] = 'modified'
        file_name = to_file
        
        if 'new file mode' in section:
            status = 'added'
            file_name = to_file
        elif 'deleted file mode' in section:
            status = 'deleted'
            file_name = from_file
        elif from_file != to_file:
            status = 'renamed'
            file_name = to_file
        
        is_binary = 'Binary files' in section or 'GIT binary patch' in section
        
        if is_binary:
            files.append({
                'file': file_name,
                'changed_lines': 0,
                'excerpt': ['Binary file changed'],
                'additions': 0,
                'deletions': 0,
                'is_binary': True,
                'status': status
            })
            continue
        
        # Extract the actual diff content - everything after the first @@ line
        hunks = re.findall(r'@@.*?@@.*?(?=(?:\n@@|\n?$))', section, re.DOTALL)
        
        # If no hunks were found, try a different approach
        diff_content = ''
        if not hunks:
            header_end_index = section.find('\n+++')
            if header_end_index != -1:
                first_hunk_index = section.find('@@', header_end_index)
                if first_hunk_index != -1:
                    diff_content = section[first_hunk_index:]
        else:
            diff_content = '\n'.join(hunks)
        
        if not diff_content:
            continue
        
        # Process the diff content
        lines = [line for line in diff_content.split('\n') if line]
        
        # Count additions and deletions
        added_lines = sum(1 for line in lines if line.startswith('+'))
        removed_lines = sum(1 for line in lines if line.startswith('-'))
        
        total_additions += added_lines
        total_deletions += removed_lines
        
        # Get changed lines (lines starting with + or -)
        changed_lines = [line for line in lines if line.startswith('+') or line.startswith('-')]
        
        # Maximum line length to include in excerpt
        MAX_LINE_LENGTH = 500
        
        # Create the excerpt with trimmed lines
        excerpt: List[str] = []
        
        # Check if we have any very large lines in this file
        has_very_large_lines = any(len(line) > 3000 for line in changed_lines)
        
        # Process all changed lines up to max_excerpt_lines
        for line in changed_lines[:max_excerpt_lines]:
            if len(line) <= MAX_LINE_LENGTH:
                excerpt.append(line)
            else:
                # For long lines, trim them and add information about how much is trimmed
                prefix = line[0]  # Keep the + or - prefix
                remaining_chars = len(line) - MAX_LINE_LENGTH
                
                # Format large numbers with commas for readability
                formatted_length = f"{len(line):,}"
                formatted_remaining = f"{remaining_chars:,}"
                
                excerpt.append(f"{prefix}{line[1:MAX_LINE_LENGTH]}... [trimmed {formatted_remaining} chars from {formatted_length} char line]")
        
        # Add ellipsis if there are more lines than what we included
        if len(changed_lines) > max_excerpt_lines:
            excerpt.append(f"... ({len(changed_lines) - max_excerpt_lines} more lines)")
        
        files.append({
            'file': file_name,
            'changed_lines': added_lines + removed_lines,
            'excerpt': excerpt,
            'additions': added_lines,
            'deletions': removed_lines,
            'is_binary': False,
            'status': status
        })
    
    return {
        'files': files,
        'total_additions': total_additions,
        'total_deletions': total_deletions,
        'total_files_changed': len(files)
    }


def get_github_token() -> Optional[str]:
    """
    Get GitHub token from environment variables.
    
    Returns:
        Optional[str]: GitHub token if found, None otherwise
    """
    return os.getenv("GITHUB_TOKEN")


def fetch_commit_message(commit_sha: str, repo: str = "google/adk-python") -> str:
    """
    Fetch commit message from a GitHub repository.
    
    Args:
        commit_sha: The commit SHA to fetch message for
        repo: Repository in format 'owner/repo' (default: google/adk-python)
        
    Returns:
        Commit message string
    """
    print(f"[FETCH_COMMIT_MESSAGE] Fetching commit message for {commit_sha} from {repo}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        response = requests.get(
            f"https://api.github.com/repos/{repo}/commits/{commit_sha}",
            headers=headers
        )
        response.raise_for_status()
        commit_data = response.json()
        return commit_data.get('commit', {}).get('message', 'Unknown commit')
    except Exception as e:
        print(f"[FETCH_COMMIT_MESSAGE] Error: {e}")
        return "Unknown commit"


def fetch_commit_diff_raw(repo: str, commit_sha: str) -> str:
    """
    Fetch raw commit diff from GitHub API.
    
    Args:
        repo: Repository in format 'owner/repo'
        commit_sha: The commit hash to get the diff for
        
    Returns:
        Raw diff string from GitHub API
        
    Raises:
        requests.exceptions.RequestException: If the request fails
    """
    print(f"[FETCH_COMMIT_DIFF_RAW] Fetching commit diff for {commit_sha} from {repo}")
    
    github_token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3.diff"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        response = requests.get(
            f"https://api.github.com/repos/{repo}/commits/{commit_sha}",
            headers=headers
        )
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[FETCH_COMMIT_DIFF_RAW] Error fetching commit diff: {e}")
        raise


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


def fetch_file_with_metadata(repo: str, file_path: str, branch: str, github_token: str) -> tuple[str, Dict[str, Any]]:
    """
    Fetch a single file with full metadata from GitHub API.
    
    Args:
        repo: Repository in format 'owner/repo'
        file_path: Path to the file
        branch: Branch name
        github_token: GitHub authentication token
    
    Returns:
        tuple: (file_path, result_dict) where result_dict contains either success or error info
    """
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {'ref': branch} if branch else {}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle file content decoding
            if data.get('encoding') == 'base64':
                content = base64.b64decode(data['content']).decode('utf-8')
            else:
                content = data.get('content', '')
            
            # Create metadata structure
            metadata = {
                'name': file_path.split('/')[-1],
                'path': file_path,
                'size': len(content.encode('utf-8')),
                'type': 'file',
                'sha': data.get('sha', ''),
                'encoding': data.get('encoding', ''),
                'url': data.get('url', ''),
                'html_url': data.get('html_url', ''),
                'git_url': data.get('git_url', ''),
                'download_url': data.get('download_url', '')
            }
            
            return file_path, {
                'status': 'success',
                'content': content,
                'metadata': metadata
            }
        else:
            return file_path, {
                'status': 'error',
                'message': f"HTTP {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return file_path, {
            'status': 'error',
            'message': f"Exception fetching {file_path}: {str(e)}"
        }


def fetch_multiple_files_content(repo: str, file_paths: List[str], branch: str = "main") -> Dict[str, Dict[str, Any]]:
    """
    Fetch multiple files concurrently from a GitHub repository using ThreadPoolExecutor.
    
    Args:
        repo: Repository in format 'owner/repo'
        file_paths: List of file paths to fetch
        branch: Branch name (default: main)
        
    Returns:
        Dict mapping file_path to result dict containing content and metadata
    """
    print(f"[FETCH_MULTIPLE_FILES] Fetching {len(file_paths)} files concurrently from {repo}")
    
    github_token = get_github_token()
    if not github_token:
        print("[FETCH_MULTIPLE_FILES] Error: GitHub token not found")
        return {file_path: {'status': 'error', 'message': 'GitHub token not found'} for file_path in file_paths}
    
    file_results = {}
    
    # Use ThreadPoolExecutor for concurrent fetching
    with ThreadPoolExecutor(max_workers=min(len(file_paths), 10)) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(fetch_file_with_metadata, repo, file_path, branch, github_token): file_path
            for file_path in file_paths
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                _, result = future.result()
                file_results[file_path] = result
                
                if result['status'] != 'success':
                    print(f"[FETCH_MULTIPLE_FILES] Failed to fetch {file_path}: {result['message']}")
                    
            except Exception as exc:
                file_results[file_path] = {
                    'status': 'error',
                    'message': f"Exception occurred: {str(exc)}"
                }
                print(f"[FETCH_MULTIPLE_FILES] Exception fetching {file_path}: {exc}")
    
    successful = sum(1 for r in file_results.values() if r['status'] == 'success')
    print(f"[FETCH_MULTIPLE_FILES] Completed: {successful}/{len(file_paths)} files fetched successfully")
    
    return file_results


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