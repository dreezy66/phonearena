#!/usr/bin/env python3
"""
Aponi Dashboard — REST-only, Termux-friendly client

Usage:
  * Set environment variables (preferred):
      export GCP_PROJECT_ID="your-gcp-project-id"
      export FIRESTORE_OAUTH_TOKEN="ya29.xxxxxx"   # optional, required for Firestore access
      export GEMINI_API_KEY="AIza...."            # or GEMINI_OAUTH_TOKEN (bearer)
  * Or run with --mock to use local mock data.

Example:
  python3 Aponi_aponi_rest.py data
  python3 Aponi_aponi_rest.py report
  python3 Aponi_aponi_rest.py insight --prompt "How to reduce errors?"
  python3 Aponi_aponi_rest.py log

Notes:
  - Firestore document storage approach: this client stores a single JSON blob under the Firestore document
    field "payload" (stringValue). This avoids dealing with gRPC or Firestore typed fields.
  - For secure production-grade Firestore access, create a short-lived OAuth2 token for the service account
    and set FIRESTORE_OAUTH_TOKEN.
"""

from __future__ import annotations
import os
import json
import time
import logging
import argparse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -------------------------
# Configure logger + HTTP
# -------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("aponi_rest")

# Requests session with retry/backoff
def create_session(retries: int = 4, backoff_factor: float = 0.6, status_forcelist=(500, 502, 503, 504)):
    s = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'])
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

SESSION = create_session()

# -------------------------
# Data models (dataclasses)
# -------------------------
@dataclass
class AgentStatus:
    id: str
    name: str
    parent: Optional[str]
    status: str

@dataclass
class LogEntry:
    timestamp: datetime
    message: str
    type: str

    def to_json(self) -> Dict[str, Any]:
        return {"timestamp": self.timestamp.astimezone(timezone.utc).isoformat(), "message": self.message, "type": self.type}

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "LogEntry":
        ts = d.get("timestamp")
        try:
            ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00')) if isinstance(ts, str) else datetime.now(timezone.utc)
        except Exception:
            ts_dt = datetime.now(timezone.utc)
        return LogEntry(timestamp=ts_dt, message=d.get("message", ""), type=d.get("type", "info"))

@dataclass
class PerformanceData:
    labels: List[str] = field(default_factory=list)
    runs: List[int] = field(default_factory=list)
    errors: List[int] = field(default_factory=list)

@dataclass
class RemoteWorkerStatus:
    online: bool = False
    tasksQueued: int = 0
    lastPing: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class AponiData:
    activeAgents: int = 0
    successfulRuns: int = 0
    totalErrors: int = 0
    lineage: List[AgentStatus] = field(default_factory=list)
    remoteWorkerStatus: RemoteWorkerStatus = field(default_factory=RemoteWorkerStatus)
    agentLogs: List[LogEntry] = field(default_factory=list)
    performanceData: PerformanceData = field(default_factory=PerformanceData)

    def to_plain_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return {
            "activeAgents": self.activeAgents,
            "successfulRuns": self.successfulRuns,
            "totalErrors": self.totalErrors,
            "lineage": [asdict(x) for x in self.lineage],
            "remoteWorkerStatus": {
                "online": self.remoteWorkerStatus.online,
                "tasksQueued": self.remoteWorkerStatus.tasksQueued,
                "lastPing": self.remoteWorkerStatus.lastPing.astimezone(timezone.utc).isoformat()
            },
            "agentLogs": [log.to_json() for log in self.agentLogs],
            "performanceData": asdict(self.performanceData)
        }

    @staticmethod
    def from_plain_dict(d: Dict[str, Any]) -> "AponiData":
        lineage = [AgentStatus(**i) for i in d.get("lineage", [])]
        rws = d.get("remoteWorkerStatus", {})
        remote = RemoteWorkerStatus(
            online=bool(rws.get("online", False)),
            tasksQueued=int(rws.get("tasksQueued", 0)),
            lastPing=(datetime.fromisoformat(rws["lastPing"].replace('Z', '+00:00')) if rws.get("lastPing") else datetime.now(timezone.utc))
        )
        logs = [LogEntry.from_json(l) for l in d.get("agentLogs", [])]
        perf = PerformanceData(**d.get("performanceData", {})) if d.get("performanceData") else PerformanceData()
        return AponiData(
            activeAgents=int(d.get("activeAgents", 0)),
            successfulRuns=int(d.get("successfulRuns", 0)),
            totalErrors=int(d.get("totalErrors", 0)),
            lineage=lineage,
            remoteWorkerStatus=remote,
            agentLogs=logs,
            performanceData=perf
        )

# -------------------------
# AponiDashboard (REST)
# -------------------------
class AponiDashboardREST:
    """Termux-optimized Aponi client that uses Firestore + Gemini via REST."""

    DEFAULT_COLLECTION_PATH = "artifacts/default-app-id/public/data/aponi_dashboard_metrics"
    DEFAULT_DOC_ID = "metrics"

    def __init__(self,
                 project_id: str,
                 gemini_api_key: Optional[str] = None,
                 gemini_oauth_token: Optional[str] = None,
                 firestore_oauth_token: Optional[str] = None,
                 collection_path: Optional[str] = None,
                 doc_id: Optional[str] = None,
                 cache_ttl: int = 30,
                 http_session: requests.Session = SESSION):
        self.project_id = project_id
        self.gemini_api_key = gemini_api_key
        self.gemini_oauth_token = gemini_oauth_token
        self.firestore_oauth_token = firestore_oauth_token
        self.collection_path = collection_path or self.DEFAULT_COLLECTION_PATH
        self.doc_id = doc_id or self.DEFAULT_DOC_ID
        self._cache_ttl = cache_ttl
        self._data_cache: Optional[AponiData] = None
        self._cache_time = 0
        self.session = http_session
        self.generation_model = "gemini-2.5"  # user can override if desired

    # -------------------------
    # Firestore REST helpers
    # -------------------------
    def _firestore_doc_url(self) -> str:
        # document path: projects/{project}/databases/(default)/documents/{collection_path}/{doc_id}
        # ensure no leading/trailing slashes in collection_path
        coll = self.collection_path.strip("/")
        return f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{coll}/{self.doc_id}"

    def _firestore_headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.firestore_oauth_token:
            h["Authorization"] = f"Bearer {self.firestore_oauth_token}"
        return h

    def _get_firestore_doc(self) -> Optional[Dict[str, Any]]:
        url = self._firestore_doc_url()
        headers = self._firestore_headers()
        try:
            r = self.session.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 404:
                return None
            else:
                log.warning("Firestore GET failed: %s %s", r.status_code, r.text[:400])
                return None
        except Exception as e:
            log.exception("Firestore GET exception: %s", e)
            return None

    def _write_firestore_doc_payload(self, payload_dict: Dict[str, Any]) -> bool:
        """
        Writes the entire payload JSON as a single string field named 'payload'.
        This keeps Firestore interactions simple and avoids typed field conversion.
        """
        url = self._firestore_doc_url()
        headers = self._firestore_headers()
        body = {"fields": {"payload": {"stringValue": json.dumps(payload_dict)}}}
        try:
            # Use PATCH — will create or update the document.
            r = self.session.patch(url, headers=headers, json=body, timeout=15)
            if r.status_code in (200, 201):
                return True
            else:
                log.warning("Firestore PATCH failed: %s %s", r.status_code, r.text[:400])
                return False
        except Exception as e:
            log.exception("Firestore PATCH exception: %s", e)
            return False

    def _read_payload_from_doc(self, doc_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse the 'payload' stringValue from a Firestore document JSON and return the inner JSON.
        """
        if not doc_json:
            return None
        fields = doc_json.get("fields", {})
        payload_field = fields.get("payload", {})
        payload_str = payload_field.get("stringValue")
        if not payload_str:
            log.debug("No payload string found in document.")
            return None
        try:
            return json.loads(payload_str)
        except Exception as e:
            log.exception("Failed to parse payload JSON: %s", e)
            return None

    # -------------------------
    # Public methods
    # -------------------------
    def get_dashboard_data(self, use_cache: bool = True, force_refresh: bool = False) -> Optional[AponiData]:
        """Fetch dashboard data from Firestore (REST). Uses TTL cache to limit reads."""
        if use_cache and not force_refresh and self._data_cache and (time.time() - self._cache_time) < self._cache_ttl:
            log.debug("Returning cached AponiData")
            return self._data_cache

        doc = self._get_firestore_doc()
        if doc is None:
            # doc doesn't exist: create mock data and return
            log.info("No Firestore document found. Initializing mock data.")
            self._setup_mock_data()
            doc = self._get_firestore_doc()
            if doc is None:
                # still none -> convert mock created locally
                mock = self._initial_mock_data()
                self._data_cache = AponiData.from_plain_dict(mock)
                self._cache_time = time.time()
                return self._data_cache

        payload = self._read_payload_from_doc(doc)
        if payload is None:
            log.info("Payload missing or corrupt. Replacing with mock data.")
            self._setup_mock_data()
            payload = self._initial_mock_data()

        try:
            aponi_data = AponiData.from_plain_dict(payload)
            self._data_cache = aponi_data
            self._cache_time = time.time()
            log.debug("Fetched data from Firestore and cached.")
            return aponi_data
        except Exception as e:
            log.exception("Failed to convert payload to AponiData: %s", e)
            return None

    def _initial_mock_data(self) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "activeAgents": 12,
            "successfulRuns": 85,
            "totalErrors": 5,
            "lineage": [
                {"id": "agent_alpha", "name": "Alpha Agent", "parent": None, "status": "Running"},
                {"id": "agent_beta", "name": "Beta Agent", "parent": "agent_alpha", "status": "Sleeping"},
                {"id": "agent_gamma", "name": "Gamma Agent", "parent": "agent_alpha", "status": "Error"}
            ],
            "remoteWorkerStatus": {"online": True, "tasksQueued": 3, "lastPing": now_iso},
            "agentLogs": [
                {"timestamp": now_iso, "message": "System started.", "type": "info"},
                {"timestamp": now_iso, "message": "Agent Alpha initialized.", "type": "info"},
                {"timestamp": now_iso, "message": "Agent Gamma encountered a timeout error.", "type": "error"}
            ],
            "performanceData": {"labels": ["Jan","Feb","Mar","Apr","May","Jun"], "runs":[30,45,60,55,75,85], "errors":[2,1,3,2,1,0]}
        }

    def _setup_mock_data(self) -> bool:
        payload = self._initial_mock_data()
        return self._write_firestore_doc_payload(payload)

    # -------------------------
    # Log handling
    # -------------------------
    def append_log(self, message: str, log_type: str = "info") -> bool:
        """Append a log entry (read-modify-write). Not atomic across concurrent writers."""
        try:
            doc = self._get_firestore_doc()
            payload = self._read_payload_from_doc(doc) if doc else None
            if payload is None:
                payload = self._initial_mock_data()

            logs = payload.get("agentLogs", [])
            new_log = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message, "type": log_type}
            logs.append(new_log)
            # Keep last N logs to prevent unbounded growth (example limit: 500)
            payload["agentLogs"] = logs[-500:]
            success = self._write_firestore_doc_payload(payload)
            if success:
                # Invalidate cache to pick up new log
                self._data_cache = None
                return True
            return False
        except Exception as e:
            log.exception("Failed to append log: %s", e)
            return False

    # -------------------------
    # Gemini REST helpers
    # -------------------------
    def _gemini_headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.gemini_oauth_token:
            h["Authorization"] = f"Bearer {self.gemini_oauth_token}"
        return h

    def _call_gemini(self, prompt: str, system_instruction: Optional[str] = None, max_tokens: int = 512) -> Optional[str]:
        """
        Call Gemini via REST. Accepts either API key (query param) or OAuth bearer token (Authorization).
        Attempts a few response parsing heuristics to be resilient to small API differences.
        """
        if not (self.gemini_api_key or self.gemini_oauth_token):
            log.warning("No Gemini credentials provided.")
            return None

        base = f"https://generativelanguage.googleapis.com/v1beta2/models/{self.generation_model}:generateText"
        if self.gemini_api_key:
            url = f"{base}?key={self.gemini_api_key}"
        else:
            url = base

        body = {
            "prompt": {
                "text": f"{system_instruction or ''}\n\n{prompt}"
            },
            "maxOutputTokens": max_tokens
        }

        try:
            r = self.session.post(url, headers=self._gemini_headers(), json=body, timeout=20)
            if r.status_code not in (200, 201):
                log.warning("Gemini API call failed: %s %s", r.status_code, r.text[:400])
                return None
            j = r.json()
            # Heuristics for parsing typical responses:
            # - look for 'candidates'[0]['output'] or 'candidates'[0]['content'] or 'output'
            text = None
            if isinstance(j, dict):
                # new style: j.get('candidates') -> list of dicts with 'output' or 'content'
                candidates = j.get("candidates")
                if candidates and isinstance(candidates, list) and len(candidates) > 0:
                    c0 = candidates[0]
                    text = c0.get("output") or c0.get("content") or c0.get("text")
                # fallback: j.get('output', {}).get('text') or 'result'
                if not text:
                    out = j.get("output") or j.get("result") or {}
                    if isinstance(out, dict):
                        text = out.get("text") or out.get("content") or out.get("output")
                    elif isinstance(out, str):
                        text = out
                # ultimate fallback: if 'candidates' not present try 'response' or 'generatedText'
                if not text:
                    text = j.get("response") or j.get("generatedText") or j.get("generated_text")
            log.debug("Gemini response parsed text length=%s", len(text) if text else 0)
            return text
        except Exception as e:
            log.exception("Gemini REST call exception: %s", e)
            return None

    # -------------------------
    # High-level LLM helpers
    # -------------------------
    def _get_system_prompt(self, role: str) -> str:
        prompts = {
            "assistant": "You are an AI assistant for an autonomous agent dashboard. Provide concise, helpful insights.",
            "report_writer": "You are a professional technical report writer. Produce a concise Markdown report summarizing KPIs and logs.",
            "live_logger": "Generate a concise, realistic log entry (system event, agent action, or minor error). Reply with a single short sentence."
        }
        return prompts.get(role, "")

    def generate_insight(self, user_prompt: str) -> str:
        """High-level wrapper to generate an insight given user prompt."""
        data = self.get_dashboard_data() or AponiData()
        prompt = f"Dashboard JSON:\n{json.dumps(data.to_plain_dict(), indent=2)}\n\nUser: {user_prompt}"
        return self._call_gemini(prompt, self._get_system_prompt("assistant")) or "LLM unavailable or returned no output."

    def generate_report(self) -> str:
        """Generate a Markdown report based on latest dashboard data."""
        data = self.get_dashboard_data()
        if not data:
            return "Unable to get dashboard data."

        prompt = f"""Generate a Markdown performance report.

KPIs:
- Active Agents: {data.activeAgents}
- Successful Runs: {data.successfulRuns}
- Total Errors: {data.totalErrors}

Agent statuses:
{json.dumps([asdict(a) for a in data.lineage], indent=2)}

Recent logs:
{json.dumps([l.to_json() for l in data.agentLogs[-8:]], indent=2)}
"""
        result = self._call_gemini(prompt, self._get_system_prompt("report_writer"), max_tokens=1024)
        return result or "LLM unavailable or returned no output."

    def generate_log_entry(self) -> Optional[LogEntry]:
        """Ask Gemini to generate one log entry and append it to Firestore."""
        text = self._call_gemini("Generate one short realistic log entry.", self._get_system_prompt("live_logger"), max_tokens=80)
        if not text:
            log.warning("No log text generated.")
            return None
        typ = "info" if "error" not in text.lower() and "fail" not in text.lower() else "error"
        ok = self.append_log(text.strip(), log_type=typ)
        if ok:
            return LogEntry(timestamp=datetime.now(timezone.utc), message=text.strip(), type=typ)
        return None

# -------------------------
# CLI / Example
# -------------------------
def build_client_from_env(mock: bool = False) -> AponiDashboardREST:
    project = os.environ.get("GCP_PROJECT_ID", "")
    if not project and not mock:
        raise RuntimeError("GCP_PROJECT_ID environment variable not set. Use --mock to run without Firestore.")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    gemini_token = os.environ.get("GEMINI_OAUTH_TOKEN")
    fs_token = os.environ.get("FIRESTORE_OAUTH_TOKEN")
    client = AponiDashboardREST(project_id=project or "mock-project",
                                gemini_api_key=gemini_key,
                                gemini_oauth_token=gemini_token,
                                firestore_oauth_token=fs_token,
                                cache_ttl=30)
    if mock:
        # ensure local mock payload present (does not require network)
        client._setup_mock_data()
    return client

def main():
    parser = argparse.ArgumentParser(description="Aponi Dashboard CLI (REST, Termux friendly)")
    parser.add_argument("command", choices=["data", "insight", "report", "log"], help="Command to run")
    parser.add_argument("--prompt", "-p", type=str, help="Prompt for insight")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no external calls required)")
    args = parser.parse_args()

    client = build_client_from_env(mock=args.mock)

    print("✨ Connecting to Aponi (REST)...")
    if args.command == "data":
        data = client.get_dashboard_data()
        if data:
            print("--- Current Aponi Dashboard ---")
            print(json.dumps(data.to_plain_dict(), indent=2))
        else:
            print("Failed to retrieve dashboard data.")

    elif args.command == "insight":
        if not args.prompt:
            print("Error: --prompt is required for insight")
            return
        out = client.generate_insight(args.prompt)
        print("\n=== Insight ===\n")
        print(out)

    elif args.command == "report":
        out = client.generate_report()
        print("\n=== Report ===\n")
        print(out)

    elif args.command == "log":
        new_log = client.generate_log_entry()
        if new_log:
            print("Added log:", new_log.to_json())
        else:
            print("Failed to generate/add log.")

if __name__ == "__main__":
    main()