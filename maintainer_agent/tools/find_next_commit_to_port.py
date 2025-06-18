from typing import Dict, Any, List, Optional, TypedDict, Tuple
import os
import sys

# Add parent directory to Python path when running directly
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.get_repo_commits import get_repo_commits
from utils.get_repo_issues import get_repo_issues
from utils.get_commit_diff import get_commit_diff, CommitDiffResponse
from utils.get_file_content_from_repo import get_file_content_from_repo

class FileWithContent(TypedDict):
    """Represents a file change with its content"""
    file: str
    status: str
    additions: int
    deletions: int
    is_binary: bool
    excerpt: List[str]
    full_file_content: Optional[str]  # The complete file content at this commit

class CommitToPort(TypedDict):
    """Represents a commit that needs to be ported from Python to TypeScript, including its diff information"""
    commit: Dict[str, Any]  # The commit data from GitHub API
    files: List[FileWithContent]  # List of changed files with their content
    total_additions: int
    total_deletions: int
    total_files_changed: int

def find_next_commit_to_port(
    python_username: str = "google",
    python_repo: str = "adk-python",
    ts_username: str = "njraladdin",
    ts_repo: str = "adk-typescript",
    max_items: int = 10
) -> Tuple[Optional[CommitToPort], Optional[str]]:
    """
    Finds the next commit from the Python repo that needs to be ported to TypeScript.
    A commit needs porting if there is no corresponding issue in the TypeScript repo
    with [commit:<commit_sha>] in its title.

    Args:
        python_username (str): Username of Python repo owner
        python_repo (str): Python repository name
        ts_username (str): Username of TypeScript repo owner
        ts_repo (str): TypeScript repository name
        max_items (int): Maximum number of items to check

    Returns:
        Tuple[Optional[CommitToPort], Optional[str]]: A tuple containing:
            - The next commit to port with its diff info and file contents, or None if no commits need porting
            - An error message if there was an error, or None if successful
    """
    # Get recent commits from Python repo (newest first)
    commits = get_repo_commits(python_username, python_repo, max_items)
    if commits is None:
        return None, f"Failed to fetch commits from {python_username}/{python_repo}"
    
    if not commits:
        return None, None  # No commits found, but no error
    
    # Get recent issues from TypeScript repo
    issues = get_repo_issues(ts_username, ts_repo, state="all", count=max_items)
    if issues is None:
        return None, f"Failed to fetch issues from {ts_username}/{ts_repo}"
    
    # Create a set of processed commit IDs from issue titles
    processed_commits = set()
    for issue in issues:
        title = issue["title"]
        # Look for both short and full SHA formats
        if "[commit:" in title and "]" in title:
            start = title.find("[commit:") + 8
            end = title.find("]", start)
            if start > 7 and end > start:
                commit_id = title[start:end].strip()
                # Add both full SHA and short SHA to processed set
                processed_commits.add(commit_id)
                processed_commits.add(commit_id[:7])
    
    # Reverse commits to get oldest first
    commits.reverse()
    
    # Find the first (oldest) commit that hasn't been processed
    for commit in commits:
        commit_sha = commit["sha"]
        commit_sha_short = commit_sha[:7]
        
        if commit_sha not in processed_commits and commit_sha_short not in processed_commits:
            # Found an unprocessed commit - get its diff
            diff_info = get_commit_diff(python_username, python_repo, commit_sha)
            if diff_info is None:
                return None, f"Failed to fetch diff for commit {commit_sha}"
            
            # Prepare files with content
            files_with_content: List[FileWithContent] = []
            for file_diff in diff_info["files"]:
                file_path = file_diff["file"]
                file_status = file_diff["status"]
                
                # Get the full file content at this commit
                full_file_content = None
                if file_status != 'deleted':  # Don't fetch content for deleted files
                    try:
                        full_file_content = get_file_content_from_repo(python_username, python_repo, file_path, commit_sha)
                    except Exception:
                        # If we can't get the file content, just continue with None
                        pass
                
                files_with_content.append({
                    "file": file_path,
                    "status": file_status,
                    "additions": file_diff["additions"],
                    "deletions": file_diff["deletions"],
                    "is_binary": file_diff["is_binary"],
                    "excerpt": file_diff["excerpt"],
                    "full_file_content": full_file_content
                })
            
            return {
                "commit": commit,
                "files": files_with_content,
                "total_additions": diff_info["total_additions"],
                "total_deletions": diff_info["total_deletions"],
                "total_files_changed": diff_info["total_files_changed"]
            }, None
            
    return None, None  # No unprocessed commits found, but no error

if __name__ == "__main__":
    # Example usage
    result, error = find_next_commit_to_port()
    if error:
        print(f"Error: {error}")
    elif result:
        commit = result["commit"]
        commit_sha = commit["sha"]
        commit_msg = commit["commit"]["message"].split("\n")[0]  # First line of commit message
        print(f"Found commit to port: {commit_sha} - {commit_msg}")
        print(f"Changes: +{result['total_additions']}, -{result['total_deletions']} in {result['total_files_changed']} files")
        print("\nFiles changed:")
        for file in result["files"]:
            print(f"\n{file['file']} ({file['status']}):")
            print(f"  +{file['additions']}, -{file['deletions']}")
            
            # Print full file content if available
            if file['full_file_content'] is not None:
                print("\n  Full file content:")
                print("  " + "\n  ".join(file['full_file_content'].splitlines()[:20]))
                if len(file['full_file_content'].splitlines()) > 20:
                    print("  ... (truncated)")
            
            # Print excerpt if no content is available
            elif file['excerpt']:
                print("  Excerpt of changes:")
                for line in file['excerpt']:
                    print(f"    {line}")
    else:
        print("No commits need porting at this time") 