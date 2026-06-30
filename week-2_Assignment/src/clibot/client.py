from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class OpenRouterClient:
    api_key: str
    model: str = "openai/gpt-4o-mini"
    app_name: str = "CLIBot"
    site_url: str = ""
    timeout: float = 120.0
    messages: list[ChatMessage] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> OpenRouterClient:
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )

        return cls(
            api_key=api_key,
            model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip(),
            app_name=os.getenv("OPENROUTER_APP_NAME", "CLIBot").strip(),
            site_url=os.getenv("OPENROUTER_SITE_URL", "").strip(),
        )

    def clear_history(self) -> None:
        self.messages.clear()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name
        return headers

    def _payload(self, stream: bool) -> dict[str, Any]:
        MAX_TURNS = 10
        recent = self.messages[-(MAX_TURNS * 2) :]
        return {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in recent
            ],
            "stream": stream,
        }

    def stream(self, user_text: str) -> Iterator[str]:
        self.messages.append(ChatMessage(role="user", content=user_text))

        chunks: list[str] = []
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(
                "POST",
                OPENROUTER_URL,
                headers=self._headers(),
                json=self._payload(stream=True),
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    payload = line.removeprefix("data: ").strip()
                    if payload == "[DONE]":
                        break

                    delta = self._parse_stream_chunk(payload)
                    if delta:
                        chunks.append(delta)
                        yield delta

        reply = "".join(chunks)
        if reply:
            self.messages.append(ChatMessage(role="assistant", content=reply))

    def generate_with_metrics(self, prompt: str) -> dict[str, Any]:
        """Stateless generation that captures usage metrics and latency."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "usage": {"include": True},
        }

        started = time.perf_counter()
        ttft_s: float | None = None
        chunks: list[str] = []
        usage: dict[str, Any] = {}

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(
                "POST",
                OPENROUTER_URL,
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    raw = line.removeprefix("data: ").strip()
                    if raw == "[DONE]":
                        break

                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if data.get("usage"):
                        usage = data["usage"]

                    choices = data.get("choices") or []
                    if not choices:
                        continue

                    delta = (choices[0].get("delta") or {}).get("content") or ""
                    if delta:
                        if ttft_s is None:
                            ttft_s = time.perf_counter() - started
                        chunks.append(delta)

        latency_s = time.perf_counter() - started
        return {
            "response": "".join(chunks),
            "latency_s": latency_s,
            "ttft_s": ttft_s,
            "usage": usage,
        }

    @staticmethod
    def _parse_stream_chunk(payload: str) -> str:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return ""

        choices = data.get("choices") or []
        if not choices:
            return ""

        delta = choices[0].get("delta") or {}
        return delta.get("content") or ""
