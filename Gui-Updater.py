#!/usr/bin/env python3
import sys, subprocess, shutil, time
from pathlib import Path

def backup_nested():
    src = Path("NestedShorthand.dat")
    if not src.exists(): src = Path("datablock.dat")
    if not src.exists(): return "No file to backup"
    dst = Path(f"NestedShorthand.dat.bak.{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(src, dst)
    shutil.copy2(src, Path("NestedShorthand.dat.bak"))
    return str(dst)

def call_updater(msg="", fp="", note=""):
    cmd = [sys.executable, "update.py", "--token", "mini-ai"]
    if fp: cmd += ["--file", fp]
    else: cmd += ["--message", msg]
    if note: cmd += ["--note", note]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.stdout + "\n" + r.stderr

def run_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext
    except: return False
    root = tk.Tk()
    root.title("AnthroHeart — Friendly Updater — Python Only — SUBMIT button fixed")
    root.geometry("1000x800")
    bg="#1e1e2f"; fg="#e0e0ff"; accent="#7aa2f7"
    root.configure(bg=bg)
    tk.Label(root, text="AnthroHeart — Python Only — Friendly — Categories first, POW second", bg=bg, fg=accent, font=("Arial",14,"bold")).pack(pady=5)
    # Categories
    cat_frame = tk.Frame(root, bg=bg)
    cat_frame.pack(fill="x", padx=10, pady=5)
    tk.Label(cat_frame, text="Categories (Ctrl+Click multi-pick): ALL, SCIENCE, MATHEMATICS, SOFTWARE, AI, SIMULATIONS, LANGUAGES, MUSIC, FILMS, GAMES, EDUCATION, ART, LAW_OF_ONE etc.", bg=bg, fg=fg).pack(anchor="w")
    cat_list = tk.Listbox(cat_frame, selectmode="multiple", height=6, bg="#2a2a40", fg=fg, selectbackground=accent)
    for c in ["ALL","SCIENCE","MATHEMATICS","SOFTWARE","AI","SIMULATIONS","LANGUAGES","MUSIC","FILMS","GAMES","EDUCATION","ART","LAW_OF_ONE","RA_CONTACT","STORY","HYPERCOMPUTER","DOCS"]:
        cat_list.insert("end", c)
    cat_list.pack(fill="x")
    cat_list.selection_set(0)
    # POWs
    pow_frame = tk.Frame(root, bg=bg)
    pow_frame.pack(fill="x", padx=10, pady=5)
    tk.Label(pow_frame, text="POW Sizes — Powers of 10 — Each POW for Each Category", bg=bg, fg=fg).pack(anchor="w")
    pow_list = tk.Listbox(pow_frame, selectmode="multiple", height=6, bg="#2a2a40", fg=fg, selectbackground=accent)
    for p in ["Small 1KB","1MB","1GB","10GB","100GB","1TB","10TB","100TB","1PB","10PB","100PB","1EB","10EB MAX"]:
        pow_list.insert("end", p)
    pow_list.pack(fill="x")
    pow_list.selection_set(12)
    # Message
    msg_frame = tk.Frame(root, bg=bg)
    msg_frame.pack(fill="x", padx=10, pady=5)
    tk.Label(msg_frame, text="Message (input argument):", bg=bg, fg=fg).pack(anchor="w")
    msg_text = scrolledtext.ScrolledText(msg_frame, height=4, bg="#2a2a40", fg=fg, insertbackground=fg)
    msg_text.pack(fill="x")
    # File
    file_var = tk.StringVar()
    file_f = tk.Frame(root, bg=bg)
    file_f.pack(fill="x", padx=10, pady=3)
    tk.Label(file_f, text="Or file:", bg=bg, fg=fg).pack(side="left")
    tk.Entry(file_f, textvariable=file_var, width=50, bg="#2a2a40", fg=fg).pack(side="left", padx=5)
    tk.Button(file_f, text="Browse", command=lambda: file_var.set(filedialog.askopenfilename()), bg=accent, fg="black").pack(side="left")
    # Output
    out = scrolledtext.ScrolledText(root, height=8, bg="#11111b", fg="#a6e3a1")
    out.pack(fill="both", expand=True, padx=10, pady=5)
    # SUBMIT BUTTON — FIXED — ALWAYS VISIBLE AT BOTTOM
    def on_submit():
        cats = [cat_list.get(i) for i in cat_list.curselection()] or ["ALL"]
        pows = [pow_list.get(i) for i in pow_list.curselection()] or ["10EB MAX"]
        msg = msg_text.get("1.0","end").strip()
        fp = file_var.get().strip()
        if not msg and not fp:
            messagebox.showwarning("Input needed", "Provide message or file")
            return
        full_msg = msg + f"\n\nCategories: {cats}\nPOWs: {pows}\nMatrix: {len(cats)}x{len(pows)}={len(cats)*len(pows)} combos"
        bp = backup_nested()
        out.insert("end", f"Backup {bp}\nCats {cats} POWs {pows}\n")
        out.insert("end", call_updater(full_msg, fp) + "\nDone\n")
        out.see("end")
    bottom = tk.Frame(root, bg=bg, height=80)
    bottom.pack(fill="x", side="bottom", pady=10)
    tk.Button(bottom, text="🚀 SUBMIT — Backup + Send Update — CLICK HERE — Python Only", command=on_submit, bg="#89b4fa", fg="black", font=("Arial",13,"bold"), height=2, relief="raised", bd=4, cursor="hand2").pack(fill="both", expand=True, padx=20, pady=10)
    root.mainloop()
    return True

if __name__=="__main__":
    if not run_gui():
        print("CLI fallback")
        backup_nested()
        msg = input("Message: ")
        print(call_updater(msg))
