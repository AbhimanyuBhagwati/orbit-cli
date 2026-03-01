from __future__ import annotations

from orbit.config import get_config
from orbit.context.scanner import scan
from orbit.llm.ollama_provider import OllamaProvider
from orbit.ui.console import console

ASK_SYSTEM_PROMPT = """You are a helpful DevOps assistant. Answer questions about the user's
environment based on the provided context. Be concise and specific.
If you're not sure, say so. Do not execute any commands."""


async def ask(question: str) -> None:
    """Answer a question about the environment. No execution."""
    config = get_config()
    provider = OllamaProvider(host=config.ollama_host, port=config.ollama_port)

    console.print("[orbit.blue]Scanning environment...[/]")
    env = await scan()

    context_parts = [f"[{slot.source}]\n{slot.content}" for slot in env.slots if slot.available]
    context_text = "\n\n".join(context_parts) if context_parts else "No context available."

    messages = [
        {"role": "system", "content": ASK_SYSTEM_PROMPT},
        {"role": "user", "content": f"Environment:\n{context_text}\n\nQuestion: {question}"},
    ]

    try:
        # Stream the response
        response = provider.chat(model=config.default_model, messages=messages, temperature=0.3)
        console.print()
        console.print(str(response))
    except Exception as e:
        console.print(f"[orbit.error]Error: {e}[/]")
