"""
Workspace utilities for managing the agent workspace and TypeScript repository.

This module provides functions for setting up, managing, and working with
the agent workspace including repository cloning, dependency installation,
and project building.
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple

from .constants import AGENT_WORKSPACE_DIR, TYPESCRIPT_REPO_DIR, TYPESCRIPT_REPO_URL


def get_npm_command() -> str:
    """
    Get the appropriate npm command based on the current platform.
    
    Returns:
        str: The npm command to use ('npm.cmd' on Windows, 'npm' otherwise)
    """
    is_windows = platform.system().lower() == 'windows'
    return "npm.cmd" if is_windows else "npm"


def is_windows_platform() -> bool:
    """
    Check if the current platform is Windows.
    
    Returns:
        bool: True if running on Windows, False otherwise
    """
    return platform.system().lower() == 'windows'


def create_workspace_directory(workspace_path: Optional[Path] = None) -> Path:
    """
    Create the agent workspace directory if it doesn't exist.
    
    Args:
        workspace_path: Optional custom workspace path. If None, uses default from constants.
        
    Returns:
        Path: The workspace directory path
    """
    if workspace_path is None:
        workspace_path = Path(AGENT_WORKSPACE_DIR)
    
    workspace_path.mkdir(exist_ok=True, parents=True)
    return workspace_path


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


def install_dependencies(project_path: Path, npm_flags: Optional[list] = None) -> Tuple[bool, str]:
    """
    Install npm dependencies for a Node.js/TypeScript project.
    
    Args:
        project_path: Path to the project directory containing package.json
        npm_flags: Optional list of additional npm flags (default: ["--ignore-scripts"])
        
    Returns:
        Tuple[bool, str]: (success, message) - success status and descriptive message
    """
    if npm_flags is None:
        npm_flags = ["--ignore-scripts"]
    
    npm_cmd = get_npm_command()
    is_windows = is_windows_platform()
    
    if not (project_path / "package.json").exists():
        return False, f"No package.json found in {project_path}"
    
    try:
        print(f"Installing dependencies using {npm_cmd}...")
        cmd = [npm_cmd, "install"] + npm_flags
        
        subprocess.run(
            cmd,
            cwd=str(project_path),
            check=True,
            capture_output=True,
            text=True,
            shell=is_windows
        )
        
        return True, "Dependencies installed successfully"
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to install dependencies (exit code {e.returncode})"
        if e.stdout:
            error_msg += f"\nStdout: {e.stdout}"
        if e.stderr:
            error_msg += f"\nStderr: {e.stderr}"
        return False, error_msg
    except Exception as e:
        return False, f"Unexpected error during dependency installation: {e}"


def build_project(project_path: Path, build_script: str = "build") -> dict:
    """
    Build a Node.js/TypeScript project using npm run build.
    
    Args:
        project_path: Path to the project directory
        build_script: The npm script to run (default: "build")
        
    Returns:
        dict: {
            "success": bool,
            "message": str,
            "stdout": str,
            "stderr": str,
            "exit_code": int
        }
    """
    npm_cmd = get_npm_command()
    is_windows = is_windows_platform()
    
    if not (project_path / "package.json").exists():
        return {
            "success": False,
            "message": f"No package.json found in {project_path}",
            "stdout": "",
            "stderr": "",
            "exit_code": -1
        }
    
    try:
        print(f"Building project using {npm_cmd} run {build_script}...")
        print(f"Working directory: {project_path}")
        
        # Log environment information for debugging
        node_version_result = subprocess.run(
            ["node", "--version"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            shell=is_windows
        )
        if node_version_result.returncode == 0:
            print(f"Node.js version: {node_version_result.stdout.strip()}")
        
        npm_version_result = subprocess.run(
            [npm_cmd, "--version"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            shell=is_windows
        )
        if npm_version_result.returncode == 0:
            print(f"npm version: {npm_version_result.stdout.strip()}")
        
        # Run the build
        result = subprocess.run(
            [npm_cmd, "run", build_script],
            cwd=str(project_path),
            check=True,
            capture_output=True,
            text=True,
            shell=is_windows
        )
        
        return {
            "success": True,
            "message": f"Project built successfully using '{build_script}' script",
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "exit_code": result.returncode
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "message": f"Failed to build project (exit code {e.returncode})",
            "stdout": e.stdout or "",
            "stderr": e.stderr or "", 
            "exit_code": e.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error during build: {e}",
            "stdout": "",
            "stderr": "",
            "exit_code": -1
        }





def get_typescript_repo_path(workspace_path: Optional[Path] = None) -> Path:
    """
    Get the path to the TypeScript repository within the workspace.
    
    Args:
        workspace_path: Optional custom workspace path. If None, uses default.
        
    Returns:
        Path: The path to the TypeScript repository
    """
    if workspace_path is None:
        workspace_path = Path(AGENT_WORKSPACE_DIR)
    
    return workspace_path / TYPESCRIPT_REPO_DIR


def is_typescript_repo_ready(workspace_path: Optional[Path] = None) -> bool:
    """
    Check if the TypeScript repository is cloned and ready for use.
    
    Args:
        workspace_path: Optional custom workspace path. If None, uses default.
        
    Returns:
        bool: True if the repository exists and appears to be properly set up
    """
    typescript_repo_path = get_typescript_repo_path(workspace_path)
    
    # Check if the directory exists and has .git folder
    if not typescript_repo_path.exists() or not (typescript_repo_path / ".git").exists():
        return False
    
    # Check if package.json exists (indicates it's a Node.js project)
    if not (typescript_repo_path / "package.json").exists():
        return False
    
    # Check if node_modules exists (indicates dependencies are installed)
    if not (typescript_repo_path / "node_modules").exists():
        return False
    
    return True 