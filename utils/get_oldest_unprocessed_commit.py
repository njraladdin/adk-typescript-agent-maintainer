from typing import Dict, Any, List, Optional, TypedDict
import os
import sys

# Add parent directory to Python path when running directly
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.get_repo_commits import get_repo_commits
from utils.get_repo_issues import get_repo_issues
from utils.get_commit_diff import get_commit_diff, CommitDiffResponse

class UnprocessedCommitInfo(TypedDict):
    """Represents an unprocessed commit with its diff information"""
    commit: Dict[str, Any]
    diff: CommitDiffResponse

def get_oldest_unprocessed_commit(
    python_username: str = "google",
    python_repo: str = "adk-python",
    ts_username: str = "njraladdin",
    ts_repo: str = "adk-typescript",
    max_items: int = 10
) -> Optional[UnprocessedCommitInfo]:
    """
    Finds the oldest unprocessed commit from the Python repo by checking against TypeScript repo issues.
    A commit is considered processed if there exists an issue with [commit:<commit_sha>] in its title.
    Also fetches the diff information for the unprocessed commit.

    Args:
        python_username (str): Username of Python repo owner
        python_repo (str): Python repository name
        ts_username (str): Username of TypeScript repo owner
        ts_repo (str): TypeScript repository name
        max_items (int): Maximum number of items to check

    Returns:
        Optional[UnprocessedCommitInfo]: The oldest unprocessed commit with its diff info, or None if all are processed
    """
    # Get recent commits from Python repo
    commits = get_repo_commits(python_username, python_repo, max_items)
    
    # Get recent issues from TypeScript repo
    issues = get_repo_issues(ts_username, ts_repo, state="all", count=max_items)
    
    # Create a set of processed commit IDs from issue titles
    processed_commits = set()
    for issue in issues:
        title = issue["title"]
        if "[commit:" in title and "]" in title:
            # Extract commit ID from title
            start = title.find("[commit:") + 8
            end = title.find("]", start)
            if start > 7 and end > start:  # Ensure we found valid markers
                commit_id = title[start:end]
                processed_commits.add(commit_id)
    
    # Find the oldest unprocessed commit
    for commit in reversed(commits):  # Reverse to get oldest first
        commit_sha = commit["sha"][:7]  # Use first 7 chars of SHA
        if commit_sha not in processed_commits:
            # Get the diff information for this commit
            diff_info = get_commit_diff(python_username, python_repo, commit["sha"])
            return {
                "commit": commit,
                "diff": diff_info
            }
            
    return None

if __name__ == "__main__":
    # Example usage
    result = get_oldest_unprocessed_commit()
    if result:
        commit = result["commit"]
        diff = result["diff"]
        commit_sha = commit["sha"][:7]
        commit_msg = commit["commit"]["message"].split("\n")[0]  # First line of commit message
        print(f"Found unprocessed commit: {commit_sha} - {commit_msg}")
        print(f"Changes: +{diff['total_additions']}, -{diff['total_deletions']} in {diff['total_files_changed']} files")
        print("\nFiles changed:")
        for file in diff["files"]:
            print(f"\n{file['file']} ({file['status']}):")
            print(f"  +{file['additions']}, -{file['deletions']}")
            if file['excerpt']:
                print("  Excerpt:")
                for line in file['excerpt']:
                    print(f"    {line}")
    else:
        print("No unprocessed commits found") 