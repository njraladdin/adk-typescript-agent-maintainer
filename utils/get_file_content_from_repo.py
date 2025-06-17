from typing import Optional
import requests
from requests.exceptions import RequestException

def get_file_content_from_repo(
    username: str,
    repo: str,
    file_path: str,
    branch: Optional[str] = None
) -> str:
    """
    Gets the content of a file from a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        file_path (str): Path to the file within the repository
        branch (Optional[str]): Optional branch name (defaults to the repository's default branch)

    Returns:
        str: The file content as a string

    Raises:
        RequestException: If there's an error fetching the file content
    """
    try:
        # Build the URL - if branch is specified, include it, otherwise get from default branch
        url = f"https://api.github.com/repos/{username}/{repo}/contents/{file_path}"
        if branch:
            url += f"?ref={branch}"
        
        response = requests.get(
            url,
            headers={
                'Accept': 'application/vnd.github.v3.raw'
            }
        )
        response.raise_for_status()
        return response.text
    except RequestException as error:
        print(f"Error fetching file content: {error}")
        raise

if __name__ == "__main__":
    # Example usage
    try:
        # Example values for testing
        test_username = "google"
        test_repo = "adk-python"
        test_file_path = "README.md"  # Example file path
        test_branch = "main"  # Optional branch name
        
        print(f"Fetching {test_file_path} from {test_username}/{test_repo} repo (branch: {test_branch or 'default'}):")
        content = get_file_content_from_repo(test_username, test_repo, test_file_path, test_branch)
        print(content)
    except Exception as error:
        print(f"Test failed: {error}") 