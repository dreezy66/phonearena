# pdf_reader_agent.py — ingest and summarize PDF content for agents
import os, json
from arena_core.agent_runtime import get_agents, save_agents

try:
    import fitz  # PyMuPDF
except ImportError:
    print("[PDF Agent] PyMuPDF not installed, please install via pip install pymupdf")
    fitz = None

KNOWLEDGE_DIR = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "agent_data", "knowledge")

os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

def ingest_pdf(agent, pdf_path):
    if not fitz:
        return
    if not os.path.exists(pdf_path):
        print(f"[PDF Agent] PDF not found: {pdf_path}")
        return
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        # save raw text
        out_path = os.path.join(KNOWLEDGE_DIR, f"{agent.name}_pdf.txt")
        with open(out_path, "w") as f:
            f.write(full_text)
        # simple summary: first 500 chars
        agent.knowledge_summary = full_text[:500] + "..." if len(full_text) > 500 else full_text
        print(f"[PDF Agent] Ingested PDF for {agent.name}: {pdf_path}")
    except Exception as e:
        print(f"[PDF Agent] Failed to ingest PDF {pdf_path}: {e}")

def ingest_all_pdfs():
    agents = get_agents()
    for agent in agents:
        pdfs = getattr(agent, "assigned_pdfs", [])
        for pdf_path in pdfs:
            ingest_pdf(agent, pdf_path)
    save_agents(agents)
