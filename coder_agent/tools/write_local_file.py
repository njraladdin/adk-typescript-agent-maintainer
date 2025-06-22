from typing import Optional, Dict, Any
import os
import json
from pathlib import Path
from google.adk.tools import ToolContext

# Import the workspace directory constants from callbacks
from ..callbacks import AGENT_WORKSPACE_DIR, TYPESCRIPT_REPO_DIR

def write_local_file(
    issue_number: int,
    file_path: str,
    content: str,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Writes a file directly to the local TypeScript repository directory structure.
    
    This tool writes files to a locally cloned TypeScript repository. Use the exact same 
    file paths as they appear in the TypeScript repository file structure (e.g., 
    "src/agents/base-agent.ts", "src/tools/example-tool.ts").
    
    Args:
        issue_number (int): The GitHub issue number these changes are associated with
        file_path (str): The exact file path as it appears in the TypeScript repository 
                        (e.g., "src/agents/base-agent.ts", "package.json")
        content (str): The complete file content to write
        tool_context (ToolContext): Automatically injected by ADK for state access
    
    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - output_path: str (The full path where the file was written)
            - message: str (Success/error message)
    """
    # Log the start of the tool execution with main parameters
    print(f"[WRITE_LOCAL_FILE] issue_number={issue_number} file_path={file_path}")
    
    try:
        # Get the TypeScript repository path from the tool context state or use the default path
        if tool_context and 'typescript_repo_path' in tool_context.state:
            typescript_repo_path = Path(tool_context.state['typescript_repo_path'])
            print(f"[WRITE_LOCAL_FILE] Using TypeScript repository path from tool context: {typescript_repo_path}")
        else:
            # Use the default path
            typescript_repo_path = Path(AGENT_WORKSPACE_DIR) / TYPESCRIPT_REPO_DIR
            print(f"[WRITE_LOCAL_FILE] Using default TypeScript repository path: {typescript_repo_path}")
        
        # Ensure the TypeScript repository directory exists
        if not typescript_repo_path.exists():
            raise FileNotFoundError(f"TypeScript repository directory {typescript_repo_path} does not exist. Please run setup_agent_workspace first.")
        
        # Prepare the file path in the TypeScript repository
        file_path = file_path.lstrip("/")  # Remove leading slash if present
        output_path = typescript_repo_path / file_path
        
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file content to the TypeScript repository
        output_path.write_text(content, encoding='utf-8')
        
        success_result = {
            "status": "success",
            "output_path": str(output_path),
            "message": f"File successfully written to {output_path}"
        }
        
        # Log the output of the tool execution
        print(f"[WRITE_LOCAL_FILE] : output status=success, output_path={output_path}")
        
        return success_result
        
    except Exception as error:
        error_result = {
            "status": "error",
            "message": f"Error writing file: {str(error)}"
        }
        
        # Log the error output
        print(f"[WRITE_LOCAL_FILE] : output status=error, message={error_result['message']}")
        
        return error_result

if __name__ == "__main__":
    # Example usage
    try:
        test_content = """
        export function helloWorld() {
            console.log("Hello from TypeScript!");
        }
        """
        
        result = write_local_file(
            issue_number=123,
            file_path="src/hello.ts",
            content=test_content
        )
        
        if result["status"] == "success":
            print(f"File written successfully to: {result['output_path']}")
        else:
            print(f"Error: {result['message']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 