from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException
from google.adk.tools import ToolContext

# Import the individual functions we're combining
from .get_commit_diff import get_commit_diff
from .create_issue import create_issue
from .create_branch import create_branch

def setup_commit_port(
    commit_sha: str,
    username: str = "njraladdin",
    repo: str = "adk-typescript",
    base_branch: str = "main",
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Sets up all the initial GitHub infrastructure for porting a commit:
    1. Gets commit diff information from the source repository
    2. Creates a tracking issue with commit details
    3. Creates a feature branch for the porting work
    
    Args:
        commit_sha (str): The commit hash to port from google/adk-python
        username (str): GitHub username for target repo (default: njraladdin)
        repo (str): GitHub repository name for target repo (default: adk-typescript)
        base_branch (str): Base branch for the new feature branch (default: main)
        tool_context (ToolContext): Automatically injected by ADK for auth handling
    
    Returns:
        Dict[str, Any]: Combined response containing:
            - status: str ('success' or 'error')
            - commit_diff: Dict (from get_commit_diff)
            - issue_number: int (created issue number)
            - issue_url: str (created issue URL)
            - branch_name: str (created branch name)
            - message: str (error message if status is 'error')
    """
    # Log the start of the setup process
    print(f"[SETUP_COMMIT_PORT] Starting setup for commit {commit_sha}")
    
    try:
        # Step 1: Get commit diff information
        print(f"[SETUP_COMMIT_PORT] Step 1: Getting commit diff for {commit_sha}")
        commit_diff_result = get_commit_diff(
            username="google",
            repo="adk-python", 
            commit_sha=commit_sha,
            tool_context=tool_context
        )
        
        if commit_diff_result['status'] != 'success':
            error_result = {
                'status': 'error',
                'message': f"Failed to get commit diff: {commit_diff_result.get('message', 'Unknown error')}"
            }
            print(f"[SETUP_COMMIT_PORT] : output status=error, message={error_result['message']}")
            return error_result
        
        commit_diff = commit_diff_result['diff']
        
        # Step 2: Create tracking issue with commit information
        print(f"[SETUP_COMMIT_PORT] Step 2: Creating tracking issue")
        
        # Format issue title and body
        short_sha = commit_sha[:7]
        
        # Get commit message from the diff result if available
        # For now, we'll use a placeholder - this could be enhanced to get actual commit message
        commit_message = f"Port changes from commit {short_sha}"
        
        issue_title = f"[NEW COMMIT IN PYTHON VERSION] [commit:{short_sha}] {commit_message}"
        
        # Create detailed issue body
        files_changed = [f['file'] for f in commit_diff['files']]
        files_list = '\n'.join([f"- `{file}`" for file in files_changed])
        
        issue_body = f"""## Commit Information
**Source Commit:** [`{short_sha}`](https://github.com/google/adk-python/commit/{commit_sha})
**Repository:** google/adk-python

## Summary
This issue tracks the porting of commit {short_sha} from the Python ADK repository to TypeScript.

## Files Changed ({commit_diff['total_files_changed']} files)
{files_list}

## Change Statistics
- **Total additions:** {commit_diff['total_additions']}
- **Total deletions:** {commit_diff['total_deletions']}
- **Files changed:** {commit_diff['total_files_changed']}

## Next Steps
1. ✅ Create tracking issue (this issue)
2. ✅ Create feature branch
3. 🔄 Port the changes using coder_agent
4. ⏳ Create pull request with ported changes

---
*This issue was automatically created by the maintainer agent.*"""

        issue_result = create_issue(
            username=username,
            repo=repo,
            title=issue_title,
            body=issue_body,
            tool_context=tool_context
        )
        
        if issue_result['status'] != 'success':
            error_result = {
                'status': 'error',
                'message': f"Failed to create issue: {issue_result.get('message', 'Unknown error')}"
            }
            print(f"[SETUP_COMMIT_PORT] : output status=error, message={error_result['message']}")
            return error_result
        
        issue_number = issue_result['number']
        issue_url = issue_result['html_url']
        
        # Step 3: Create feature branch
        print(f"[SETUP_COMMIT_PORT] Step 3: Creating feature branch")
        branch_name = f"port-{short_sha}"
        
        branch_result = create_branch(
            username=username,
            repo=repo,
            branch_name=branch_name,
            base_branch=base_branch,
            tool_context=tool_context
        )
        
        if branch_result['status'] != 'success':
            error_result = {
                'status': 'error', 
                'message': f"Failed to create branch: {branch_result.get('message', 'Unknown error')}"
            }
            print(f"[SETUP_COMMIT_PORT] : output status=error, message={error_result['message']}")
            return error_result
        
        # Step 4: Return success response with all information
        success_result = {
            'status': 'success',
            'commit_sha': commit_sha,
            'commit_diff': commit_diff,
            'issue_number': issue_number,
            'issue_url': issue_url,
            'branch_name': branch_name,
            'message': f"Successfully set up porting infrastructure for commit {short_sha}"
        }
        
        print(f"[SETUP_COMMIT_PORT] : output status=success, issue_number={issue_number}, branch_name={branch_name}")
        return success_result
        
    except Exception as error:
        error_result = {
            'status': 'error',
            'message': f"Unexpected error during setup: {str(error)}"
        }
        print(f"[SETUP_COMMIT_PORT] : output status=error, message={error_result['message']}")
        return error_result


if __name__ == "__main__":
    # Example usage for testing
    try:
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        if not github_token:
            print("Please set GITHUB_TOKEN environment variable for testing")
            exit(1)
        
        # Mock tool context for testing
        class MockToolContext:
            def __init__(self):
                self.state = {"github_token": github_token}
        
        result = setup_commit_port(
            commit_sha="abc1234567890abcdef",  # Replace with actual commit SHA
            tool_context=MockToolContext()
        )
        
        if result['status'] == 'success':
            print(f"✅ Setup completed successfully!")
            print(f"   Issue: {result['issue_url']}")
            print(f"   Branch: {result['branch_name']}")
        else:
            print(f"❌ Setup failed: {result['message']}")
            
    except Exception as error:
        print(f"Test failed: {error}") 