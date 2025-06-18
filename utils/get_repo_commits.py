import requests
from typing import List, Dict, Any, Optional
from requests.exceptions import RequestException

def get_repo_commits(
    username: str,
    repo: str,
    count: int = 10
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetches the latest commits from a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        count (int): Number of commits to retrieve (default: 10)

    Returns:
        Optional[List[Dict[str, Any]]]: List of commit objects, or None if there was an error
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
        error_msg = str(error)
        if "rate limit exceeded" in error_msg.lower():
            print(f"GitHub API rate limit exceeded. Please try again later.")
        else:
            print(f"Error fetching commits from {username}/{repo}: {error}")
        return None

if __name__ == "__main__":
    # Test the function
    # Using test values
    test_username = "google"
    test_repo = "adk-python"
    
    print(f"Fetching latest commits from {test_username}/{test_repo} repo:")
    commits = get_repo_commits(test_username, test_repo, 5)
    if commits:
        print(commits)
    else:
        print("Failed to fetch commits") 