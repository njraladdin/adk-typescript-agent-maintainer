import os
import sys
from typing import Dict, List, Optional, TypedDict, Literal
from google.adk.agents import Agent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest

# Add parent directory to Python path to allow imports from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .tools.get_repo_file_structure import get_repo_file_structure
from .tools.get_file_content import get_file_content
from .tools.write_local_file import write_local_file

def gather_initial_context(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Before model callback to gather initial context about commits and repo structures."""
    print("Gathering initial context...")
    
    # Get commit details
    commit_info = callback_context.tools.get_commit_diff()  # We need to add this tool
    
    # Get both repo structures
    python_structure = callback_context.tools.get_repo_file_structure(repo="google/adk-python")
    typescript_structure = callback_context.tools.get_repo_file_structure(repo="njraladdin/adk-typescript")
    
    # Get content of all changed Python files
    changed_files = {}
    for file_path in commit_info["changed_files"]:
        if file_path.endswith(".py"):
            content = callback_context.tools.get_file_content(
                repo="google/adk-python",
                file_path=file_path
            )
            changed_files[file_path] = content
    
    # Store everything in session state
    callback_context.session.state.update({
        "commit_info": commit_info,
        "python_structure": python_structure,
        "typescript_structure": typescript_structure,
        "changed_files": changed_files
    })
    
    print(f"Initial context gathered and stored in session state. Found {len(changed_files)} changed Python files.")
    return None  # Continue with normal agent execution

# Context Gatherer Agent - Can be run independently
context_gatherer = LlmAgent(
    name="ContextGatherer",
    model="gemini-2.5-flash",
    description="Agent responsible for gathering comprehensive context from both repositories for Python to TypeScript conversion.",
    instruction="""You are a comprehensive context gatherer for Python to TypeScript conversion.

REPOSITORY CONTEXT:
- SOURCE REPOSITORY: google/adk-python 
  * This is Google's official Agent Development Kit for Python
  * Contains the original Python implementation with new commits/features
  * Initial context about the commit, repo structures, and changed files has been gathered for you
  
- TARGET REPOSITORY: njraladdin/adk-typescript
  * This is the TypeScript port of the ADK
  * Contains equivalent TypeScript implementations of Python features
  * Initial context about the repo structure has been gathered for you

YOUR TASK:
1. Review the gathered context from session state:
   - Commit information
   - Repository structures
   - Content of changed Python files
2. Find and fetch equivalent TypeScript files
3. Identify and fetch any additional context files needed

Once you have gathered all the necessary context, you should transfer to the TypeScript converter agent.
All the context you've gathered will be available to them.""",
    tools=[get_repo_file_structure, get_file_content],
    before_model_callback=gather_initial_context
)

# TypeScript Converter Agent - Can be run independently with provided context
typescript_converter = LlmAgent(
    name="TypeScriptConverterAgent",
    model="gemini-2.5-flash",
    description="Agent responsible for converting Python code to TypeScript code using the gathered context.",
    instruction="""You are a specialized Python to TypeScript Code Converter.

When you receive control, you will have access to all the context gathered by the ContextGatherer agent, including:
- The commit being converted
- Repository structures
- Content of changed Python files
- Content of related TypeScript files
- Any additional context files

Your task is to:
1. Review all the gathered context
2. Convert each Python file to its TypeScript equivalent
3. Follow TypeScript best practices and idioms
4. Add proper type definitions and documentation
5. Save the converted files in output/commit_<sha>/

Use the write_local_file tool to save your converted TypeScript files.""",
    tools=[write_local_file]
)

# Create parent agent with sub-agents
root_agent = LlmAgent(
    name="PythonToTypeScriptConverterAgent",
    model="gemini-2.5-flash",
    description="Parent agent responsible for coordinating the Python to TypeScript code conversion process.",
    instruction="""You are the main coordinator for Python to TypeScript code conversion.
Your task is to orchestrate the conversion process by:

1. First, delegating to the ContextGathererAgent to collect all necessary information
2. Then, transferring to the TypeScriptConverterAgent to perform the actual code conversion

The context will be maintained through the conversation, so all gathered information will be available.""",
    tools=[get_repo_file_structure, get_file_content, write_local_file],
    sub_agents=[context_gatherer, typescript_converter]
)

