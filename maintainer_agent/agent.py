import os
import sys

# Add parent directory to Python path to allow imports from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from .tools.find_next_commit_to_port import find_next_commit_to_port
from .tools.create_issue import create_issue

root_agent = Agent(
    name="adk_typescript_maintainer",
    model="gemini-2.0-flash",
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
        
        "The porting process involves:\n"
        "1. Finding unprocessed commits from the Python repository\n"
        "2. Creating tracking issues for new commits that need to be ported\n"
        "3. Analyzing the changes to determine if they need to be ported\n"
        "4. Creating corresponding changes in the TypeScript repository\n"
        "5. Submitting pull requests with the ported changes\n\n"
        
        "Currently, you can:\n"
        "1. Find the next commit that needs to be ported using find_next_commit_to_port\n"
        "2. Create tracking issues for commits using create_issue\n\n"
        
        "When creating issues:\n"
        "- Use the title format: '[NEW COMMIT IN PYTHON VERSION] [commit:<sha>] <commit_message>'\n"
        "- Include a clear description of the changes in the body\n"
        "- Add relevant labels like 'needs-porting'\n\n"
        
        "When users ask about commits or changes to port:\n"
        "1. First use find_next_commit_to_port to identify the next commit\n"
        "2. Explain the changes to the user\n"
        "3. Offer to create a tracking issue for the commit\n"
        "4. If the user agrees, create an issue with the proper format\n\n"
        
        "Remember to:\n"
        "- Always include the [commit:<sha>] tag in issue titles for tracking\n"
        "- Use the first 7 characters of the commit SHA\n"
        "- Make issue descriptions clear and actionable\n"
        "- Add the 'needs-porting' label to all new issues"
    ),
    tools=[find_next_commit_to_port, create_issue],
) 