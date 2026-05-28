#!/usr/bin/env python3
"""
LUNA — Intelligence Artificielle Familiale
Point d'entrée principal.
"""
import os
import sys
from pathlib import Path

# Charge .env en premier
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
from core import voice

console = Console()

BANNER = r"""
 ██╗     ██╗   ██╗███╗   ██╗ █████╗
 ██║     ██║   ██║████╗  ██║██╔══██╗
 ██║     ██║   ██║██╔██╗ ██║███████║
 ██║     ██║   ██║██║╚██╗██║██╔══██║
 ███████╗╚██████╔╝██║ ╚████║██║  ██║
 ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝
"""

PRIORITY_COLORS = {
    "owner": "gold1",
    "spouse": "orchid",
    "child": "cyan",
}


def print_banner():
    console.print(Panel(
        Text(BANNER, style="bold blue", justify="center"),
        subtitle="[dim]Intelligence Artificielle Familiale[/dim]",
        border_style="blue",
    ))


def select_user() -> str:
    """Sélection et authentification de l'utilisateur."""
    users = get_all_users()

    console.print("\n[bold]Qui êtes-vous ?[/bold]")
    user_list = sorted(users.items(), key=lambda x: get_role_config(x[1]["role"])["priority"])

    for i, (uid, user) in enumerate(user_list, 1):
        rc = get_role_config(user["role"])
        color = PRIORITY_COLORS.get(user["role"], "white")
        console.print(f"  [{i}] [{color}]{user['name']}[/{color}]")

    console.print()

    # Accepte le nom ou le numéro
    choice = Prompt.ask("Votre nom ou numéro").strip()

    # Résolution par numéro
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(user_list):
            user_id = user_list[idx][0]
        else:
            console.print("[red]Numéro invalide.[/red]")
            return select_user()
    else:
        # Résolution par nom/alias
        user_id = identify_by_name(choice)
        if not user_id:
            console.print(f"[red]Utilisateur '{choice}' inconnu.[/red]")
            return select_user()

    # Authentification PIN
    user = get_user(user_id)
    for attempt in range(3):
        pin = Prompt.ask(f"PIN pour {user['name']}", password=True)
        if authenticate(user_id, pin):
            rc = get_role_config(user["role"])
            color = PRIORITY_COLORS.get(user["role"], "white")
            console.print(
                f"\n[green]✓ Authentifié :[/green] "
                f"[{color}]{user['name']}[/{color}] "
                f"[dim]({rc['label']})[/dim]"
            )
            return user_id
        remaining = 2 - attempt
        if remaining > 0:
            console.print(f"[red]PIN incorrect. {remaining} essai(s) restant(s).[/red]")

    console.print("[bold red]Accès refusé après 3 tentatives.[/bold red]")
    sys.exit(1)


def input_loop(luna: Luna, voice_mode: bool) -> None:
    """Boucle principale de conversation."""
    user = luna.user
    color = PRIORITY_COLORS.get(user["role"], "white")
    prompt_text = f"[{color}]{user['name']}[/{color}] ❯ "

    console.print("\n[dim]Tapez votre message, /aide pour les commandes, /quitter pour quitter.[/dim]")
    if voice_mode:
        console.print("[dim]Mode vocal actif — appuyez sur Entrée sans texte pour parler.[/dim]")

    while True:
        try:
            user_input = Prompt.ask(prompt_text).strip()

            # Mode vocal : entrée vide = écouter le micro
            if not user_input and voice_mode and voice.is_stt_available():
                console.print("[dim]Écoute...[/dim]")
                spoken = voice.listen()
                if spoken:
                    console.print(f"[dim]Vous avez dit : {spoken}[/dim]")
                    user_input = spoken
                else:
                    console.print("[yellow]Rien entendu.[/yellow]")
                    continue

            if not user_input:
                continue

            luna.chat(user_input)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Au revoir ![/dim]")
            break
        except SystemExit:
            console.print("\n[dim]À bientôt ![/dim]")
            break


def main():
    # Vérifie la configuration
    if not is_setup_done():
        console.print("[yellow]Première utilisation détectée.[/yellow]")
        console.print("Lancez d'abord : [bold]python setup_wizard.py[/bold]")
        sys.exit(1)

    # Vérifie la clé API
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[red]Erreur : ANTHROPIC_API_KEY manquante.[/red]")
        console.print("Créez un fichier .env avec votre clé Anthropic.")
        console.print("Exemple : [dim]ANTHROPIC_API_KEY=sk-ant-...[/dim]")
        sys.exit(1)

    print_banner()

    # Vérifie le mode vocal
    voice_mode = voice.is_voice_available()
    if voice_mode:
        console.print("[dim]🎙  Mode vocal disponible.[/dim]")

    # Authentification
    user_id = select_user()

    # Démarre Luna
    try:
        luna = Luna(user_id)
        luna.greet()
        input_loop(luna, voice_mode)
    except ValueError as e:
        console.print(f"[red]Erreur de configuration : {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Erreur inattendue : {e}[/red]")
        raise


if __name__ == "__main__":
    main()
