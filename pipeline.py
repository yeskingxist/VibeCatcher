import time
import re
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Callable
from rich.console import Console

from auth import auth_manager
from bot_guard import bot_guard
from reels import reel_manager
from user_ops import user_ops_manager
from pdf_builder import generate_cumulative_pdf

console = Console(force_terminal=True)

class ReelHarvestPipeline:
    """End-to-end automation pipeline: Reel Watch -> Follow Creator -> Comment -> DM Capture -> Scrape -> PDF Summary."""

    def scrape_url(self, url: str) -> Dict[str, Any]:
        """Fetches and summarizes webpage content from extracted DM link."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=10.0)
            if response.status_code != 200:
                return {"url": url, "title": "External Resource", "summary": f"HTTP {response.status_code}", "snippets": []}

            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "Extracted Resource"
            
            # Extract paragraphs
            paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 30]
            snippets = paragraphs[:5] # Top highlights
            
            summary = " ".join(paragraphs[:3])[:300] + "..." if paragraphs else "Resource content parsed."

            return {
                "url": url,
                "title": title,
                "summary": summary,
                "snippets": snippets
            }
        except Exception as e:
            return {"url": url, "title": "Resource Page", "summary": f"Failed to fetch content: {str(e)}", "snippets": []}

    def process_reel(self, reel_url: str, comment_text: str, progress_cb: Callable[[str, int], None]) -> Dict[str, Any]:
        """
        Executes the full automated workflow.
        progress_cb(step_message, percentage) updates UI in real-time.
        """
        if not auth_manager.load_session():
            raise Exception("Instagram login required. Please authenticate CLI first.")

        # Step 1: Resolving Reel & Media Info
        progress_cb("1/6: Resolving Reel & Simulating Watch Time...", 10)
        media_id = reel_manager.extract_media_id(reel_url)
        media_info = auth_manager.client.media_info(media_id)
        creator = media_info.user
        creator_username = creator.username
        raw_caption = getattr(media_info, 'caption_text', '') or ''
        # Basic summary: strip hashtags, join lines
        clean_caption = re.sub(r'#\w+', '', raw_caption)
        clean_caption = " ".join([line.strip() for line in clean_caption.split('\n') if line.strip()])
        
        if len(clean_caption) < 10 and getattr(media_info, 'video_url', None):
            progress_cb("Reel has no caption. Transcribing audio via AI...", 15)
            try:
                import subprocess
                import speech_recognition as sr
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                    resp = httpx.get(media_info.video_url, follow_redirects=True, timeout=20.0)
                    temp_video.write(resp.content)
                    temp_video_path = temp_video.name
                    
                temp_audio_path = temp_video_path.replace(".mp4", ".wav")
                subprocess.run(['ffmpeg', '-i', temp_video_path, '-q:a', '0', '-map', 'a', temp_audio_path, '-y'], 
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                recognizer = sr.Recognizer()
                with sr.AudioFile(temp_audio_path) as source:
                    audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                
                clean_caption = f"🎤 [AI Transcript]: {text}"
                try: os.remove(temp_video_path)
                except: pass
                try: os.remove(temp_audio_path)
                except: pass
            except Exception as tr_err:
                console.print(f"[yellow]Transcription failed: {tr_err}[/yellow]")
                clean_caption = ""

        summary_caption = clean_caption[:200] + "..." if len(clean_caption) > 200 else clean_caption
        
        # Simulate reel watch delay
        time.sleep(4.0)

        # Step 2: Follow Creator
        progress_cb(f"2/6: Following Creator @{creator_username}...", 25)
        user_ops_manager.follow_user(creator_username)
        progress_cb("Waiting 3 seconds after follow...", 35)
        time.sleep(3.0)

        # Step 3: Comment on Reel & Send DM Keyword Trigger
        progress_cb("3/6: Cleaning up previous comments...", 45)
        reel_manager.delete_my_previous_comments(reel_url)
        
        progress_cb(f"3/6: Posting comment: '{comment_text}' on Reel...", 50)
        comment_id = reel_manager.comment_on_reel(reel_url, comment_text)

        try:
            # Step 4: Wait and Poll for DM Auto-Responder (40 Seconds Loop)
            progress_cb("4/6: Polling Direct Messages for Creator Auto-Responder (40s timer)...", 65)
            
            extracted_urls = []
            attempted_postbacks = set()
            start_time = time.time()
            max_wait = 40  # 40 seconds timer
            
            tid = None
            
            while time.time() - start_time < max_wait:
                elapsed = int(time.time() - start_time)
                progress_cb(f"4/6: Waiting for DM... ({elapsed}s / {max_wait}s)", 65 + int((elapsed / max_wait) * 15))
                
                try:
                    items = []
                    
                    # 1. If we already resolved a tid, try to fetch its messages
                    if tid:
                        try:
                            raw_thread = auth_manager.client.private_request(f'direct_v2/threads/{tid}/?limit=20')
                            items = raw_thread.get('thread', {}).get('items', [])
                        except Exception:
                            tid = None  # Reset if thread became inaccessible
                    
                    # 2. If no tid or no items, scan active inbox first (prioritizing new active threads)
                    if not tid or not items:
                        raw_inbox = auth_manager.client.private_request('direct_v2/inbox/?limit=10')
                        threads = raw_inbox.get('inbox', {}).get('threads', [])
                        for t in threads:
                            if any(u.get('username', '').lower() == creator_username.lower() or str(u.get('pk')) == str(creator.pk) for u in t.get('users', [])):
                                tid = t.get('thread_id')
                                items = t.get('items', [])
                                break
                    
                    # 3. Fallback to direct thread by participants if still not found
                    if not tid:
                        thread_data = auth_manager.client.direct_thread_by_participants([creator.pk])
                        thread_info = thread_data.get('thread', thread_data) if isinstance(thread_data, dict) else {}
                        tid = thread_info.get('thread_id')
                        if tid:
                            raw_thread = auth_manager.client.private_request(f'direct_v2/threads/{tid}/?limit=20')
                            items = raw_thread.get('thread', {}).get('items', [])

                    for item in items:
                        # Filter out messages sent by viewer (us)
                        if item.get('is_sent_by_viewer') is True:
                            continue

                        # 1. Plain text regex
                        text = item.get('text', '')
                        if text:
                            urls = re.findall(r'https?://[^\s"\'\>\]\)]+', text)
                            for u in urls:
                                if not any(domain in u.lower() for domain in ["instagram.com", "facebook.com", "fb.com", "fbcdn.net"]):
                                    extracted_urls.append(u)

                        # 2. CTA Buttons (ManyChat / Cosmofeed Auto-Responder)
                        generic_xma_list = item.get('generic_xma', [])
                        for xma in generic_xma_list:
                            for btn in xma.get('cta_buttons', []):
                                action_url = btn.get('action_url', '')
                                if action_url:
                                    # Extract nested target URL (e.g. url=https%3A%2F%2Fdrive.google.com...)
                                    if 'url=' in action_url:
                                        raw_target = action_url.split('url=')[-1]
                                        import urllib.parse
                                        unquoted = urllib.parse.unquote(raw_target)
                                        # Clean tracking query params if needed
                                        clean_url = unquoted.split('&')[0] if '&' in unquoted else unquoted
                                        target_url = clean_url
                                    else:
                                        target_url = action_url
                                        
                                    if not any(domain in target_url.lower() for domain in ["instagram.com", "facebook.com", "fb.com", "fbcdn.net"]):
                                        extracted_urls.append(target_url)

                        # 4. Handle Postback Buttons (engagement/follow gates)
                        generic_xma_list = item.get('generic_xma', [])
                        for xma in generic_xma_list:
                            for btn in xma.get('cta_buttons', []):
                                if btn.get('cta_type') == 'postback' or (not btn.get('action_url') and btn.get('title')):
                                    btn_title = btn.get('title', '')
                                    if btn_title and btn_title not in attempted_postbacks:
                                        console.print(f"[cyan]Detected postback gate button: '{btn_title}'. Sending auto-reply to unlock...[/cyan]")
                                        try:
                                            auth_manager.client.direct_send(btn_title, thread_ids=[tid])
                                            attempted_postbacks.add(btn_title)
                                        except Exception as send_err:
                                            console.print(f"[yellow]Failed to send postback reply: {send_err}[/yellow]")

                        # 3. Encoded URL Regex search in entire item string
                        item_str = str(item)
                        encoded_matches = re.findall(r'https%3A%2F%2F[^\s"\'\>\]\)\&\\]+', item_str)
                        for em in encoded_matches:
                            import urllib.parse
                            decoded = urllib.parse.unquote(em)
                            if not any(cdn in decoded for cdn in ["cdninstagram.com", "fbcdn.net", "instagram.com/reel"]):
                                extracted_urls.append(decoded)

                    extracted_urls = list(set(extracted_urls))
                    if extracted_urls:
                        progress_cb(f"[OK] DM Received & {len(extracted_urls)} Link(s) Captured!", 80)
                        break
                except Exception as err:
                    console.print(f"[yellow]DM Poll note: {err}[/yellow]")

                if extracted_urls:
                    break
                    
                time.sleep(5.0) # Poll every 5 seconds
            
            # Step 5: Scrape Extracted Resources
            progress_cb(f"5/6: Found {len(extracted_urls)} link(s). Scraping resource contents...", 85)
            resources_data = []
            for url in extracted_urls:
                data = self.scrape_url(url)
                resources_data.append(data)

            # Step 6: Maintain Cumulative JSON History & Generate Consolidated PDF Document
            progress_cb("6/6: Updating Cumulative History & PDF Document...", 95)
            
            import json
            from pathlib import Path
            history_file = Path(__file__).parent / "history.json"
            
            history_data = []
            if history_file.exists():
                try:
                    with open(history_file, "r", encoding="utf-8") as h_f:
                        history_data = json.load(h_f)
                except Exception:
                    pass

            profile_pic_url = str(getattr(creator, 'profile_pic_url', '') or getattr(creator, 'profile_pic_url_hd', '') or '')
            # Append new entry
            history_data.append({
                "creator": creator_username,
                "profile_pic": profile_pic_url,
                "reel_url": reel_url,
                "caption": summary_caption,
                "resources": resources_data
            })

            # Save back to history.json
            try:
                with open(history_file, "w", encoding="utf-8") as h_f:
                    json.dump(history_data, h_f, indent=4)
            except Exception as write_json_err:
                console.print(f"[yellow]History JSON save note: {write_json_err}[/yellow]")

            # Regenerate consolidated PDF
            pdf_filename = "consolidated_report.pdf"
            generated_pdf_name = generate_cumulative_pdf(pdf_filename, history_data)

            # Schedule 5-Minute Auto-Delete / Hide DM Thread Background Task
            if 'tid' in locals() and tid:
                import threading
                def auto_delete_thread_task(thread_id_to_delete: str, username_to_clean: str):
                    time.sleep(300.0) # Wait 5 minutes (300s)
                    try:
                        auth_manager.client.direct_thread_hide(thread_id_to_delete)
                        console.print(f"[dim green][OK] Auto-cleaned DM thread for @{username_to_clean} after 5 minutes.[/dim green]")
                    except Exception as clean_err:
                        console.print(f"[dim yellow]Auto-clean note: {clean_err}[/dim yellow]")

                t = threading.Thread(target=auto_delete_thread_task, args=(tid, creator_username), daemon=True)
                t.start()

            progress_cb("Complete! Consolidated PDF Ready for Download. (DM thread queued to auto-clean in 5 mins)", 100)

            return {
                "status": "success",
                "creator": creator_username,
                "reel_url": reel_url,
                "extracted_urls": extracted_urls,
                "pdf_filename": generated_pdf_name,
                "download_url": f"/downloads/{generated_pdf_name}"
            }
        finally:
            if comment_id:
                console.print(f"[yellow]Auto-cleaning trigger comment (ID: {comment_id}) to leave no traces...[/yellow]")
                try:
                    auth_manager.client.comment_bulk_delete(media_id, [comment_id])
                    console.print("[bold green][OK] Trigger comment cleaned successfully![/bold green]")
                except Exception as del_err:
                    console.print(f"[dim yellow]Could not auto-clean trigger comment: {del_err}[/dim yellow]")

pipeline = ReelHarvestPipeline()
