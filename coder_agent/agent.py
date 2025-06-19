import os
import sys
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

# --- ADK Imports ---
from google.adk.agents import Agent
from google.adk.tools import AgentTool

# --- Tool Imports ---
# Make sure these tool files exist in a 'tools' subdirectory
# and the functions are correctly implemented.
from .tools.get_commit_diff import get_commit_diff
from .tools.get_repo_file_structure import get_repo_file_structure
from .tools.get_file_content import get_file_content
from .tools.write_local_file import write_local_file

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
# This agent's only job is to collect all information and output a GatheredContext object.
context_gatherer_agent = Agent(
    name="ContextGatherer",
    model="gemini-1.5-pro-latest",
    tools=[get_commit_diff, get_repo_file_structure, get_file_content],
    
    instruction="""
    You are an expert context gatherer for a Python-to-TypeScript code migration.
    Your sole purpose is to collect all necessary information and output it as a single, complete JSON object
    that strictly follows the provided schema. Do not add any other text, reasoning, or explanations.

    INPUT: You will be given a commit SHA.
    
    YOUR STEPS:
    1.  Use the `get_commit_diff` tool with the provided commit SHA to get the diff and list of changed files.
    2.  Use the `get_repo_file_structure` tool for BOTH the Python repo ('google/adk-python') and the TypeScript repo ('njraladdin/adk-typescript').
    3.  For EACH changed Python file from the commit info, use the `get_file_content` tool to fetch its full content.
    4.  Based on the file paths and structures, determine the most likely equivalent file paths in the TypeScript repo.
    5.  For EACH equivalent TypeScript file you identify, use `get_file_content` to fetch its content.
    6.  Analyze the imports in the changed Python files and their TypeScript equivalents. If you identify other relevant files needed for context (e.g., imported local modules), fetch their content as well.
    7.  Once all information is gathered, structure it PERFECTLY according to the provided JSON schema and output it as your final answer.
    """,
    
    # This forces the agent's output to be a valid `GatheredContext` JSON object.
    output_schema=GatheredContext,
    
    # This tells the framework to save the structured output to the session state.
    # The key 'gathered_context' can be used by the next agent.
    output_key="gathered_context" 
)

# --- Agent 2: Code Translator ---
# This agent receives the context and performs the translation.
code_translator_agent = Agent(
    name="CodeTranslator",
    model="gemini-1.5-pro-latest",
    tools=[write_local_file],
    
    # Note: The `{gathered_context}` placeholder will be automatically filled
    # with the output from the previous agent.
    instruction="""
    You are an expert Python-to-TypeScript developer specializing in code migration.
    You will be provided with a complete JSON object containing all the information you need:
    commit diffs, file structures, and the full content of all relevant source files
    from both the Python and TypeScript repositories. This context is available in the `{gathered_context}` placeholder.

    YOUR TASK:
    1.  Carefully analyze the provided context in `{gathered_context}`.
    2.  For each changed Python file, write the new, updated TypeScript equivalent, applying the logic from the Python diff.
    3.  Ensure your code adheres to TypeScript best practices, is well-typed, and idiomatic.
    4.  Use the `write_local_file` tool to save each newly generated TypeScript file. The path should be relative to an `output/` directory (e.g., 'output/src/new-file.ts').
    5.  After all files are written, your final response must be a simple confirmation message, like 'Porting complete. All files have been saved.'
    """
)


# ==============================================================================
# 3. WRAP SUB-AGENTS AS TOOLS
# ==============================================================================

context_gatherer_tool = AgentTool(agent=context_gatherer_agent)
code_translator_tool = AgentTool(agent=code_translator_agent)


# ==============================================================================
# 4. DEFINE THE FLEXIBLE ROOT AGENT (for interactive use)
# ==============================================================================

# This is the agent you will interact with directly via chat.
root_agent = Agent(
    name="CodePorterCoordinator",
    model="gemini-1.5-pro-latest",
    
    # Provide the sub-agents as tools to the coordinator.
    tools=[
        context_gatherer_tool,
        code_translator_tool,
    ],
    
    instruction="""
    You are an expert coordinator for a code porting workflow. You have two main sub-agents available as tools:
    1.  `ContextGatherer(commit_id: str)`: Use this tool to collect all necessary files and context for a given commit.
    2.  `CodeTranslator()`: Use this tool to perform the actual code translation. It will automatically use the context gathered by the `ContextGatherer` if it has been run in the same session.

    Your job is to understand the user's request and orchestrate the workflow.

    - If the user provides a commit ID and asks to start the full porting process, you MUST first call the `ContextGatherer` tool with the commit ID. After it completes, its output will be available in the conversation history. You should then call the `CodeTranslator` tool to finish the job.
    
    - If the user explicitly asks to ONLY gather context for a commit ID, just call the `ContextGatherer` tool and present its JSON output directly to the user.
    
    - If the user provides context and asks to ONLY translate, call the `CodeTranslator` tool.
    """,
)