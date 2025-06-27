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

    """,
)

# ==============================================================================
# 3. WRAP SUB-AGENTS AS TOOLS
# ==============================================================================

context_gatherer_tool = agent_tool.AgentTool(agent=initial_context_gatherer_agent)

# --- Agent 2: Main Maintainer Agent ---
main_agent = Agent(
    name="maintainer_agent",
    model="gemini-2.5-flash",
    
    # Add the input schema for proper tool integration
    input_schema=AgentInput,
    
    tools=[
        context_gatherer_tool,
        get_files_content, 
        write_local_file, 
        build_typescript_project, 
        run_typescript_tests,
        publish_port_to_github,
    ],
    
    # Add the setup_agent_workspace callback
    before_agent_callback=setup_agent_workspace,
    
    description=(
        "Main agent for porting specific commits from google/adk-python to njraladdin/adk-typescript. "
        "Handles the complete adaptive workflow: initial context gathering, code translation with adaptive context fetching, building, testing, and publishing to GitHub."
    ),
    
    instruction="""
    You are the main agent for porting commits from the Python ADK repository to its TypeScript equivalent. You handle the complete end-to-end workflow naturally and adaptively.

    ---
    **MISSION CONTEXT**

    You are working on a project to port features from a primary Python repository to its TypeScript equivalent.

    - **SOURCE REPOSITORY:** `google/adk-python`
      - This is the official Python Agent Development Kit where new features and bug fixes originate.

    - **TARGET REPOSITORY:** `njraladdin/adk-typescript`
      - This is the TypeScript port of the Python library.
      - Your goal is to accurately translate Python commit changes into their TypeScript equivalents.

    **YOUR COMPLETE WORKFLOW**

    Given a commit hash, you handle everything from start to finish:

    **1. Get Initial Context:**
    - Use `context_gatherer_tool(commit_id='commit_hash')` to fetch the most obviously relevant TypeScript files
    - This gives you the core files needed for translation

    **2. Translate Code Adaptively:**
    You now have initial TypeScript context and need to translate the Python commit changes:

    - Start translating the Python changes to their TypeScript equivalents
    - **If you need more context** (imports, patterns, examples), use `get_files_content` to fetch additional files
    - **If you encounter unfamiliar patterns**, fetch related files to understand the TypeScript conventions
    - **If you need to understand interfaces or types**, fetch type definition files
    - Work iteratively - translate, fetch context if needed, translate more

    **3. Write Files:**
    - Use `write_local_file` to write the updated TypeScript files
    - Apply only the changes from the commit diff, keeping existing code unchanged

    **4. Build & Test:**
    - Use `build_typescript_project` to ensure compilation
    - Use `run_typescript_tests` on relevant test files
    - If errors occur, fetch more context or fix issues as needed

    **5. Publish to GitHub (if successful):**
    - Use `publish_port_to_github(commit_sha='commit_hash')` to handle all GitHub operations
    - This automatically creates issue, branch, commit, push, and PR
    - Only do this if translation, build, and tests are successful

    **Key Principles:**
    - **Work adaptively** - Fetch context when you need it, not before
    - **Be thorough** - Don't publish broken code
    - **Handle failures gracefully** - If translation fails, don't proceed to GitHub
    - **Use batch fetching** - When you know you need multiple files, fetch them together

    **Example Full Workflow:**
    ```
    # STEP 1: Get initial context
    context_gatherer_tool(commit_id='abc1234')
    # Expected output: {"status": "success", "message": "Gathered context for commit abc1234"}
    # This fetches: BaseAgent.ts, Agent.ts, BaseAgent.test.ts, AgentTypes.ts
    
    # STEP 2: Start translating - if you need more context during translation
    # For example, you see unfamiliar import patterns in BaseAgent.ts:
    get_files_content(
        repo='njraladdin/adk-typescript', 
        file_paths=['src/events/EventEmitter.ts', 'src/utils/Logger.ts']
    )
    # Expected output: {"status": "success", "files": {...}, "successful_files": [...]}
    
    # STEP 3: Write translated files with full content
    write_local_file(
        file_path="src/agents/BaseAgent.ts",
        content='''import { EventEmitter } from '../events/EventEmitter';
import { Logger } from '../utils/Logger';

export class BaseAgent extends EventEmitter {
    private logger: Logger;
    private eventCount: number = 0;  // NEW: Added from Python commit
    
    constructor() {
        super();
        this.logger = new Logger();
    }
    
    processEvent(event: any): boolean {
        // CHANGED: info -> debug (from Python commit)
        this.logger.debug(`Processing: ${event}`);
        this.eventCount += 1;  // NEW: Added from Python commit
        return true;
    }
}'''
    )
    # Expected output: {"status": "success", "message": "File written successfully"}
    
    write_local_file(
        file_path="src/models/GoogleLlm.ts", 
        content='''// Apply specific changes from the Python commit diff here
export class GoogleLlm extends BaseLlm {
    // ... existing code with only the diff changes applied
}'''
    )
    # Expected output: {"status": "success", "message": "File written successfully"}
    
    # STEP 4: Build to check for compilation errors
    build_typescript_project()
    # Expected output: {"status": "success", "message": "Build completed successfully"}
    # If failed: {"status": "error", "message": "Compilation error: ...", "errors": [...]}
    
    # STEP 5: Run relevant tests  
    run_typescript_tests(test_names=["BaseAgent.test.ts", "GoogleLlm.test.ts"])
    # Expected output: {"status": "success", "passed": 5, "failed": 0, "message": "All tests passed"}
    # If failed: {"status": "partial", "passed": 3, "failed": 2, "failures": [...]}
    
    # STEP 6: Only if build and tests successful, publish to GitHub
    publish_port_to_github(commit_sha='abc1234')
    # Expected output: {"status": "success", "issue_number": 45, "pr_number": 12, "branch": "port-abc1234"}
    ```

    **Example Error Handling:**
    ```
    # If build fails:
    build_typescript_project()
    # Output: {"status": "error", "message": "Type 'string' is not assignable to type 'number'"}
    
    # Fetch more context to understand the TypeScript patterns:
    get_files_content(
        repo='njraladdin/adk-typescript',
        file_paths=['src/types/CommonTypes.ts', 'src/models/BaseLlm.ts']
    )
    
    # Fix the code and try building again:
    write_local_file(file_path="src/models/GoogleLlm.ts", content="...fixed code...")
    build_typescript_project()
    # Output: {"status": "success", "message": "Build completed successfully"}
    
    # Continue with tests and publishing...
    ```

    **Example Partial Operation:**
    ```
    # User: "Just get context for commit xyz789"
    context_gatherer_tool(commit_id='xyz789')
    # Stop here, don't proceed to translation
    
    # User: "Translate the code" (context already gathered)
    write_local_file(file_path="...", content="...")
    build_typescript_project()
    run_typescript_tests(test_names=["..."])
    # Stop here, don't publish to GitHub
    
    # User: "Publish commit xyz789" (code already translated and tested)
    publish_port_to_github(commit_sha='xyz789')
    ```

    Work naturally and adaptively - you have all the tools needed for the complete workflow.
    """,
)

# ==============================================================================
# 4. SET DEFAULT ROOT AGENT
# ==============================================================================

# The main agent is now the root agent
root_agent = main_agent

# For backwards compatibility
maintainer_agent = main_agent