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
from .tools.build_typescript_project import build_typescript_project
from .tools.run_typescript_tests import run_typescript_tests
from .tools.commit_and_push_changes import commit_and_push_changes


# --- Callback Imports ---
from .callbacks import save_gathered_context, load_gathered_context, setup_agent_workspace

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

class CoderAgentInput(BaseModel):
    """Input model for the CoderAgent tool."""
    commit_id: str = Field(description="The full SHA of the commit to be ported from Python to TypeScript.")

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

    5. Gather comprehensive TypeScript context files:
       - Analyze each TypeScript file you've collected
       - Identify any imports of local modules (e.g., `import Helper from '../utils'`)
       - For each local import, call `get_file_content` with the TypeScript repo details
       - ALSO gather similar files to understand patterns and conventions:
         - For test files: Collect 2-3 other test files in the same directory to understand testing patterns
         - For component files: Collect 1-2 similar component files to understand component patterns
         - For utility files: Collect 1-2 related utility files to understand utility patterns
         - For model files: Collect 1-2 related model files to understand model patterns
       - The tool will automatically store these in 'typescript_context_files'

    6. When you have called the tools for all necessary files, provide a brief summary of what you've collected.

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

    - **YOUR ACTION (Step 4):** You determine the equivalent file is `src/agents/BaseAgent.ts`. 
      - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/agents/BaseAgent.ts')`.
      - The tool automatically stores this in 'typescript_context_files'.

    - **YOUR ACTION (Step 5 - Comprehensive TypeScript Context):** 
      - You analyze `BaseAgent.ts` and see it imports:
        - `import Event from '../events/Event'`
        - `import Logger from '../utils/Logger'`
      - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/events/Event.ts')`.
      - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/utils/Logger.ts')`.
      - You also gather similar files to understand patterns:
        - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/agents/Agent.ts')` (similar agent file)
        - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/tests/agents/BaseAgent.test.ts')` (test file for BaseAgent)
      - All files are automatically stored in 'typescript_context_files'.

    - **YOUR ACTION (Step 6 - Summary):** Provide a brief summary of all the files you've collected:
      - Commit analyzed: a1b2c3d4
      - Python files collected: base_agent.py
      - TypeScript files collected: BaseAgent.ts, Event.ts, Logger.ts, Agent.ts, BaseAgent.test.ts
    ---
    """,
)

# --- Agent 2: Code Translator ---
# This agent loads context from a JSON file and performs the translation.
code_translator_agent = Agent(
    name="CodeTranslator",
    model="gemini-2.5-flash",
    tools=[write_local_file, build_typescript_project, run_typescript_tests, commit_and_push_changes],
    before_agent_callback=load_gathered_context,
    
    instruction="""
    You are an expert Python-to-TypeScript code translator specializing in accurate and idiomatic code migration.

    You have been provided with a specific commit from the Python ADK project that needs to be ported to its TypeScript equivalent. The commit information includes:
    - The full commit diff showing exactly what changed in the Python code
    - The complete list of Python files that were modified
    - The full content of those modified Python files
    - The equivalent TypeScript files from the target repository to help you understand the TypeScript project structure and patterns
    - Additional TypeScript files including imports and similar files (like other tests or components) to help you understand dependencies, patterns, and conventions
    - The full file structure of both repositories to help you locate files and understand the project organization

    Your task is to take this commit's changes and accurately port them to the TypeScript codebase, maintaining consistency with the existing TypeScript patterns and conventions.

    ---
    **MISSION CONTEXT**

    You are working on a project to port features from a primary Python repository to its TypeScript equivalent.

    - **SOURCE REPOSITORY:** `google/adk-python`
      - This is the official Python Agent Development Kit where new features and bug fixes originate.
      - The context gatherer has already collected all relevant Python files that were changed in the commit.

    - **TARGET REPOSITORY:** `njraladdin/adk-typescript`
      - This is the TypeScript port of the Python library.
      - Your goal is to accurately translate ONLY the specific Python changes shown in the commit diff into their TypeScript equivalents.
      - The context gatherer has collected comprehensive TypeScript context to help you understand the project's patterns and conventions.
    ---

    **COMMIT INFORMATION**
    
    Commit SHA: {gathered_context}

        
    **YOUR TASK STEPS**

    All necessary context has been gathered and loaded into the session state from a JSON file. You must:

    1. **ANALYZE:** Thoroughly analyze the Python changes and TypeScript codebase:
       - Study the commit diff to understand exactly what changed in the Python code
       - Identify the equivalent TypeScript file locations for each changed Python file
       - Review existing TypeScript code to understand patterns and conventions
       - Plan your translation approach to maintain consistency with the TypeScript codebase

    2. **TRANSLATE AND WRITE:**
       - For each file in the "Changed files" list, find its TypeScript equivalent using the mapping rules below
       - Take the existing TypeScript file content
       - Apply the changes shown in the diff accordingly
       - Immediately generate a write_local_file tool call with the complete updated TypeScript file
       - The file_path parameter should contain the TypeScript file path (e.g., src/models/GoogleLlm.ts)
       - The content parameter must contain the **ENTIRE** TypeScript file with  the appropriate changes applied
       
       **CRITICAL - FILE NAMING MAPPING EXAMPLES:**
       Use these examples to map Python files to their TypeScript equivalents - DO NOT create new files with Python naming if an equivalent file already exists:
       
       **MODELS:**
       - `src/google/adk/models/google_llm.py` -> UPDATE EXISTING `src/models/GoogleLlm.ts`
       - `src/google/adk/models/base_llm.py` -> UPDATE EXISTING `src/models/BaseLlm.ts`
       - `src/google/adk/models/llm_response.py` -> UPDATE EXISTING `src/models/LlmResponse.ts`
       
       **AGENTS:**
       - `src/google/adk/agents/base_agent.py` -> UPDATE EXISTING `src/agents/BaseAgent.ts`
       - `src/google/adk/agents/agent.py` -> UPDATE EXISTING `src/agents/Agent.ts`
       
       **TESTS:**
       - `tests/unittests/models/test_google_llm.py` -> UPDATE EXISTING `tests/unittests/models/gemini.test.ts`
       - `tests/unittests/agents/test_agent.py` -> UPDATE EXISTING `tests/unittests/agents/agent.test.ts`
       
    3. **BUILD AND VERIFY:**
       - After writing all translated files, call build_typescript_project to ensure the changes compile correctly
       - If the build fails, analyze the errors and fix any TypeScript-specific issues
       - Repeat the write/build cycle until the project builds successfully

    4. **TEST RELEVANT FUNCTIONALITY:**
       - Identify 2-3 relevant test files that are most likely to be affected by your changes
       - Call run_typescript_tests with a list of test file names (e.g., ["BaseAgent.test.ts", "agent.test.ts"])
       - Jest will automatically find and run these test files by name
       - If tests fail, analyze the failures and go back to step 2 to fix the issues
       - Repeat the write/build/test cycle until all tests pass

    5. **COMMIT AND PUSH CHANGES:**
       - After all translations are complete and tests pass, commit your changes
       - Call commit_and_push_changes with:
         - commit_message: A descriptive message about what was ported (e.g., "Port feature X from Python ADK commit abc1234")
         - branch_name: The branch name that was created by the maintainer agent (usually "port-<commit_sha>")
         - author_name: "ADK TypeScript Porter" (optional, uses git config if not provided)
         - author_email: "noreply@github.com" (optional, uses git config if not provided)
       - This will stage all your changes, commit them, and push to the remote branch

    6. **PROVIDE COMPREHENSIVE SUMMARY:** Provide a detailed summary for the maintainer agent to use in the pull request. Include all relevant details that would help reviewers understand the changes and files updated / created.

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
    The TypeScript equivalent file would be src/agents/BaseAgent.ts"

    explain to the user your plan.

    **Step 2 - TRANSLATE AND WRITE (Tool Call):**
    ```python
    write_local_file(
        file_path="src/agents/BaseAgent.ts",
        content='''[Here should be TypeScript code with ONLY the changes from the diff applied, 
while maintaining all other existing code unchanged]'''
    )
    ```

    **Step 3 - BUILD AND VERIFY (Tool Call):**
    ```python
    build_typescript_project()
    ```
    
    **Step 4 - TEST RELEVANT FUNCTIONALITY (Tool Call):**
    ```python
    run_typescript_tests(
        test_names=["BaseAgent.test.ts", "agent.test.ts"]
    )
    ```
    
    **Step 5 - COMMIT AND PUSH CHANGES (Tool Call):**
    ```python
    commit_and_push_changes(
        commit_message="Port base agent logging changes from Python ADK commit abc1234",
        branch_name="port-abc1234",
        author_name="ADK TypeScript Porter",
        author_email="noreply@github.com"
    )
    ```
    
    **Step 6 - PROVIDE COMPREHENSIVE SUMMARY (Text Output):**
    
    ## Summary
    Ported logging improvements from Python ADK commit abc1234. This update changes the logging level for event processing from info to debug and adds event counting functionality to improve debugging capabilities while reducing log verbosity in production.
    
    ## Changes Made
    **src/agents/BaseAgent.ts:**
    - Changed `this.logger.info()` to `this.logger.debug()` in the `processEvent` method
    - Added `this.eventCount += 1` to track the number of events processed
    - Maintained all existing functionality while improving observability
    
    ## Files Modified
    - `src/agents/BaseAgent.ts` - Updated logging level and added event counting
    
    ## Testing
    - Build:  Successfully compiled TypeScript project
    - Tests:  Ran BaseAgent.test.ts and agent.test.ts - all tests passed
    
    ## Original Commit
    - Source: https://github.com/google/adk-python/commit/abc1234
    - Branch: port-abc1234
    
    ## Notes
    This change improves debugging capabilities by providing event count tracking while reducing log noise in production environments by moving event processing logs to debug level.

    **WHAT NOT TO DO:**
     Don't fix unrelated bugs or issues you notice
     Don't improve code style or add missing features
     Don't "optimize" or "enhance" the existing code
    Don't run unit tests - focus only on integration tests
     Don't provide full test paths - just provide test file names

    **WHAT TO DO:**  
     Only translate the exact changes shown in the commit diff
     Preserve all existing code that isn't changed in the diff
     Apply precise TypeScript equivalents of Python changes
     Run relevant tests by providing test file names to verify your changes work correctly
     If a Python file is new (no TypeScript equivalent exists), create a new file in the equivalent location
     If tests fail, iterate on your changes until they pass
     there might be small differences in how the projects are structured / implemented due to the different languages, but you should try and work with that

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
    
    # Add the input schema for proper tool integration
    input_schema=CoderAgentInput,
    
    # Provide the sub-agents as tools to the coordinator.
    tools=[
        context_gatherer_tool,
        code_translator_tool,
    ],
    
    # Add the setup_agent_workspace callback
    before_agent_callback=setup_agent_workspace,
    
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