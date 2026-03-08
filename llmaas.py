"""
Script autonome minimal pour faire une requête vers LLMaaS.
Contient tout le code strictement nécessaire (pas de dépendance au projet).
"""

import json
from contextlib import contextmanager
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ── HTTP Client ──────────────────────────────────────────────────────────────


class BaseHTTPClient:
    def __init__(self, base_url: str, headers: dict[str, str], timeout: float = 30.0,
                 max_retries: int = 3, backoff_factor: float = 0.5):
        self.base_url = base_url.rstrip("/")
        self.headers = headers
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self.headers)
        retry = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["POST"],
            raise_on_status=False,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    @contextmanager
    def _session_context(self):
        session = self._create_session()
        try:
            yield session
        finally:
            session.close()

    def request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        with self._session_context() as session:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            return response


# ── LLM Client ───────────────────────────────────────────────────────────────


class LLMClient:
    def __init__(self, api_key: str, base_url: str, timeout: float = 60.0,
                 max_retries: int = 3):
        self.http = BaseHTTPClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=timeout,
            max_retries=max_retries,
        )

    def generate(self, messages: list[dict[str, str]], model: str,
                 temperature: float = 0.7, max_tokens: Optional[int] = None,
                 **kwargs: Any) -> dict[str, Any]:
        payload = {"model": model, "messages": messages, "temperature": temperature, **kwargs}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        response = self.http.request("POST", "/v1/chat/completions", json=payload)
        return response.json()


# ── Main ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    client = LLMClient(
        api_key="YOUR_API_KEY",
        base_url="https://llmaas-ap88967-prod.data.cloud.net.intra/",
    )

    result = client.generate(
        model="mistral-medium-2508",
        messages=[
            {"role": "system", "content": "Tu es un assistant utile."},
            {"role": "user", "content": "Bonjour !"},
        ],
        temperature=0.7,
    )

    # Extraire la réponse
    answer = result["choices"][0]["message"]["content"]
    print(answer)
