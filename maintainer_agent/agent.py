import os
import sys
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

# Add parent directory to Python path to allow imports from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- ADK Imports ---
from google.adk.agents import Agent
from google.adk.tools import agent_tool

# --- Coder Agent Tool Imports ---
from .tools.get_file_content import get_file_content, get_files_content
from .tools.write_local_file import write_local_file
from .tools.build_typescript_project import build_typescript_project
from .tools.run_typescript_tests import run_typescript_tests

# --- Maintainer Agent Tool Imports ---
from .tools.publish_port_to_github import publish_port_to_github


# --- Callback Imports ---
from .callbacks import save_gathered_context, load_gathered_context, setup_agent_workspace, gather_commit_context

# ==============================================================================
# 1. DEFINE THE STRUCTURED DATA MODELS
# ==============================================================================

class CommitInfo(BaseModel):
    """Holds information about a specific commit."""
    commit_sha: str = Field(description="The full SHA of the commit.")
    diff: str = Field(description="The diff output of the commit.")
    changed_files: List[str] = Field(description="A list of file paths that were changed in the commit.")

class GatheredContext(BaseModel):
    """
    A structured data model to hold all the context required for porting
    a commit from Python to TypeScript.
    """
    commit_info: CommitInfo = Field(description="Detailed information about the source commit.")
    python_repo_structure: Dict = Field(description="The file and directory structure of the Python repository.")
    typescript_repo_structure: Dict = Field(description="The file and directory structure of the TypeScript repository.")
    source_python_files: Dict[str, str] = Field(description="A dictionary mapping the path of each changed Python file to its full content.")
    equivalent_typescript_files: Dict[str, str] = Field(description="A dictionary mapping the path of equivalent TypeScript files to their full content.")
    additional_context_files: Dict[str, str] = Field(description="A dictionary for any other files that were fetched for additional context.")

class AgentInput(BaseModel):
    """Input model for both Coder and Maintainer agents."""
    commit_id: str = Field(description="The full SHA of the commit to be ported from Python to TypeScript.")

# ==============================================================================
# 2. DEFINE THE CODER SUB-AGENTS
# ==============================================================================

# --- Agent 1: Initial Context Gatherer ---
initial_context_gatherer_agent = Agent(
    name="initial_context_gatherer_agent",
    model="gemini-2.5-flash",
    tools=[get_files_content],
    before_agent_callback=gather_commit_context,
    after_agent_callback=save_gathered_context,
    
    instruction="""
    You are an initial context gatherer. Your job is simple: analyze the commit and fetch the most obviously relevant TypeScript files in one batch.

    ---
    **AVAILABLE CONTEXT**
    
    **Commit Information:**
    {commit_context}

    **TypeScript Repository Structure:**
    {typescript_repo_structure}

    **YOUR SIMPLE TASK**

    1. **Analyze the commit** - Look at what Python files changed and understand the basic functionality
    
    2. **Make ONE batch fetch** - Use `get_files_content` to fetch the most obviously relevant TypeScript files:
       - Direct TypeScript equivalents of changed Python files
       - Related base classes or interfaces 
       - A few test files for pattern understanding
       - Common dependencies you can easily identify

    **Keep it simple** - Don't overthink it. Just get the obvious files that the coder will definitely need. The coder agent can fetch more specific files later if needed.

    **Example:** 
    For Python file `google/adk/agents/base_agent.py`, fetch:
    ```
    get_files_content(
        repo='njraladdin/adk-typescript',
        file_paths=[
            'src/agents/BaseAgent.ts',           # Direct equivalent  
            'src/agents/Agent.ts',               # Related agent
            'tests/agents/BaseAgent.test.ts',    # Test patterns
            'src/types/AgentTypes.ts'            # Type definitions
        ]
    )
    ```

    That's it. Keep it straightforward.
    """,
)

# --- Agent 2: Coder ---
coder_agent = Agent(
    name="coder_agent",
    model="gemini-2.5-flash",
    tools=[get_files_content, write_local_file, build_typescript_project, run_typescript_tests],
    before_agent_callback=load_gathered_context,
    
    instruction="""
    You are an expert Python-to-TypeScript code translator. You work adaptively - fetching additional context as needed, just like a human developer.

    ---
    **MISSION CONTEXT**

    You are working on a project to port features from a primary Python repository to its TypeScript equivalent.

    - **SOURCE REPOSITORY:** `google/adk-python`
      - This is the official Python Agent Development Kit where new features and bug fixes originate.
      - The context gatherer has already collected all relevant Python files that were changed in the commit.

    - **TARGET REPOSITORY:** `njraladdin/adk-typescript`
      - This is the TypeScript port of the Python library.
      - Your goal is to accurately translate the specific Python changes shown in the commit diff into their TypeScript equivalents.
      - The context gatherer has collected comprehensive TypeScript context to help you understand the project's patterns and conventions.
    ---

    **AVAILABLE CONTEXT**

    **Commit Information:**
    {commit_context}

    **TypeScript Repository Structure:**
    {typescript_repo_structure}

    **Initial TypeScript Files:**
    {typescript_files}

    **YOUR WORKFLOW**

    You have initial TypeScript context and need to translate the Python commit changes to TypeScript:

    **Translate & Fetch Context as Needed:**
    - Start translating the Python changes to their TypeScript equivalents
    - **If you need more context** (imports, patterns, examples), use `get_files_content` to fetch additional files
    - **If you encounter unfamiliar patterns**, fetch related files to understand the TypeScript conventions
    - **If you need to understand interfaces or types**, fetch type definition files
    - Work iteratively - translate, fetch context, translate more

    **Write Files:**
    - Use `write_local_file` to write the updated TypeScript files
    - Apply only the changes from the commit diff, keeping existing code unchanged

    **Build & Test:**
    - Use `build_typescript_project` to ensure compilation
    - Use `run_typescript_tests` on relevant test files
    - If errors occur, fetch more context or fix issues as needed

    **Key Principles:**
    - **Fetch context on-demand** - Don't guess, get the files you need when you need them
    - **Be adaptive** - If something doesn't make sense, fetch more examples
    - **Work iteratively** - Code a bit, research a bit, code more
    - **Use batch fetching** - When you know you need multiple files, fetch them together

    **Example Adaptive Workflow:**
    ```
    # Start translating BaseAgent.ts, realize I need to understand event handling
    get_files_content(repo='njraladdin/adk-typescript', file_paths=['src/events/Event.ts', 'src/events/EventHandler.ts'])
    
    # Continue coding, encounter a build error about missing interface
    get_files_content(repo='njraladdin/adk-typescript', file_paths=['src/types/LlmTypes.ts'])
    
    # Finish translation and test
    ```

    Work naturally and adaptively - you have the tools to get any context you need.
    """,
)

# ==============================================================================
# 3. WRAP SUB-AGENTS AS TOOLS
# ==============================================================================

context_gatherer_tool = agent_tool.AgentTool(agent=initial_context_gatherer_agent)
coder_agent_tool = agent_tool.AgentTool(agent=coder_agent)

# ==============================================================================
# 4. DEFINE THE MAINTAINER AGENT 
# ==============================================================================

maintainer_agent = Agent(
    name="maintainer_agent",
    model="gemini-2.5-flash",
    
    # Add the input schema for proper tool integration
    input_schema=AgentInput,
    
    description=(
        "Main agent for porting specific commits from google/adk-python to njraladdin/adk-typescript. "
        "Handles the complete workflow: gathering context, translating code, building, testing, and publishing to GitHub."
    ),
    
    # Provide all the tools needed for the complete workflow
    tools=[
        context_gatherer_tool,
        coder_agent_tool,
        publish_port_to_github,
    ],
    
    # Add the setup_agent_workspace callback
    before_agent_callback=setup_agent_workspace,
    
    instruction="""
    You are the main agent for porting specific commits from the Python ADK repository to its TypeScript equivalent. 
    You handle the complete end-to-end workflow from gathering context to publishing on GitHub.

    **WORKFLOW:**
    1. **Gather Context** - Use ContextGatherer to collect all necessary files and context for the commit
    2. **Translate Code** - Use Coder to translate, build, and test the Python code to TypeScript  
    3. **Publish to GitHub** - Use publish_port_to_github to handle all GitHub operations in one call

    **STEPS:**
    Given a commit hash (e.g., 'abc1234'), you will:

    1. **Gather Context**:
       - Use `ContextGatherer(commit_id='abc1234')` to collect all necessary files and context
       - This will gather commit info, Python files, TypeScript equivalents, and related files

    2. **Translate Code**:
       - Use `Coder()` to translate the Python code to TypeScript
       - The Coder will load the context, translate files, build, and test
       - If Coder fails, stop here (no GitHub operations needed)

    3. **Publish to GitHub** (only if code translation succeeds):
       - Use `publish_port_to_github(commit_sha='abc1234')`
       - This will automatically create issue, branch, commit, push, and PR

    **EXAMPLE - FULL WORKFLOW:**
    User: 'Port commit abc1234'

    Step 1: `ContextGatherer(commit_id='abc1234')`
    → [SUCCESS] Gathered context for 3 Python files and their TypeScript equivalents

    Step 2: `Coder()`
    → [SUCCESS] Translated files, build successful, tests passing

    Step 3: `publish_port_to_github(commit_sha='abc1234')`
    → [SUCCESS] Created issue #45, branch port-abc1234, and PR #12

    **EXAMPLE - CODE TRANSLATION FAILURE:**
    User: 'Port commit ghi9012'

    Step 1: `ContextGatherer(commit_id='ghi9012')`
    → [SUCCESS] Context gathered

    Step 2: `Coder()`
    → [FAILED] TypeScript compilation errors
    → Stop here (no GitHub operations performed)

    **PARTIAL OPERATIONS:**
    You can also handle specific requests:
    - 'Gather context for commit abc123' → Use `ContextGatherer` only
    - 'Translate the gathered context' → Use `Coder` only  
    - 'Publish commit abc123 to GitHub' → Use `publish_port_to_github` only
    """,
)

# ==============================================================================
# 5. SET DEFAULT ROOT AGENT
# ==============================================================================

# For backwards compatibility, export maintainer_agent as root_agent
root_agent = maintainer_agent