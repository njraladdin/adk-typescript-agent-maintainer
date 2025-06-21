from typing import Optional, Dict, Any, List
import base64
import requests
from requests.exceptions import RequestException

def get_file_sha(
    username: str,
    repo: str,
    file_path: str,
    branch: Optional[str] = None,
    github_token: Optional[str] = None
) -> Optional[str]:
    """
    Gets the SHA of a file in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        file_path (str): Path to the file within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Optional[str]: The file's SHA if it exists, None otherwise
    """
    # Log the start of the tool execution with main parameters
    print(f"[GET_FILE_SHA] username={username} repo={repo} file_path={file_path} branch={branch or 'default'}")
    
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/contents/{file_path}"
        if branch:
            url += f"?ref={branch}"
            
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            sha = response.json()["sha"]
            # Log the output of the tool execution
            print(f"[GET_FILE_SHA] : output status=success, sha={sha}")
            return sha
        
        # Log the output when file doesn't exist
        print(f"[GET_FILE_SHA] : output status=success, sha=None (file not found)")
        return None
    
    except RequestException as error:
        # Log the error output
        print(f"[GET_FILE_SHA] : output status=error, message={str(error)}")
        return None

def write_file_to_repo(
    username: str,
    repo: str,
    file_path: str,
    content: str,
    commit_message: str,
    branch: str = "main",
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Writes or updates a file in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        file_path (str): Path where to create/update the file
        content (str): Content to write to the file
        commit_message (str): Commit message for the change
        branch (str): Branch to write to (default: 'main')
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Dict[str, Any]: The response data from GitHub API

    Raises:
        RequestException: If there's an error writing the file
    """
    # Log the start of the tool execution with main parameters
    print(f"[WRITE_FILE_TO_REPO] username={username} repo={repo} file_path={file_path} branch={branch}")
    
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/contents/{file_path}"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # Convert content to base64
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        # Get the file's SHA if it exists
        file_sha = get_file_sha(username, repo, file_path, branch, github_token)
        
        data = {
            "message": commit_message,
            "content": content_base64,
            "branch": branch
        }
        
        if file_sha:
            data["sha"] = file_sha
        
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        # Log the output of the tool execution
        action = "updated" if file_sha else "created"
        print(f"[WRITE_FILE_TO_REPO] : output status=success, action={action}, file_path={file_path}")
        
        return result
    
    except RequestException as error:
        print(f"Error writing file: {error}")
        # Log the error output
        print(f"[WRITE_FILE_TO_REPO] : output status=error, message={str(error)}")
        raise

def write_files_to_repo(
    username: str,
    repo: str,
    files: List[Dict[str, str]],
    commit_message: str,
    branch: str = "main",
    github_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Writes multiple files to a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        files (List[Dict[str, str]]): List of files to write, each with 'path' and 'content' keys
        commit_message (str): Commit message for the changes
        branch (str): Branch to write to (default: 'main')
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        List[Dict[str, Any]]: List of response data from GitHub API for each file

    Raises:
        RequestException: If there's an error writing any file
    """
    # Log the start of the tool execution with main parameters
    print(f"[WRITE_FILES_TO_REPO] username={username} repo={repo} file_count={len(files)} branch={branch}")
    
    results = []
    for file in files:
        result = write_file_to_repo(
            username,
            repo,
            file["path"],
            file["content"],
            commit_message,
            branch,
            github_token
        )
        results.append(result)
    
    # Log the output of the tool execution
    print(f"[WRITE_FILES_TO_REPO] : output status=success, files_written={len(results)}")
    
    return results

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_files = [
            {
                "path": "test/file1.txt",
                "content": "This is test file 1"
            },
            {
                "path": "test/file2.txt",
                "content": "This is test file 2"
            }
        ]
        test_commit_message = "Add test files"
        test_branch = "feature/test-branch"
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        results = write_files_to_repo(
            test_username,
            test_repo,
            test_files,
            test_commit_message,
            test_branch,
            github_token
        )
        print("Files written successfully!")
        for result in results:
            print(f"Committed: {result['content']['path']}")
    except Exception as error:
        print(f"Test failed: {error}") 