from __future__ import annotations

import sys

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from clibot.client import OpenRouterClient

console = Console()


def print_help() -> None:
    console.print(
        Panel(
            "[bold]/help[/]    Show this help\n"
            "[bold]/clear[/]   Clear conversation history\n"
            "[bold]/model[/]   Show the current model\n"
            "[bold]/quit[/]    Exit the chat",
            title="Commands",
            border_style="cyan",
        )
    )


def print_welcome(client: OpenRouterClient) -> None:
    console.print(
        Panel(
            f"[bold]CLIBot[/] — OpenRouter chat\n"
            f"Model: [cyan]{client.model}[/]\n"
            f"Type a message or [bold]/help[/] for commands.",
            border_style="green",
        )
    )


def main() -> None:
    load_dotenv()

    try:
        client = OpenRouterClient.from_env()
    except ValueError as exc:
        console.print(f"[red]Error:[/] {exc}")
        sys.exit(1)

    print_welcome(client)

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]")
            break

        if not user_input:
            continue

        command = user_input.lower()
        if command in {"/quit", "/exit", "/q"}:
            console.print("[dim]Goodbye![/]")
            break
        if command == "/help":
            print_help()
            continue
        if command == "/clear":
            client.clear_history()
            console.print("[dim]Conversation cleared.[/]")
            continue
        if command == "/model":
            console.print(f"[cyan]Current model:[/] {client.model}")
            continue

        console.print("[bold blue]Assistant[/]", end=" ")
        try:
            chunks: list[str] = []
            for chunk in client.stream(user_input):
                console.print(chunk, end="")
                chunks.append(chunk)
            if not chunks:
                console.print("[dim](no response)[/]")
            console.print()
        except httpx.HTTPStatusError as exc:
            console.print()
            console.print(f"[red]API error {exc.response.status_code}:[/] {exc.response.text}")
            client.messages.pop()
        except httpx.HTTPError as exc:
            console.print()
            console.print(f"[red]Network error:[/] {exc}")
            client.messages.pop()


if __name__ == "__main__":
    main()
