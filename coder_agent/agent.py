import os
import sys
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

# --- ADK Imports ---
from google.adk.agents import Agent
from google.adk.tools import agent_tool

# --- Tool Imports ---
# Make sure these tool files exist in a 'tools' subdirectory
# and the functions are correctly implemented.
from .tools.get_commit_diff import get_commit_diff
from .tools.get_repo_file_structure import get_repo_file_structure
from .tools.get_file_content import get_file_content
from .tools.write_local_file import write_local_file

# --- Callback Imports ---
from .callbacks import save_gathered_context

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


# ==============================================================================
# 2. DEFINE THE SUB-AGENTS
# ==============================================================================

# --- Agent 1: Context Gatherer ---
# This agent's only job is to collect all information and store it in session state.
context_gatherer_agent = Agent(
    name="ContextGatherer",
    model="gemini-2.5-flash",
    tools=[get_commit_diff, get_repo_file_structure, get_file_content],
    after_agent_callback=save_gathered_context,
    
    instruction="""
    You are an expert context gatherer for a code migration project. Your sole purpose is to populate a complete context object in the session state by calling the necessary tools. The tools will automatically update the session state for you.

    ---
    **MISSION CONTEXT**

    You are working on a project to port features from a primary Python repository to its TypeScript equivalent.

    - **SOURCE REPOSITORY:** `google/adk-python`
      - This is the official Python Agent Development Kit where new features and bug fixes originate.
      - You will be given a commit from this repository to analyze.

    - **TARGET REPOSITORY:** `njraladdin/adk-typescript`
      - This is the TypeScript port of the Python library.
      - Your goal is to gather all the necessary context so that another agent can accurately replicate the Python commit's changes in this TypeScript repository.
    ---

    **YOUR TASK STEPS**

    You will be given a commit SHA as input. You must perform the following steps by calling the appropriate tools:

    1. Call `get_commit_diff` with the provided commit SHA to get the list of changed files.
       - The tool will automatically store commit info in the session state.

    2. Call `get_repo_file_structure` for both repositories:
       - For Python: repo='google/adk-python'
       - For TypeScript: repo='njraladdin/adk-typescript'
       - The tool will automatically store repo structures in the session state.

    3. For each changed Python file from the commit diff, call `get_file_content` with:
       - repo='google/adk-python'
       - file_path=<path to the Python file>
       - The tool will automatically store these in 'python_context_files'.

    4. For each equivalent TypeScript file you identify (if any), call `get_file_content` with:
       - repo='njraladdin/adk-typescript'
       - file_path=<path to the TypeScript file>
       - The tool will automatically store these in 'typescript_context_files'.

    5. Gather additional Python context files:
       - Analyze each Python file you've collected
       - Identify any imports of local modules (e.g., `from ..utils import helper`)
       - For each local import, call `get_file_content` with the Python repo details
       - The tool will automatically store these in 'python_context_files'

    6. Gather additional TypeScript context files:
       - Analyze each TypeScript file you've collected
       - Identify any imports of local modules (e.g., `import  Helper  from '../utils'`)
       - For each local import, call `get_file_content` with the TypeScript repo details
       - The tool will automatically store these in 'typescript_context_files'

    7. When you have called the tools for all necessary files, provide a brief summary of what you've collected.

    ---
    **EXAMPLE SCENARIO**

    - **INPUT:** Commit 'a1b2c3d4'

    - **YOUR ACTION (Step 1):** Call `get_commit_diff(repo='google/adk-python', commit_sha='a1b2c3d4')`.
      - Result: Changed file is `google/adk/agents/base_agent.py`.
      - The tool automatically stores this in the session state under 'commit_info'.

    - **YOUR ACTION (Step 2):** 
      - Call `get_repo_file_structure(repo='google/adk-python')`.
      - Call `get_repo_file_structure(repo='njraladdin/adk-typescript')`.
      - The tool automatically stores these in 'python_repo_structure' and 'typescript_repo_structure'.

    - **YOUR ACTION (Step 3):** Call `get_file_content(repo='google/adk-python', file_path='google/adk/agents/base_agent.py')`.
      - The tool automatically stores this in 'python_context_files'.

    - **YOUR ACTION (Step 4):** You determine the equivalent file is `src/agents/base-agent.ts`. 
      - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/agents/base-agent.ts')`.
      - The tool automatically stores this in 'typescript_context_files'.

    - **YOUR ACTION (Step 5 - Additional Python Context):** You analyze `base_agent.py` and see it imports:
      - `from ..events.event import Event`
      - `from ..utils.logger import Logger`
      - Call `get_file_content(repo='google/adk-python', file_path='google/adk/events/event.py')`.
      - Call `get_file_content(repo='google/adk-python', file_path='google/adk/utils/logger.py')`.
      - Both files are automatically stored in 'python_context_files'.

    - **YOUR ACTION (Step 6 - Additional TypeScript Context):** You analyze `base-agent.ts` and see it imports:
      - `import  Event  from '../events/event'`
      - `import Logger  from '../utils/logger'`
      - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/events/event.ts')`.
      - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/utils/logger.ts')`.
      - Both files are automatically stored in 'typescript_context_files'.

    - **YOUR ACTION (Step 7 - Summary):** Provide a brief summary of all the files you've collected:
      - Commit analyzed: a1b2c3d4
      - Python files collected: base_agent.py, event.py, logger.py
      - TypeScript files collected: base-agent.ts, event.ts, logger.ts
    ---
    """,
)

# --- Agent 2: Code Translator ---
# This agent receives the context from session state and performs the translation.
code_translator_agent = Agent(
    name="CodeTranslator",
    model="gemini-2.5-flash",
    tools=[write_local_file],
    
    instruction="""
    You are an expert Python-to-TypeScript developer specializing in code migration.
    All the necessary context has been gathered and stored in the session state by the previous agent.
    The session state contains:
    - commit_info: Details about the source commit including SHA, diff, and changed files
    - python_repo_structure: The file structure of the Python repository
    - typescript_repo_structure: The file structure of the TypeScript repository  
    - python_context_files: Content of all Python files (both changed files and additional context)
    - typescript_context_files: Content of all TypeScript files (both equivalent files and additional context)

    YOUR TASK:
    1.  Access and analyze the gathered context from the session state.
    2.  For each changed Python file, write the new, updated TypeScript equivalent, applying the logic from the Python diff.
    3.  Ensure your code adheres to TypeScript best practices, is well-typed, and idiomatic.
    4.  Use the `write_local_file` tool to save each newly generated TypeScript file. The path should be relative to an `output/` directory (e.g., 'output/src/new-file.ts').
    5.  After all files are written, provide a summary of what was translated and confirm that all files have been saved.

    Remember: All the context you need is already available in the session state - you don't need to fetch any additional information.
    """
)


# ==============================================================================
# 3. WRAP SUB-AGENTS AS TOOLS
# ==============================================================================

context_gatherer_tool = agent_tool.AgentTool(agent=context_gatherer_agent)
code_translator_tool = agent_tool.AgentTool(agent=code_translator_agent)


# ==============================================================================
# 4. DEFINE THE FLEXIBLE ROOT AGENT (for interactive use)
# ==============================================================================

# This is the agent you will interact with directly via chat.
root_agent = Agent(
    name="CodePorterCoordinator",
    model="gemini-2.5-flash",
    
    # Provide the sub-agents as tools to the coordinator.
    tools=[
        context_gatherer_tool,
        code_translator_tool,
    ],
    
    instruction="""
    You are an expert coordinator for a code porting workflow. You have two main sub-agents available as tools:
    1.  `ContextGatherer(commit_id: str)`: Use this tool to collect all necessary files and context for a given commit. The tool will automatically store all gathered information in the session state, organizing files into 'python_context_files' and 'typescript_context_files'.
    2.  `CodeTranslator()`: Use this tool to perform the actual code translation. It will automatically access the context from the session state that was populated by the ContextGatherer.

    Your job is to understand the user's request and orchestrate the workflow.

    - If the user provides a commit ID and asks to start the full porting process, you MUST first call the `ContextGatherer` tool with the commit ID. After it completes successfully, call the `CodeTranslator` tool to finish the job.
    
    - If the user explicitly asks to ONLY gather context for a commit ID, just call the `ContextGatherer` tool and report on what was collected.
    
    - If the user asks to ONLY translate (assuming context is already gathered), call the `CodeTranslator` tool.

    The session state automatically handles data persistence between the two agents, so you don't need to worry about passing data manually.
    """,
)