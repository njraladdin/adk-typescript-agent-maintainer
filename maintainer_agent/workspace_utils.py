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
from typing import Optional, Tuple, List, Dict, Any

from .constants import AGENT_WORKSPACE_DIR, TYPESCRIPT_REPO_DIR, TYPESCRIPT_REPO_URL
from .git_cli_utils import clone_repo, is_windows_platform


def get_npm_command() -> str:
    """
    Get the appropriate npm command based on the current platform.
    
    Returns:
        str: The npm command to use ('npm.cmd' on Windows, 'npm' otherwise)
    """
    is_windows = is_windows_platform()
    return "npm.cmd" if is_windows else "npm"


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
            shell=is_windows,
            encoding='utf-8',
            errors='replace'
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
            shell=is_windows,
            encoding='utf-8',
            errors='replace'
        )
        if node_version_result.returncode == 0:
            print(f"Node.js version: {node_version_result.stdout.strip()}")
        
        npm_version_result = subprocess.run(
            [npm_cmd, "--version"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            shell=is_windows,
            encoding='utf-8',
            errors='replace'
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
            shell=is_windows,
            encoding='utf-8',
            errors='replace'
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
    setup_status = check_workspace_setup_status(workspace_path)
    return setup_status["all_steps_completed"]


def run_tests(project_path: Path, test_names: List[str]) -> Dict[str, Any]:
    """
    Run tests for a Node.js/TypeScript project using npm test.
    
    Args:
        project_path: Path to the project directory
        test_names: List of test file names to run (Jest will auto-discover by filename)
        
    Returns:
        dict: {
            "success": bool,
            "message": str,
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "test_results": dict
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
            "exit_code": -1,
            "test_results": {}
        }
    
    try:
        test_script = "test"  # Hardcoded to "test"
        print(f"Running tests using {npm_cmd} run {test_script}...")
        print(f"Working directory: {project_path}")
        print(f"Test names: {test_names}")
        
        # Build the test command
        cmd = [npm_cmd, "run", test_script] + test_names
        
        # Run the tests
        result = subprocess.run(
            cmd,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            shell=is_windows,
            timeout=300,  # 5 minute timeout
            encoding='utf-8',
            errors='replace'  # Replace problematic characters instead of failing
        )
        
        success = result.returncode == 0
        message = "Tests completed successfully" if success else f"Tests failed with exit code {result.returncode}"
        
        # Parse test results from both stdout and stderr
        combined_output = (result.stdout or "") + "\n" + (result.stderr or "")
        test_results = _parse_test_output(combined_output)
        
        return {
            "success": success,
            "message": message,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "exit_code": result.returncode,
            "test_results": test_results
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Test execution timed out after 5 minutes",
            "stdout": "",
            "stderr": "Timeout expired",
            "exit_code": -2,
            "test_results": {}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to run tests: {str(e)}",
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "test_results": {}
        }


def setup_typescript_repository_environment(project_path: Path) -> Tuple[bool, str]:
    """
    Setup environment variables for the TypeScript repository by creating a .env file.
    
    This reads environment variables from the system environment
    and creates a .env file in the TypeScript repository with the required variables.
    
    Args:
        project_path: Path to the TypeScript repository directory
        
    Returns:
        Tuple[bool, str]: (success, message) - success status and descriptive message
    """
    try:
        print(f"Setting up TypeScript repository environment at {project_path}...")
        
        # Get environment variables directly from system environment
        env_vars = {
            'GOOGLE_GENAI_USE_VERTEXAI': os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'TRUE'),
            'GOOGLE_CLOUD_PROJECT': os.getenv('GOOGLE_CLOUD_PROJECT', 'progress-tracker-e27a5'),
            'GOOGLE_CLOUD_LOCATION': os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
        }
        
        # Create .env file in the repository
        env_path = project_path / ".env"
        env_content = ""
        
        for key, value in env_vars.items():
            env_content += f"{key}={value}\n"
        
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print(f"Created .env file at {env_path}")
        for key, value in env_vars.items():
            display_value = '***' if 'key' in key.lower() or 'secret' in key.lower() or 'token' in key.lower() else value
            print(f"  {key}={display_value}")
        
        return True, f"TypeScript repository environment set up successfully at {env_path}"
        
    except Exception as e:
        error_msg = f"Failed to setup TypeScript repository environment: {e}"
        print(error_msg)
        return False, error_msg


def check_workspace_setup_status(workspace_path: Optional[Path] = None) -> Dict[str, bool]:
    """
    Check the status of each step in the workspace setup process.
    
    This function checks if each of the following steps has been completed:
    1. Workspace directory exists
    2. Repository has been cloned
    3. Dependencies have been installed (node_modules exists)
    4. Project has been built (dist folder exists)
    5. Environment has been set up (.env file exists)
    
    Args:
        workspace_path: Optional custom workspace path. If None, uses default.
        
    Returns:
        Dict[str, bool]: Dictionary with the status of each step
    """
    if workspace_path is None:
        workspace_path = Path(AGENT_WORKSPACE_DIR)
    
    typescript_repo_path = get_typescript_repo_path(workspace_path)
    
    # Check each step in the setup process
    workspace_exists = workspace_path.exists()
    
    repo_cloned = False
    if workspace_exists:
        repo_cloned = typescript_repo_path.exists() and (typescript_repo_path / ".git").exists() and (typescript_repo_path / "package.json").exists()
    
    dependencies_installed = False
    if repo_cloned:
        dependencies_installed = (typescript_repo_path / "node_modules").exists()
    
    project_built = False
    if repo_cloned:
        project_built = (typescript_repo_path / "dist").exists()
    
    env_setup = False
    if repo_cloned:
        env_setup = (typescript_repo_path / ".env").exists()
    
    return {
        "workspace_exists": workspace_exists,
        "repo_cloned": repo_cloned,
        "dependencies_installed": dependencies_installed,
        "project_built": project_built,
        "env_setup": env_setup,
        "all_steps_completed": workspace_exists and repo_cloned and dependencies_installed and project_built and env_setup
    }


def read_local_files(file_paths: List[str], workspace_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """
    Read multiple files from the local TypeScript repository.
    
    Args:
        file_paths: List of file paths relative to the TypeScript repository root
        workspace_path: Optional custom workspace path. If None, uses default.
        
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping file paths to their content and metadata.
                                  Only includes successfully read files.
    """
    if workspace_path is None:
        workspace_path = Path(AGENT_WORKSPACE_DIR)
    
    typescript_repo_path = get_typescript_repo_path(workspace_path)
    
    if not typescript_repo_path.exists():
        print(f"TypeScript repository not found at {typescript_repo_path}")
        return {}
    
    files = {}
    
    for file_path in file_paths:
        try:
            full_path = typescript_repo_path / file_path
            
            if not full_path.exists():
                print(f"File not found: {file_path}")
                continue
            
            if not full_path.is_file():
                print(f"Path is not a file: {file_path}")
                continue
            
            # Read file content
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Get file metadata
            stat = full_path.stat()
            metadata = {
                'name': full_path.name,
                'size': stat.st_size,
                'path': file_path,
                'full_path': str(full_path)
            }
            
            files[file_path] = {
                'content': content,
                'metadata': metadata
            }
            
            print(f"Successfully read local file: {file_path} ({metadata['size']} bytes)")
            
        except Exception as e:
            print(f"Error reading local file {file_path}: {e}")
            continue
    
    return files


def _parse_test_output(stdout: str) -> Dict[str, Any]:
    """
    Parse test output to extract useful information.
    
    Args:
        stdout: The stdout from the test run
        
    Returns:
        Dict containing parsed test results
    """
    test_results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "skipped_tests": 0,
        "test_files": [],
        "errors": []
    }
    
    try:
        lines = stdout.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Jest-specific patterns
            # Look for "Tests: X passed, Y failed, Z total" format
            if line.startswith('Tests:'):
                import re
                # Extract numbers with their context
                passed_match = re.search(r'(\d+)\s+passed', line)
                failed_match = re.search(r'(\d+)\s+failed', line) 
                total_match = re.search(r'(\d+)\s+total', line)
                skipped_match = re.search(r'(\d+)\s+skipped', line)
                
                if passed_match:
                    test_results["passed_tests"] = int(passed_match.group(1))
                if failed_match:
                    test_results["failed_tests"] = int(failed_match.group(1))
                if total_match:
                    test_results["total_tests"] = int(total_match.group(1))
                if skipped_match:
                    test_results["skipped_tests"] = int(skipped_match.group(1))
            
            # Look for "Test Suites: X passed, Y total" format
            elif line.startswith('Test Suites:'):
                # This gives us info about test suites, but we focus on individual tests
                pass
            
            # Look for PASS/FAIL indicators with test file names
            elif line.startswith('PASS ') or line.startswith('FAIL '):
                import re
                # Extract test file names from PASS/FAIL lines
                matches = re.findall(r'[\w/.-]+\.(?:test|spec)\.\w+', line)
                test_results["test_files"].extend(matches)
            
            # Look for test file references in other contexts
            elif '.test.' in line or '.spec.' in line:
                import re
                matches = re.findall(r'[\w/.-]+\.(?:test|spec)\.\w+', line)
                test_results["test_files"].extend(matches)
            
            # Look for error indicators
            elif any(keyword in line.lower() for keyword in ['error:', 'failed:', 'exception:', '✕', '×']):
                test_results["errors"].append(line)
        
        # If we didn't get total_tests from parsing, calculate it
        if test_results["total_tests"] == 0:
            test_results["total_tests"] = test_results["passed_tests"] + test_results["failed_tests"] + test_results["skipped_tests"]
        
        # Remove duplicates from test files
        test_results["test_files"] = list(set(test_results["test_files"]))
        
    except Exception as e:
        print(f"Failed to parse test output: {e}")
    
    return test_results 