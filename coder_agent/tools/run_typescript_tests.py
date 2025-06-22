import os
from typing import List, Dict, Any
from pathlib import Path
from google.adk.tools import ToolContext

# Import workspace utilities
from ..workspace_utils import run_tests, get_typescript_repo_path, is_typescript_repo_ready
from ..constants import AGENT_WORKSPACE_DIR


def run_typescript_tests(
    test_paths: List[str],
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Run TypeScript tests using npm.
    
    This tool runs the specified tests using npm test. The environment setup
    (creating .env file) should already be done during workspace setup.
    
    Args:
        test_paths (List[str]): List of test file paths starting from src/
        tool_context (ToolContext): Automatically injected by ADK for state access
    
    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - message: str (Success/error message)
            - stdout: str (Test output)
            - stderr: str (Error output if any)
            - exit_code: int (Process exit code)
            - repo_path: str (Path to the TypeScript repository)
            - test_results: Dict (Parsed test results if available)
    """
    print(f"[RUN_TYPESCRIPT_TESTS] Running tests for {len(test_paths)} files")
    
    try:
        # Get the TypeScript repository path
        if tool_context and 'typescript_repo_path' in tool_context.state:
            typescript_repo_path = Path(tool_context.state['typescript_repo_path'])
            print(f"[RUN_TYPESCRIPT_TESTS] Using TypeScript repository path from tool context: {typescript_repo_path}")
        else:
            typescript_repo_path = get_typescript_repo_path()
            print(f"[RUN_TYPESCRIPT_TESTS] Using default TypeScript repository path: {typescript_repo_path}")
        
        # Check if the repository is ready
        if not is_typescript_repo_ready():
            error_result = {
                "status": "error",
                "message": f"TypeScript repository at {typescript_repo_path} is not ready. Please run setup_agent_workspace first.",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "repo_path": str(typescript_repo_path),
                "test_results": {}
            }
            print(f"[RUN_TYPESCRIPT_TESTS] : output status=error, message={error_result['message']}")
            return error_result
        
        # Convert test paths to full paths
        full_test_paths = _convert_test_paths(test_paths, typescript_repo_path)
        print(f"[RUN_TYPESCRIPT_TESTS] Full test paths: {full_test_paths}")
        
        # Run the tests using workspace utility
        test_result = run_tests(typescript_repo_path, full_test_paths)
        
        # Format the result
        result = {
            "status": "success" if test_result["success"] else "error",
            "message": test_result["message"],
            "stdout": test_result["stdout"],
            "stderr": test_result["stderr"],
            "exit_code": test_result["exit_code"],
            "repo_path": str(typescript_repo_path),
            "test_results": test_result["test_results"]
        }
        
        # Log the output
        status = "success" if test_result["success"] else "error"
        print(f"[RUN_TYPESCRIPT_TESTS] : output status={status}, exit_code={test_result['exit_code']}")
        
        if status == "error":
            print(f"[RUN_TYPESCRIPT_TESTS] : error message={test_result['message']}")
            print(f"[RUN_TYPESCRIPT_TESTS] : stderr=\n{test_result['stderr']}")
        
        return result
        
    except Exception as error:
        error_result = {
            "status": "error",
            "message": f"Unexpected error during test execution: {str(error)}",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "repo_path": str(typescript_repo_path) if 'typescript_repo_path' in locals() else "unknown",
            "test_results": {}
        }
        
        print(f"[RUN_TYPESCRIPT_TESTS] : output status=error, message={error_result['message']}")
        return error_result


def _convert_test_paths(test_paths: List[str], typescript_repo_path: Path) -> List[str]:
    """
    Convert test paths from src/... format to full paths.
    
    Args:
        test_paths: List of test paths starting from src/
        typescript_repo_path: Path to the TypeScript repository
        
    Returns:
        List[str]: List of full test file paths
    """
    full_test_paths = []
    for test_path in test_paths:
        # Remove leading 'src/' if present and add full path
        clean_path = test_path.replace('src/', '', 1) if test_path.startswith('src/') else test_path
        full_path = typescript_repo_path / 'src' / clean_path
        full_test_paths.append(str(full_path))
    
    return full_test_paths


if __name__ == "__main__":
    # Example usage for testing
    try:
        print("Testing run_typescript_tests tool...")
        
        # Example test paths
        test_paths = ["src/tests/example.test.ts"]
        
        result = run_typescript_tests(test_paths)
        
        print(f"Test Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Exit Code: {result['exit_code']}")
        print(f"Repository Path: {result['repo_path']}")
        print(f"Test Results: {result['test_results']}")
        
        if result['status'] == "success":
            print("✅ Tests completed successfully!")
        else:
            print("❌ Tests failed!")
            print(f"Test Output:\n{result['stdout']}")
            print(f"Test Errors:\n{result['stderr']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 