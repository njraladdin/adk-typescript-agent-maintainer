import requests
from typing import List, Dict, Any, Literal
from requests.exceptions import RequestException

def get_repo_issues(
    username: str,
    repo: str,
    state: Literal["open", "closed", "all"] = "open",
    count: int = 30
) -> List[Dict[str, Any]]:
    """
    Fetches the list of issues from a GitHub repository.

    Args:
        username (str): GitHub username or organization name
        repo (str): GitHub repository name
        state (str): Issue state to filter by (default: 'open')
        count (int): Number of issues to retrieve (default: 30)

    Returns:
        List[Dict[str, Any]]: List of issue objects

    Raises:
        RequestException: If there's an error fetching the issues
    """
    try:
        response = requests.get(
            f"https://api.github.com/repos/{username}/{repo}/issues",
            params={
                "state": state,
                "per_page": count
            },
            headers={
                "Accept": "application/vnd.github.v3+json"
            }
        )
        response.raise_for_status()
        return response.json()
    except RequestException as error:
        print(f"Error fetching issues: {error}")
        raise

if __name__ == "__main__":
    # Test the function
    try:
        # Using test values
        test_username = "google"
        test_repo = "adk-python"
        
        print(f"Fetching open issues from {test_username}/{test_repo} repo:")
        issues = get_repo_issues(test_username, test_repo, "open", 5)
        print(issues)
    except Exception as error:
        print(f"Test failed: {error}") 