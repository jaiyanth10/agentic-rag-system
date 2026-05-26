# 🤖 Agentic RAG System

**Reverse-engineering Claude/Cursor's Context Retrieval Mechanism**

An intelligent document search system that mimics how AI coding assistants like Claude and Cursor understand your codebase. Built with PydanticAI, featuring an interactive Gradio UI and production-ready architecture.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![PydanticAI](https://img.shields.io/badge/PydanticAI-0.8+-orange.svg)

---
## UI Preview 
<img width="2502" height="1366" alt="image" src="https://github.com/user-attachments/assets/a2e3dc89-1255-4deb-9328-50d0ab196bb5" />

---
## 🎯 What Is This?

Ever wondered how Claude, Cursor, or GitHub Copilot **understand** your entire codebase? They don't read every file at once (impossible due to token limits). Instead, they use **Agentic RAG** - an AI agent that intelligently decides:

1. **What** to search for
2. **Which** files to read
3. **When** to stop searching

This project recreates that mechanism for markdown documentation, showing you exactly how it works!

---

## 🧠 What is Agentic RAG?

### Traditional RAG (Most Systems)
```
User Query → Embedding → Vector Search → Top-K Results → LLM → Answer
```
- **Single-step**: One search, done
- **Static**: Always returns top-K results
- **No reasoning**: Can't adjust strategy

### Agentic RAG (This Project!)
```
User Query → Agent Thinks → Tool 1 (grep) → Agent Evaluates
         ↑                                          ↓
         └──────── Tool 2 (read_file) ←──── Needs More Info?
                             ↓
                    Tool 3 (list_files)
                             ↓
                    Answer with Citations
```

**Key Difference**: The **agent decides** which tools to use and when, just like a human researcher!

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/agentic-rag
cd agentic-rag

# 2. Install UV (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# 3. Create virtual environment & install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install pydantic pydantic-ai gradio python-dotenv openai

# 4. Setup environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Run the interactive UI
python app.py
```

The UI will open at [http://localhost:7860](http://localhost:7860)

---

## 📁 Project Structure

```
agentic-rag/
├── RAG.py                  # Core RAG system with detailed comments
├── app.py                  # Interactive Gradio UI
├── notes/                  # Sample documents (your knowledge base)
│   ├── deployment-process.md
│   ├── incident-2847.md
│   ├── api-documentation.md
│   └── architecture.md
├── pyproject.toml          # Project dependencies (UV format)
├── .env                    # Your API keys (not in git)
├── .env.example            # Template for .env
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

---

## 🛠️ How It Works: Deep Dive

### The Architecture

```
┌─────────────────────────────────────────────────────┐
│                  USER QUESTION                       │
│          "Why deploy at 03:47 UTC?"                 │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│             PYDANTIC AI AGENT                        │
│          (GPT-4.1-nano - The Brain)                 │
│                                                      │
│  Decides which tools to use and when                │
│  Multi-step reasoning, not single search            │
└─────┬──────────────┬──────────────┬────────────────┘
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ TOOL 1   │  │ TOOL 2   │  │ TOOL 3       │
│          │  │          │  │              │
│list_files│  │  grep()  │  │ read_file()  │
│    ()    │  │          │  │              │
│          │  │          │  │              │
│Discovery │  │ Search   │  │ Deep Read    │
└──────────┘  └──────────┘  └──────────────┘
      │              │              │
      └──────────────┴──────────────┘
                     │
                     ▼
              ┌─────────────┐
              │   notes/    │
              │  *.md files │
              └─────────────┘
```

### The Three Tools

#### 1. `list_files(pattern="*.md")` - Discovery
**Purpose**: See what documents are available

**When agent uses it**: 
- First step to understand what exists
- Narrowing down relevant files

**Example**:
```python
list_files("deploy*.md")
# Returns: deployment-process.md, deployment-checklist.md
```

#### 2. `grep(pattern, max_results=30)` - Search
**Purpose**: Find keywords across all documents

**When agent uses it**:
- Searching for specific terms ("03:47", "deploy", "incident")
- Getting quick overview of mentions

**Example**:
```python
grep("03:47")
# Returns:
# deployment-process.md:15: Our nightly deployment runs at 03:47 UTC
# incident-2847.md:8: The incident occurred at 03:47 UTC
```

**How it works**:
- Uses Python regex (case-insensitive)
- Searches all .md files in `notes/`
- Can show context lines around matches
- Limits results to prevent token overflow

#### 3. `read_file(path, offset=1, limit=200)` - Deep Read
**Purpose**: Read specific sections of a file

**When agent uses it**:
- After finding relevant file via grep
- Need full context around a match
- Reading entire document sections

**Example**:
```python
read_file("deployment-process.md", offset=10, limit=20)
# Returns lines 10-29 with line numbers
```

**Why limit lines?**
- LLMs have token limits (can't send 10,000 lines!)
- Cost control (fewer tokens = less money)
- Forces agent to be strategic about what to read

---

## 🎬 Example: How the Agent Thinks

**User asks**: *"Why does our deploy run at 03:47 UTC?"*

### Agent's Internal Process:

```
Turn 1: Agent Thinks
├─ "I need to find information about deployment timing"
├─ "Let me search for '03:47' across all docs"
└─ Calls: grep("03:47")
   Returns: 2 matches in deployment-process.md and incident-2847.md

Turn 2: Agent Evaluates
├─ "Found mentions in 2 files, need more context"
├─ "deployment-process.md seems most relevant"
└─ Calls: read_file("deployment-process.md", offset=10, limit=30)
   Returns: Full section explaining the timing reasoning

Turn 3: Agent Synthesizes
├─ "I have enough information now"
├─ "deployment-process.md explains it's to avoid backup conflicts"
├─ "incident-2847.md shows what happened when timing was wrong"
└─ Generates answer with citations from both sources
```

**Result**: Answer with exact quotes proving every claim!

---

## 📊 Key Features

### ✅ Production-Ready
- ⚡ **Fast**: UV package manager (10-100x faster than pip)
- 🔒 **Secure**: Path validation prevents directory traversal
- 💰 **Cost-Optimized**: Request limits and bounded outputs
- 📝 **Logged**: All operations tracked for debugging
- 🛡️ **Error Handling**: Graceful failures with helpful messages

### ✅ Developer-Friendly
- 📖 **Extensively Commented**: Every line explained
- 🎨 **Clean Code**: Follows Python best practices
- 🧪 **Type Hints**: Full type annotations
- 📚 **Documentation**: This README + inline docs

### ✅ Interactive UI
- 💬 **Chat Interface**: Ask questions naturally
- 📊 **Statistics**: See token usage and costs
- 🔍 **Citations**: Every answer shows sources
- ⚡ **Real-time**: Progress indicators and streaming

---

## 💡 Use Cases

### 1. Company Documentation Search
Replace your wiki search with an intelligent assistant:
- "What's our incident response procedure?"
- "How do I configure the API?"
- "What caused the outage last week?"

### 2. Code Documentation
Add markdown docs to `notes/` and search your codebase:
- "How does authentication work?"
- "What's the deployment process?"
- "Where is the rate limiting configured?"

### 3. Learning Tool
Understand how AI agents work by seeing:
- Which tools they call
- How they reason through problems
- Why they make certain decisions

### 4. Research Assistant
Store papers, articles, notes and query them:
- "What does the paper say about transformers?"
- "Compare approach A vs B"
- "Summarize findings on topic X"

---

## 🎓 Learning Highlights

### For Students
This project teaches:
- **AI Agents**: How LLMs use tools (not just chat!)
- **RAG Systems**: Retrieval-Augmented Generation explained
- **Python**: Clean code practices, type hints, documentation
- **API Design**: Tool interfaces and structured outputs
- **Production Patterns**: Error handling, logging, security

### For Engineers
Key concepts demonstrated:
- **Agentic AI**: Multi-step reasoning vs single-shot inference
- **Tool Calling**: Function calling patterns with LLMs
- **Structured Outputs**: Pydantic models for reliability
- **Cost Optimization**: Token limits and request caps
- **Developer Experience**: UV, type hints, clear errors

---

## 📈 Performance & Costs

### Typical Query
- **Time**: 2-5 seconds
- **Agent Turns**: 2-4 tool calls
- **Tokens**: 1,000-3,000 total
- **Cost**: $0.0001-0.0005 (less than a tenth of a cent!)

### Why So Cheap?
- Using GPT-4.1-nano ($0.15 per 1M input tokens)
- Bounded outputs (max 200 lines per read)
- Smart search (only reads what's needed)
- Request limits (max 20 turns)

### Comparison
| System | Cost per Query | Speed |
|--------|---------------|-------|
| This (GPT-4.1-nano) | $0.0003 | 3s |
| GPT-4-turbo | $0.003 | 4s |
| Claude Opus | $0.015 | 5s |

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
MODEL=openai:gpt-4.1-nano
MAX_AGENT_TURNS=20
MAX_READ_LINES=200
```

### Customization

#### Change the Model
Edit `RAG.py`:
```python
agent = Agent(
    "openai:gpt-4-turbo",  # or gpt-4o, gpt-3.5-turbo
    # ... rest of config
)
```

#### Add More Tools
```python
def search_database(query: str) -> str:
    """Search a SQL database"""
    # Your implementation
    pass

agent = Agent(
    tools=[list_files, grep, read_file, search_database],  # Add new tool!
    # ... rest of config
)
```

#### Use Different File Types
Change glob pattern in `grep()` and `list_files()`:
```python
NOTES_DIR.glob("*.txt")  # Text files
NOTES_DIR.glob("**/*.py")  # Python files recursively
```

---
## Future Enhancements
Ideas for contributions:
- [ ] Add PDF support (extract text)
- [ ] Implement caching (avoid re-searching)
- [ ] Add more file types (.txt, .rst, .pdf)
- [ ] Real-time tool call visualization
- [ ] Cost tracking dashboard
- [ ] Multi-language support
- [ ] Vector search (semantic similarity)

---

## 🐛 Troubleshooting

### "OPENAI_API_KEY not found"
- Create `.env` file: `cp .env.example .env`
- Add your API key from https://platform.openai.com/api-keys

### "No matches found"
- Check `notes/` directory has `.md` files
- Try broader search terms
- Use `list_files()` to see what's available

### "Import Error: No module named 'pydantic_ai'"
- Activate virtual environment: `source .venv/bin/activate`
- Install dependencies: `uv pip install -r requirements.txt`

### Gradio won't launch
- Check port 7860 isn't in use
- Try different port: Edit `app.py` line with `server_port=7860`

---

## 📚 Related Resources

### Learn More About:
- [PydanticAI Documentation](https://ai.pydantic.dev/)
- [What is RAG?](https://www.pinecone.io/learn/retrieval-augmented-generation/)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [UV Package Manager](https://github.com/astral-sh/uv)



**Built with curiosity and code** 🚀
