from typing import TypedDict, List, Literal, Optional, Dict, Any
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

class FileDiff(TypedDict):
    """Represents a structured diff for a file"""
    file: str
    changed_lines: int
    excerpt: List[str]
    additions: int
    deletions: int
    is_binary: bool
    status: Literal['modified', 'added', 'deleted', 'renamed']

class CommitDiffResponse(TypedDict):
    """Represents a structured commit diff"""
    files: List[FileDiff]
    total_additions: int
    total_deletions: int
    total_files_changed: int

TOKEN_CACHE_KEY = "github_token"
GATHERED_CONTEXT_KEY = "gathered_context"

def parse_diff(raw_diff: str, max_excerpt_lines: int) -> CommitDiffResponse:
    """
    Parse a raw git diff into a structured format.
    
    Args:
        raw_diff: The raw diff string from GitHub API
        max_excerpt_lines: Maximum number of lines to include in the excerpt
    
    Returns:
        Structured diff object
    """
    files: List[FileDiff] = []
    total_additions = 0
    total_deletions = 0
    
    # Split the diff by file sections (diff --git lines)
    file_patterns = raw_diff.split('\ndiff --git ')
    
    # First element might be empty or contain some header information
    file_sections = ['diff --git ' + file_patterns[0]] if file_patterns[0].strip() else []
    
    # Add the rest of the file sections with the diff --git prefix restored
    file_sections.extend(f'diff --git {pattern}' for pattern in file_patterns[1:])
    
    for section in file_sections:
        if not section.startswith('diff --git'):
            continue
        
        # Extract filenames from the section
        import re
        file_name_match = re.search(r'diff --git a/(.*?) b/(.*?)(\n|$)', section)
        if not file_name_match:
            continue
        
        from_file = file_name_match.group(1)
        to_file = file_name_match.group(2)
        
        # Determine file status
        status: Literal['modified', 'added', 'deleted', 'renamed'] = 'modified'
        file_name = to_file
        
        if 'new file mode' in section:
            status = 'added'
            file_name = to_file
        elif 'deleted file mode' in section:
            status = 'deleted'
            file_name = from_file
        elif from_file != to_file:
            status = 'renamed'
            file_name = to_file
        
        is_binary = 'Binary files' in section or 'GIT binary patch' in section
        
        if is_binary:
            files.append({
                'file': file_name,
                'changed_lines': 0,
                'excerpt': ['Binary file changed'],
                'additions': 0,
                'deletions': 0,
                'is_binary': True,
                'status': status
            })
            continue
        
        # Extract the actual diff content - everything after the first @@ line
        hunks = re.findall(r'@@.*?@@.*?(?=(?:\n@@|\n?$))', section, re.DOTALL)
        
        # If no hunks were found, try a different approach
        diff_content = ''
        if not hunks:
            header_end_index = section.find('\n+++')
            if header_end_index != -1:
                first_hunk_index = section.find('@@', header_end_index)
                if first_hunk_index != -1:
                    diff_content = section[first_hunk_index:]
        else:
            diff_content = '\n'.join(hunks)
        
        if not diff_content:
            continue
        
        # Process the diff content
        lines = [line for line in diff_content.split('\n') if line]
        
        # Count additions and deletions
        added_lines = sum(1 for line in lines if line.startswith('+'))
        removed_lines = sum(1 for line in lines if line.startswith('-'))
        
        total_additions += added_lines
        total_deletions += removed_lines
        
        # Get changed lines (lines starting with + or -)
        changed_lines = [line for line in lines if line.startswith('+') or line.startswith('-')]
        
        # Maximum line length to include in excerpt
        MAX_LINE_LENGTH = 500
        
        # Create the excerpt with trimmed lines
        excerpt: List[str] = []
        
        # Check if we have any very large lines in this file
        has_very_large_lines = any(len(line) > 3000 for line in changed_lines)
        
        # Process all changed lines up to max_excerpt_lines
        for line in changed_lines[:max_excerpt_lines]:
            if len(line) <= MAX_LINE_LENGTH:
                excerpt.append(line)
            else:
                # For long lines, trim them and add information about how much is trimmed
                prefix = line[0]  # Keep the + or - prefix
                remaining_chars = len(line) - MAX_LINE_LENGTH
                
                # Format large numbers with commas for readability
                formatted_length = f"{len(line):,}"
                formatted_remaining = f"{remaining_chars:,}"
                
                excerpt.append(f"{prefix}{line[1:MAX_LINE_LENGTH]}... [trimmed {formatted_remaining} chars from {formatted_length} char line]")
        
        # Add ellipsis if there are more lines than what we included
        if len(changed_lines) > max_excerpt_lines:
            excerpt.append(f"... ({len(changed_lines) - max_excerpt_lines} more lines)")
        
        files.append({
            'file': file_name,
            'changed_lines': added_lines + removed_lines,
            'excerpt': excerpt,
            'additions': added_lines,
            'deletions': removed_lines,
            'is_binary': False,
            'status': status
        })
    
    return {
        'files': files,
        'total_additions': total_additions,
        'total_deletions': total_deletions,
        'total_files_changed': len(files)
    }

def get_commit_diff(
    username: str,
    repo: str,
    commit_sha: str,
    max_excerpt_lines: int = 10,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Gets the diff for a specific commit and automatically stores it in the session state.
    
    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        commit_sha (str): The commit hash to get the diff for
        max_excerpt_lines (int): Maximum number of lines to include in the excerpt (default: 10)
        tool_context (ToolContext): Automatically injected by ADK for auth handling
    
    Returns:
        Dict[str, Any]: Response containing:
            - status: str ('success' or 'error')
            - diff: CommitDiffResponse (Structured diff object containing file diffs and stats)
            - message: str (Error message if status is 'error')
    """
    try:
        # Step 1: Check for cached token
        github_token = tool_context.state.get(TOKEN_CACHE_KEY) if tool_context else None
        
        # If no token, we need to get it from environment or request it
        if not github_token:
            # For now, let's try to get it from environment as a fallback
            import os
            github_token = os.getenv("GITHUB_TOKEN")
            
            if github_token and tool_context:
                # Cache the token for future use
                tool_context.state[TOKEN_CACHE_KEY] = github_token
            elif not github_token:
                return {
                    'status': 'error', 
                    'message': 'GitHub token not found. Please set GITHUB_TOKEN environment variable or provide authentication.'
                }

        headers = {}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        headers["Accept"] = "application/vnd.github.v3.diff"
        
        response = requests.get(
            f"https://api.github.com/repos/{username}/{repo}/commits/{commit_sha}",
            headers=headers
        )
        response.raise_for_status()
        
        diff_data = parse_diff(response.text, max_excerpt_lines)
        
        # Store commit info in session state
        if tool_context:
            # Initialize gathered_context if it doesn't exist
            if GATHERED_CONTEXT_KEY not in tool_context.state:
                tool_context.state[GATHERED_CONTEXT_KEY] = {}
            
            # Store commit info - this structure remains the same
            # Other tools will store files in python_context_files and typescript_context_files
            tool_context.state[GATHERED_CONTEXT_KEY]['commit_info'] = {
                'commit_sha': commit_sha,
                'diff': response.text,  # Store raw diff
                'changed_files': [file_info['file'] for file_info in diff_data['files']]
            }
        
        return {
            'status': 'success',
            'diff': diff_data
        }
    except RequestException as error:
        # If we get a 401/403, clear the cached token
        if hasattr(error, 'response') and error.response.status_code in (401, 403) and tool_context:
            tool_context.state[TOKEN_CACHE_KEY] = None
            return {'status': 'error', 'message': 'Authentication failed. Token may be invalid.'}
        print(f"Error fetching commit diff: {error}")
        return {'status': 'error', 'message': str(error)}

if __name__ == "__main__":
    # Example usage
    try:
        # Example values for testing
        test_username = "google"
        test_repo = "adk-python"
        test_commit_sha = "6dec235c13f42f1a6f69048b30fb78f48831cdbd"  # Example commit SHA
        
        print(f"Fetching diff for commit {test_commit_sha} from {test_username}/{test_repo} repo:")
        diff_data = get_commit_diff(test_username, test_repo, test_commit_sha, 10)
        import json
        print(json.dumps(diff_data, indent=2))
    except Exception as error:
        print(f"Test failed: {error}") 