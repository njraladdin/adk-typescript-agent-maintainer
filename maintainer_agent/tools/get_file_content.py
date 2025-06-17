from typing import Optional, Dict, Any, Tuple
import requests
from requests.exceptions import RequestException

def get_file_content(
    username: str,
    repo: str,
    file_path: str,
    branch: Optional[str] = None,
    github_token: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Gets the content and metadata of a file from a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        file_path (str): Path to the file within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        Tuple[str, Dict[str, Any]]: A tuple containing:
            - The file content as a string
            - File metadata including:
                - sha: str (File's SHA hash)
                - size: int (File size in bytes)
                - encoding: str (File encoding, usually 'base64' or 'utf-8')
                - url: str (API URL for the file)
                - html_url: str (Web URL for the file)
                - git_url: str (Git URL for the file)
                - download_url: str (Raw content URL)
                - type: str (Usually 'file')
                - content: str (Raw content from API)
                - name: str (File name)
                - path: str (File path)

    Raises:
        RequestException: If there's an error fetching the file content
        ValueError: If the file is not found or is a directory
    """
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/contents/{file_path}"
        if branch:
            url += f"?ref={branch}"
            
        headers = {
            "Accept": "application/vnd.github.v3.raw"
        }
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # First get the metadata with regular API call
        meta_headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if github_token:
            meta_headers["Authorization"] = headers["Authorization"]
        
        meta_response = requests.get(url, headers=meta_headers)
        meta_response.raise_for_status()
        metadata = meta_response.json()
        
        if isinstance(metadata, list):
            raise ValueError(f"Path '{file_path}' points to a directory, not a file")
        
        # Then get the raw content
        content_response = requests.get(url, headers=headers)
        content_response.raise_for_status()
        content = content_response.text
        
        return content, metadata
    
    except RequestException as error:
        print(f"Error fetching file content: {error}")
        raise

def file_exists(
    username: str,
    repo: str,
    file_path: str,
    branch: Optional[str] = None,
    github_token: Optional[str] = None
) -> bool:
    """
    Checks if a file exists in a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        file_path (str): Path to the file within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)
        github_token (Optional[str]): GitHub personal access token for authentication

    Returns:
        bool: True if the file exists, False otherwise
    """
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
            content = response.json()
            # Make sure it's a file, not a directory
            return not isinstance(content, list)
        return False
    
    except RequestException:
        return False

if __name__ == "__main__":
    # Example usage
    try:
        test_username = "test-user"
        test_repo = "test-repo"
        test_file = "README.md"
        test_branch = "main"
        
        # Note: You would need to set your GitHub token as an environment variable
        import os
        github_token = os.getenv("GITHUB_TOKEN")
        
        # Check if file exists
        if file_exists(test_username, test_repo, test_file, test_branch, github_token):
            print(f"Fetching content of {test_file} from {test_username}/{test_repo}:")
            content, metadata = get_file_content(
                test_username,
                test_repo,
                test_file,
                test_branch,
                github_token
            )
            print("\nFile metadata:")
            print(f"Name: {metadata['name']}")
            print(f"Size: {metadata['size']} bytes")
            print(f"SHA: {metadata['sha']}")
            print("\nContent preview (first 200 chars):")
            print(content[:200] + "..." if len(content) > 200 else content)
        else:
            print(f"File {test_file} not found")
    except Exception as error:
        print(f"Test failed: {error}") 