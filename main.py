#!/usr/bin/env python3
"""
LUNA — Intelligence Artificielle Familiale
Point d'entrée principal.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from core.identity import (
    is_setup_done, authenticate, get_user,
    identify_by_name, get_all_users,
)
from core.permissions import get_role_config
from core.luna import Luna
from core import voice_engine
from core import autonomy

console = Console()

BANNER = r"""
 ██╗     ██╗   ██╗███╗   ██╗ █████╗
 ██║     ██║   ██║████╗  ██║██╔══██╗
 ██║     ██║   ██║██╔██╗ ██║███████║
 ██║     ██║   ██║██║╚██╗██║██╔══██║
 ███████╗╚██████╔╝██║ ╚████║██║  ██║
 ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝
"""

PRIORITY_COLORS = {"owner": "gold1", "spouse": "orchid", "child": "cyan"}


def print_banner() -> None:
    console.print(Panel(
        Text(BANNER, style="bold blue", justify="center"),
        subtitle="[dim]Intelligence Artificielle Familiale — Évolutive · Autonome · Protectrice[/dim]",
        border_style="blue",
    ))


def select_user() -> str:
    users = get_all_users()
    console.print("\n[bold]Qui êtes-vous ?[/bold]")
    user_list = sorted(
        users.items(),
        key=lambda x: get_role_config(x[1]["role"])["priority"],
    )

    for i, (uid, user) in enumerate(user_list, 1):
        color = PRIORITY_COLORS.get(user["role"], "white")
        console.print(f"  [{i}] [{color}]{user['name']}[/{color}]")
    console.print()

    choice = Prompt.ask("Votre nom ou numéro").strip()

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(user_list):
            user_id = user_list[idx][0]
        else:
            console.print("[red]Numéro invalide.[/red]")
            return select_user()
    else:
        user_id = identify_by_name(choice)
        if not user_id:
            console.print(f"[red]'{choice}' inconnu.[/red]")
            return select_user()

    user = get_user(user_id)
    for attempt in range(3):
        pin = Prompt.ask(f"PIN pour {user['name']}", password=True)
        if authenticate(user_id, pin):
            rc = get_role_config(user["role"])
            color = PRIORITY_COLORS.get(user["role"], "white")
            console.print(
                f"\n[green]✓[/green] [{color}]{user['name']}[/{color}] "
                f"[dim]({rc['label']})[/dim]"
            )
            return user_id
        remaining = 2 - attempt
        if remaining > 0:
            console.print(f"[red]PIN incorrect. {remaining} essai(s) restant(s).[/red]")

    console.print("[bold red]Accès refusé.[/bold red]")
    sys.exit(1)


def _start_services() -> None:
    """Démarre tous les services en arrière-plan."""
    # Moteur vocal
    voice_engine.start()
    engine_name = voice_engine.get_engine_name()
    if voice_engine.is_available():
        console.print(f"[dim]🔊 Voix : {engine_name}[/dim]")
    else:
        console.print("[dim]🔇 Voix inactive (pip install edge-tts pour activer)[/dim]")

    # Moteur d'autonomie
    autonomy.start()
    console.print("[dim]🤖 Autonomie activée.[/dim]")

    # Serveur iOS
    try:
        from core.server import LunaServer
        from config_loader import get_ios_port
        import socket
        port = get_ios_port()
        server = LunaServer(port=port)
        server.start()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        console.print(f"[dim]📱 Serveur iOS : {ip}:{port}[/dim]")
    except Exception as e:
        console.print(f"[dim]Serveur iOS désactivé : {e}[/dim]")


def input_loop(luna: Luna) -> None:
    user = luna.user
    color = PRIORITY_COLORS.get(user["role"], "white")
    prompt_text = f"[{color}]{user['name']}[/{color}] ❯ "

    console.print(
        "\n[dim]Parlez librement, ou tapez /aide pour les commandes.[/dim]"
    )

    while True:
        try:
            user_input = Prompt.ask(prompt_text).strip()
            if not user_input:
                continue
            luna.chat(user_input)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]À bientôt ![/dim]")
            break
        except SystemExit:
            console.print("\n[dim]Au revoir ![/dim]")
            break


def main() -> None:
    if not is_setup_done():
        console.print("[yellow]Première utilisation — lancez : python setup_wizard.py[/yellow]")
        sys.exit(1)

    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[red]ANTHROPIC_API_KEY manquante — créez un fichier .env[/red]")
        sys.exit(1)

    print_banner()
    _start_services()

    user_id = select_user()

    try:
        luna = Luna(user_id)
        luna.greet()
        input_loop(luna)
    except ValueError as e:
        console.print(f"[red]Erreur : {e}[/red]")
        sys.exit(1)
    finally:
        voice_engine.stop()
        autonomy.stop()


if __name__ == "__main__":
    main()
