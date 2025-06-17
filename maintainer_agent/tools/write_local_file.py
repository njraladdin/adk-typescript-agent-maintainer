from typing import Optional, Dict, Any
import os
import json
from pathlib import Path

def write_local_file(
    issue_number: int,
    file_path: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Writes a file to a local output directory for review before committing to the repository.
    Files are organized by issue number to keep track of changes.
    
    Args:
        issue_number (int): The GitHub issue number these changes are associated with
        file_path (str): The target path in the repository (will be preserved in output structure)
        content (str): The content to write to the file
        metadata (Optional[Dict[str, Any]]): Optional metadata about the file/changes to save
            Example metadata:
            {
                "original_file": "path/to/python/file.py",
                "commit_sha": "abc123",
                "description": "Ported from Python version X.Y.Z"
            }
    
    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - output_path: str (The full path where the file was written)
            - message: str (Success/error message)
    """
    try:
        # Create base output directory if it doesn't exist
        base_dir = Path("output")
        base_dir.mkdir(exist_ok=True)
        
        # Create issue-specific directory
        issue_dir = base_dir / f"issue_{issue_number}"
        issue_dir.mkdir(exist_ok=True)
        
        # Preserve the repository path structure
        file_path = file_path.lstrip("/")  # Remove leading slash if present
        output_path = issue_dir / file_path
        
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file content
        output_path.write_text(content, encoding='utf-8')
        
        # If metadata provided, save it alongside the file
        if metadata:
            meta_path = output_path.parent / f"{output_path.name}.meta.json"
            meta_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        
        return {
            "status": "success",
            "output_path": str(output_path),
            "message": f"File successfully written to {output_path}"
        }
        
    except Exception as error:
        return {
            "status": "error",
            "message": f"Error writing file: {str(error)}"
        }

if __name__ == "__main__":
    # Example usage
    try:
        test_content = """
        export function helloWorld() {
            console.log("Hello from TypeScript!");
        }
        """
        
        test_metadata = {
            "original_file": "python/hello.py",
            "commit_sha": "abc123def456",
            "description": "Ported from Python hello() function"
        }
        
        result = write_local_file(
            issue_number=123,
            file_path="src/hello.ts",
            content=test_content,
            metadata=test_metadata
        )
        
        if result["status"] == "success":
            print(f"File written successfully to: {result['output_path']}")
        else:
            print(f"Error: {result['message']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 