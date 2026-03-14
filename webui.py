"""
RAG Bot WebUI — Gradio chatbot interface.

A ChatGPT-like conversational UI that queries the RAG API backend.
Run: python webui.py
"""
import os
import requests
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("RAG_API_URL", "http://localhost:8001")


def check_api_health():
    """Check if the RAG API is reachable and return status info."""
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        data = resp.json()
        docs = data.get("documents_indexed", 0)
        models = data.get("models", {})
        return True, docs, models
    except Exception:
        return False, 0, {}


def chat_with_rag(user_message: str, history: list):
    """Send user message to RAG API and yield the response."""
    if not user_message.strip():
        return history

    try:
        resp = requests.post(
            f"{API_URL}/chat",
            params={"query": user_message},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        answer = data.get("answer", "Pas de réponse.")
        sources = data.get("sources", [])
        timings = data.get("timings", {})
        chunks = data.get("reranked_chunks", [])

        # Build rich response with metadata
        response_parts = [answer]

        # Add sources
        if sources:
            source_list = ", ".join(f"`{s}`" for s in sources)
            response_parts.append(f"\n\n📄 **Sources:** {source_list}")

        # Add top chunks with scores
        if chunks:
            chunk_details = []
            for i, c in enumerate(chunks):
                score_pct = c.get("score", 0) * 100
                preview = c.get("text", "")[:120].replace("\n", " ")
                chunk_details.append(f"  {i+1}. ({score_pct:.1f}%) {preview}…")
            response_parts.append("\n\n📊 **Contextes utilisés:**\n" + "\n".join(chunk_details))

        # Add timings
        if timings:
            total = timings.get("total_ms", 0)
            embed = timings.get("embed_ms", 0)
            retrieve = timings.get("retrieve_ms", 0)
            rerank = timings.get("rerank_ms", 0)
            generate = timings.get("generate_ms", 0)
            response_parts.append(
                f"\n\n⏱️ **Latence:** {total:.0f}ms "
                f"(embed {embed:.0f} → retrieve {retrieve:.0f} → rerank {rerank:.0f} → generate {generate:.0f})"
            )

        full_response = "\n".join(response_parts)

    except requests.exceptions.ConnectionError:
        full_response = (
            "❌ **Erreur de connexion** — L'API RAG n'est pas accessible.\n\n"
            f"Vérifiez que le serveur tourne sur `{API_URL}`."
        )
    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = e.response.json().get("detail", str(e))
        except Exception:
            error_detail = str(e)
        full_response = f"⚠️ **Erreur API:** {error_detail}"
    except Exception as e:
        full_response = f"❌ **Erreur inattendue:** {str(e)}"

    history.append((user_message, full_response))
    return history


def ingest_documents():
    """Trigger document ingestion via the API."""
    try:
        resp = requests.post(f"{API_URL}/ingest", timeout=60)
        resp.raise_for_status()
        data = resp.json()
        files = data.get("files", {})
        total = data.get("total_chunks", 0)

        file_details = "\n".join(f"  • `{name}`: {count} chunks" for name, count in files.items())
        return f"✅ **Ingestion réussie !**\n\n{file_details}\n\n**Total: {total} chunks indexés.**"
    except requests.exceptions.ConnectionError:
        return f"❌ **API inaccessible** sur `{API_URL}`"
    except Exception as e:
        return f"❌ **Erreur:** {str(e)}"


def build_status_html():
    """Build a status string for the sidebar."""
    alive, docs, models = check_api_health()
    if alive:
        llm = models.get("llm", "?")
        embed = models.get("embedding", "?")
        rerank = models.get("reranker", "?")
        return (
            f"🟢 API connectée\n"
            f"📚 {docs} documents indexés\n"
            f"🤖 LLM: {llm}\n"
            f"🔤 Embed: {embed}\n"
            f"🔀 Rerank: {rerank}"
        )
    return "🔴 API déconnectée"


# ── Build Gradio UI ─────────────────────────────────────────────────

THEME = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="slate",
    neutral_hue="slate",
    font=gr.themes.GoogleFont("Source Sans 3"),
    font_mono=gr.themes.GoogleFont("JetBrains Mono"),
)

CSS = """
.contain { max-width: 900px; margin: 0 auto; }
footer { display: none !important; }
.status-box { font-family: 'JetBrains Mono', monospace; font-size: 13px; line-height: 1.6; }
"""

with gr.Blocks(theme=THEME, css=CSS, title="RAG Bot") as demo:

    gr.Markdown(
        "# 🤖 RAG Bot\n"
        "Posez vos questions — les réponses sont générées à partir de vos documents.",
    )

    with gr.Row():
        # ── Main chat area ──
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(
                label="Conversation",
                height=520,
                show_copy_button=True,
                placeholder="Posez une question sur vos documents…",
            )

            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Écrivez votre question ici…",
                    show_label=False,
                    scale=6,
                    container=False,
                    autofocus=True,
                )
                send_btn = gr.Button("Envoyer", variant="primary", scale=1)

        # ── Sidebar ──
        with gr.Column(scale=1, min_width=220):
            gr.Markdown("### ⚙️ Panneau")

            status_display = gr.Textbox(
                label="Statut",
                value=build_status_html,
                interactive=False,
                lines=5,
                elem_classes=["status-box"],
            )

            refresh_btn = gr.Button("🔄 Rafraîchir statut", size="sm")
            refresh_btn.click(fn=build_status_html, outputs=status_display)

            gr.Markdown("---")

            ingest_btn = gr.Button("📥 Indexer les documents", variant="secondary")
            ingest_output = gr.Markdown("")
            ingest_btn.click(fn=ingest_documents, outputs=ingest_output)

            gr.Markdown("---")

            clear_btn = gr.Button("🗑️ Vider la conversation", variant="stop", size="sm")
            clear_btn.click(fn=lambda: [], outputs=chatbot)

    # ── Event bindings ──
    msg.submit(fn=chat_with_rag, inputs=[msg, chatbot], outputs=chatbot).then(
        fn=lambda: "", outputs=msg,
    )
    send_btn.click(fn=chat_with_rag, inputs=[msg, chatbot], outputs=chatbot).then(
        fn=lambda: "", outputs=msg,
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
