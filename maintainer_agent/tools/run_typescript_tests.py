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
    print(f"[RUN_TYPESCRIPT_TESTS] Input: test_names={test_names}")
    
    try:
        # Get the TypeScript repository path
        if tool_context and 'typescript_repo_path' in tool_context.state:
            typescript_repo_path = Path(tool_context.state['typescript_repo_path'])
        else:
            typescript_repo_path = get_typescript_repo_path()
        
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
            print(f"[RUN_TYPESCRIPT_TESTS] Output: status=error, message={error_result['message']}")
            return error_result
        
        # Run the tests using workspace utility
        test_result = run_tests(typescript_repo_path, test_names)
        
        # Format the result
        result = {
            "status": "success" if test_result["success"] else "error",
            "message": test_result["message"],
            "stdout": test_result["stdout"].encode('ascii', errors='replace').decode('ascii') if test_result["stdout"] else "",
            "stderr": test_result["stderr"].encode('ascii', errors='replace').decode('ascii') if test_result["stderr"] else "",
            "exit_code": test_result["exit_code"],
            "repo_path": str(typescript_repo_path),
            "test_results": test_result["test_results"]
        }
        
        # Log the final output
        status = "success" if test_result["success"] else "error"
        test_results = test_result["test_results"]
        
        # Log the actual test output for debugging
        if test_result["stderr"]:
            print(f"[RUN_TYPESCRIPT_TESTS] Test Results:")
            for line in test_result["stderr"].splitlines():
                print(f"  {line}")
        
        if status == "success":
            print(f"[RUN_TYPESCRIPT_TESTS] Output: status=success, passed={test_results.get('passed_tests', 0)}, failed={test_results.get('failed_tests', 0)}, total={test_results.get('total_tests', 0)}")
        else:
            print(f"[RUN_TYPESCRIPT_TESTS] Output: status=error, exit_code={test_result['exit_code']}, message={test_result['message']}")
        
        return result
        
    except Exception as error:
        error_message = str(error).encode('ascii', errors='replace').decode('ascii')
        error_result = {
            "status": "error",
            "message": f"Unexpected error during test execution: {error_message}",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "repo_path": str(typescript_repo_path) if 'typescript_repo_path' in locals() else "unknown",
            "test_results": {}
        }
        
        print(f"[RUN_TYPESCRIPT_TESTS] Output: status=error, message={error_result['message']}")
        return error_result


if __name__ == "__main__":
    # Example usage for testing
    try:
        print("Testing run_typescript_tests tool...")
        
        # Example test names
        test_names = ["callback.test.ts"]
        
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