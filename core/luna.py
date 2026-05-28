"""
Classe principale Luna — orchestre IA, identité, mémoire et voix.
"""
from rich.console import Console
from rich.panel import Panel
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

        if command == "/aide" or command == "/help":
            return self._cmd_help()
        elif command == "/note":
            return self._cmd_note(args)
        elif command == "/notes":
            return self._cmd_show_notes()
        elif command == "/effacer":
            return self._cmd_clear()
        elif command == "/utilisateurs":
            return self._cmd_users()
        elif command == "/quitter" or command == "/exit":
            raise SystemExit(0)
        else:
            msg = f"Commande inconnue: `{command}`. Tapez `/aide` pour la liste."
            console.print(f"[yellow]{msg}[/yellow]")
            return msg

    def _cmd_help(self) -> str:
        lines = [
            "[bold]Commandes disponibles:[/bold]",
            "  /aide          — Affiche cette aide",
            "  /note <texte>  — Sauvegarde une note longue durée",
            "  /notes         — Affiche toutes vos notes",
            "  /effacer       — Efface l'historique de cette session",
            "  /quitter       — Quitter Luna",
        ]
        if has_permission(self.user["role"], "manage_users"):
            lines += [
                "",
                "[bold]Commandes propriétaire:[/bold]",
                "  /utilisateurs  — Liste les comptes famille",
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
            msg = "Accès refusé. Seul le propriétaire peut voir les comptes."
            console.print(f"[red]{msg}[/red]")
            return msg
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
