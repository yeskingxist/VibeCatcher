import time
import threading
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from auth import auth_manager
from bot_guard import bot_guard

console = Console()

class DirectChatManager:
    """Manages Instagram Direct Messages and Interactive Live Terminal Chat."""

    def send_dm(self, username: str, message_text: str) -> bool:
        """Sends a Direct Message to a specific username."""
        if not bot_guard.check_rate_limit("dm"):
            return False

        try:
            user_id = auth_manager.client.user_id_from_username(username)
            bot_guard.apply_delay("dm", text_payload=message_text)

            console.print(f"[cyan]Sending DM to @{username}...[/cyan]")
            result = auth_manager.client.direct_send_text(message_text, user_ids=[user_id])
            bot_guard.record_action("dm")
            
            console.print(f"[bold green][OK] DM sent to @{username}![/bold green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Failed to send DM: {e}[/bold red]")
            return False

    def list_inbox(self, amount: int = 10):
        """Displays recent direct message threads."""
        try:
            threads = auth_manager.client.direct_threads(amount=amount)
            console.print("\n[bold cyan]Inbox - Instagram Direct[/bold cyan]")
            
            for idx, thread in enumerate(threads, 1):
                users = ", ".join([f"@{u.username}" for u in thread.users])
                last_msg = thread.messages[0].text if thread.messages and thread.messages[0].text else "[Media/Other]"
                console.print(f"[bold gold1]{idx}.[/bold gold1] [bold white]{users}[/bold white] (ID: {thread.id})")
                console.print(f"   Last msg: [dim]{last_msg[:50]}[/dim]\n")
            return threads
        except Exception as e:
            console.print(f"[bold red]Failed to load inbox: {e}[/bold red]")
            return []

    def live_chat_session(self, username: str):
        """Starts an interactive real-time live chat session with a user in the terminal."""
        try:
            console.print(f"[yellow]Opening live chat session with @{username}...[/yellow]")
            user_id = auth_manager.client.user_id_from_username(username)
            thread = auth_manager.client.direct_thread_by_participants([user_id])
            thread_id = thread.id
        except Exception as e:
            console.print(f"[bold red]Could not find/open thread with @{username}: {e}[/bold red]")
            return

        console.print(Panel(f"[bold green]Connected to Live Chat with @{username}[/bold green]\nType '/exit' or '/quit' to leave chat.", title="Insta CLI Live Chat"))

        seen_msg_ids = set()
        stop_polling = threading.Event()

        def fetch_messages_loop():
            while not stop_polling.is_set():
                try:
                    updated_thread = auth_manager.client.direct_thread(thread_id)
                    for msg in reversed(updated_thread.messages):
                        if msg.id not in seen_msg_ids:
                            seen_msg_ids.add(msg.id)
                            sender = "You" if str(msg.user_id) == str(auth_manager.client.user_id) else f"@{username}"
                            color = "cyan" if sender == "You" else "green"
                            if msg.text:
                                console.print(f"[{color}][{sender}]: {msg.text}[/{color}]")
                except Exception:
                    pass
                time.sleep(3.0)

        # Start background polling thread for incoming messages
        poll_thread = threading.Thread(target=fetch_messages_loop, daemon=True)
        poll_thread.start()

        session = PromptSession()

        try:
            with patch_stdout():
                while True:
                    user_input = session.prompt(f"You (@{username}) > ")
                    if user_input.strip().lower() in ("/exit", "/quit", "exit", "quit"):
                        break
                    if not user_input.strip():
                        continue

                    # Send text message
                    auth_manager.client.direct_send_text(user_input, thread_id=thread_id)
                    bot_guard.record_action("dm")
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            stop_polling.set()
            console.print("[yellow]Exited Live Chat.[/yellow]")

direct_chat_manager = DirectChatManager()
