import os
import sys

# Add parent directory to Python path to allow imports from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from .tools.find_next_commit_to_port import find_next_commit_to_port

root_agent = Agent(
    name="adk_typescript_maintainer",
    model="gemini-2.0-flash",
    description=(
        "Agent responsible for maintaining and porting changes from google/adk-python "
        "to njraladdin/adk-typescript. The agent monitors the Python repository for new "
        "changes and helps port them to the TypeScript version."
    ),
    instruction=(
        "You are a specialized agent that helps maintain the TypeScript port of Google's "
        "Agent Development Kit (ADK). Your primary responsibility is to monitor changes "
        "in the google/adk-python repository and help port those changes to "
        "njraladdin/adk-typescript.\n\n"
        
        "The porting process involves:\n"
        "1. Finding unprocessed commits from the Python repository\n"
        "2. Analyzing the changes to determine if they need to be ported\n"
        "3. Creating corresponding changes in the TypeScript repository\n"
        "4. Submitting pull requests with the ported changes\n\n"
        
        "Currently, you can help users find the next commit that needs to be ported from "
        "the Python repository. You should explain what changes are in the commit and help "
        "users understand what needs to be ported.\n\n"
        
        "When users ask about commits or changes to port, use the find_next_commit_to_port "
        "tool to identify the next commit that needs attention. Explain the changes clearly "
        "and help users understand what files were modified and what the changes entail."
    ),
    tools=[find_next_commit_to_port],
) 