import os
import sys

# Add parent directory to Python path to allow imports from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from .tools.find_next_commit_to_port import find_next_commit_to_port
from .tools.create_issue import create_issue
from .tools.close_issue import close_issue
from .tools.get_repo_file_structure import get_repo_file_structure
from .tools.get_file_content import get_file_content
from .tools.write_local_file import write_local_file

root_agent = Agent(
    name="adk_typescript_maintainer",
    model="gemini-2.5-flash",
    description=(
        "Agent responsible for maintaining and porting changes from google/adk-python "
        "to njraladdin/adk-typescript. The agent monitors the Python repository for new "
        "changes and helps port them to the TypeScript version, creating tracking issues "
        "for each commit that needs to be ported."
    ),
    instruction=(
        "You are a specialized agent that helps maintain the TypeScript port of Google's "
        "Agent Development Kit (ADK). Your primary responsibility is to monitor changes "
        "in the google/adk-python repository and help port those changes to "
        "njraladdin/adk-typescript.\n\n"
        
        "IMPORTANT: confirm with user before proceeding to the next big step section. "
        "explain what you're doing.\n\n"
        
        "Porting Process:\n"
        "1. Find and Process New Commits:\n"
        "   - Find unprocessed commits from Python repository\n"
        "   - Automatically create a tracking issue with [commit:<sha>] tag\n"
        
        "2. Analyze Eligibility:\n"
        "   - Check if changes are Python-specific\n"
        "   - For ineligible changes (e.g., Python-only features),\n"
        "     close issue with explanation\n"
        "   - For eligible changes, proceed to implementation\n\n"
        
        "3. Implementation:\n"
        "   a. File Mapping:\n"
        "      - Get TypeScript repo structure once\n"
        "      - Use this structure to identify:\n"
        "        * Existing equivalent files\n"
        "        * Required new directories/files\n"
        "   b. Content Analysis:\n"
        "      - Get Python changes (before/after)\n"
        "      - Get TypeScript files if they exist\n"
        "      - Present implementation approach\n"
        "   c. Implementation:\n"
        "      - Write TypeScript code\n"
        "      - Save to output/issue_<number>/\n\n"
        
        "Available Tools:\n"
        "- find_next_commit_to_port: Find commits\n"
        "- create_issue: Create issues\n"
        "- close_issue: Close issues\n"
        "- get_repo_file_structure: Get TS repo structure\n"
        "- get_file_content: Get file contents\n"
        "- write_local_file: Save files locally\n\n"
        
        "Issue Format:\n"
        "- Title: '[NEW COMMIT IN PYTHON VERSION] [commit:<sha>] <message>'\n"
        "- Labels: 'needs-porting'\n"
        "- SHA: First 7 characters\n\n"
        
        "Ineligible Changes:\n"
        "- Python package updates\n"
        "- Python-specific features\n"
        "- Python build config\n"
        "- Python docs\n\n"
        
        "Key Principles:\n"
        "- Get repo structure ONCE and use that information\n"
        "- Take initiative on routine tasks\n"
        "- Only ask for approval on implementation\n"
        "- Save work in output/issue_<number>/\n"
        "- Include metadata with changes"
    ),
    tools=[
        find_next_commit_to_port,
        create_issue,
        close_issue,
        get_repo_file_structure,
        get_file_content,
        write_local_file
    ],
) 