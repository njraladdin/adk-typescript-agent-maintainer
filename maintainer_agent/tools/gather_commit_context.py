"""
Tool for gathering commit context - fetching commit diff, changed files, and TypeScript repository structure.
This tool replaces the previous callback-based approach for gathering commit context.
"""

import json
from typing import Dict, Any, List

from ..github_api_utils import fetch_commit_diff_data, fetch_repo_structure, fetch_multiple_files_content


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
    print(f"[gather_commit_context]: commit_id={commit_id}")
    
    try:
        # Step 1: Get commit diff and changed files
        commit_info = fetch_commit_diff_data(commit_id)
        
        if not commit_info or 'commit_sha' not in commit_info:
            error_result = {
                "status": "error",
                "message": f"Failed to fetch commit information for {commit_id}",
                "commit_sha": "",
                "diff": "",
                "changed_files": [],
                "typescript_repo_structure": ""
            }
            print(f"[gather_commit_context] ERROR: {error_result['message']}")
            return error_result
        
        # Step 2: Get content of all changed Python files concurrently
        changed_files_with_content = []
        changed_file_paths = commit_info.get('changed_files', [])
        
        if changed_file_paths:
            # Use the concurrent fetch utility
            file_results = fetch_multiple_files_content('google/adk-python', changed_file_paths, commit_id)
            
            # Process results and build the changed_files_with_content list
            for file_path in changed_file_paths:
                result = file_results.get(file_path, {})
                if result.get('status') == 'success' and result.get('content'):
                    changed_files_with_content.append({
                        'path': file_path,
                        'content': result['content']
                    })
        
        # Step 3: Get TypeScript repository structure  
        try:
            typescript_structure = fetch_repo_structure('njraladdin/adk-typescript')
        except Exception as e:
            typescript_structure = "Failed to fetch repository structure"
        
        success_result = {
            "status": "success",
            "commit_sha": commit_info['commit_sha'],  
            "diff": commit_info['diff'],
            "changed_files": changed_files_with_content,
            "typescript_repo_structure": typescript_structure,
            "message": f"Successfully gathered context for commit {commit_id}"
        }
        
        print(f"[gather_commit_context]: status=success, commit_sha={commit_info['commit_sha']}, changed_files_count={len(changed_files_with_content)}")
        return success_result
        
    except Exception as e:
        error_msg = f"Failed to gather commit context for {commit_id}: {str(e)}"
        error_result = {
            "status": "error",
            "message": error_msg,
            "commit_sha": "",
            "diff": "",
            "changed_files": [],
            "typescript_repo_structure": ""
        }
        print(f"[gather_commit_context] ERROR: {error_msg}")
        return error_result 