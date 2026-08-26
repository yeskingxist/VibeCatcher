import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from auth import auth_manager
from reels import reel_manager
from user_ops import user_ops_manager
from posts import post_manager
from direct_chat import direct_chat_manager
from config import config

app = typer.Typer(help="Instagram Terminal Suite — Native Private API CLI", add_completion=False)
console = Console()

BANNER = """[bold magenta]
============================================================
  INSTA CLI - Native Android Private API Engine
============================================================
[/bold magenta]"""

@app.command()
def login():
    """Log in to Instagram and store session credentials safely."""
    console.print(BANNER)
    auth_manager.login()

@app.command()
def comment(reel_url: str = typer.Argument(..., help="Reel URL or Shortcode"),
            text: str = typer.Argument(..., help="Comment text")):
    """Comment on any Instagram Reel with anti-detection protection."""
    if not auth_manager.load_session():
        auth_manager.login()
    reel_manager.comment_on_reel(reel_url, text)

@app.command()
def follow(username: str = typer.Argument(..., help="Instagram username to follow")):
    """Follow an Instagram user."""
    if not auth_manager.load_session():
        auth_manager.login()
    user_ops_manager.follow_user(username)

@app.command()
def unfollow(username: str = typer.Argument(..., help="Instagram username to unfollow")):
    """Unfollow an Instagram user."""
    if not auth_manager.load_session():
        auth_manager.login()
    user_ops_manager.unfollow_user(username)

@app.command()
def dm(username: str = typer.Argument(..., help="Recipient username"),
       message: str = typer.Argument(..., help="Direct Message text")):
    """Send a Direct Message to a user."""
    if not auth_manager.load_session():
        auth_manager.login()
    direct_chat_manager.send_dm(username, message)

@app.command()
def chat(username: str = typer.Argument(..., help="Username to live chat with")):
    """Open interactive real-time Live Terminal Chat session."""
    if not auth_manager.load_session():
        auth_manager.login()
    direct_chat_manager.live_chat_session(username)

@app.command(name="delete-post")
def delete_post(url_or_id: str = typer.Argument(..., help="Post URL, Shortcode, or Media ID")):
    """Delete a post or reel from your account."""
    if not auth_manager.load_session():
        auth_manager.login()
    post_manager.delete_post(url_or_id)

@app.command(name="my-posts")
def my_posts(amount: int = typer.Option(20, help="Number of posts to fetch")):
    """List your published Instagram posts."""
    if not auth_manager.load_session():
        auth_manager.login()
    post_manager.list_my_posts(amount=amount)

@app.command()
def inbox(amount: int = typer.Option(10, help="Number of direct threads to display")):
    """View your Direct Messages inbox."""
    if not auth_manager.load_session():
        auth_manager.login()
    direct_chat_manager.list_inbox(amount=amount)

@app.command()
def menu():
    """Interactive Menu for easy CLI navigation."""
    console.print(BANNER)

    if not auth_manager.load_session():
        if not auth_manager.login():
            return

    while True:
        console.print(Panel("""[bold cyan]Main Operations Menu[/bold cyan]
[gold1]1.[/gold1] Comment on a Reel
[gold1]2.[/gold1] Follow User
[gold1]3.[/gold1] Unfollow User
[gold1]4.[/gold1] Send Direct Message
[gold1]5.[/gold1] Open Live Chat Session
[gold1]6.[/gold1] Delete Post / Reel
[gold1]7.[/gold1] View My Posts
[gold1]8.[/gold1] View Inbox
[gold1]9.[/gold1] Change Safety Preset (Current: [yellow]{preset}[/yellow])
[gold1]0.[/gold1] Exit""".format(preset=config.safety_preset), title="Insta CLI Options"))

        choice = Prompt.ask("Select Option", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"])

        if choice == "1":
            url = Prompt.ask("Reel URL or Shortcode")
            text = Prompt.ask("Comment Text")
            reel_manager.comment_on_reel(url, text)
        elif choice == "2":
            user = Prompt.ask("Username to follow")
            user_ops_manager.follow_user(user)
        elif choice == "3":
            user = Prompt.ask("Username to unfollow")
            user_ops_manager.unfollow_user(user)
        elif choice == "4":
            user = Prompt.ask("Recipient Username")
            msg = Prompt.ask("Message Text")
            direct_chat_manager.send_dm(user, msg)
        elif choice == "5":
            user = Prompt.ask("Username to live chat with")
            direct_chat_manager.live_chat_session(user)
        elif choice == "6":
            post_manager.interactive_delete()
        elif choice == "7":
            post_manager.list_my_posts()
        elif choice == "8":
            direct_chat_manager.list_inbox()
        elif choice == "9":
            preset = Prompt.ask("Select Safety Mode", choices=["safe", "normal", "aggressive"])
            config.safety_preset = preset
            console.print(f"[bold green]Safety preset changed to: {preset}[/bold green]")
        elif choice == "0":
            console.print("[yellow]Exiting Insta CLI. Stay safe![/yellow]")
            break

if __name__ == "__main__":
    if len(sys.argv) == 1:
        menu()
    else:
        app()
