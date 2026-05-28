"""
Classe principale Luna — orchestre tous les systèmes.
"""
import socket
import threading
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import memory
from .ai_engine import AIEngine
from .autonomy import pop_proactive, add_reminder, get_reminders
from .guardian import analyze_message, get_recent_alerts
from .identity import get_user
from .learning import (
    update_from_message, learn_fact, update_preference,
    get_evolution_report, record_correction, build_adaptive_context,
)
from .permissions import has_permission, get_role_config
from .voice_engine import speak, is_available as voice_ok, get_engine_name

console = Console()


class Luna:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user = get_user(user_id)
        self.engine = AIEngine()
        self.role_config = get_role_config(self.user["role"])
        self.session_num = memory.increment_session(user_id)
        self._last_response = ""

    # ── Affichage ─────────────────────────────────────────────────────────────

    def _user_color(self) -> str:
        return {"owner": "gold1", "spouse": "orchid", "child": "cyan"}.get(
            self.user["role"], "white"
        )

    def _print_luna(self, text: str, say: bool = True) -> None:
        if not text.strip():
            return
        console.print(Panel(
            Text(text, style="white"),
            title="[bold blue]✦ LUNA[/bold blue]",
            border_style="blue",
            padding=(0, 2),
        ))
        if say and voice_ok():
            speak(text)

    def _print_system(self, text: str, style: str = "dim") -> None:
        console.print(f"[{style}]{text}[/{style}]")

    # ── Salutation ────────────────────────────────────────────────────────────

    def greet(self) -> None:
        # Messages proactifs en attente
        pending = pop_proactive(self.user_id)
        if pending:
            self._print_luna(pending)
            memory.add_message(self.user_id, "assistant", pending)
            return

        notes = memory.get_notes(self.user_id)
        notes_block = ""
        if notes:
            notes_block = "\n\nNotes récentes : " + " | ".join(
                n["content"] for n in notes[-2:]
            )

        reminders = get_reminders(self.user_id)
        rem_block = f"\n{len(reminders)} rappel(s) en attente." if reminders else ""

        greeting_prompt = (
            f"Nouvelle session #{self.session_num} pour {self.user['name']}. "
            f"Dis bonjour chaleureusement et propose ton aide de façon naturelle.{notes_block}{rem_block}"
        )
        history = [{"role": "user", "content": greeting_prompt}]

        console.print()
        full_response = ""
        with console.status("[blue]Luna...[/blue]", spinner="dots"):
            for chunk in self.engine.chat_stream(self.user, history, self.user_id):
                full_response += chunk

        self._print_luna(full_response)
        memory.add_message(self.user_id, "assistant", full_response)

    # ── Conversation principale ───────────────────────────────────────────────

    def chat(self, user_input: str) -> str:
        if user_input.strip().startswith("/"):
            return self._handle_command(user_input.strip())

        # Analyse de sécurité
        threat = analyze_message(user_input, self.user["role"], self.user_id)
        if threat.should_block:
            self._print_luna(threat.block_response, say=True)
            if threat.notify_owner and self.user["role"] != "owner":
                self._notify_owner(f"Alerte sécurité : tentative bloquée pour {self.user['name']}")
            return threat.block_response

        # Apprentissage (message entrant)
        profile = update_from_message(self.user_id, user_input, role="user")
        mood = profile.get("current_mood", "neutral")

        # Auto-détection de faits à mémoriser
        self._auto_learn(user_input)

        # Ajout à l'historique
        memory.add_message(self.user_id, "user", user_input)
        history = memory.get_history(self.user_id)

        full_response = ""
        console.print()

        with console.status("[blue]Luna réfléchit...[/blue]", spinner="dots"):
            for chunk in self.engine.chat_stream(self.user, history, self.user_id):
                full_response += chunk

        memory.add_message(self.user_id, "assistant", full_response)
        update_from_message(self.user_id, full_response, role="assistant")
        self._print_luna(full_response)
        self._last_response = full_response

        # Message proactif en attente ?
        pending = pop_proactive(self.user_id)
        if pending:
            console.print()
            self._print_luna(f"[Proactif] {pending}")

        return full_response

    # ── Auto-apprentissage ────────────────────────────────────────────────────

    def _auto_learn(self, text: str) -> None:
        """Extrait des faits implicites du message."""
        import re
        patterns = [
            (r"j'aime (\w[\w\s]{2,20})", "Aime : {}"),
            (r"je préfère (\w[\w\s]{2,20})", "Préfère : {}"),
            (r"je déteste (\w[\w\s]{2,20})", "Déteste : {}"),
            (r"je travaille (?:comme|en tant que) (\w[\w\s]{2,20})", "Travaille comme : {}"),
            (r"j'habite (?:à|en|au) (\w[\w\s]{2,20})", "Habite : {}"),
            (r"j'ai (\d+) ans", "Âge : {} ans"),
            (r"ma fille s'appelle (\w+)", "Prénom fille : {}"),
            (r"ma femme s'appelle (\w+)", "Prénom femme : {}"),
        ]
        for pattern, template in patterns:
            m = re.search(pattern, text.lower())
            if m:
                learn_fact(self.user_id, template.format(m.group(1)))

    def _notify_owner(self, message: str) -> None:
        """Notifie le propriétaire d'un événement important."""
        from .autonomy import push_proactive
        push_proactive("owner", f"🔔 {message}")

    # ── Gestion des commandes ─────────────────────────────────────────────────

    def _handle_command(self, cmd: str) -> str:
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        dispatch = {
            "/aide": lambda: self._cmd_help(),
            "/help": lambda: self._cmd_help(),
            "/note": lambda: self._cmd_note(args),
            "/notes": lambda: self._cmd_show_notes(),
            "/effacer": lambda: self._cmd_clear(),
            "/utilisateurs": lambda: self._cmd_users(),
            "/rappel": lambda: self._cmd_reminder(args),
            "/rappels": lambda: self._cmd_show_reminders(),
            "/evolution": lambda: self._cmd_evolution(),
            "/voix": lambda: self._cmd_voice_info(),
            "/ios": lambda: self._cmd_ios(args),
            "/iphone": lambda: self._cmd_ios(args),
            "/appareils": lambda: self._cmd_ios_devices(),
            "/raccourcis": lambda: self._cmd_ios_shortcuts(),
            "/position": lambda: self._cmd_ios_location(args),
            "/alertes": lambda: self._cmd_alerts(),
            "/apprendre": lambda: self._cmd_learn(args),
            "/quitter": self._quit,
            "/exit": self._quit,
        }

        fn = dispatch.get(command)
        if fn:
            return fn() or ""
        console.print(f"[yellow]Commande inconnue : `{command}`. Tapez /aide[/yellow]")
        return ""

    def _quit(self):
        raise SystemExit(0)

    # ── Commandes standard ────────────────────────────────────────────────────

    def _cmd_help(self) -> str:
        lines = [
            "[bold]Commandes Luna[/bold]",
            "",
            "[bold cyan]Conversation & Mémoire[/bold cyan]",
            "  /note <texte>           — Note longue durée",
            "  /notes                  — Voir vos notes",
            "  /rappel <h:mm> <texte>  — Programmer un rappel",
            "  /rappels                — Voir les rappels en attente",
            "  /effacer                — Effacer l'historique",
            "  /apprendre <fait>       — Dire à Luna quelque chose à retenir",
            "",
            "[bold cyan]Évolution & Statut[/bold cyan]",
            "  /evolution              — Rapport d'apprentissage de Luna",
            "  /voix                   — Infos sur le moteur vocal actif",
            "",
            "[bold cyan]Contrôle iOS[/bold cyan]",
            "  /ios <id>               — Déclenche un raccourci sur votre iPhone",
            "  /appareils              — iPhones enregistrés",
            "  /raccourcis             — Liste des raccourcis disponibles",
            "  /position [uid]         — Dernière position GPS",
        ]
        if has_permission(self.user["role"], "manage_users"):
            lines += [
                "",
                "[bold red]Propriétaire uniquement[/bold red]",
                "  /utilisateurs           — Comptes famille",
                "  /alertes                — Journal de sécurité",
                "  /ios <uid> <id>         — Contrôle l'iPhone d'un membre",
            ]
        lines.append("\n  /quitter  — Quitter")
        console.print("\n".join(lines))
        return ""

    def _cmd_note(self, text: str) -> str:
        if not text:
            console.print("[yellow]Usage : /note <texte>[/yellow]")
            return ""
        memory.add_note(self.user_id, text)
        console.print(f"[green]✓ Note enregistrée.[/green]")
        return ""

    def _cmd_show_notes(self) -> str:
        notes = memory.get_notes(self.user_id)
        if not notes:
            console.print("[dim]Aucune note.[/dim]")
            return ""
        console.print("[bold]Vos notes :[/bold]")
        for i, note in enumerate(notes, 1):
            date = note["timestamp"][:10]
            console.print(f"  [dim]{i}.[/dim] [{date}] {note['content']}")
        return ""

    def _cmd_clear(self) -> str:
        memory.clear_history(self.user_id)
        console.print("[green]✓ Historique effacé.[/green]")
        return ""

    def _cmd_users(self) -> str:
        if not has_permission(self.user["role"], "manage_users"):
            console.print("[red]Accès refusé.[/red]")
            return ""
        from .identity import get_all_users
        users = get_all_users()
        for uid, u in users.items():
            rc = get_role_config(u["role"])
            console.print(f"  • [bold]{u['name']}[/bold] ({rc['label']}, priorité {rc['priority']})")
        return ""

    def _cmd_reminder(self, args: str) -> str:
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            console.print("[yellow]Usage : /rappel HH:MM <texte du rappel>[/yellow]")
            return ""
        time_str, text = parts
        try:
            add_reminder(self.user_id, text, time_str)
            console.print(f"[green]✓ Rappel programmé à {time_str} : {text}[/green]")
        except Exception as e:
            console.print(f"[red]Erreur : {e}[/red]")
        return ""

    def _cmd_show_reminders(self) -> str:
        reminders = get_reminders(self.user_id)
        if not reminders:
            console.print("[dim]Aucun rappel en attente.[/dim]")
            return ""
        console.print("[bold]Rappels en attente :[/bold]")
        for r in reminders:
            at = r["at"][:16].replace("T", " ")
            console.print(f"  ⏰ [{at}] {r['text']}")
        return ""

    def _cmd_evolution(self) -> str:
        report = get_evolution_report(self.user_id)
        table = Table(title="Évolution de Luna", border_style="blue")
        table.add_column("Indicateur", style="bold")
        table.add_column("Valeur", style="cyan")

        table.add_row("Score d'évolution", f"{report['evolution_score']:.0f} / 100")
        table.add_row("Interactions totales", str(report["interactions"]))
        table.add_row("Ratio positif", f"{report['positive_ratio']}%")
        table.add_row("Gratitudes reçues", str(report["gratitude_count"]))
        table.add_row("Faits mémorisés", str(report["learned_facts"]))

        if report["peak_hour"] is not None:
            table.add_row("Heure de pic", f"{report['peak_hour']}h")

        if report["top_topics"]:
            topics_str = ", ".join(f"{t[0]}({t[1]})" for t in report["top_topics"])
            table.add_row("Sujets favoris", topics_str)

        console.print(table)

        moods = report.get("mood_distribution", {})
        if moods:
            console.print("\n[bold]Distribution d'humeur récente :[/bold]")
            for mood, count in sorted(moods.items(), key=lambda x: -x[1]):
                bar = "█" * min(count, 20)
                console.print(f"  {mood:<12} {bar} ({count})")
        return ""

    def _cmd_voice_info(self) -> str:
        engine = get_engine_name()
        status = "[green]Actif[/green]" if voice_ok() else "[red]Inactif[/red]"
        console.print(f"[bold]Moteur vocal :[/bold] {engine}  {status}")
        if not voice_ok():
            console.print("[dim]Installez edge-tts : pip install edge-tts[/dim]")
        return ""

    def _cmd_learn(self, fact: str) -> str:
        if not fact:
            console.print("[yellow]Usage : /apprendre <fait à mémoriser>[/yellow]")
            return ""
        learn_fact(self.user_id, fact)
        console.print(f"[green]✓ Mémorisé : {fact}[/green]")
        return ""

    def _cmd_alerts(self) -> str:
        if not has_permission(self.user["role"], "manage_users"):
            console.print("[red]Accès refusé.[/red]")
            return ""
        alerts = get_recent_alerts(15)
        if not alerts:
            console.print("[green]Aucune alerte de sécurité.[/green]")
            return ""
        console.print("[bold]Dernières alertes :[/bold]")
        for a in reversed(alerts):
            ts = a.get("timestamp", "")[:16].replace("T", " ")
            console.print(
                f"  [{ts}] [red]{a.get('type', '?')}[/red] — "
                f"utilisateur : {a.get('user_id', '?')}"
            )
        return ""

    # ── Commandes iOS ─────────────────────────────────────────────────────────

    def _cmd_ios(self, args: str) -> str:
        from skills.ios_shortcuts import send_command, get_shortcut_by_id
        from .identity import get_all_users

        if not args:
            console.print("[yellow]Usage : /ios <id>  ou  /ios <uid> <id>[/yellow]")
            console.print("[dim]Tapez /raccourcis pour voir les IDs.[/dim]")
            return ""

        parts = args.split(maxsplit=1)
        users = get_all_users()

        if len(parts) == 2 and parts[0] in users:
            target_uid, shortcut_id = parts
            if not has_permission(self.user["role"], "manage_users"):
                console.print("[red]Seul le propriétaire peut contrôler l'iPhone d'un autre membre.[/red]")
                return ""
        else:
            target_uid = self.user_id
            shortcut_id = parts[0]

        shortcut = get_shortcut_by_id(shortcut_id)
        if not shortcut:
            console.print(f"[red]Raccourci '{shortcut_id}' introuvable. Tapez /raccourcis[/red]")
            return ""

        target_name = users.get(target_uid, {}).get("name", target_uid)
        with console.status(f"[blue]Envoi vers {target_name}...[/blue]"):
            result = send_command(target_uid, shortcut_id, current_user_role=self.user["role"])

        if "error" in result:
            console.print(f"[red]✗ {result['error']}[/red]")
        else:
            console.print(
                f"[green]✓ '{shortcut['shortcut_name']}' envoyé à {target_name}[/green]"
            )
        return ""

    def _cmd_ios_devices(self) -> str:
        from skills.ios_shortcuts import list_devices
        from skills.ios_device import list_connected_devices, is_available as pmd3_ok
        from .identity import get_all_users

        users = get_all_users()
        registered = list_devices()
        table = Table(title="iPhones", border_style="blue")
        table.add_column("Membre", style="bold")
        table.add_column("IP")
        table.add_column("Statut")

        for uid, user in users.items():
            dev = registered.get(uid, {})
            ip = dev.get("ip") or "—"
            status = "[green]Configuré[/green]" if dev.get("ip") else "[dim]À configurer[/dim]"
            table.add_row(user["name"], ip, status)

        console.print(table)
        console.print(f"\n[bold]IP de Luna :[/bold] [cyan]{_get_local_ip()}[/cyan]")

        if pmd3_ok():
            usb = list_connected_devices()
            if usb and "error" not in usb[0]:
                for d in usb:
                    console.print(f"  USB : [cyan]{d.get('udid')}[/cyan]")
        return ""

    def _cmd_ios_shortcuts(self) -> str:
        from skills.ios_shortcuts import list_shortcuts
        shortcuts = list_shortcuts(self.user["role"])
        table = Table(title="Raccourcis iOS", border_style="blue")
        table.add_column("ID", style="cyan")
        table.add_column("Nom")
        table.add_column("Description")
        for s in shortcuts:
            tag = " [red][owner][/red]" if s.get("owner_only") else ""
            table.add_row(s["id"], s["shortcut_name"] + tag, s["description"])
        console.print(table)
        return ""

    def _cmd_ios_location(self, args: str) -> str:
        from core.server import get_last_location
        from .identity import get_all_users

        uid = args.strip() or self.user_id
        if uid != self.user_id and not has_permission(self.user["role"], "manage_users"):
            console.print("[red]Accès refusé.[/red]")
            return ""

        users = get_all_users()
        name = users.get(uid, {}).get("name", uid)
        loc = get_last_location(uid)

        if not loc:
            console.print(f"[yellow]Aucune position pour {name}.[/yellow]")
            console.print("[dim]Déclenchez le Raccourci 'Luna Position' sur l'iPhone.[/dim]")
            return ""

        console.print(f"\n[bold]Position de {name} :[/bold]")
        console.print(f"  Coordonnées : [cyan]{loc['lat']}, {loc['lon']}[/cyan]")
        if loc.get("address"):
            console.print(f"  Adresse : {loc['address']}")
        console.print(f"  Précision : {loc.get('accuracy', '?')} m")
        console.print(f"  Reçu : [dim]{loc['timestamp'][:19]}[/dim]")
        return ""


def _get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
