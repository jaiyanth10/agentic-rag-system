"""
Interactive Gradio UI for Agentic RAG System

This provides a chat-like interface where users can ask questions
and see real-time tool usage, just like Claude/Cursor!
"""

import gradio as gr
import time
from pathlib import Path
from RAG import create_agent, SearchAnswer, AGENT_REQUEST_LIMIT

# ============================================================
# QUERY HANDLER: Process user questions
# ============================================================

def query_documents(question: str, progress=gr.Progress()):
    """
    Process a user question and return formatted response.
    
    Args:
        question: User's question
        progress: Gradio progress tracker (shows loading animation)
    
    Returns:
        tuple: (answer_markdown, citations_markdown, stats_markdown, tool_log)
    """
    if not question or not question.strip():
        return "❌ Please enter a question!", "", "", ""
    
    progress(0, desc="Creating agent...")
    
    try:
        agent = create_agent()
    except ValueError as e:
        return f"❌ Setup Error: {e}\n\nPlease create a .env file with your OPENAI_API_KEY", "", "", ""
    
    progress(0.2, desc="Agent is thinking...")
    
    # Track tool calls for visualization
    tool_log = []
    start_time = time.perf_counter()
    
    try:
        # Run the agent
        result = agent.run_sync(question)
        
        elapsed = time.perf_counter() - start_time
        
        progress(1.0, desc="Complete!")
        
        # Format the answer
        answer_md = f"## 💡 Answer\n\n{result.output.answer}"
        
        # Format citations
        citations_md = "## 📚 Sources\n\n"
        if result.output.citations:
            for i, citation in enumerate(result.output.citations, 1):
                citations_md += f"### {i}. `{citation.file}`\n\n"
                citations_md += "```\n"
                citations_md += citation.quote
                citations_md += "\n```\n\n"
        else:
            citations_md += "*No citations provided*\n"
        
        # Format statistics
        usage = result.usage()
        cost = (usage.input_tokens * 0.00000015) + (usage.output_tokens * 0.0000006)
        
        stats_md = f"""## 📊 Statistics

| Metric | Value |
|--------|-------|
| ⏱️ Time | {elapsed:.2f}s |
| 🔄 Agent Turns | {usage.requests} |
| � Input Tokens | {usage.input_tokens:,} |
| 💭 Output Tokens | {usage.output_tokens:,} |
| 💰 Estimated Cost | ${cost:.4f} |
"""
        
        # Tool visualization would go here
        # (In a real implementation, we'd intercept tool calls)
        tool_log = f"✅ Query completed in {elapsed:.2f}s\n"
        tool_log += f"🔄 Took {usage.requests} agent turns\n"
        
        return answer_md, citations_md, stats_md, tool_log
        
    except Exception as e:
        return f"❌ Error: {str(e)}", "", "", ""


# ============================================================
# GRADIO INTERFACE: Build the UI
# ============================================================

def create_ui():
    """Create and configure the Gradio interface."""
    
    with gr.Blocks(title="Agentic RAG System", theme=gr.themes.Soft()) as demo:
        # Header
        gr.Markdown(
            """
            # 🤖 Agentic RAG System
            ### Inspired by Claude/Cursor's Context Retrieval Mechanism
            
            Ask questions about company documentation and get answers with citations!
            The agent intelligently searches through documents using multiple tools.
            
            ---
            """
        )
        
        # Main content area
        with gr.Row():
            with gr.Column(scale=2):
                # Question input
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g., Why does our deploy run at 03:47 UTC?",
                    lines=3
                )
                
                # Action buttons
                with gr.Row():
                    submit_btn = gr.Button("🔍 Search", variant="primary", scale=3)
                    clear_btn = gr.Button("🗑️ Clear", scale=1)
                
                # Example questions
                gr.Examples(
                    examples=[
                        "Why does our nightly deploy job run at 03:47 UTC specifically?",
                        "What caused incident #2847?",
                        "How do I authenticate with the User Service API?",
                        "What is our system architecture?",
                        "What are the rate limits for the API?",
                    ],
                    inputs=question_input,
                    label="Example Questions"
                )
            
            with gr.Column(scale=1):
                # Info panel
                gr.Markdown(
                    """
                    ### ℹ️ How It Works
                    
                    1. **Agent analyzes** your question
                    2. **Searches** relevant documents
                    3. **Reads** specific sections
                    4. **Generates** answer with citations
                    
                    ### 🛠️ Tools Available
                    - `list_files()` - Discover documents
                    - `grep()` - Search for keywords
                    - `read_file()` - Read specific content
                    
                    ### 📁 Documents
                    """
                )
                
                # List available documents
                notes_dir = Path(__file__).parent / "notes"
                if notes_dir.exists():
                    docs = sorted([f.name for f in notes_dir.glob("*.md")])
                    docs_list = "\n".join([f"- `{doc}`" for doc in docs])
                    gr.Markdown(docs_list)
        
        # Results area
        gr.Markdown("---")
        gr.Markdown("## 📋 Results")
        
        with gr.Tabs():
            with gr.Tab("Answer"):
                answer_output = gr.Markdown(label="Answer")
            
            with gr.Tab("Citations"):
                citations_output = gr.Markdown(label="Sources")
            
            with gr.Tab("Statistics"):
                stats_output = gr.Markdown(label="Usage Stats")
            
            with gr.Tab("Tool Log"):
                tool_log_output = gr.Textbox(
                    label="Tool Calls",
                    lines=10,
                    interactive=False
                )
        
        # Connect buttons to function
        submit_btn.click(
            fn=query_documents,
            inputs=[question_input],
            outputs=[answer_output, citations_output, stats_output, tool_log_output]
        )
        
        clear_btn.click(
            lambda: ("", "", "", "", ""),
            outputs=[question_input, answer_output, citations_output, stats_output, tool_log_output]
        )
        
        # Footer
        gr.Markdown(
            """
            ---
            
            **💡 Tip:** The agent uses multi-step reasoning - it decides which tools to use and when!
            
            **🔒 Privacy:** Your API key is loaded from `.env` and never exposed.
            
            **💰 Cost:** ~$0.0001-0.001 per query (very cheap with GPT-4.1-nano)
            """
        )
    
    return demo


# ============================================================
# MAIN: Launch the application
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Launching Agentic RAG System")
    print("=" * 60)
    print()
    print("📝 Make sure you have:")
    print("   1. Created .env file with OPENAI_API_KEY")
    print("   2. Added documents to the 'notes' folder")
    print()
    print("🌐 Opening in your browser...")
    print("=" * 60)
    print()
    
    demo = create_ui()
    demo.launch(
        server_name="127.0.0.1",  # Local only (not exposed to internet)
        server_port=7860,          # Port number
        share=False,               # Set True to get public link
        show_api=False             # Hide API docs
    )
