from __future__ import annotations
import argparse
import concurrent.futures
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODELS = (
    ("nvidia/nemotron-3-ultra-550b-a55b:free", "Nemotron Ultra", "reasoning"),
    ("openai/gpt-4o-mini", "GPT-4o Mini", "fast / cheap"),
    ("google/gemma-4-26b-a4b-it:free", "Gemma 4 26B", "balanced"),
)

DEFAULT_PROMPT = (
    "How do you plan your day to stay productive?"
)

console = Console()


@dataclass
class ModelResult:
    model_id: str
    label: str
    tier: str
    latency_s: float
    ttft_s: float | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float | None
    tokens_per_second: float | None
    response: str
    error: str | None = None


def load_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
    return api_key


def load_models() -> list[tuple[str, str, str]]:
    overrides = [
        os.getenv("COMPARE_MODEL_1", "").strip(),
        os.getenv("COMPARE_MODEL_2", "").strip(),
        os.getenv("COMPARE_MODEL_3", "").strip(),
    ]
    if any(overrides):
        models = []
        for index, model_id in enumerate(overrides, start=1):
            if not model_id:
                continue
            models.append((
                model_id,
                os.getenv(f"COMPARE_MODEL_{index}_LABEL", model_id).strip(),
                os.getenv(f"COMPARE_MODEL_{index}_TIER", "custom").strip(),
            ))
        if models:
            return models
    return list(DEFAULT_MODELS)


def _extract_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            exc.response.read()
            detail = exc.response.json().get("error", {})
            message = detail.get("message") or detail
            base = f"HTTP {exc.response.status_code}: {message}"
        except Exception:
            base = f"HTTP {exc.response.status_code}"

        if exc.response.status_code == 402:
            base += " (add credits at openrouter.ai/credits)"
        elif exc.response.status_code == 404:
            base += " (model slug not found — check openrouter.ai/models)"
        return base
    return str(exc)


def _calc_tokens_per_second(
    latency_s: float, ttft_s: float | None, completion_tokens: int
) -> float | None:
    if completion_tokens <= 0:
        return None
    generation_time = latency_s - (ttft_s or 0.0)
    if generation_time <= 0:
        return None
    return completion_tokens / generation_time


def run_model(
    api_key: str,
    model_id: str,
    label: str,
    tier: str,
    prompt: str,
    *,
    timeout: float = 120.0,
) -> ModelResult:
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "usage": {"include": True},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    started = time.perf_counter()
    ttft_s: float | None = None
    chunks: list[str] = []
    usage: dict[str, Any] = {}

    try:
        with httpx.Client(timeout=timeout) as client:
            with client.stream(
                "POST", OPENROUTER_URL, headers=headers, json=payload
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
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(
            usage.get("total_tokens") or prompt_tokens + completion_tokens
        )
        cost_raw = usage.get("cost")
        cost_usd = float(cost_raw) if cost_raw is not None else None

        return ModelResult(
            model_id=model_id,
            label=label,
            tier=tier,
            latency_s=latency_s,
            ttft_s=ttft_s,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            tokens_per_second=_calc_tokens_per_second(
                latency_s, ttft_s, completion_tokens
            ),
            response="".join(chunks),
        )
    except Exception as exc:
        latency_s = time.perf_counter() - started
        return ModelResult(
            model_id=model_id,
            label=label,
            tier=tier,
            latency_s=latency_s,
            ttft_s=ttft_s,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd=None,
            tokens_per_second=None,
            response="",
            error=_extract_error(exc),
        )


def run_comparison(
    prompt: str,
    *,
    parallel: bool = False,
    timeout: float = 120.0,
) -> list[ModelResult]:
    api_key = load_api_key()
    models = load_models()

    def _run(spec: tuple[str, str, str]) -> ModelResult:
        model_id, label, tier = spec
        return run_model(api_key, model_id, label, tier, prompt, timeout=timeout)

    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as pool:
            futures = [pool.submit(_run, spec) for spec in models]
            return [future.result() for future in futures]

    return [_run(spec) for spec in models]


def save_results(
    path: Path,
    prompt: str,
    results: list[ModelResult],
    *,
    parallel: bool,
) -> Path:
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "prompt": prompt,
        "parallel": parallel,
        "models": [asdict(result) for result in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def print_summary(results: list[ModelResult]) -> None:
    ok_latencies = [r.latency_s for r in results if not r.error]
    ok_costs = [r.cost_usd for r in results if not r.error and r.cost_usd is not None]
    fastest = min(ok_latencies) if ok_latencies else None
    cheapest = min(ok_costs) if ok_costs else None

    table = Table(title="Model Comparison", show_lines=True)
    table.add_column("Model", style="bold")
    table.add_column("Tier")
    table.add_column("Latency", justify="right")
    table.add_column("TTFT", justify="right")
    table.add_column("Output tok/s", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Status")

    for result in results:
        latency_style = "green" if fastest and not result.error and result.latency_s == fastest else ""
        cost_style = (
            "green"
            if cheapest
            and not result.error
            and result.cost_usd is not None
            and result.cost_usd == cheapest
            else ""
        )
        status = Text("error", style="red") if result.error else Text("ok", style="green")

        table.add_row(
            result.label,
            result.tier,
            Text(f"{result.latency_s:.2f}s", style=latency_style),
            f"{result.ttft_s:.2f}s" if result.ttft_s is not None else "n/a",
            f"{result.tokens_per_second:.1f} tok/s" if result.tokens_per_second else "n/a",
            str(result.total_tokens),
            Text(f"${result.cost_usd:.6f}" if result.cost_usd is not None else "n/a", style=cost_style),
            status,
        )

    console.print(table)


def print_responses(results: list[ModelResult]) -> None:
    for result in results:
        title = f"{result.label} ({result.model_id})"
        if result.error:
            body = f"[red]Request failed:[/red] {result.error}"
        else:
            body = result.response.strip() or "[dim](empty response)[/dim]"
        console.print(Panel(body, title=title, expand=False))


def main() -> None:
    load_dotenv()
    default_output = Path(__file__).parent / "results.json"

    parser = argparse.ArgumentParser(
        description="Compare 3 OpenRouter models on the same prompt."
    )
    parser.add_argument("--prompt", help="Prompt text (or use COMPARE_PROMPT env).")
    parser.add_argument("--prompt-file", type=Path, help="Read prompt from a file.")
    parser.add_argument("--parallel", action="store_true", help="Run models concurrently.")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=default_output,
        help=f"Save results JSON (default: {default_output.name}).",
    )
    args = parser.parse_args()

    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8").strip()
    elif args.prompt:
        prompt = args.prompt.strip()
    else:
        prompt = os.getenv("COMPARE_PROMPT", DEFAULT_PROMPT).strip() or DEFAULT_PROMPT

    console.print(Panel(prompt, title="Prompt", expand=False))
    console.print()

    results = run_comparison(prompt, parallel=args.parallel, timeout=args.timeout)
    output_path = save_results(args.output, prompt, results, parallel=args.parallel)

    print_summary(results)
    console.print()
    print_responses(results)
    console.print(f"\n[green]Saved results to[/] {output_path.resolve()}")


if __name__ == "__main__":
    main()
