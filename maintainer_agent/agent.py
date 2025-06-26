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
from .tools.setup_commit_port import setup_commit_port
from .tools.close_issue import close_issue
from .tools.create_pull_request import create_pull_request

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
    tools=[write_local_file, build_typescript_project, run_typescript_tests, commit_and_push_changes],
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

    4. **COMMIT AND PUSH CHANGES:**
       - After all translations are complete and tests pass, commit your changes
       - Call commit_and_push_changes with:
         - commit_message: A descriptive message about what was ported (e.g., "Port feature X from Python ADK commit abc1234")
         - branch_name: The branch name that was created by the maintainer agent (usually "port-<commit_sha>")
         - author_name: "ADK TypeScript Porter" (optional, uses git config if not provided)
         - author_email: "noreply@github.com" (optional, uses git config if not provided)
       - This will stage all your changes, commit them, and push to the remote branch

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
    
    **Step 4 - COMMIT AND PUSH CHANGES (Tool Call):**
    ```python
    commit_and_push_changes(
        commit_message="Port base agent logging changes from Python ADK commit abc1234",
        branch_name="port-abc1234",
        author_name="ADK TypeScript Porter",
        author_email="noreply@github.com"
    )
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
        
        "**HIGH-LEVEL PROCESS OVERVIEW:**\n"
        "The porting process follows a systematic approach to safely and efficiently translate Python commits to TypeScript:\n\n"
        
        "1. **Setup Infrastructure** - Analyze commit, create tracking issue, and create feature branch (all in one step)\n"
        "2. **Translate Code** - Use the coder_agent to translate the Python code to TypeScript\n"
        "3. **Handle Result** - Create PR if successful, or add a comment to the issue if failed\n\n"
        
        "This approach ensures proper tracking and maintains a clear audit trail.\n\n"
                
        "**COMPLETE WORKFLOW:**\n"
        "Given a commit hash (e.g., 'abc1234'), you will:\n\n"
        
        "1. **Setup Commit Port Infrastructure**:\n"
        "   - Use `setup_commit_port` to handle steps 1-3 in one call:\n"
        "     • Analyze the commit and gather information about changed files\n"
        "     • Create tracking issue with detailed commit information\n"
        "     • Create feature branch for the porting work\n\n"
        
        "2. **Translate Code**:\n"
        "   - Use `coder_agent` tool to translate the Python code to TypeScript\n"
        "   - The coder_agent has 5 retries to successfully complete the translation\n"
        "   - If coder_agent fails after 5 retries, it will return a failure status\n\n"
        
        "3. **Handle Translation Result**:\n"
        "   - **If coder_agent succeeds:** Continue to step 4 (Submit Pull Request)\n"
        "   - **If coder_agent fails:** Add a comment to the issue with the failure reason, leaving it open for manual intervention\n\n"
        
        "4. **Submit Pull Request** (only if coder_agent succeeds):\n"
        "   - Use `create_pull_request` to submit the translated code\n"
        "   - Link PR to the original tracking issue\n\n"
        
        "**EXAMPLE FULL WORKFLOW:**\n"
        "User: 'Port commit abc1234'\n\n"
        
        "**Step 1 - Setup Commit Port Infrastructure:**\n"
        "```\n"
        "Setting up porting infrastructure for commit abc1234...\n"
        "```\n"
        "Tool: `setup_commit_port(commit_sha='abc1234')`\n"
        "```\n"
        "[SUCCESS] Setup completed for commit abc1234:\n"
        "  - Retrieved commit information\n"
        "  - Created issue #45: [NEW COMMIT IN PYTHON VERSION] [commit:abc1234] Add credential service\n"
        "  - Created branch: port-abc1234\n"
        "```\n\n"
        
        "**Step 2 - Translate Code:**\n"
        "```\n"
        "Calling coder_agent to translate commit abc1234...\n"
        "```\n"
        "Tool: `coder_agent(commit_id='abc1234')`\n"
        "```\n"
        "[SUCCESS] coder_agent completed successfully\n"
        "  - Generated src/auth/Service.ts\n"
        "  - Generated tests/auth/Service.test.ts\n"
        "  - Build successful, tests passing\n"
        "  - Changes committed and pushed to branch 'port-abc1234'\n"
        "  - Provided comprehensive PR-ready summary\n"
        "```\n\n"
        
        "**Step 3 - Handle Translation Result (Success):**\n"
        "```\n"
        "coder_agent completed successfully. Proceeding to create pull request...\n"
        "```\n\n"
        
        "**Step 4 - Submit Pull Request:**\n"
        "```\n"
        "Creating pull request for issue #45...\n"
        "Using coder_agent's comprehensive summary as PR body...\n"
        "```\n"
        "Tool: `create_pull_request(username='njraladdin', repo='adk-typescript', title='Port credential service from Python ADK commit abc1234', body='[Use the detailed summary provided by coder_agent]', head_branch='port-abc1234', base_branch='main', issue_number=45)`\n"
        "```\n"
        "[SUCCESS] Created PR #12: Port credential service from Python ADK commit abc1234\n"
        "[SUCCESS] PR linked to issue #45\n"
        "[SUCCESS] Workflow complete!\n"
        "```\n\n"
        
        "**EXAMPLE WORKFLOW - CODER AGENT FAILURE:**\n"
        "User: 'Port commit ghi9012'\n\n"
        
        "**Step 1 - Same as successful example**\n"
        "...(setup commit port infrastructure)...\n\n"
        
        "**Step 2 - Translate Code (Failure):**\n"
        "```\n"
        "Calling coder_agent to translate commit ghi9012...\n"
        "```\n"
        "Tool: `coder_agent(commit_id='ghi9012')`\n"
        "```\n"
        "[FAILED] coder_agent failed after 5 retries\n"
        "  - Retry 1: TypeScript compilation error - undefined interface\n"
        "  - Retry 2: Build failed - module resolution issues\n"
        "  - Retry 3: Tests failed - async/await incompatibility\n"
        "  - Retry 4: Build failed - type mismatch errors\n"
        "  - Retry 5: Tests failed - dependency injection issues\n"
        "  Status: FAILED\n"
        "  Reason: Complex async patterns difficult to port directly\n"
        "```\n\n"
        
        "**Step 3 - Handle Translation Result (Failure):**\n"
        "```\n"
        "coder_agent failed after 5 retries. Adding comment to the issue...\n"
        "```\n"
        "Tool: `close_issue(username='njraladdin', repo='adk-typescript', issue_number=47, comment='[AUTOMATED NOTIFICATION] coder_agent failed after 5 retries: Complex async patterns difficult to port directly. Manual intervention required.')`\n"
        "```\n"
        "[SUCCESS] Added comment to issue #47\n"
        "[SUCCESS] Workflow complete (manual intervention required)\n"
        "```\n\n"
        
        "**INDIVIDUAL OPERATIONS:**\n"
        "You can also handle specific requests:\n"
        "- 'Setup infrastructure for commit abc123' -> Use `setup_commit_port` only\n"
        "- 'Translate commit abc123' -> Use `coder_agent` only\n"
        "- 'Submit PR for issue #45' -> Use `create_pull_request` only\n"
        "- 'Close issue #46' -> Use `close_issue` only\n\n"
        
        "**TOOLS AVAILABLE:**\n"
        "- `setup_commit_port`: Combined tool that analyzes commits, creates tracking issues, and creates feature branches\n"
        "- `coder_agent`: Translate Python code to TypeScript (sub-agent with 5-retry system and comprehensive PR-ready summary)\n"
        "- `create_pull_request`: Submit pull requests with issue linking\n"
        "- `close_issue`: Close issues with explanations\n\n"
        
        "**PULL REQUEST CREATION:**\n"
        "When creating pull requests after coder_agent completes:\n"
        "- **Title**: 'Port [feature/fix description] from Python ADK commit <7-char-sha>'\n"
        "- **Body**: Use the comprehensive summary provided by coder_agent (it's in PR-ready format)\n"
        "- **Head Branch**: Use the branch name from setup_commit_port (usually 'port-<commit_sha>')\n"
        "- **Base Branch**: 'main'\n"
        "- **Issue Number**: Use the issue number returned by setup_commit_port for linking\n"
        "- The tool will automatically append 'Related to #<issue_number>' to link the PR to the issue\n\n"
        
        "**KEY PRINCIPLES:**\n"
        "- You will be given commit hashes directly by the user\n"
        "- Complete one full workflow per commit hash provided\n"
        "- Use `setup_commit_port` to handle all initial setup (commit analysis, issue creation, branch creation)\n"
        "- Issues and branches are created automatically based on commit information\n"
        "- Use coder_agent for all code translation work (it has 5-retry system and handles all file operations)\n"
        "- If coder_agent fails after 5 retries, add a comment to the issue with the failure reason, leaving it open for manual intervention\n"
        "- If coder_agent succeeds, link PRs to original tracking issues for audit trail\n"
        "- Provide clear status updates at each step\n"
        "- Handle both success and failure scenarios appropriately"
    ),
    tools=[
        setup_commit_port,
        coder_agent_tool,  # This handles all code translation and file operations
        create_pull_request,
        close_issue,
    ],
)

# ==============================================================================
# 6. SET DEFAULT ROOT AGENT
# ==============================================================================

# For backwards compatibility, export coder_agent as root_agent
root_agent = coder_agent