"""
RAG Tools - Search, List, and Read Functions

This module contains the three core tools that the agent uses:
1. grep() - Search for patterns across documents (using ripgrep for speed!)
2. list_files() - Discover available files
3. read_file() - Read specific file content

Separated from main RAG.py for cleaner architecture.
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

# Setup logging
logger = logging.getLogger(__name__)

# Configuration - imported from calling module or set directly
NOTES_DIR = (Path(__file__).parent / "notes").resolve()
READ_MAX_LINES = 200


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
    target = (NOTES_DIR / path).resolve()
    
    if not target.is_relative_to(NOTES_DIR):
        logger.warning(f"Blocked unsafe path access: {path}")
        return None
    
    return target


# ============================================================
# TOOL 1: Search - Find text across all documents
# ============================================================

def grep(pattern: str, max_results: int = 30, context: int = 0) -> str:
    """
    Search for a pattern across all markdown files using ripgrep.
    
    Ripgrep (rg) is a Rust-based search tool that's 10-100x faster than grep!
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
    
    Note: Uses ripgrep (rg) for blazing fast search!
    Fallback to Python re module if ripgrep not installed.
    """
    logger.info(f"Searching for pattern: '{pattern}' (max {max_results} results)")
    
    if max_results < 1:
        return "Error: max_results must be at least 1"
    if context < 0:
        return "Error: context cannot be negative"
    
    if not NOTES_DIR.exists():
        return f"Error: Notes directory not found at {NOTES_DIR}"
    
    # Try using ripgrep first (much faster!)
    try:
        # Build ripgrep command
        # -i = case insensitive
        # -n = show line numbers
        # --no-heading = don't group by file
        # -C = context lines
        # --max-count = limit matches per file
        cmd = [
            "rg",
            "-i",  # case-insensitive
            "-n",  # line numbers
            "--no-heading",  # format: file:line:text
            "-g", "*.md",  # only .md files
        ]
        
        if context > 0:
            cmd.extend(["-C", str(context)])  # context lines
        
        cmd.extend(["--max-count", str(max_results)])
        cmd.append(pattern)
        cmd.append(str(NOTES_DIR))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Success! Parse output
            lines = result.stdout.strip().split('\n')
            if len(lines) > max_results:
                lines = lines[:max_results]
                lines.append(f"\n... more matches not shown. Try a more specific search.")
            return '\n'.join(lines)
        elif result.returncode == 1:
            # No matches found
            return f"No matches found for pattern: '{pattern}'"
        else:
            # Error occurred, fall back to Python implementation
            logger.warning(f"ripgrep error: {result.stderr}, falling back to Python")
            raise FileNotFoundError("ripgrep failed")
    
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError) as e:
        # ripgrep not installed or failed, use Python fallback
        logger.info(f"Using Python regex fallback: {e}")
        return _grep_python_fallback(pattern, max_results, context)


def _grep_python_fallback(pattern: str, max_results: int, context: int) -> str:
    """
    Pure Python implementation of grep (fallback when ripgrep unavailable).
    """
    results = []
    total_matches = 0
    
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Error: Invalid search pattern: {e}"
    
    for md_file in sorted(NOTES_DIR.glob("*.md")):
        try:
            content = md_file.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, start=1):
                if regex.search(line):
                    total_matches += 1
                    
                    if context > 0:
                        start = max(0, line_num - context - 1)
                        end = min(len(lines), line_num + context)
                        context_lines = lines[start:end]
                        
                        formatted = "\n".join(
                            f"{md_file.name}:{i+start+1}: {l}"
                            for i, l in enumerate(context_lines)
                        )
                        results.append(formatted)
                    else:
                        results.append(f"{md_file.name}:{line_num}: {line}")
                    
                    if len(results) >= max_results:
                        break
        
        except UnicodeDecodeError:
            logger.warning(f"Skipping non-UTF8 file: {md_file.name}")
            continue
        
        if len(results) >= max_results:
            break
    
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
    
    if not NOTES_DIR.exists():
        return f"Error: Notes directory not found at {NOTES_DIR}"
    
    try:
        paths = NOTES_DIR.glob(pattern)
    except (NotImplementedError, ValueError) as e:
        return f"Error: Invalid glob pattern '{pattern}': {e}"
    
    matches = sorted(
        str(path.relative_to(NOTES_DIR))
        for path in paths
        if path.is_file()
    )
    
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
    
    if not safe.exists():
        return f"Error: File not found: {path}"
    
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
        content = safe.read_text(encoding='utf-8')
        lines = content.splitlines()
    except UnicodeDecodeError:
        return f"Error: '{path}' is not a valid text file (cannot decode as UTF-8)"
    
    # Calculate which lines to return
    start_idx = offset - 1
    end_idx = min(start_idx + limit, len(lines))
    
    excerpt = lines[start_idx:end_idx]
    
    if not excerpt:
        return f"No lines found. File has {len(lines)} total lines, but you requested offset={offset}"
    
    # Format with line numbers
    formatted = "\n".join(
        f"{line_num}: {line}"
        for line_num, line in enumerate(excerpt, start=offset)
    )
    
    return formatted
