import requests
from typing import List, Dict, Any
from requests.exceptions import RequestException

def get_repo_commits(
    username: str,
    repo: str,
    count: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetches the latest commits from a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        count (int): Number of commits to retrieve (default: 10)

    Returns:
        List[Dict[str, Any]]: List of commit objects

    Raises:
        RequestException: If there's an error fetching the commits
    """
    try:
        response = requests.get(
            f"https://api.github.com/repos/{username}/{repo}/commits",
            params={
                "per_page": count
            },
            headers={
                "Accept": "application/vnd.github.v3+json"
            }
        )
        response.raise_for_status()
        return response.json()
    except RequestException as error:
        print(f"Error fetching commits: {error}")
        raise

if __name__ == "__main__":
    # Test the function
    try:
        # Using test values
        test_username = "google"
        test_repo = "adk-python"
        
        print(f"Fetching latest commits from {test_username}/{test_repo} repo:")
        commits = get_repo_commits(test_username, test_repo, 5)
        print(commits)
    except Exception as error:
        print(f"Test failed: {error}") 