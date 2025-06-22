from typing import Optional, Dict, Any
import os
import json
from pathlib import Path

def write_local_file(
    file_path: str,
    content: str
) -> Dict[str, Any]:
    """
    Writes a file to a local output directory for review before committing to the repository.
    
    Args:
        file_path (str): The target path in the repository (will be preserved in output structure)
        content (str): The content to write to the file
    
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
        
        # Preserve the repository path structure
        file_path = file_path.lstrip("/")  # Remove leading slash if present
        output_path = base_dir / file_path
        
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file content
        output_path.write_text(content, encoding='utf-8')
        
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
        
        result = write_local_file(
            file_path="src/hello.ts",
            content=test_content
        )
        
        if result["status"] == "success":
            print(f"File written successfully to: {result['output_path']}")
        else:
            print(f"Error: {result['message']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 