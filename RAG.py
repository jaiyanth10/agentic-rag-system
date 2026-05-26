"""
Agentic RAG System - Inspired by Claude/Cursor's Context Retrieval

This system uses an AI agent to intelligently search through documents,
similar to how Claude and Cursor understand your codebase.

Key Concepts:
- Agent: AI that decides which tools to use
- Tools: Functions the agent can call (search, read files, list files)
- RAG: Retrieval-Augmented Generation (search first, then generate answer)
"""

import logging
import os
import time
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Import our tool functions from separate module
from tools import grep, list_files, read_file

# Load environment variables from .env file
# This loads your OPENAI_API_KEY
load_dotenv()

# Maximum number of tool calls the agent can make (cost control)
AGENT_REQUEST_LIMIT = 20

# Setup logging to see what the agent is doing
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
    """Run the RAG system from command line."""
    print("=" * 60)
    print("🤖 Agentic RAG System - CLI Demo")
    print("=" * 60)
    print()
    
    try:
        agent = create_agent()
    except ValueError as e:
        print(f"❌ Setup Error: {e}")
        return
    
    query = "Where does our deployment happen and when?"
    print(f"📝 Query: {query}")
    print("🔍 Searching...\n")
    
    start_time = time.perf_counter()
    
    try:
        result = agent.run_sync(query)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    elapsed_time = time.perf_counter() - start_time
    usage = result.usage()
    
    # Extract tool calls using PydanticAI's built-in method
    tool_calls = []
    for msg in result.all_messages():
        if hasattr(msg, 'parts'):
            for part in msg.parts:
                if hasattr(part, 'tool_name') and part.tool_name != 'final_result':
                    tool_calls.append(part.tool_name)
    
    # Clean, concise output
    print("💡 Answer:")
    print(result.output.answer)
    print()
    
    # Show actual tool calls
    if tool_calls:
        print("🔧 Tools executed:")
        for i, tool in enumerate(tool_calls, 1):
            print(f"   {i}. {tool}")
        print()
    
    print(f"📊 {len(result.output.citations)} sources • {elapsed_time:.1f}s • {len(tool_calls)} tool calls")
    print()
    print("=" * 60)
    print("🌐 For full interactive UI with citations and examples:")
    print("   Run: python app.py")
    print("   Then open: http://localhost:7860")
    print("=" * 60)


if __name__ == "__main__":
    main()