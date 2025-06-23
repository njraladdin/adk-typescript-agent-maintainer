import os
from typing import List, Dict, Any
from pathlib import Path
from google.adk.tools import ToolContext

# Import workspace utilities
from ..workspace_utils import run_tests, get_typescript_repo_path, is_typescript_repo_ready
from ..constants import AGENT_WORKSPACE_DIR


def run_typescript_tests(
    test_names: List[str],
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Run TypeScript tests by test file names using npm test.
    
    This tool runs the specified test files using npm test. Jest will automatically
    find the test files by their names. The environment setup (.env file) should 
    already be done during workspace setup.
    
    Args:
        test_names (List[str]): List of test file names (e.g., ["BaseAgent.test.ts", "GoogleLlm.test.ts"])
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
    print(f"[RUN_TYPESCRIPT_TESTS] Running tests: {', '.join(test_names)}")
    
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
        
        # Jest will auto-discover tests by filename, so just pass the test names directly
        print(f"[RUN_TYPESCRIPT_TESTS] Test names for Jest: {test_names}")
        
        # Run the tests using workspace utility
        test_result = run_tests(typescript_repo_path, test_names)
        
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
        
        # Log test results summary
        test_results = test_result["test_results"]
        print(f"[RUN_TYPESCRIPT_TESTS] : test summary: {test_results.get('passed_tests', 0)} passed, {test_results.get('failed_tests', 0)} failed, {test_results.get('skipped_tests', 0)} skipped, {test_results.get('total_tests', 0)} total")
        
        # Log test files that were run
        if test_results.get('test_files'):
            print(f"[RUN_TYPESCRIPT_TESTS] : test files run: {', '.join(test_results.get('test_files', []))}")
        
        if status == "success":
            print(f"[RUN_TYPESCRIPT_TESTS] : success message={test_result['message']}")
            # Print a sample of the stdout to show test results
            if test_result['stdout']:
                stdout_preview = '\n'.join(test_result['stdout'].splitlines()[:20])  # First 20 lines
                print(f"[RUN_TYPESCRIPT_TESTS] : stdout preview=\n{stdout_preview}")
                if len(test_result['stdout'].splitlines()) > 20:
                    print(f"[RUN_TYPESCRIPT_TESTS] : stdout truncated... (showing first 20 lines of {len(test_result['stdout'].splitlines())} total)")
        else:
            print(f"[RUN_TYPESCRIPT_TESTS] : error message={test_result['message']}")
            print(f"[RUN_TYPESCRIPT_TESTS] : stderr=\n{test_result['stderr']}")
            
            # For errors, also print the stdout which often contains test failure details
            if test_result['stdout']:
                stdout_preview = '\n'.join(test_result['stdout'].splitlines()[:30])  # First 30 lines for errors
                print(f"[RUN_TYPESCRIPT_TESTS] : stdout preview=\n{stdout_preview}")
                if len(test_result['stdout'].splitlines()) > 30:
                    print(f"[RUN_TYPESCRIPT_TESTS] : stdout truncated... (showing first 30 lines of {len(test_result['stdout'].splitlines())} total)")
            
            # Print any error messages extracted from test results
            if test_results.get('errors'):
                print(f"[RUN_TYPESCRIPT_TESTS] : test errors=\n" + '\n'.join(test_results.get('errors', [])))
        
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


if __name__ == "__main__":
    # Example usage for testing
    try:
        print("Testing run_typescript_tests tool...")
        
        # Example test names
        test_names = ["example.test.ts"]
        
        result = run_typescript_tests(test_names)
        
        print(f"Test Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Exit Code: {result['exit_code']}")
        print(f"Repository Path: {result['repo_path']}")
        
        # Print test results summary
        test_results = result['test_results']
        print("\n=== Test Results Summary ===")
        print(f"Total Tests: {test_results.get('total_tests', 0)}")
        print(f"Passed: {test_results.get('passed_tests', 0)}")
        print(f"Failed: {test_results.get('failed_tests', 0)}")
        print(f"Skipped: {test_results.get('skipped_tests', 0)}")
        
        # Print test files
        if test_results.get('test_files'):
            print("\n=== Test Files Run ===")
            for test_file in test_results.get('test_files', []):
                print(f"- {test_file}")
        
        if result['status'] == "success":
            print("\n✅ Tests completed successfully!")
        else:
            print("\n❌ Tests failed!")
            
            # Print any error messages
            if test_results.get('errors'):
                print("\n=== Test Errors ===")
                for error in test_results.get('errors', []):
                    print(f"- {error}")
            
            print("\n=== Test Output ===")
            print(result['stdout'][:500] + "..." if len(result['stdout']) > 500 else result['stdout'])
            
            print("\n=== Error Output ===")
            print(result['stderr'][:500] + "..." if len(result['stderr']) > 500 else result['stderr'])
            
    except Exception as error:
        print(f"Test failed: {error}") 