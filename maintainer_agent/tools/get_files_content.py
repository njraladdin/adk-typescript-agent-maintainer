from typing import Optional, Dict, Any, List
from google.adk.tools import ToolContext
from ..workspace_utils import read_local_files

def get_files_content(
    file_paths: List[str],
    tool_context: ToolContext = None
) -> Dict[str, Dict[str, Any]]:
    """
    Gets the content and metadata of multiple files from the local TypeScript repository.

    Args:
        file_paths (List[str]): List of file paths within the TypeScript repository (relative to repo root)
        tool_context (ToolContext): Automatically injected by ADK for session state handling

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping file paths to their content and metadata.
                                  Only includes successfully read files.
    """
    print(f"[get_files_content]: file_paths={file_paths}")
    
    try:
        files = read_local_files(file_paths)
        
        if tool_context and files:
            if 'typescript_files' not in tool_context.state:
                tool_context.state['typescript_files'] = {}
            
            for file_path, file_data in files.items():
                tool_context.state['typescript_files'][file_path] = file_data['content']
        
        if files:
            successful_files = list(files.keys())
            print(f"[get_files_content]: status=success, files_count={len(files)}, successful_files={successful_files}")
            return {
                "status": "success",
                "files": files,
                "successful_files": successful_files,
                "message": f"Successfully read {len(files)} files from local TypeScript repository"
            }
        else:
            print(f"[get_files_content]: status=error, message=No files were successfully read")
            return {
                "status": "error", 
                "files": {},
                "successful_files": [],
                "message": "No files were successfully read from local TypeScript repository"
            }
    
    except Exception as error:
        error_msg = f"Error in get_files_content: {error}"
        print(f"[get_files_content]: status=error, message={error_msg}")
        return {
            "status": "error",
            "files": {},
            "successful_files": [],
            "message": error_msg
        }

if __name__ == "__main__":
    # Example usage
    try:
        test_files = ["README.md", "package.json", "src/agents/BaseAgent.ts"]
        
        print(f"Testing local file reading of {len(test_files)} files:")
        result = get_files_content(test_files)
        
        if result["status"] == "success":
            files = result["files"]
            print(f"\nRead {len(files)} files successfully:")
            for file_path, file_data in files.items():
                metadata = file_data['metadata']
                content_preview = file_data['content'][:100]
                print(f"- {file_path}: {metadata['size']} bytes")
                print(f"  Preview: {content_preview}...")
        else:
            print(f"Failed: {result['message']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 