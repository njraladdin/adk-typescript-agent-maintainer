from typing import Dict, Any
from pathlib import Path
from google.adk.tools import ToolContext

# Import workspace utilities
from ..workspace_utils import build_project, get_typescript_repo_path, is_typescript_repo_ready
from ..constants import AGENT_WORKSPACE_DIR, TYPESCRIPT_REPO_DIR


def build_typescript_project(
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Build the TypeScript project using npm run build.
    
    This tool builds the locally cloned TypeScript repository. It automatically
    detects the repository location and runs the default npm build script.
    
    Args:
        tool_context (ToolContext): Automatically injected by ADK for state access
    
    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - message: str (Success/error message)
            - stdout: str (Build output)
            - stderr: str (Error output if any)
            - exit_code: int (Process exit code)
            - repo_path: str (Path to the TypeScript repository)
    """
    # Log the start of the tool execution
    print(f"[BUILD_TYPESCRIPT_PROJECT] Running npm build")
    
    try:
        # Get the TypeScript repository path from the tool context state or use the default path
        if tool_context and 'typescript_repo_path' in tool_context.state:
            typescript_repo_path = Path(tool_context.state['typescript_repo_path'])
            print(f"[BUILD_TYPESCRIPT_PROJECT] Using TypeScript repository path from tool context: {typescript_repo_path}")
        else:
            # Use the default path
            typescript_repo_path = get_typescript_repo_path()
            print(f"[BUILD_TYPESCRIPT_PROJECT] Using default TypeScript repository path: {typescript_repo_path}")
        
        # Check if the repository is ready for building
        if not is_typescript_repo_ready():
            error_result = {
                "status": "error",
                "message": f"TypeScript repository at {typescript_repo_path} is not ready for building. Please run setup_agent_workspace first.",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "repo_path": str(typescript_repo_path)
            }
            print(f"[BUILD_TYPESCRIPT_PROJECT] : output status=error, message={error_result['message']}")
            return error_result
        
        # Use the workspace utility to build the project with default "build" script
        build_result = build_project(typescript_repo_path, "build")
        
        # Format the result with additional context information
        result = {
            "status": "success" if build_result["success"] else "error",
            "message": build_result["message"],
            "stdout": build_result["stdout"],
            "stderr": build_result["stderr"],
            "exit_code": build_result["exit_code"],
            "repo_path": str(typescript_repo_path)
        }
        
        # Log the output of the tool execution
        status = "success" if build_result["success"] else "error"
        print(f"[BUILD_TYPESCRIPT_PROJECT] : output status={status}, exit_code={build_result['exit_code']}")
        
        # For errors, print the complete message and outputs
        if status == "error":
            print(f"[BUILD_TYPESCRIPT_PROJECT] : error message={build_result['message']}")
            print(f"[BUILD_TYPESCRIPT_PROJECT] : stdout=\n{build_result['stdout']}")
            print(f"[BUILD_TYPESCRIPT_PROJECT] : stderr=\n{build_result['stderr']}")
        
        return result
        
    except Exception as error:
        error_result = {
            "status": "error",
            "message": f"Unexpected error during build: {str(error)}",
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "repo_path": str(typescript_repo_path) if 'typescript_repo_path' in locals() else "unknown"
        }
        
        # Log the error output
        print(f"[BUILD_TYPESCRIPT_PROJECT] : output status=error, message={error_result['message']}")
        
        return error_result


if __name__ == "__main__":
    # Example usage for testing
    try:
        print("Testing build_typescript_project tool...")
        
        result = build_typescript_project()
        
        print(f"Build Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Exit Code: {result['exit_code']}")
        print(f"Repository Path: {result['repo_path']}")
        
        if result['status'] == "success":
            print("✅ Build completed successfully!")
            if result['stdout']:
                print(f"Build Output:\n{result['stdout']}")
        else:
            print("❌ Build failed!")
            print(f"Error Message: {result['message']}")
            print(f"Build Output:\n{result['stdout']}")
            print(f"Build Errors:\n{result['stderr']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 