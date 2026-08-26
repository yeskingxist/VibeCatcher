import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from auth import auth_manager
from reels import reel_manager
from user_ops import user_ops_manager
from direct_chat import direct_chat_manager
from pipeline import pipeline

class InstaAppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Native Desktop App")
        self.root.geometry("640x580")
        self.root.configure(bg="#0b0f19")
        
        # Styles
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#0b0f19", foreground="#f8fafc", font=("Inter", 10))
        style.configure("Header.TLabel", background="#0b0f19", foreground="#a855f7", font=("Inter", 16, "bold"))
        style.configure("TButton", background="#6366f1", foreground="#ffffff", font=("Inter", 10, "bold"))
        style.map("TButton", background=[("active", "#4f46e5")])

        # Header
        header = ttk.Label(root, text="Instagram Native Desktop Suite", style="Header.TLabel")
        header.pack(pady=15)

        # Tab Control
        self.tabControl = ttk.Notebook(root)
        
        self.tab_login = ttk.Frame(self.tabControl)
        self.tab_reels = ttk.Frame(self.tabControl)
        self.tab_dm = ttk.Frame(self.tabControl)
        self.tab_pipeline = ttk.Frame(self.tabControl)

        self.tabControl.add(self.tab_login, text="Account Login")
        self.tabControl.add(self.tab_reels, text="Reels & Follow")
        self.tabControl.add(self.tab_dm, text="Direct Chat")
        self.tabControl.add(self.tab_pipeline, text="Auto Harvester")

        self.tabControl.pack(expand=1, fill="both", padx=15, pady=10)

        self._build_login_tab()
        self._build_reels_tab()
        self._build_dm_tab()
        self._build_pipeline_tab()

    def _build_login_tab(self):
        frame = tk.Frame(self.tab_login, bg="#111827", bd=1, relief="solid")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(frame, text="Instagram Username:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(15, 2))
        self.u_entry = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.u_entry.pack(fill="x", padx=15, pady=5)

        tk.Label(frame, text="Instagram Password:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(10, 2))
        self.p_entry = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.p_entry.pack(fill="x", padx=15, pady=5)

        btn = tk.Button(frame, text="Log In to Instagram", bg="#6366f1", fg="white", font=("Inter", 11, "bold"), command=self.do_login)
        btn.pack(fill="x", padx=15, pady=20)

        self.login_status = tk.Label(frame, text="Status: Checking session...", bg="#111827", fg="#94a3b8")
        self.login_status.pack(pady=5)

    def do_login(self):
        u = self.u_entry.get().strip()
        p = self.p_entry.get().strip()
        if not u or not p:
            messagebox.showerror("Error", "Please enter both username and password.")
            return
        
        self.login_status.config(text="Authenticating...", fg="#38bdf8")

        def task():
            success = auth_manager.login(u, p)
            if success:
                self.login_status.config(text=f"[OK] Logged in as @{u}", fg="#34d399")
                messagebox.showinfo("Success", f"Successfully authenticated as @{u}")
            else:
                self.login_status.config(text="Login Failed. Check credentials / IP.", fg="#f87171")

        threading.Thread(target=task, daemon=True).start()

    def _build_reels_tab(self):
        frame = tk.Frame(self.tab_reels, bg="#111827", bd=1, relief="solid")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(frame, text="Reel URL / Shortcode:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(15, 2))
        self.reel_entry = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.reel_entry.pack(fill="x", padx=15, pady=5)

        tk.Label(frame, text="Comment Text:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(10, 2))
        self.comment_entry = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.comment_entry.pack(fill="x", padx=15, pady=5)

        tk.Button(frame, text="Comment on Reel", bg="#a855f7", fg="white", font=("Inter", 10, "bold"),
                  command=lambda: self.run_bg(lambda: reel_manager.comment_on_reel(self.reel_entry.get(), self.comment_entry.get()))).pack(fill="x", padx=15, pady=10)

        tk.Label(frame, text="Target Username to Follow:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(15, 2))
        self.user_entry = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.user_entry.pack(fill="x", padx=15, pady=5)

        tk.Button(frame, text="Follow User", bg="#10b981", fg="white", font=("Inter", 10, "bold"),
                  command=lambda: self.run_bg(lambda: user_ops_manager.follow_user(self.user_entry.get()))).pack(fill="x", padx=15, pady=10)

    def _build_dm_tab(self):
        frame = tk.Frame(self.tab_dm, bg="#111827", bd=1, relief="solid")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(frame, text="Recipient Username:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(15, 2))
        self.dm_user = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.dm_user.pack(fill="x", padx=15, pady=5)

        tk.Label(frame, text="Direct Message Text:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(10, 2))
        self.dm_msg = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.dm_msg.pack(fill="x", padx=15, pady=5)

        tk.Button(frame, text="Send Direct Message", bg="#06b6d4", fg="white", font=("Inter", 10, "bold"),
                  command=lambda: self.run_bg(lambda: direct_chat_manager.send_dm(self.dm_user.get(), self.dm_msg.get()))).pack(fill="x", padx=15, pady=15)

    def _build_pipeline_tab(self):
        frame = tk.Frame(self.tab_pipeline, bg="#111827", bd=1, relief="solid")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(frame, text="Reel Link:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(15, 2))
        self.pipe_reel = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.pipe_reel.pack(fill="x", padx=15, pady=5)

        tk.Label(frame, text="Trigger Keyword:", bg="#111827", fg="#cbd5e1").pack(anchor="w", padx=15, pady=(10, 2))
        self.pipe_kw = tk.Entry(frame, bg="#1e293b", fg="#ffffff", insertbackground="white", font=("Inter", 11))
        self.pipe_kw.insert(0, "link")
        self.pipe_kw.pack(fill="x", padx=15, pady=5)

        self.status_lbl = tk.Label(frame, text="Idle", bg="#111827", fg="#94a3b8")
        self.status_lbl.pack(pady=10)

        tk.Button(frame, text="Run Full Auto Pipeline", bg="#ec4899", fg="white", font=("Inter", 11, "bold"),
                  command=self.run_pipeline).pack(fill="x", padx=15, pady=10)

    def run_pipeline(self):
        url = self.pipe_reel.get().strip()
        kw = self.pipe_kw.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a Reel URL.")
            return

        def task():
            def cb(msg, pct):
                self.status_lbl.config(text=f"{pct}% - {msg}", fg="#38bdf8")
            try:
                res = pipeline.process_reel(url, kw, cb)
                self.status_lbl.config(text=f"✓ Complete! PDF saved: {res['pdf_filename']}", fg="#34d399")
                messagebox.showinfo("Success", f"PDF Summary generated: {res['pdf_filename']}")
            except Exception as e:
                self.status_lbl.config(text=f"Error: {e}", fg="#f87171")
                messagebox.showerror("Pipeline Failed", str(e))

        threading.Thread(target=task, daemon=True).start()

    def run_bg(self, fn):
        def task():
            try:
                fn()
                messagebox.showinfo("Done", "Operation finished successfully.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = InstaAppGUI(root)
    root.mainloop()
