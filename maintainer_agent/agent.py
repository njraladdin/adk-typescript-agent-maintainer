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
from .tools.get_commit_diff import get_commit_diff
from .tools.get_repo_file_structure import get_repo_file_structure
from .tools.get_file_content import get_file_content
from .tools.write_local_file import write_local_file
from .tools.build_typescript_project import build_typescript_project
from .tools.run_typescript_tests import run_typescript_tests
from .tools.commit_and_push_changes import commit_and_push_changes

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

# --- Agent 1: Context Gatherer ---
context_gatherer_agent = Agent(
    name="ContextGatherer",
    model="gemini-2.5-flash",
    tools=[get_file_content],
    before_agent_callback=gather_commit_context,
    after_agent_callback=save_gathered_context,
    
    instruction="""
    You are an expert context gatherer for a code migration project. Your purpose is to gather comprehensive TypeScript context by analyzing the basic context that has already been collected for you.

    ---
    **MISSION CONTEXT**

    You are working on a project to port features from a primary Python repository to its TypeScript equivalent.

    - **SOURCE REPOSITORY:** `google/adk-python`
      - This is the official Python Agent Development Kit where new features and bug fixes originate.

    - **TARGET REPOSITORY:** `njraladdin/adk-typescript`
      - This is the TypeScript port of the Python library.
      - Your goal is to gather comprehensive TypeScript context to help another agent accurately replicate the Python commit's changes.
    ---

    **AVAILABLE CONTEXT**
    
    The following information has already been gathered and is available in your session state:

    **Commit Information:**
    {commit_context}

    **TypeScript Repository Structure:**
    {typescript_repo_structure}

    **YOUR TASK**

    Your job is to gather comprehensive TypeScript context files to help the translation agent understand TypeScript patterns and conventions:

    1. **Identify Equivalent TypeScript Files:**
       - For each changed Python file, determine its TypeScript equivalent using the repository structure
       - Call `get_file_content` with repo='njraladdin/adk-typescript' and the TypeScript file path
       - The tool will automatically store these in the 'typescript_files' session state

    2. **Gather Comprehensive TypeScript Context:**
       - Analyze each TypeScript file you've collected
       - Identify any imports of local modules (e.g., `import Helper from '../utils'`)
       - For each local import, call `get_file_content` with the TypeScript repo details
       - ALSO gather similar files to understand patterns and conventions:
         - For test files: Collect 2-3 other test files in the same directory to understand testing patterns
         - For component files: Collect 1-2 similar component files to understand component patterns
         - For utility files: Collect 1-2 related utility files to understand utility patterns
         - For model files: Collect 1-2 related model files to understand model patterns
       - The tool will automatically store these in the 'typescript_files' session state

    ---
    **EXAMPLE WORKFLOW**

    Given the Python changed file `google/adk/agents/base_agent.py`:

    1. **Identify equivalent:** The TypeScript equivalent would be `src/agents/BaseAgent.ts`
       - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/agents/BaseAgent.ts')`

    2. **Gather dependencies:** Analyze `BaseAgent.ts` and see it imports:
       - `import Event from '../events/Event'`
       - `import Logger from '../utils/Logger'`
       - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/events/Event.ts')`
       - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/utils/Logger.ts')`

    3. **Gather patterns:** To understand agent patterns:
       - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='src/agents/Agent.ts')` (similar agent file)
       - Call `get_file_content(repo='njraladdin/adk-typescript', file_path='tests/agents/BaseAgent.test.ts')` (test file)

    ---
    """,
)

# --- Agent 2: Code Translator ---
code_translator_agent = Agent(
    name="CodeTranslator",
    model="gemini-2.5-flash",
    tools=[write_local_file, build_typescript_project, run_typescript_tests],
    before_agent_callback=load_gathered_context,
    
    instruction="""
    You are an expert Python-to-TypeScript code translator specializing in accurate and idiomatic code migration.

    You have been provided with a specific commit from the Python ADK project that needs to be ported to its TypeScript equivalent. The commit information includes:
    - The full commit diff showing exactly what changed in the Python code
    - The complete list of Python files that were modified
    - The full content of those modified Python files
    - The relevant TypeScript files from the target repository to help you understand the TypeScript project structure and patterns
    - The TypeScript repository structure to help you locate files and understand the project organization

    Your task is to take this commit's changes and accurately port them to the TypeScript codebase, maintaining consistency with the existing TypeScript patterns and conventions.

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

    **TypeScript Context Files:**
    {typescript_files}
        
    **YOUR TASK STEPS**

    All necessary context has been gathered and loaded into the session state. You must work with ONLY the provided context. You must:

    1. **TRANSLATE AND WRITE:**
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
       
    2. **BUILD AND VERIFY:**
       - After writing all translated files, call build_typescript_project to ensure the changes compile correctly
       - If the build fails, analyze the errors and fix any TypeScript-specific issues

    3. **TEST RELEVANT FUNCTIONALITY:**
       - Identify 2-3 relevant test files that are most likely to be affected by your changes
       - Call run_typescript_tests with a list of test file names (e.g., ["BaseAgent.test.ts", "agent.test.ts"])
       - Jest will automatically find and run these test files by name
       - If tests fail, analyze the failures and go back to step 1 to fix the issues

    **IMPORTANT:** After completing all translations, building successfully, and passing tests, you are DONE. 

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

    **Step 1 - TRANSLATE AND WRITE (Tool Call):**
    ```python
    write_local_file(
        file_path="src/agents/BaseAgent.ts",
        content='''[Here should be TypeScript code with ONLY the changes from the diff applied, 
while maintaining all other existing code unchanged]'''
    )
    ```

    **Step 2 - BUILD AND VERIFY (Tool Call):**
    ```python
    build_typescript_project()
    # If build fails, analyze errors and fix any TypeScript-specific issues
    ```
    
    **Step 3 - TEST RELEVANT FUNCTIONALITY (Tool Call):**
    ```python
    run_typescript_tests(
        test_names=["BaseAgent.test.ts", "agent.test.ts"]
    )
    # If tests fail, analyze the failures and go back to step 1 to fix the issues
    ```

    """
)

# ==============================================================================
# 3. WRAP SUB-AGENTS AS TOOLS
# ==============================================================================

context_gatherer_tool = agent_tool.AgentTool(agent=context_gatherer_agent)
code_translator_tool = agent_tool.AgentTool(agent=code_translator_agent)

# ==============================================================================
# 4. DEFINE THE CODER AGENT (for interactive use)
# ==============================================================================

coder_agent = Agent(
    name="coder_agent",
    model="gemini-2.5-flash",
    
    # Add the input schema for proper tool integration
    input_schema=AgentInput,
    
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

# Convert coder agent to a tool for use by maintainer agent
coder_agent_tool = agent_tool.AgentTool(agent=coder_agent)

# ==============================================================================
# 5. DEFINE THE MAINTAINER AGENT
# ==============================================================================

maintainer_agent = Agent(
    name="maintainer_agent",
    model="gemini-2.5-flash",
    
    # Add the input schema for proper tool integration
    input_schema=AgentInput,
    
    description=(
        "Main coordinator for porting specific commits from google/adk-python to njraladdin/adk-typescript. "
        "Handles the complete workflow: creating issues and branches, using the coder agent for translation, "
        "and submitting pull requests."
    ),
    instruction=(
        "You are the main coordinator for porting specific commits from the Python ADK repository "
        "to its TypeScript equivalent. You will be given a commit hash and handle the complete workflow.\n\n"
        
        "**STREAMLINED WORKFLOW:**\n"
        "The porting process now has only 2 main steps:\n\n"
        
        "1. **Code Translation** - Use the coder_agent to translate, build, and test the Python code to TypeScript\n"
        "2. **GitHub Publishing** - Use one consolidated tool to handle all GitHub operations\n\n"
        
        "This approach ensures we don't create GitHub artifacts unless the code actually works.\n\n"
                
        "**COMPLETE WORKFLOW:**\n"
        "Given a commit hash (e.g., 'abc1234'), you will:\n\n"
        
        "1. **Translate Code First**:\n"
        "   - Use `coder_agent` tool to translate the Python code to TypeScript\n"
        "   - The coder_agent will gather context, translate files, build, and test\n"
        "   - The coder_agent will NOT commit or push - it only does code work\n"
        "   - If coder_agent fails, stop here (no GitHub operations needed)\n\n"
        
        "2. **Publish to GitHub** (only if coder_agent succeeds):\n"
        "   - Use `publish_port_to_github` with the commit SHA\n"
        "   - This single tool will automatically:\n"
        "     • Fetch commit information for titles and descriptions\n"
        "     • Create tracking issue with commit details\n"
        "     • Create feature branch (port-<7-char-sha>)\n"
        "     • Commit and push the translated code\n"
        "     • Create pull request linking to the issue\n\n"
        
        "**EXAMPLE WORKFLOW:**\n"
        "User: 'Port commit abc1234'\n\n"
        
        "**Step 1 - Translate Code:**\n"
        "```\n"
        "Translating Python code to TypeScript for commit abc1234...\n"
        "```\n"
        "Tool: `coder_agent(commit_id='abc1234')`\n"
        "```\n"
        "[SUCCESS] coder_agent completed successfully\n"
        "  - Gathered context from both repositories\n"
        "  - Generated src/auth/Service.ts\n"
        "  - Generated tests/auth/Service.test.ts\n"
        "  - Build successful, tests passing\n"
        "  - Code is ready for GitHub publishing\n"
        "```\n\n"
        
        "**Step 2 - Publish to GitHub:**\n"
        "```\n"
        "Code translation successful! Publishing to GitHub...\n"
        "```\n"
        "Tool: `publish_port_to_github(commit_sha='abc1234')`\n"
        "```\n"
        "[SUCCESS] Published port to GitHub successfully\n"
        "  - Created issue #45: [NEW COMMIT IN PYTHON VERSION] [commit:abc1234] Add credential service\n"
        "  - Created branch: port-abc1234\n"
        "  - Committed and pushed changes\n"
        "  - Created PR #12: Port credential service from Python ADK commit abc1234\n"
        "  - PR linked to issue #45\n"
        "[SUCCESS] Workflow complete!\n"
        "```\n\n"
        
        "**EXAMPLE WORKFLOW - CODE TRANSLATION FAILURE:**\n"
        "User: 'Port commit ghi9012'\n\n"
        
        "**Step 1 - Translate Code (Failure):**\n"
        "```\n"
        "Translating Python code to TypeScript for commit ghi9012...\n"
        "```\n"
        "Tool: `coder_agent(commit_id='ghi9012')`\n"
        "```\n"
        "[FAILED] coder_agent failed\n"
        "  - TypeScript compilation errors - undefined interface\n"
        "  - Complex async patterns difficult to port directly\n"
        "  Status: FAILED\n"
        "```\n\n"
        
        "**Result:**\n"
        "```\n"
        "Code translation failed. No GitHub operations will be performed.\n"
        "Manual intervention required to fix the TypeScript issues.\n"
        "Workflow stopped - no artifacts created.\n"
        "```\n\n"
        
        "**TOOLS AVAILABLE:**\n"
        "- `coder_agent`: Translate Python code to TypeScript (context gathering, translation, build, test)\n"
        "- `publish_port_to_github`: Handle all GitHub operations in one call (issue, branch, commit, PR)\n\n"
        
        "**KEY PRINCIPLES:**\n"
        "- You will be given commit hashes directly by the user\n"
        "- Complete one full workflow per commit hash provided\n"
        "- Use `coder_agent` first - it handles all code translation work\n"
        "- Only proceed with GitHub publishing if code translation succeeds\n"
        "- Use `publish_port_to_github` for all GitHub operations - it's fully automated\n"
        "- If code translation fails, stop immediately (no GitHub artifacts created)\n"
        "- Provide clear status updates at each step\n"
        "- The workflow is now much simpler: Code → GitHub (if code succeeds)"
    ),
    tools=[
        coder_agent_tool,  # This handles all code translation and file operations
        publish_port_to_github,  # This handles all GitHub operations in one call
    ],
)

# ==============================================================================
# 6. SET DEFAULT ROOT AGENT
# ==============================================================================

# For backwards compatibility, export coder_agent as root_agent
root_agent = coder_agent