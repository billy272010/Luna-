"""
Classe principale Luna — orchestre IA, identité, mémoire, voix et iOS.
"""
import socket
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import memory, voice
from .ai_engine import AIEngine
from .identity import get_user
from .permissions import has_permission, get_role_config

console = Console()


class Luna:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user = get_user(user_id)
        self.engine = AIEngine()
        self.role_config = get_role_config(self.user["role"])
        self.session_num = memory.increment_session(user_id)

    def _user_color(self) -> str:
        colors = {"owner": "gold1", "spouse": "orchid", "child": "cyan"}
        return colors.get(self.user["role"], "white")

    def _print_luna(self, text: str) -> None:
        console.print(Panel(
            Text(text, style="white"),
            title="[bold blue]✦ LUNA[/bold blue]",
            border_style="blue",
            padding=(0, 2),
        ))
        if voice.is_voice_available():
            # Enlève les emojis pour la synthèse vocale
            clean = "".join(c for c in text if ord(c) < 0x2000)
            voice.speak(clean)

    def greet(self) -> None:
        color = self._user_color()
        notes = memory.get_notes(self.user_id)
        notes_block = ""
        if notes:
            recent = notes[-3:]
            notes_block = "\n\nNotes à garder en mémoire:\n" + "\n".join(
                f"- {n['content']}" for n in recent
            )

        messages = memory.get_history(self.user_id, max_messages=0)
        greeting_prompt = (
            f"Nouvelle session #{self.session_num} pour {self.user['name']}. "
            f"Dis bonjour et propose ton aide.{notes_block}"
        )
        history = [{"role": "user", "content": greeting_prompt}]

        console.print()
        full_response = ""
        with console.status("[blue]Luna réfléchit...[/blue]", spinner="dots"):
            for chunk in self.engine.chat_stream(self.user, history):
                full_response += chunk

        self._print_luna(full_response)
        memory.add_message(self.user_id, "assistant", full_response)

    def chat(self, user_input: str) -> str:
        # Commandes spéciales
        if user_input.strip().startswith("/"):
            return self._handle_command(user_input.strip())

        memory.add_message(self.user_id, "user", user_input)
        history = memory.get_history(self.user_id)

        full_response = ""
        console.print()

        # Streaming avec affichage progressif
        with console.status("[blue]Luna réfléchit...[/blue]", spinner="dots"):
            for chunk in self.engine.chat_stream(self.user, history):
                full_response += chunk

        memory.add_message(self.user_id, "assistant", full_response)
        self._print_luna(full_response)
        return full_response

    def _handle_command(self, cmd: str) -> str:
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in ("/aide", "/help"):
            return self._cmd_help()
        elif command == "/note":
            return self._cmd_note(args)
        elif command == "/notes":
            return self._cmd_show_notes()
        elif command == "/effacer":
            return self._cmd_clear()
        elif command == "/utilisateurs":
            return self._cmd_users()
        # ── iOS ──────────────────────────────────────────────────────────
        elif command == "/ios":
            return self._cmd_ios(args)
        elif command == "/iphone":
            return self._cmd_ios(args)
        elif command == "/appareils":
            return self._cmd_ios_devices()
        elif command == "/raccourcis":
            return self._cmd_ios_shortcuts()
        elif command == "/position":
            return self._cmd_ios_location(args)
        # ─────────────────────────────────────────────────────────────────
        elif command in ("/quitter", "/exit"):
            raise SystemExit(0)
        else:
            msg = f"Commande inconnue: `{command}`. Tapez `/aide` pour la liste."
            console.print(f"[yellow]{msg}[/yellow]")
            return msg

    def _cmd_help(self) -> str:
        lines = [
            "[bold]Commandes disponibles:[/bold]",
            "  /aide                   — Affiche cette aide",
            "  /note <texte>           — Sauvegarde une note longue durée",
            "  /notes                  — Affiche toutes vos notes",
            "  /effacer                — Efface l'historique de cette session",
            "  /quitter                — Quitter Luna",
            "",
            "[bold]Contrôle iOS:[/bold]",
            "  /ios <id_raccourci>     — Déclenche un raccourci sur votre iPhone",
            "  /iphone <uid> <id>      — Raccourci sur l'iPhone d'un autre membre",
            "  /appareils              — Liste les iPhones enregistrés",
            "  /raccourcis             — Liste les raccourcis disponibles",
            "  /position [uid]         — Dernière position GPS connue",
        ]
        if has_permission(self.user["role"], "manage_users"):
            lines += [
                "",
                "[bold]Commandes propriétaire:[/bold]",
                "  /utilisateurs           — Liste les comptes famille",
                "  /ios <uid> <id>         — Contrôle l'iPhone de n'importe quel membre",
            ]
        console.print("\n".join(lines))
        return ""

    def _cmd_note(self, text: str) -> str:
        if not text:
            console.print("[yellow]Usage: /note <texte de la note>[/yellow]")
            return ""
        memory.add_note(self.user_id, text)
        msg = f"Note enregistrée: \"{text}\""
        console.print(f"[green]✓ {msg}[/green]")
        return msg

    def _cmd_show_notes(self) -> str:
        notes = memory.get_notes(self.user_id)
        if not notes:
            console.print("[dim]Aucune note enregistrée.[/dim]")
            return ""
        console.print("[bold]Vos notes:[/bold]")
        for i, note in enumerate(notes, 1):
            date = note["timestamp"][:10]
            console.print(f"  [dim]{i}.[/dim] [{date}] {note['content']}")
        return ""

    def _cmd_clear(self) -> str:
        memory.clear_history(self.user_id)
        msg = "Historique de conversation effacé."
        console.print(f"[green]✓ {msg}[/green]")
        return msg

    def _cmd_users(self) -> str:
        if not has_permission(self.user["role"], "manage_users"):
            console.print("[red]Accès refusé. Seul le propriétaire peut voir les comptes.[/red]")
            return ""
        from .identity import get_all_users
        users = get_all_users()
        console.print("[bold]Comptes famille:[/bold]")
        for uid, u in users.items():
            rc = get_role_config(u["role"])
            console.print(
                f"  • [bold]{u['name']}[/bold] "
                f"({rc['label']}, priorité {rc['priority']})"
            )
        return ""

    # ── Commandes iOS ─────────────────────────────────────────────────────────

    def _cmd_ios(self, args: str) -> str:
        """
        Usage :
          /ios <id_raccourci>              → sur votre propre iPhone
          /ios <user_id> <id_raccourci>    → iPhone d'un autre membre (owner only)
        """
        from skills.ios_shortcuts import send_command, get_shortcut_by_id
        from .identity import get_all_users

        if not args:
            console.print("[yellow]Usage: /ios <id_raccourci>  ou  /ios <uid> <id_raccourci>[/yellow]")
            console.print("[dim]Tapez /raccourcis pour voir les IDs disponibles.[/dim]")
            return ""

        parts = args.split(maxsplit=1)
        users = get_all_users()

        # Détermine si le 1er mot est un user_id connu
        if len(parts) == 2 and parts[0] in users:
            target_uid = parts[0]
            shortcut_id = parts[1]
            if not has_permission(self.user["role"], "manage_users"):
                console.print("[red]Seul le propriétaire peut contrôler l'iPhone d'un autre membre.[/red]")
                return ""
        else:
            target_uid = self.user_id
            shortcut_id = parts[0]

        shortcut = get_shortcut_by_id(shortcut_id)
        if not shortcut:
            console.print(f"[red]Raccourci '{shortcut_id}' introuvable.[/red]")
            console.print("[dim]Tapez /raccourcis pour voir la liste.[/dim]")
            return ""

        target_user = users.get(target_uid, {})
        target_name = target_user.get("name", target_uid)

        with console.status(f"[blue]Envoi vers {target_name}...[/blue]"):
            result = send_command(target_uid, shortcut_id, current_user_role=self.user["role"])

        if "error" in result:
            console.print(f"[red]✗ Erreur : {result['error']}[/red]")
        else:
            console.print(
                f"[green]✓ Raccourci '[bold]{shortcut['shortcut_name']}[/bold]' "
                f"envoyé à {target_name}[/green]"
            )
        return ""

    def _cmd_ios_devices(self) -> str:
        """Liste les iPhones enregistrés + appareils USB connectés."""
        from skills.ios_shortcuts import list_devices
        from skills.ios_device import list_connected_devices, is_available as pmd3_ok
        from .identity import get_all_users

        users = get_all_users()
        registered = list_devices()

        table = Table(title="iPhones enregistrés", border_style="blue")
        table.add_column("Membre", style="bold")
        table.add_column("Appareil")
        table.add_column("IP locale")
        table.add_column("Statut")

        for uid, user in users.items():
            dev = registered.get(uid, {})
            ip = dev.get("ip") or "—"
            name = dev.get("name") or "Non configuré"
            status = "[green]Configuré[/green]" if dev.get("ip") else "[dim]À configurer[/dim]"
            table.add_row(user["name"], name, ip, status)

        console.print(table)

        if pmd3_ok():
            usb = list_connected_devices()
            if usb and "error" not in usb[0]:
                console.print("\n[bold]Appareils USB connectés :[/bold]")
                for d in usb:
                    console.print(f"  • UDID : [cyan]{d.get('udid')}[/cyan]")
            else:
                console.print("\n[dim]Aucun iPhone connecté en USB.[/dim]")
        else:
            console.print("\n[dim]pymobiledevice3 non installé — contrôle USB indisponible.[/dim]")

        local_ip = _get_local_ip()
        console.print(f"\n[bold]IP de Luna sur ce réseau :[/bold] [cyan]{local_ip}[/cyan]")
        console.print("[dim]Les iPhones doivent utiliser cette IP pour contacter Luna.[/dim]")
        return ""

    def _cmd_ios_shortcuts(self) -> str:
        """Affiche les raccourcis disponibles."""
        from skills.ios_shortcuts import list_shortcuts

        shortcuts = list_shortcuts(self.user["role"])
        table = Table(title="Raccourcis iOS disponibles", border_style="blue")
        table.add_column("ID", style="cyan")
        table.add_column("Nom du Raccourci")
        table.add_column("Description")
        table.add_column("Catégorie")

        for s in shortcuts:
            owner_tag = " [red][owner][/red]" if s.get("owner_only") else ""
            table.add_row(
                s["id"],
                s["shortcut_name"] + owner_tag,
                s["description"],
                s["category"],
            )

        console.print(table)
        console.print("\n[dim]Usage : /ios <ID>  ou  /ios <uid> <ID>[/dim]")
        return ""

    def _cmd_ios_location(self, args: str) -> str:
        """Affiche la dernière position GPS connue d'un membre."""
        from core.server import get_last_location
        from .identity import get_all_users

        uid = args.strip() if args.strip() else self.user_id

        if uid != self.user_id and not has_permission(self.user["role"], "manage_users"):
            console.print("[red]Seul le propriétaire peut voir la position des autres membres.[/red]")
            return ""

        users = get_all_users()
        name = users.get(uid, {}).get("name", uid)
        loc = get_last_location(uid)

        if not loc:
            console.print(f"[yellow]Aucune position reçue de {name}.[/yellow]")
            console.print("[dim]Le Raccourci 'Luna Position' doit être exécuté sur l'iPhone.[/dim]")
            return ""

        console.print(f"\n[bold]Position de {name} :[/bold]")
        console.print(f"  Coordonnées : [cyan]{loc['lat']}, {loc['lon']}[/cyan]")
        if loc.get("address"):
            console.print(f"  Adresse     : {loc['address']}")
        console.print(f"  Précision   : {loc.get('accuracy', '?')} m")
        console.print(f"  Reçu le     : [dim]{loc['timestamp'][:19]}[/dim]")
        console.print(
            f"\n  [link=https://maps.apple.com/?q={loc['lat']},{loc['lon']}]"
            f"Ouvrir dans Maps[/link]"
        )
        return ""


def _get_local_ip() -> str:
    """Retourne l'IP locale de la machine."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
