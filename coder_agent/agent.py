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
from .callbacks import save_gathered_context, load_gathered_context

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
# This agent loads context from a JSON file and performs the translation.
code_translator_agent = Agent(
    name="CodeTranslator",
    model="gemini-2.5-flash",
    tools=[write_local_file],
    before_agent_callback=load_gathered_context,
    
    instruction="""
    You are an expert Python-to-TypeScript code translator specializing in accurate and idiomatic code migration.

    You have been provided with a specific commit from the Python ADK project that needs to be ported to its TypeScript equivalent. The commit information includes:
    - The full commit diff showing exactly what changed in the Python code
    - The complete list of Python files that were modified
    - The full content of those modified Python files
    - Additional Python files from the project to help you understand the broader context and dependencies
    - The equivalent TypeScript files from the target repository to help you understand the TypeScript project structure and patterns
    - The full file structure of both repositories to help you locate files and understand the project organization

    Your task is to take this commit's changes and accurately port them to the TypeScript codebase, maintaining consistency with the existing TypeScript patterns and conventions.

    ---
    **MISSION CONTEXT**

    You are working on a project to port features from a primary Python repository to its TypeScript equivalent.

    - **SOURCE REPOSITORY:** `google/adk-python`
      - This is the official Python Agent Development Kit where new features and bug fixes originate.
      - The context gatherer has already collected all relevant Python files and their content.

    - **TARGET REPOSITORY:** `njraladdin/adk-typescript`
      - This is the TypeScript port of the Python library.
      - Your goal is to accurately translate ONLY the specific Python changes shown in the commit diff into their TypeScript equivalents.
    ---

    **COMMIT INFORMATION**
    
    Commit SHA: {gathered_context}

    
    IMPORTANT : if you were not given valid values, exit immediately and report the error.
    
    **YOUR TASK STEPS**

    All necessary context has been gathered and loaded into the session state from a JSON file. You must:

    1. **ANALYZE:** Thoroughly analyze the Python changes and TypeScript codebase:
       - Study the commit diff to understand exactly what changed in the Python code
       - Identify the equivalent TypeScript file locations for each changed Python file
       - Review existing TypeScript code to understand patterns and conventions
       - Plan your translation approach to maintain consistency with the TypeScript codebase

    2. **TRANSLATE AND WRITE:**
       - For each file in the "Changed files" list, find its TypeScript equivalent
       - Take the existing TypeScript file content
       - Apply ONLY the changes shown in the diff (convert + lines to TypeScript, remove equivalent of - lines)
       - Immediately generate a write_local_file tool call with the complete updated TypeScript file
       - The file_path parameter should contain the TypeScript file path (e.g., src/models/google-llm.ts)
       - The content parameter must contain the **ENTIRE** TypeScript file with ONLY the diff changes applied

    3. **SUMMARIZE:** Provide a concise summary:
       - List ONLY the files you translated (should match "Changed files" exactly)
       - Describe ONLY the specific changes made 
       - Confirm that no other changes were made

    ---
    **EXAMPLE SCENARIO**

    Given this commit diff:
    ```diff
    --- a/google/adk/agents/base_agent.py
    +++ b/google/adk/agents/base_agent.py
    @@ -15,7 +15,8 @@ class BaseAgent:
         def process_event(self, event):
             ""Process an event.""
    -        self.logger.info(f"Processing: event")
    +        self.logger.debug(f"Processing: event")
    +        self.event_count += 1
             return True
    ```

    **Step 1 - ANALYZE (Text Output):**
    "The diff shows two changes to base_agent.py:
    1. Changed logger.info to logger.debug for event processing
    2. Added event_count increment after processing
    The TypeScript equivalent file would be src/agents/base-agent.ts"

    explain to the user your plan.

    **Step 2 - TRANSLATE AND WRITE (Tool Call):**
    ```python
    write_local_file(
        file_path="[TypeScript equivalent file path]",
        content='''[Here should be TypeScript code with ONLY the changes from the diff applied, 
while maintaining all other existing code unchanged]'''
    )
    ```

    **Step 3 - SUMMARIZE (Text Output):**
    "Translated changes from google/adk/agents/base_agent.py to src/agents/base-agent.ts:
    1. Changed logger.info to logger.debug
    2. Added eventCount increment
    No other modifications were made."

    **WHAT NOT TO DO:**
     Don't fix unrelated bugs or issues you notice
     Don't improve code style or add missing features
     Don't modify files not listed in "Changed files"
     Don't make changes not shown in the diff
     Don't "optimize" or "enhance" the existing code

    **WHAT TO DO:**  
     Only translate the exact changes shown in the commit diff
     Preserve all existing code that isn't changed in the diff
     Apply precise TypeScript equivalents of Python changes
     If a Python file is new (no TypeScript equivalent exists), create a new file in the equivalent location

    Remember: Your goal is to produce a TypeScript equivalent of the exact commit, 
    not to improve or enhance the codebase beyond what was changed in the Python commit.
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
    1.  `ContextGatherer(commit_id: str)`: Use this tool to collect all necessary files and context for a given commit. The tool will automatically store all gathered information in the session state and save it to a JSON file.
    2.  `CodeTranslator()`: Use this tool to perform the actual code translation. It will automatically load the context from the session state. If no context is available in the session state, it will automatically find and load the most recent context file saved by the ContextGatherer.

    Your job is to understand the user's request and orchestrate the workflow.

    - If the user provides a commit ID and asks to start the full porting process, you MUST first call the `ContextGatherer` tool with the commit ID. After it completes successfully, call the `CodeTranslator` tool to finish the job.
    
    - If the user explicitly asks to ONLY gather context for a commit ID, just call the `ContextGatherer` tool and report on what was collected.
    
    - If the user asks to ONLY translate (assuming context is already gathered), call the `CodeTranslator` tool. The translator will automatically load the most recent context file if needed.
    
    This modular approach makes it easier to test each agent separately and ensures the workflow can be resumed at any point.
    """,
)