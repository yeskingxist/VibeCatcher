from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt

from auth import auth_manager
from bot_guard import bot_guard
from reels import reel_manager

console = Console()

class PostManager:
    """Manages Instagram user posts (listing, deleting posts/reels)."""

    def list_my_posts(self, amount: int = 20):
        """Lists user's recent published posts."""
        try:
            user_id = auth_manager.client.user_id
            console.print(f"[yellow]Fetching recent {amount} posts...[/yellow]")
            medias = auth_manager.client.user_medias(user_id, amount=amount)

            if not medias:
                console.print("[dim]No posts found.[/dim]")
                return []

            table = Table(title="Your Recent Instagram Posts")
            table.add_column("#", style="cyan", justify="center")
            table.add_column("Media ID", style="dim")
            table.add_column("Type", style="green")
            table.add_column("Likes", style="magenta")
            table.add_column("Comments", style="yellow")
            table.add_column("Caption Snippet", style="white")

            for idx, media in enumerate(medias, 1):
                m_type = "Reel/Video" if media.media_type in (2, 8) else "Photo"
                caption = (media.caption_text or "").replace("\n", " ")[:35] + "..." if media.caption_text else "[No Caption]"
                table.add_row(str(idx), str(media.pk), m_type, str(media.like_count), str(media.comment_count), caption)

            console.print(table)
            return medias
        except Exception as e:
            console.print(f"[bold red]Failed to fetch posts: {e}[/bold red]")
            return []

    def delete_post(self, media_url_or_id: str) -> bool:
        """Deletes a post by URL, shortcode, or Media PK."""
        try:
            media_id = reel_manager.extract_media_id(media_url_or_id)
            
            confirm = Confirm.ask(f"[bold red]Are you sure you want to PERMANENTLY delete post {media_id}?[/bold red]")
            if not confirm:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return False

            bot_guard.apply_delay("delete")
            result = auth_manager.client.media_delete(media_id)
            bot_guard.record_action("delete")
            
            if result:
                console.print(f"[bold green][OK] Post {media_id} deleted successfully![/bold green]")
                return True
            else:
                console.print(f"[red]Failed to delete post {media_id}.[/red]")
                return False
        except Exception as e:
            console.print(f"[bold red]Delete post error: {e}[/bold red]")
            return False

    def interactive_delete(self):
        """Interactively lists posts and prompts user to pick which one to delete."""
        medias = self.list_my_posts(amount=15)
        if not medias:
            return

        choice = Prompt.ask("\nEnter post # to delete (or press Enter to cancel)", default="")
        if choice.isdigit() and 1 <= int(choice) <= len(medias):
            selected_media = medias[int(choice) - 1]
            self.delete_post(str(selected_media.pk))

post_manager = PostManager()
