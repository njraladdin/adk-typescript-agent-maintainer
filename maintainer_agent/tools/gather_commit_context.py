"""
Tool for gathering commit context - fetching commit diff, changed files, and TypeScript repository structure.
This tool replaces the previous callback-based approach for gathering commit context.
"""

import json
from typing import Dict, Any, List

from ..github_api_utils import fetch_commit_diff_data, fetch_repo_structure, fetch_file_content


def gather_commit_context(commit_id: str) -> Dict[str, Any]:
    """
    Gather comprehensive context for a specific commit including diff, changed files, and repository structure.
    
    This tool fetches:
    1. Commit diff and metadata from the Python repository
    2. Content of all changed Python files at the commit
    3. TypeScript repository structure for context
    
    Args:
        commit_id: The full SHA of the commit to gather context for
        
    Returns:
        Dict containing:
        - status: "success" or "error"
        - commit_sha: The actual commit SHA
        - diff: The commit diff text
        - changed_files: List of dicts with 'path' and 'content' keys
        - typescript_repo_structure: String representation of TypeScript repo structure
        - message: Success/error message
    """
    print(f"TOOL: Gathering commit context for {commit_id}")
    
    try:
        # Step 1: Get commit diff and changed files
        print("TOOL: Fetching commit diff...")
        commit_info = fetch_commit_diff_data(commit_id)
        
        if not commit_info or 'commit_sha' not in commit_info:
            return {
                "status": "error",
                "message": f"Failed to fetch commit information for {commit_id}",
                "commit_sha": "",
                "diff": "",
                "changed_files": [],
                "typescript_repo_structure": ""
            }
        
        # Step 2: Get content of each changed Python file
        print("TOOL: Fetching Python file contents...")
        changed_files_with_content = []
        
        for file_path in commit_info.get('changed_files', []):
            try:
                # Fetch the file content at the specific commit
                content = fetch_file_content('google/adk-python', file_path, commit_id)
                if content:
                    changed_files_with_content.append({
                        'path': file_path,
                        'content': content
                    })
                else:
                    print(f"TOOL: Warning - No content retrieved for {file_path}")
            except Exception as e:
                print(f"TOOL: Error fetching content for {file_path}: {e}")
        
        # Step 3: Get TypeScript repository structure  
        print("TOOL: Fetching TypeScript repository structure...")
        try:
            typescript_structure = fetch_repo_structure('njraladdin/adk-typescript')
        except Exception as e:
            print(f"TOOL: Warning - Failed to fetch TypeScript repository structure: {e}")
            typescript_structure = "Failed to fetch repository structure"
        
        print(f"TOOL: Successfully gathered context for commit {commit_id}")
        print(f"TOOL: Found {len(changed_files_with_content)} changed Python files with content")
        
        return {
            "status": "success",
            "commit_sha": commit_info['commit_sha'],  
            "diff": commit_info['diff'],
            "changed_files": changed_files_with_content,
            "typescript_repo_structure": typescript_structure,
            "message": f"Successfully gathered context for commit {commit_id}"
        }
        
    except Exception as e:
        error_msg = f"Failed to gather commit context for {commit_id}: {str(e)}"
        print(f"TOOL ERROR: {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "commit_sha": "",
            "diff": "",
            "changed_files": [],
            "typescript_repo_structure": ""
        } 