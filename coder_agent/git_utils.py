"""
Git utilities for interacting with git repositories.

This module provides functions for git operations like cloning, committing,
and pushing changes to repositories.
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

def is_windows_platform() -> bool:
    """
    Check if the current platform is Windows.
    
    Returns:
        bool: True if running on Windows, False otherwise
    """
    return platform.system().lower() == 'windows'

def clone_repo(repo_url: str, target_path: Path, force: bool = False) -> Tuple[bool, str]:
    """
    Clone a Git repository to the specified path.
    
    Args:
        repo_url: The URL of the repository to clone
        target_path: The path where the repository should be cloned
        force: If True, remove existing directory before cloning
        
    Returns:
        Tuple[bool, str]: (success, message) - success status and descriptive message
    """
    is_windows = is_windows_platform()
    
    # Check if repository already exists
    if target_path.exists():
        if (target_path / ".git").exists() and not force:
            return True, f"Repository already exists at {target_path}"
        elif force:
            import shutil
            shutil.rmtree(target_path)
    
    try:
        print(f"Cloning repository {repo_url} to {target_path}...")
        subprocess.run(
            ["git", "clone", repo_url, str(target_path)],
            check=True,
            capture_output=True,
            text=True,
            shell=is_windows
        )
        
        abs_path = target_path.absolute()
        return True, f"Repository cloned successfully to {abs_path}"
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to clone repository: {e}"
        if e.stderr:
            error_msg += f"\nError details: {e.stderr}"
        return False, error_msg
    except Exception as e:
        return False, f"Unexpected error during cloning: {e}"

def get_current_branch(repo_path: Path) -> Tuple[bool, str]:
    """
    Get the name of the current branch in a git repository.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Tuple[bool, str]: (success, branch_name_or_error)
    """
    is_windows = is_windows_platform()
    
    if not (repo_path / ".git").exists():
        return False, f"No git repository found at {repo_path}"
    
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
            shell=is_windows,
            encoding='utf-8',
            errors='replace'
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Failed to get current branch: {e.stderr}"
    except Exception as e:
        return False, f"Unexpected error getting branch: {e}"

def switch_branch(repo_path: Path, branch_name: str, create_if_not_exists: bool = True) -> Tuple[bool, str]:
    """
    Switch to a specified branch in a git repository.
    
    Args:
        repo_path: Path to the git repository
        branch_name: Name of the branch to switch to
        create_if_not_exists: If True, create the branch if it doesn't exist
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    is_windows = is_windows_platform()
    
    if not (repo_path / ".git").exists():
        return False, f"No git repository found at {repo_path}"
    
    try:
        # First try to checkout the existing branch
        try:
            subprocess.run(
                ["git", "checkout", branch_name],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
                shell=is_windows
            )
            return True, f"Switched to branch '{branch_name}'"
        except subprocess.CalledProcessError:
            # Branch might not exist
            if create_if_not_exists:
                subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    check=True,
                    shell=is_windows
                )
                return True, f"Created and switched to branch '{branch_name}'"
            else:
                return False, f"Branch '{branch_name}' does not exist"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to switch branch: {e.stderr}"
    except Exception as e:
        return False, f"Unexpected error switching branch: {e}"

def get_changed_files(repo_path: Path) -> Tuple[bool, List[str]]:
    """
    Get a list of changed files in a git repository.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Tuple[bool, List[str]]: (success, list_of_changed_files)
    """
    is_windows = is_windows_platform()
    
    if not (repo_path / ".git").exists():
        return False, []
    
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
            shell=is_windows
        )
        
        files_changed = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                # Git status format: "XY filename" where X and Y are status codes
                file_path = line[3:].strip()  # Skip the first 3 characters (status + space)
                files_changed.append(file_path)
                
        return True, files_changed
    except subprocess.CalledProcessError as e:
        return False, []
    except Exception as e:
        return False, []

def stage_changes(repo_path: Path, files: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Stage changes in a git repository.
    
    Args:
        repo_path: Path to the git repository
        files: Optional list of specific files to stage. If None, stage all changes.
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    is_windows = is_windows_platform()
    
    if not (repo_path / ".git").exists():
        return False, f"No git repository found at {repo_path}"
    
    try:
        if files is None:
            # Stage all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=True,
                shell=is_windows
            )
            return True, "Staged all changes"
        else:
            # Stage specific files
            for file in files:
                subprocess.run(
                    ["git", "add", file],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    check=True,
                    shell=is_windows
                )
            return True, f"Staged {len(files)} specified files"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to stage changes: {e.stderr}"
    except Exception as e:
        return False, f"Unexpected error staging changes: {e}"

def commit_changes(
    repo_path: Path, 
    commit_message: str,
    author_name: Optional[str] = None,
    author_email: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Commit staged changes in a git repository.
    
    Args:
        repo_path: Path to the git repository
        commit_message: The commit message
        author_name: Optional git author name (uses git config if not provided)
        author_email: Optional git author email (uses git config if not provided)
        
    Returns:
        Tuple[bool, str, str]: (success, message, commit_sha)
    """
    is_windows = is_windows_platform()
    
    if not (repo_path / ".git").exists():
        return False, f"No git repository found at {repo_path}", ""
    
    try:
        # Set git author if provided
        git_env = os.environ.copy()
        if author_name:
            git_env["GIT_AUTHOR_NAME"] = author_name
            git_env["GIT_COMMITTER_NAME"] = author_name
        if author_email:
            git_env["GIT_AUTHOR_EMAIL"] = author_email
            git_env["GIT_COMMITTER_EMAIL"] = author_email
        
        # Commit changes
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
            shell=is_windows,
            env=git_env
        )
        
        # Get the commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
            shell=is_windows
        )
        commit_sha = sha_result.stdout.strip()
        
        return True, f"Committed changes: {commit_result.stdout.strip()}", commit_sha
    except subprocess.CalledProcessError as e:
        return False, f"Failed to commit changes: {e.stderr}", ""
    except Exception as e:
        return False, f"Unexpected error committing changes: {e}", ""

def push_changes(repo_path: Path, branch_name: str, remote: str = "origin") -> Tuple[bool, str]:
    """
    Push committed changes to a remote repository.
    
    Args:
        repo_path: Path to the git repository
        branch_name: The name of the branch to push
        remote: The name of the remote (default: "origin")
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    is_windows = is_windows_platform()
    
    if not (repo_path / ".git").exists():
        return False, f"No git repository found at {repo_path}"
    
    try:
        push_result = subprocess.run(
            ["git", "push", remote, branch_name],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
            shell=is_windows
        )
        
        return True, f"Pushed to {remote}/{branch_name}: {push_result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to push changes: {e.stderr}"
    except Exception as e:
        return False, f"Unexpected error pushing changes: {e}" 