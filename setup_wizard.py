"""
Assistant de configuration initial de Luna.
Lancé automatiquement à la première utilisation.
"""
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from core.identity import create_user, is_setup_done

console = Console()

BANNER = r"""
 ██╗     ██╗   ██╗███╗   ██╗ █████╗
 ██║     ██║   ██║████╗  ██║██╔══██╗
 ██║     ██║   ██║██╔██╗ ██║███████║
 ██║     ██║   ██║██║╚██╗██║██╔══██║
 ███████╗╚██████╔╝██║ ╚████║██║  ██║
 ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝
     Intelligence Artificielle Familiale
"""


def run_setup():
    console.print(Panel(BANNER, border_style="blue", title="[bold]Bienvenue[/bold]"))
    console.print("\n[bold cyan]Configuration initiale de Luna[/bold cyan]")
    console.print("Ce processus ne se fait qu'une seule fois.\n")

    # --- Propriétaire ---
    console.print("[bold gold1]═══ Compte Propriétaire (vous) ═══[/bold gold1]")
    owner_name = Prompt.ask("Votre prénom")
    owner_aliases_input = Prompt.ask(
        "Autres noms que Luna peut vous appeler (séparés par virgule, Entrée pour ignorer)",
        default="",
    )
    owner_aliases = [a.strip().lower() for a in owner_aliases_input.split(",") if a.strip()]
    owner_aliases.append(owner_name.lower())

    while True:
        owner_pin = Prompt.ask("Votre code PIN (4+ chiffres)", password=True)
        if len(owner_pin) >= 4 and owner_pin.isdigit():
            break
        console.print("[red]Le PIN doit contenir au moins 4 chiffres.[/red]")

    owner_pin_confirm = Prompt.ask("Confirmez votre PIN", password=True)
    if owner_pin != owner_pin_confirm:
        console.print("[red]Les PINs ne correspondent pas. Relancez la configuration.[/red]")
        sys.exit(1)

    # --- Épouse ---
    console.print("\n[bold orchid]═══ Compte Épouse ═══[/bold orchid]")
    wife_name = Prompt.ask("Prénom de votre épouse")
    wife_aliases_input = Prompt.ask(
        "Autres noms (séparés par virgule, Entrée pour ignorer)",
        default="",
    )
    wife_aliases = [a.strip().lower() for a in wife_aliases_input.split(",") if a.strip()]
    wife_aliases.append(wife_name.lower())

    while True:
        wife_pin = Prompt.ask(f"PIN pour {wife_name} (4+ chiffres)", password=True)
        if len(wife_pin) >= 4 and wife_pin.isdigit():
            break
        console.print("[red]Le PIN doit contenir au moins 4 chiffres.[/red]")

    # --- Fille ---
    console.print("\n[bold cyan]═══ Compte Fille ═══[/bold cyan]")
    daughter_name = Prompt.ask("Prénom de votre fille")
    daughter_aliases_input = Prompt.ask(
        "Autres noms (séparés par virgule, Entrée pour ignorer)",
        default="",
    )
    daughter_aliases = [a.strip().lower() for a in daughter_aliases_input.split(",") if a.strip()]
    daughter_aliases.append(daughter_name.lower())

    while True:
        daughter_pin = Prompt.ask(f"PIN pour {daughter_name} (4+ chiffres)", password=True)
        if len(daughter_pin) >= 4 and daughter_pin.isdigit():
            break
        console.print("[red]Le PIN doit contenir au moins 4 chiffres.[/red]")

    # --- Sauvegarde ---
    console.print("\n[dim]Création des comptes...[/dim]")
    create_user("owner", owner_name, "owner", owner_pin, owner_aliases)
    create_user("wife", wife_name, "spouse", wife_pin, wife_aliases)
    create_user("daughter", daughter_name, "child", daughter_pin, daughter_aliases)

    console.print(f"\n[bold green]✓ Configuration terminée ![/bold green]")
    console.print(f"  Propriétaire : [gold1]{owner_name}[/gold1]")
    console.print(f"  Épouse       : [orchid]{wife_name}[/orchid]")
    console.print(f"  Fille        : [cyan]{daughter_name}[/cyan]")
    console.print("\n[dim]Luna est prête. Relancez main.py pour démarrer.[/dim]\n")


if __name__ == "__main__":
    if is_setup_done():
        console.print("[yellow]La configuration est déjà effectuée.[/yellow]")
        console.print("[dim]Pour reconfigurer, supprimez data/users/users.json[/dim]")
        sys.exit(0)
    run_setup()
