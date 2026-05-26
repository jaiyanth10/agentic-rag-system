"""
Agentic RAG System - Inspired by Claude/Cursor's Context Retrieval

This system uses an AI agent to intelligently search through documents,
similar to how Claude and Cursor understand your codebase.

Key Concepts:
- Agent: AI that decides which tools to use
- Tools: Functions the agent can call (search, read files, list files)
- RAG: Retrieval-Augmented Generation (search first, then generate answer)
"""

import logging  # Track what's Agent is doing, like which tool its calling and etc. (for debugging)
import os  # Access environment variables
import re  # Regular expressions for search
import time  # Measure how long queries take
from pathlib import Path  # To handle and access file paths
from typing import Optional  # Type hints for better code(like typescript interfaces)

from dotenv import load_dotenv  # Load .env file and make it avaiable to OS
from pydantic import BaseModel, Field  # Structured data models, to ensure agent responses are consistent.
from pydantic_ai import Agent  # The AI agent framework

# Load environment variables from .env file
# This loads your OPENAI_API_KEY
load_dotenv()

# Where our markdown documents are stored
NOTES_DIR = (Path(__file__).parent / "notes").resolve()

# Maximum lines to read from a single file in one batch to prevents token overflow
READ_MAX_LINES = 200

# Maximum number of tool calls the agent can make (cost control)
AGENT_REQUEST_LIMIT = 20

# Setup logging to see what the agent is doing
logger = logging.getLogger(__name__) // Create a logger for this module with this file name
logging.basicConfig(
    level=logging.INFO, // Show INFO level logs (tool calls, searches, etc.)
    format='%(asctime)s - %(levelname)s - %(message)s' // Log format with timestamp, log level, and message
)

# ============================================================
# SECURITY: Path Validation
# ============================================================

def _safe_path(path: str) -> Optional[Path]:
    """
    Validate that a user-supplied path is safe to access.
    
    Security measure: Prevents path traversal attacks like:
    - "../../etc/passwd" (trying to access system files)
    - "../../../secret.txt" (escaping the notes directory)
    
    Args:
        path: User-supplied file path (e.g., "deployment.md")
    
    Returns:
        Path object if safe, None if dangerous
    
    Example:
        _safe_path("deployment.md")  # ✅ Returns Path
        _safe_path("../../etc/passwd")  # ❌ Returns None
    """
    # Combine user path with our notes directory
    target = (NOTES_DIR / path).resolve()  # resolve() follows symlinks and makes absolute
    
    # Check if the final path is still inside NOTES_DIR
    # This prevents escaping to parent directories
    if not target.is_relative_to(NOTES_DIR):
        logger.warning(f"Blocked unsafe path access: {path}")
        return None
    
    return target


# ============================================================
# TOOL 1: Search - Find text across all documents
# ============================================================

def grep(pattern: str, max_results: int = 30, context: int = 0) -> str:
    """
    Search for a pattern across all markdown files.
    
    This is like Ctrl+F but across ALL documents at once!
    Similar to how Claude/Cursor search your codebase.
    
    Args:
        pattern: What to search for (e.g., "deployment", "03:47")
        max_results: Maximum matches to return (prevents overwhelming the agent)
        context: Number of lines to show before/after each match
    
    Returns:
        Formatted string with all matches: "filename:line:text"
    
    Example:
        grep("deploy", max_results=5)
        # Returns:
        # deployment.md:15: Our nightly deploy runs at 03:47
        # incident.md:23: Deploy failed due to timeout
    """
    logger.info(f"Searching for pattern: '{pattern}' (max {max_results} results)")
    
    # Validation: Ensure parameters make sense
    if max_results < 1:
        return "Error: max_results must be at least 1"
    if context < 0:
        return "Error: context cannot be negative"
    
    # Check if notes directory exists
    if not NOTES_DIR.exists():
        return f"Error: Notes directory not found at {NOTES_DIR}"
    
    results = []
    total_matches = 0
    
    # Compile pattern as case-insensitive regex
    # re.IGNORECASE means "Deploy" and "deploy" both match
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Error: Invalid search pattern: {e}"
    
    # Search through all .md files
    for md_file in sorted(NOTES_DIR.glob("*.md")):
        try:
            # Read file content
            content = md_file.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            # Search each line
            for line_num, line in enumerate(lines, start=1):
                if regex.search(line):
                    # Found a match!
                    total_matches += 1
                    
                    # Get context lines if requested
                    if context > 0:
                        # Calculate range (don't go below 0 or above file length)
                        start = max(0, line_num - context - 1)
                        end = min(len(lines), line_num + context)
                        context_lines = lines[start:end]
                        
                        # Format with line numbers
                        formatted = "\n".join(
                            f"{md_file.name}:{i+start+1}: {l}"
                            for i, l in enumerate(context_lines)
                        )
                        results.append(formatted)
                    else:
                        # Just the matching line
                        results.append(f"{md_file.name}:{line_num}: {line}")
                    
                    # Stop if we hit max_results
                    if len(results) >= max_results:
                        break
        
        except UnicodeDecodeError:
            logger.warning(f"Skipping non-UTF8 file: {md_file.name}")
            continue
        
        # Stop searching files if we have enough results
        if len(results) >= max_results:
            break
    
    # Return results or "not found" message
    if not results:
        return f"No matches found for pattern: '{pattern}'"
    
    output = "\n".join(results)
    if total_matches > max_results:
        output += f"\n\n... {total_matches - max_results} more matches not shown. Try a more specific search."
    
    return output


# ============================================================
# TOOL 2: List Files - Discover what documents exist
# ============================================================

def list_files(pattern: str = "*.md") -> str:
    """
    List all files matching a pattern.
    
    This is the agent's "discovery" tool - it sees what's available
    before deciding what to search or read.
    
    Args:
        pattern: Glob pattern (e.g., "*.md", "deploy*.md", "**/*.txt")
    
    Returns:
        List of filenames, one per line
    
    Example:
        list_files("*.md")
        # Returns:
        # deployment.md
        # incident-2847.md
        # api-documentation.md
    """
    logger.info(f"Listing files with pattern: {pattern}")
    
    # Check if notes directory exists
    if not NOTES_DIR.exists():
        return f"Error: Notes directory not found at {NOTES_DIR}"
    
    try:
        # glob() finds all files matching the pattern
        # * = any filename
        # ? = single character
        # ** = recursive (subdirectories)
        paths = NOTES_DIR.glob(pattern)
    except (NotImplementedError, ValueError) as e:
        return f"Error: Invalid glob pattern '{pattern}': {e}"
    
    # Filter to only files (not directories) and sort alphabetically
    matches = sorted(
        str(path.relative_to(NOTES_DIR))  # Show relative path (not full path)
        for path in paths
        if path.is_file()  # Only files, not directories
    )
    
    # Return results or "not found" message
    if not matches:
        return f"No files matched pattern: '{pattern}'"
    
    return "\n".join(matches)


# ============================================================
# TOOL 3: Read File - Deep dive into specific documents
# ============================================================

def read_file(path: str, offset: int = 1, limit: int = READ_MAX_LINES) -> str:
    """
    Read a specific portion of a file.
    
    After finding relevant files (via grep/list), the agent uses this
    to read the full context around matches.
    
    Args:
        path: Relative file path (e.g., "deployment.md")
        offset: Starting line number (1-indexed, like in editors)
        limit: Maximum number of lines to read
    
    Returns:
        File content with line numbers
    
    Example:
        read_file("deployment.md", offset=10, limit=20)
        # Returns lines 10-29 with line numbers:
        # 10: ## Deployment Schedule
        # 11: 
        # 12: Our nightly deployment runs at 03:47 UTC
        # ...
    
    Why limit lines?
    - LLMs have token limits (can't send entire file)
        - Cost control (less tokens = less money)
    - Forces agent to be precise about what it needs
    """
    logger.info(f"Reading file: {path} (offset={offset}, limit={limit})")
    
    # SECURITY: Validate path is safe
    safe = _safe_path(path)
    if safe is None:
        return f"Error: Path '{path}' is outside the notes directory (security block)"
    
    # Check file exists
    if not safe.exists():
        return f"Error: File not found: {path}"
    
    # Check it's actually a file (not a directory)
    if not safe.is_file():
        return f"Error: '{path}' is not a file"
    
    # Validate parameters
    if offset < 1:
        return "Error: offset must be 1 or greater (line numbers start at 1)"
    if limit < 1:
        return "Error: limit must be 1 or greater"
    if limit > READ_MAX_LINES:
        return f"Error: limit must be {READ_MAX_LINES} lines or fewer (token limit protection)"
    
    try:
        # Read the entire file
        # encoding='utf-8' ensures we can read text properly
        content = safe.read_text(encoding='utf-8')
        lines = content.splitlines()
    except UnicodeDecodeError:
        return f"Error: '{path}' is not a valid text file (cannot decode as UTF-8)"
    
    # Calculate which lines to return
    # offset=1, limit=10 → lines 1-10 (indices 0-9 in Python)
    start_idx = offset - 1  # Convert to 0-indexed
    end_idx = min(start_idx + limit, len(lines))  # Don't go past end of file
    
    # Extract the requested lines
    excerpt = lines[start_idx:end_idx]
    
    # Handle edge cases
    if not excerpt:
        return f"No lines found. File has {len(lines)} total lines, but you requested offset={offset}"
    
    # Format with line numbers for readability
    # This helps the agent (and humans) see exactly which lines they're reading
    formatted = "\n".join(
        f"{line_num}: {line}"
        for line_num, line in enumerate(excerpt, start=offset)
    )
    
    return formatted


# ============================================================
# DATA MODELS: Structured Output Format
# ============================================================
# These classes define the EXACT structure of the agent's response.
# Why? So downstream code can trust the format (no parsing needed!)

class Citation(BaseModel):
    """
    A single source that supports a claim in the answer.
    
    Think of this like a footnote in a research paper.
    The agent MUST provide evidence for its claims!
    
    Attributes:
        file: Which document the information came from
        quote: Exact text from that document (proof!)
    """
    file: str = Field(
        description="Relative path to the document (e.g., 'deployment.md')"
    )
    quote: str = Field(
        description="Exact line(s) from the file that support the claim"
    )


class SearchAnswer(BaseModel):
    """
    The complete answer with sources.
    
    This is what the agent returns - ALWAYS includes citations!
    No hallucinations allowed - everything must be backed by sources.
    
    Attributes:
        answer: The actual answer in plain English
        citations: List of sources (which files/quotes support this answer)
    
    Example:
        SearchAnswer(
            answer="Deployment runs at 03:47 UTC to avoid conflicts with backups at 04:00",
            citations=[
                Citation(
                    file="deployment.md",
                    quote="Our nightly deployment runs at 03:47 UTC..."
                ),
                Citation(
                    file="incident-2847.md",
                    quote="Deployment conflicted with backup at 04:00..."
                )
            ]
        )
    """
    answer: str = Field(
        description="The answer to the user's question in plain English"
    )
    citations: list[Citation] = Field(
        description="Sources that support this answer (files and exact quotes)"
    )


# ============================================================
# THE AGENT: The Brain of the System
# ============================================================
# This is where the magic happens!
# PydanticAI connects an LLM (GPT-4) with our tools.

def create_agent():
    """
    Create and configure the RAG agent.
    
    This function sets up:
    1. Which AI model to use (the "brain")
    2. Which tools the agent can use (the "hands")
    3. What format to return (structured output)
    4. Instructions (the "personality")
    
    Returns:
        Configured Agent ready to answer questions
    """
    # Validate API key exists
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "OPENAI_API_KEY not found! "
            "Create a .env file with your API key. "
            "See .env for template."
        )
    
    agent = Agent(
        # THE BRAIN: Which AI model to use
        # "openai:gpt-4.1-nano" - Fast and cheap (~$0.15 per 1M tokens)
        # Other options: "openai:gpt-4-turbo", "openai:gpt-4o"
        "openai:gpt-4.1-nano",
        
        # THE HANDS: What tools can the agent use?
        # The agent decides WHEN and HOW to use these
        # Just like Claude/Cursor decide which files to read!
        tools=[list_files, grep, read_file],
        
        # THE FORMAT: What structure should the response have?
        # Forces the agent to ALWAYS include citations
        output_type=SearchAnswer,
        
        # THE PERSONALITY: Instructions that guide behavior
        # This is like a system prompt - tells the agent HOW to act
        instructions=(
            "You are a helpful assistant that answers questions about company documentation. "
            "ALWAYS search the documents first before answering. "
            "Use grep to find relevant information, then read_file to get full context. "
            "Provide exact quotes as citations - never make up information. "
            "If you can't find an answer in the documents, say so honestly."
        ),
    )
    
    logger.info("Agent created successfully")
    return agent


# ============================================================
# MAIN EXECUTION: Command-line Interface
# ============================================================

def main():
    """
    Run the RAG system from command line.
    
    This is a simple CLI version. Later we'll add a Gradio UI!
    """
    print("=" * 60)
    print("🤖 Agentic RAG System")
    print("=" * 60)
    print()
    
    # Create the agent
    try:
        agent = create_agent()
    except ValueError as e:
        print(f"❌ Setup Error: {e}")
        return
    
    # Example query (later we'll make this interactive)
    query = "Why does our nightly deploy job run at 03:47 UTC specifically?"
    
    print(f"📝 Question: {query}")
    print()
    print("🔍 Agent is searching...")
    print()
    
    # Track performance
    start_time = time.perf_counter()
    
    try:
        # RUN THE AGENT!
        # This is where the magic happens:
        # 1. Agent reads the question
        # 2. Decides which tools to call (grep? read_file? list_files?)
        # 3. Calls tools based on what it finds
        # 4. Repeats until it has enough info
        # 5. Returns structured answer with citations
        result = agent.run_sync(query)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    elapsed_time = time.perf_counter() - start_time
    
    # Display the answer
    print("=" * 60)
    print("💡 Answer:")
    print("=" * 60)
    print(result.output.answer)
    print()
    
    # Display citations (sources)
    print("=" * 60)
    print("📚 Sources:")
    print("=" * 60)
    for i, citation in enumerate(result.output.citations, 1):
        print(f"\n{i}. {citation.file}")
        print("   " + "─" * 50)
        # Indent the quote for readability
        for line in citation.quote.splitlines():
            print(f"   {line}")
    print()
    
    # Display usage statistics (for cost tracking)
    print("=" * 60)
    print("📊 Statistics:")
    print("=" * 60)
    usage = result.usage()
    print(f"⏱️  Time: {elapsed_time:.2f} seconds")
    print(f"🔄 Agent turns: {usage.requests}")
    print(f" Tokens used: {usage.input_tokens:,} input + {usage.output_tokens:,} output")
    
    # Rough cost calculation (GPT-4.1-nano pricing)
    # Input: ~$0.15 per 1M tokens, Output: ~$0.60 per 1M tokens
    cost = (usage.input_tokens * 0.00000015) + (usage.output_tokens * 0.0000006)
    print(f"💵 Estimated cost: ${cost:.4f}")
    print()


if __name__ == "__main__":
    main()