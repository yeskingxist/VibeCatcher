import re
from rich.console import Console
from instagrapi.exceptions import MediaNotFound

from auth import auth_manager
from bot_guard import bot_guard

console = Console()

class ReelManager:
    """Manages Instagram Reels interactions (commenting, liking, info)."""

    def shortcode_to_media_id(self, shortcode: str) -> str:
        """Converts an Instagram shortcode to its numeric media ID (PK) offline."""
        try:
            alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
            media_id = 0
            for char in shortcode:
                media_id = (media_id * 64) + alphabet.index(char)
            return str(media_id)
        except Exception:
            return shortcode

    def extract_media_id(self, reel_url_or_code: str) -> str:
        """Extracts media PK from a Reel URL or shortcode input offline."""
        match = re.search(r"instagram\.com/(?:reel|p|reels)/([A-Za-z0-9_-]+)", reel_url_or_code)
        if match:
            shortcode = match.group(1)
            return self.shortcode_to_media_id(shortcode)
        
        # If it's already a shortcode
        if not reel_url_or_code.isdigit():
            return self.shortcode_to_media_id(reel_url_or_code)
            
        return reel_url_or_code

    def comment_on_reel(self, reel_url: str, comment_text: str) -> str:
        """Comments on a Reel with anti-detection protection. Returns comment PK (ID) or None."""
        if not bot_guard.check_rate_limit("comment"):
            return None

        try:
            console.print("[yellow]Resolving Reel ID...[/yellow]")
            media_id = self.extract_media_id(reel_url)
            
            # Apply anti-bot humanized delay
            bot_guard.apply_delay("comment", text_payload=comment_text)

            console.print(f"[cyan]Posting comment on Reel ({media_id})...[/cyan]")
            comment = auth_manager.client.media_comment(media_id, comment_text)
            bot_guard.record_action("comment")
            
            console.print(f"[bold green][OK] Comment posted successfully! Comment ID: {comment.pk}[/bold green]")
            return str(comment.pk)
        except MediaNotFound:
            console.print("[bold red]Reel not found. Check the URL/shortcode.[/bold red]")
            return None
        except Exception as e:
            console.print(f"[bold red]Failed to comment on Reel: {e}[/bold red]")
            return None

    def delete_my_previous_comments(self, reel_url: str) -> int:
        """Deletes any previous comments we posted on this Reel to enable fresh triggers."""
        try:
            media_id = self.extract_media_id(reel_url)
            console.print(f"[yellow]Fetching comments to clean up previous posts on media {media_id}...[/yellow]")
            comments = auth_manager.client.media_comments(media_id, amount=100)
            my_username = auth_manager.client.username.lower()
            
            pks_to_delete = []
            for c in comments:
                if c.user.username.lower() == my_username:
                    pks_to_delete.append(c.pk)
            
            if pks_to_delete:
                console.print(f"[cyan]Found {len(pks_to_delete)} previous comment(s) from us. Deleting...[/cyan]")
                pks_str = [str(pk) for pk in pks_to_delete]
                auth_manager.client.comment_bulk_delete(media_id, pks_str)
                console.print(f"[bold green][OK] Deleted {len(pks_to_delete)} previous comment(s) successfully![/bold green]")
                return len(pks_to_delete)
            else:
                console.print("[yellow]No previous comments from us found on this Reel.[/yellow]")
                return 0
        except Exception as e:
            console.print(f"[bold red]Failed to clean up previous comments: {e}[/bold red]")
            return 0

    def like_reel(self, reel_url: str) -> bool:
        """Likes a Reel."""
        try:
            media_id = self.extract_media_id(reel_url)
            bot_guard.apply_delay("comment") # Micro delay
            auth_manager.client.media_like(media_id)
            console.print("[bold green][OK] Reel liked successfully![/bold green]")
            return True
        except Exception as e:
            console.print(f"[bold red]Failed to like Reel: {e}[/bold red]")
            return False

reel_manager = ReelManager()
