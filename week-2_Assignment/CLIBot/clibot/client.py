from __future__ import annotations

import json
import os
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
        return {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in self.messages
            ],
            "stream": stream,
        }

    def send(self, user_text: str) -> str:
        self.messages.append(ChatMessage(role="user", content=user_text))

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                OPENROUTER_URL,
                headers=self._headers(),
                json=self._payload(stream=False),
            )
            response.raise_for_status()
            data = response.json()

        reply = data["choices"][0]["message"]["content"]
        self.messages.append(ChatMessage(role="assistant", content=reply))
        return reply

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
        self.messages.append(ChatMessage(role="assistant", content=reply))

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
