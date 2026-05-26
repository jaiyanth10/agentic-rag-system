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
        answer_md = f"## Answer\n\n{result.output.answer}"
        
        # Format citations
        citations_md = "## Sources\n\n"
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
        
        stats_md = f"""## Statistics

| Metric | Value |
|--------|-------|
| Time | {elapsed:.2f}s |
| Agent Turns | {usage.requests} |
| Input Tokens | {usage.input_tokens:,} |
| Output Tokens | {usage.output_tokens:,} |
| Estimated Cost | ${cost:.4f} |
"""
        
        # Extract tool calls using PydanticAI's built-in method
        tool_calls = []
        for msg in result.all_messages():
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    if hasattr(part, 'tool_name') and part.tool_name != 'final_result':
                        tool_calls.append(part.tool_name)
        
        # Format tool log with clean execution order
        tool_log = "Tool Execution Order:\n\n"
        if tool_calls:
            for i, tool in enumerate(tool_calls, 1):
                tool_log += f"{i}. {tool}\n"
        else:
            tool_log += "No tools used\n"
        
        tool_log += f"\nCompleted in {elapsed:.2f}s ({usage.requests} agent turns)"
        
        return answer_md, citations_md, stats_md, tool_log
        
    except Exception as e:
        error_msg = str(e)
        # Handle request limit errors with friendly message
        if "request_limit" in error_msg or "exceed" in error_msg:
            return "No relevant data found. Please try a different question.", "", "", ""
        return f"❌ Error: {error_msg}", "", "", ""


# ============================================================
# GRADIO INTERFACE: Build the UI
# ============================================================

def create_ui():
    """Create and configure the Gradio interface."""
    
    # Custom theme with better background
    custom_theme = gr.themes.Default(
        primary_hue="blue",
        neutral_hue="slate",
    ).set(
        body_background_fill="*neutral_50",
        block_background_fill="white",
    )
    
    with gr.Blocks(title="Agentic RAG System", theme=custom_theme) as demo:
        # Header
        gr.Markdown(
            """
            # Agentic RAG System
            
            Ask questions about company documentation and get answers with citations.
            
            ---
            """
        )
        
        # Main content area
        with gr.Row():
            with gr.Column(scale=4):
                # Question input
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g., Why does our deploy run at 03:47 UTC?",
                    lines=3
                )
                
                # Example questions
                gr.Examples(
                    examples=[
                        "Where does our deployment happen?",
                        "What caused incident #2847?",
                    ],
                    inputs=question_input,
                    label=None,
                )
                
                # Action buttons
                with gr.Row():
                    submit_btn = gr.Button("Search", variant="primary", scale=3)
                    clear_btn = gr.Button("Clear", scale=1)
                
                # Results area (scrollable, right below input)
                gr.Markdown("---")
                
                with gr.Tabs():
                    with gr.Tab("Answer"):
                        answer_output = gr.Markdown(label="Answer")
                    
                    with gr.Tab("Citations"):
                        citations_output = gr.Markdown(label="Sources")
                    
                    with gr.Tab("Statistics"):
                        stats_output = gr.Markdown(label="Usage Stats")
                    
                    with gr.Tab("Tool Execution"):
                        tool_log_output = gr.Textbox(
                            label="Agent Tool Usage",
                            lines=8,
                            interactive=False,
                            show_label=False
                        )
            
            with gr.Column(scale=1):
                # Empty column for spacing
                pass
        
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
            
            **Note:** The agent uses multi-step reasoning to decide which tools to use.
            Estimated cost: ~$0.0001-0.001 per query.
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
