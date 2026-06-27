#!/usr/bin/env python3
"""
FNAF: Security Breach Save Editor
A GUI for editing SaveGameSlotN.sav (GVAS / UE4.27) files.

Tabs:
  - Missions:    edit the 34 story missions (status, info-state, completed steps)
  - World Flags: toggle ActivatedObjects world triggers on/off (searchable)
  - Raw Tree:    generic property-tree editor (edit any scalar value)

Requires gvas.py in the same folder. Pure stdlib + Tkinter.

Run:  python3 save_editor.py
"""
import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gvas

__version__ = "1.0.0"

MISSION_STATUSES = [
    "EMissionStatus::Inactive",
    "EMissionStatus::Active",
    "EMissionStatus::Complete",
    "EMissionStatus::Failed",
]

# ---- Dark theme palette (true-black-ish; easy on OLED) ----
DARK = {
    "bg":        "#1a1a1d",   # window / frame background
    "bg2":       "#232327",   # raised panels, entries
    "bg3":       "#2c2c31",   # hover / selected row
    "fg":        "#e6e6e6",   # primary text
    "fg_dim":    "#9a9a9a",   # secondary text
    "accent":    "#d23b3b",   # FNAF-ish red
    "accent_fg": "#ffffff",
    "border":    "#3a3a40",
    "sel":       "#3a2a2a",   # selection background (subtle red tint)
}


class SaveEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"FNAF: Security Breach — Save Editor  v{__version__}")
        self.geometry("980x680")
        self.save = None          # gvas.SaveFile
        self.path = None
        self.dirty = False

        self._apply_dark_theme()
        self._build_menu()
        self._build_toolbar()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tab_missions = ttk.Frame(self.nb)
        self.tab_flags = ttk.Frame(self.nb)
        self.tab_raw = ttk.Frame(self.nb)
        self.nb.add(self.tab_missions, text="Missions")
        self.nb.add(self.tab_flags, text="World Flags")
        self.nb.add(self.tab_raw, text="Raw Tree")

        self._build_missions_tab()
        self._build_flags_tab()
        self._build_raw_tab()

        self.status = tk.StringVar(value="Open a .sav file to begin.  (File ▸ Open)")
        tk.Label(self, textvariable=self.status, relief="flat", anchor="w",
                 bg=DARK["bg2"], fg=DARK["fg_dim"], padx=8, pady=3).pack(
            fill="x", side="bottom")

    # ---------------- dark theme ----------------
    def _apply_dark_theme(self):
        self.configure(bg=DARK["bg"])
        # Classic-widget defaults (Listbox, Menu, dialogs, etc.)
        self.option_add("*background", DARK["bg"])
        self.option_add("*foreground", DARK["fg"])
        self.option_add("*Listbox.background", DARK["bg2"])
        self.option_add("*Listbox.foreground", DARK["fg"])
        self.option_add("*Listbox.selectBackground", DARK["accent"])
        self.option_add("*Listbox.selectForeground", DARK["accent_fg"])
        self.option_add("*Entry.background", DARK["bg2"])
        self.option_add("*Entry.foreground", DARK["fg"])
        self.option_add("*Entry.insertBackground", DARK["fg"])
        self.option_add("*Menu.background", DARK["bg2"])
        self.option_add("*Menu.foreground", DARK["fg"])
        self.option_add("*Menu.activeBackground", DARK["accent"])
        self.option_add("*Menu.activeForeground", DARK["accent_fg"])
        # ttk styling — "clam" is the theme that honours custom colours
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=DARK["bg"], foreground=DARK["fg"],
                    fieldbackground=DARK["bg2"], bordercolor=DARK["border"],
                    lightcolor=DARK["bg"], darkcolor=DARK["bg"],
                    troughcolor=DARK["bg2"], focuscolor=DARK["accent"])
        s.configure("TFrame", background=DARK["bg"])
        s.configure("TLabel", background=DARK["bg"], foreground=DARK["fg"])
        s.configure("TLabelframe", background=DARK["bg"], bordercolor=DARK["border"])
        s.configure("TLabelframe.Label", background=DARK["bg"], foreground=DARK["fg_dim"])
        s.configure("TButton", background=DARK["bg3"], foreground=DARK["fg"],
                    bordercolor=DARK["border"], focusthickness=1,
                    focuscolor=DARK["accent"], padding=5)
        s.map("TButton",
              background=[("active", DARK["accent"]), ("pressed", DARK["accent"])],
              foreground=[("active", DARK["accent_fg"])])
        s.configure("TCheckbutton", background=DARK["bg"], foreground=DARK["fg"])
        s.map("TCheckbutton",
              background=[("active", DARK["bg"])],
              indicatorcolor=[("selected", DARK["accent"]), ("!selected", DARK["bg2"])])
        s.configure("TEntry", fieldbackground=DARK["bg2"], foreground=DARK["fg"],
                    insertcolor=DARK["fg"], bordercolor=DARK["border"])
        s.configure("TSpinbox", fieldbackground=DARK["bg2"], foreground=DARK["fg"],
                    bordercolor=DARK["border"], arrowcolor=DARK["fg"])
        # Combobox: field + dropdown list
        s.configure("TCombobox", fieldbackground=DARK["bg2"], background=DARK["bg3"],
                    foreground=DARK["fg"], arrowcolor=DARK["fg"], bordercolor=DARK["border"])
        s.map("TCombobox", fieldbackground=[("readonly", DARK["bg2"])],
              foreground=[("readonly", DARK["fg"])])
        self.option_add("*TCombobox*Listbox.background", DARK["bg2"])
        self.option_add("*TCombobox*Listbox.foreground", DARK["fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", DARK["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", DARK["accent_fg"])
        # Notebook tabs
        s.configure("TNotebook", background=DARK["bg"], bordercolor=DARK["border"])
        s.configure("TNotebook.Tab", background=DARK["bg2"], foreground=DARK["fg_dim"],
                    padding=(14, 6), bordercolor=DARK["border"])
        s.map("TNotebook.Tab",
              background=[("selected", DARK["bg"])],
              foreground=[("selected", DARK["fg"])])
        # Treeview
        s.configure("Treeview", background=DARK["bg2"], fieldbackground=DARK["bg2"],
                    foreground=DARK["fg"], bordercolor=DARK["border"], rowheight=22)
        s.map("Treeview",
              background=[("selected", DARK["accent"])],
              foreground=[("selected", DARK["accent_fg"])])
        s.configure("Treeview.Heading", background=DARK["bg3"], foreground=DARK["fg"],
                    bordercolor=DARK["border"], relief="flat")
        s.map("Treeview.Heading", background=[("active", DARK["bg3"])])
        # Scrollbars
        s.configure("Vertical.TScrollbar", background=DARK["bg3"],
                    troughcolor=DARK["bg"], bordercolor=DARK["bg"],
                    arrowcolor=DARK["fg"])
        s.configure("Horizontal.TScrollbar", background=DARK["bg3"],
                    troughcolor=DARK["bg"], bordercolor=DARK["bg"],
                    arrowcolor=DARK["fg"])

    # ---------------- menu / toolbar ----------------
    def _build_menu(self):
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label="Open…", command=self.open_file, accelerator="Ctrl+O")
        fm.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        fm.add_command(label="Save As…", command=self.save_file_as)
        fm.add_separator()
        fm.add_command(label="Exit", command=self.on_exit)
        m.add_cascade(label="File", menu=fm)
        hm = tk.Menu(m, tearoff=0)
        hm.add_command(label="About", command=self._about)
        m.add_cascade(label="Help", menu=hm)
        self.config(menu=m)
        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _about(self):
        messagebox.showinfo(
            "About",
            "FNAF: Security Breach — Save Editor\n"
            f"Version {__version__}\n\n"
            "Edit missions, world flags, and raw save values.\n"
            "Always keep a backup. No warranty.\n\n"
            "Unofficial fan tool. Not affiliated with Steel Wool Studios.")

    def _build_toolbar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(bar, text="Open…", command=self.open_file).pack(side="left")
        ttk.Button(bar, text="Save", command=self.save_file).pack(side="left", padx=4)
        ttk.Button(bar, text="Save As…", command=self.save_file_as).pack(side="left")
        self.file_lbl = ttk.Label(bar, text="(no file)")
        self.file_lbl.pack(side="left", padx=12)
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Backup on save (.bak)",
                        variable=self.backup_var).pack(side="right")

    # ---------------- missions tab ----------------
    def _build_missions_tab(self):
        f = self.tab_missions
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=(6, 0), pady=6)
        ttk.Label(left, text="Missions").pack(anchor="w")
        self.mission_list = tk.Listbox(
            left, width=28, exportselection=False,
            bg=DARK["bg2"], fg=DARK["fg"], selectbackground=DARK["accent"],
            selectforeground=DARK["accent_fg"], highlightthickness=0,
            relief="flat", borderwidth=0, activestyle="none")
        self.mission_list.pack(fill="y", expand=True)
        self.mission_list.bind("<<ListboxSelect>>", self._on_mission_select)

        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        self.m_name = tk.StringVar()
        ttk.Label(right, textvariable=self.m_name, font=("", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(right, text="Status:").grid(row=1, column=0, sticky="w")
        self.m_status = ttk.Combobox(right, values=MISSION_STATUSES, state="readonly", width=30)
        self.m_status.grid(row=1, column=1, sticky="w", pady=2)
        self.m_status.bind("<<ComboboxSelected>>", self._apply_mission_status)

        ttk.Label(right, text="InfoState:").grid(row=2, column=0, sticky="w")
        self.m_info = tk.IntVar()
        self.m_info_spin = ttk.Spinbox(right, from_=-1, to=99, textvariable=self.m_info,
                                       width=8, command=self._apply_mission_info)
        self.m_info_spin.grid(row=2, column=1, sticky="w", pady=2)
        self.m_info_spin.bind("<KeyRelease>", lambda e: self._apply_mission_info())

        ttk.Label(right, text="Completed steps (indices):").grid(row=3, column=0, sticky="nw", pady=(8, 0))
        cf = ttk.Frame(right); cf.grid(row=3, column=1, sticky="w", pady=(8, 0))
        self.m_tasks = tk.StringVar()
        self.m_tasks_entry = ttk.Entry(cf, textvariable=self.m_tasks, width=30)
        self.m_tasks_entry.pack(side="left")
        ttk.Button(cf, text="Apply", command=self._apply_mission_tasks).pack(side="left", padx=4)
        ttk.Label(right, text='e.g. "0, 1, 2"  (comma-separated; blank = none)',
                  foreground=DARK["fg_dim"]).grid(row=4, column=1, sticky="w")

        qf = ttk.LabelFrame(right, text="Quick actions")
        qf.grid(row=5, column=0, columnspan=2, sticky="we", pady=12)
        ttk.Button(qf, text="Mark Active", command=lambda: self._quick_status("EMissionStatus::Active")).pack(side="left", padx=4, pady=4)
        ttk.Button(qf, text="Mark Complete", command=lambda: self._quick_status("EMissionStatus::Complete")).pack(side="left", padx=4)
        ttk.Button(qf, text="Mark Inactive", command=lambda: self._quick_status("EMissionStatus::Inactive")).pack(side="left", padx=4)
        ttk.Button(qf, text="Enable first step (Active + step 0)",
                   command=self._quick_first_step).pack(side="left", padx=12)

        self._current_mission = None

    def _missions(self):
        for pr in (self.save.properties if self.save else []):
            if pr["name"] == "MissionState" and pr["type"] == "ArrayProperty":
                return pr["value"]["elements"]
        return []

    def _refresh_missions(self):
        self.mission_list.delete(0, "end")
        for elem in self._missions():
            nm = {p["name"]: p for p in elem}
            name = nm.get("Name", {}).get("value", "?")
            st = nm.get("Status", {}).get("value", "").replace("EMissionStatus::", "")
            self.mission_list.insert("end", f"{name}  [{st}]")

    def _on_mission_select(self, _evt):
        sel = self.mission_list.curselection()
        if not sel:
            return
        elem = self._missions()[sel[0]]
        nm = {p["name"]: p for p in elem}
        self._current_mission = nm
        self.m_name.set(nm.get("Name", {}).get("value", "?"))
        self.m_status.set(nm.get("Status", {}).get("value", ""))
        self.m_info.set(nm.get("InfoState", {}).get("value", 0))
        ct = nm.get("CompletedTasks", {}).get("value", {}).get("elements", [])
        self.m_tasks.set(", ".join(str(x) for x in ct))

    def _apply_mission_status(self, _evt=None):
        if not self._current_mission:
            return
        self._current_mission["Status"]["value"] = self.m_status.get()
        self._mark_dirty(); self._refresh_keep_selection()

    def _apply_mission_info(self):
        if not self._current_mission:
            return
        try:
            self._current_mission["InfoState"]["value"] = int(self.m_info.get())
            self._mark_dirty()
        except (ValueError, tk.TclError):
            pass

    def _apply_mission_tasks(self):
        if not self._current_mission:
            return
        txt = self.m_tasks.get().strip()
        try:
            vals = [int(x) for x in txt.replace(",", " ").split()] if txt else []
        except ValueError:
            messagebox.showerror("Invalid", "Steps must be integers, e.g. 0, 1, 2")
            return
        ct = self._current_mission["CompletedTasks"]["value"]
        ct["elements"] = vals
        ct["count"] = len(vals)
        self._mark_dirty()
        self.status.set(f"Completed steps set to {vals}")

    def _quick_status(self, status):
        if not self._current_mission:
            return
        self._current_mission["Status"]["value"] = status
        self.m_status.set(status)
        self._mark_dirty(); self._refresh_keep_selection()

    def _quick_first_step(self):
        if not self._current_mission:
            return
        self._current_mission["Status"]["value"] = "EMissionStatus::Active"
        self._current_mission["InfoState"]["value"] = 1
        ct = self._current_mission["CompletedTasks"]["value"]
        ct["elements"] = [0]; ct["count"] = 1
        self.m_status.set("EMissionStatus::Active")
        self.m_info.set(1); self.m_tasks.set("0")
        self._mark_dirty(); self._refresh_keep_selection()
        self.status.set("Mission set Active with first step (index 0) completed.")

    def _refresh_keep_selection(self):
        sel = self.mission_list.curselection()
        self._refresh_missions()
        if sel:
            self.mission_list.selection_set(sel[0])

    # ---------------- world flags tab ----------------
    def _build_flags_tab(self):
        f = self.tab_flags
        top = ttk.Frame(f); top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text="Filter:").pack(side="left")
        self.flag_filter = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.flag_filter)
        e.pack(side="left", fill="x", expand=True, padx=4)
        e.bind("<KeyRelease>", lambda _e: self._refresh_flags())
        ttk.Button(top, text="Add flag…", command=self._add_flag).pack(side="left")
        ttk.Button(top, text="Remove selected", command=self._remove_flag).pack(side="left", padx=4)

        cols = ("flag",)
        self.flag_tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="extended")
        self.flag_tree.heading("flag", text="Active world flags (ActivatedObjects)")
        self.flag_tree.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        ttk.Label(f, text="These are world triggers the game has marked done. "
                          "Remove one to let the game re-trigger it.",
                  foreground=DARK["fg_dim"]).pack(anchor="w", padx=8, pady=(0, 6))

    def _activated_set(self):
        for pr in (self.save.properties if self.save else []):
            if pr["name"] == "WorldStateData" and pr["type"] == "StructProperty":
                for sub in pr["value"]["props"]:
                    if sub["name"] == "ActivatedObjects":
                        return sub["value"]
        return None

    def _refresh_flags(self):
        for i in self.flag_tree.get_children():
            self.flag_tree.delete(i)
        s = self._activated_set()
        if not s:
            return
        filt = self.flag_filter.get().lower()
        for name in s["elements"]:
            if filt in name.lower():
                self.flag_tree.insert("", "end", values=(name,))

    def _remove_flag(self):
        s = self._activated_set()
        if not s:
            return
        sel = self.flag_tree.selection()
        if not sel:
            return
        names = {self.flag_tree.item(i, "values")[0] for i in sel}
        s["elements"] = [e for e in s["elements"] if e not in names]
        s["count"] = len(s["elements"])
        self._mark_dirty(); self._refresh_flags()
        self.status.set(f"Removed {len(names)} flag(s).")

    def _add_flag(self):
        s = self._activated_set()
        if not s:
            messagebox.showinfo("No save", "Open a save first.")
            return
        name = simpledialog.askstring("Add flag", "World flag name to add:")
        if not name:
            return
        if name in s["elements"]:
            messagebox.showinfo("Exists", "That flag is already active.")
            return
        s["elements"].append(name); s["count"] = len(s["elements"])
        self._mark_dirty(); self._refresh_flags()

    # ---------------- raw tree tab ----------------
    def _build_raw_tab(self):
        f = self.tab_raw
        self.raw_tree = ttk.Treeview(f, columns=("type", "value"), show="tree headings")
        self.raw_tree.heading("#0", text="Property")
        self.raw_tree.heading("type", text="Type")
        self.raw_tree.heading("value", text="Value")
        self.raw_tree.column("#0", width=420)
        self.raw_tree.column("type", width=110)
        self.raw_tree.column("value", width=340)
        vsb = ttk.Scrollbar(f, orient="vertical", command=self.raw_tree.yview)
        self.raw_tree.configure(yscroll=vsb.set)
        self.raw_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        vsb.pack(side="left", fill="y", pady=6)
        self.raw_tree.bind("<Double-1>", self._raw_edit)
        self._raw_map = {}   # tree item id -> (prop dict, kind)

    EDITABLE_SCALARS = {"IntProperty", "Int64Property", "UInt32Property",
                        "FloatProperty", "BoolProperty", "StrProperty",
                        "NameProperty", "EnumProperty", "ByteProperty"}

    def _refresh_raw(self):
        for i in self.raw_tree.get_children():
            self.raw_tree.delete(i)
        self._raw_map.clear()
        if not self.save:
            return
        for pr in self.save.properties:
            self._raw_add("", pr)

    def _raw_add(self, parent, prop):
        t = prop["type"]
        val = self._raw_value_str(prop)
        node = self.raw_tree.insert(parent, "end", text=prop["name"], values=(t, val))
        self._raw_map[node] = prop
        if t == "StructProperty" and not prop["value"].get("_binary"):
            for sub in prop["value"]["props"]:
                self._raw_add(node, sub)
        elif t == "ArrayProperty" and prop["value"]["kind"] == "struct":
            for i, elem in enumerate(prop["value"]["elements"]):
                label = self._element_label(elem)
                text = f"[{i}]  {label}" if label else f"[{i}]"
                idnode = self.raw_tree.insert(node, "end", text=text, values=("element", ""))
                for sub in elem:
                    self._raw_add(idnode, sub)
        elif t == "MapProperty":
            for i, (k, v) in enumerate(prop["value"]["pairs"]):
                text = f"[{i}]  {k}" if isinstance(k, str) else f"[{i}]  ={k}"
                knode = self.raw_tree.insert(node, "end", text=text, values=("entry", ""))
                if isinstance(v, dict) and v.get("_map_struct"):
                    for sub in v["props"]:
                        self._raw_add(knode, sub)
                else:
                    self.raw_tree.insert(knode, "end", text="value",
                                         values=(prop["value"].get("val_type", ""), str(v)))

    # Pull a human-friendly label from an array element's sub-properties.
    _LABEL_KEYS = ("Name", "ItemName", "MissionName", "Id", "Key", "Type", "PathName")

    def _element_label(self, elem):
        by_name = {p["name"]: p for p in elem}
        for k in self._LABEL_KEYS:
            if k in by_name and isinstance(by_name[k].get("value"), str):
                return by_name[k]["value"]
        return ""

    def _raw_value_str(self, prop):
        t = prop["type"]
        if t in self.EDITABLE_SCALARS:
            return str(prop.get("value"))
        if t == "StructProperty":
            return "<binary>" if prop["value"].get("_binary") else "{...}"
        if t in ("ArrayProperty", "SetProperty"):
            return f"[{prop['value'].get('count', '?')} items]"
        if t == "MapProperty":
            return f"{{{prop['value'].get('count', '?')} pairs}}"
        return ""

    def _raw_edit(self, _evt):
        item = self.raw_tree.focus()
        prop = self._raw_map.get(item)
        if not prop or prop["type"] not in self.EDITABLE_SCALARS:
            return
        t = prop["type"]
        cur = prop["value"]
        if t == "BoolProperty":
            prop["value"] = not bool(cur)
        elif t in ("IntProperty", "Int64Property", "UInt32Property"):
            v = simpledialog.askinteger("Edit", f"{prop['name']} (integer):", initialvalue=int(cur))
            if v is None:
                return
            prop["value"] = v
        elif t == "FloatProperty":
            v = simpledialog.askfloat("Edit", f"{prop['name']} (float):", initialvalue=float(cur))
            if v is None:
                return
            prop["value"] = v
        else:  # string-ish
            v = simpledialog.askstring("Edit", f"{prop['name']}:", initialvalue=str(cur))
            if v is None:
                return
            prop["value"] = v
        self.raw_tree.item(item, values=(t, self._raw_value_str(prop)))
        self._mark_dirty()

    # ---------------- file ops ----------------
    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open save", filetypes=[("UE SaveGame", "*.sav"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.save = gvas.SaveFile.load(path)
            # round-trip self-check
            if self.save.to_bytes() != open(path, "rb").read():
                messagebox.showwarning(
                    "Round-trip warning",
                    "This file did not round-trip exactly. Editing may be unsafe.\n"
                    "Proceed with caution and keep a backup.")
        except Exception as e:
            messagebox.showerror("Open failed", f"Could not parse file:\n{e}")
            return
        self.path = path
        self.dirty = False
        self.file_lbl.config(text=os.path.basename(path))
        self.title(f"FNAF SB Save Editor v{__version__} — {os.path.basename(path)}")
        self._refresh_missions()
        self._refresh_flags()
        self._refresh_raw()
        self.status.set(f"Loaded {os.path.basename(path)}  "
                        f"({len(self.save.properties)} top-level properties)")

    def save_file(self):
        if not self.save:
            return
        if not self.path:
            return self.save_file_as()
        self._write(self.path)

    def save_file_as(self):
        if not self.save:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".sav", filetypes=[("UE SaveGame", "*.sav")])
        if not path:
            return
        self._write(path)
        self.path = path
        self.file_lbl.config(text=os.path.basename(path))

    def _write(self, path):
        try:
            data = self.save.to_bytes()
        except Exception as e:
            messagebox.showerror("Serialize failed", str(e))
            return
        if self.backup_var.get() and os.path.exists(path):
            shutil.copy2(path, path + ".bak")
        with open(path, "wb") as f:
            f.write(data)
        self.dirty = False
        self.status.set(f"Saved {os.path.basename(path)} ({len(data)} bytes)"
                        + ("  + .bak backup" if self.backup_var.get() else ""))

    def _mark_dirty(self):
        self.dirty = True

    def on_exit(self):
        if self.dirty and not messagebox.askokcancel(
                "Unsaved changes", "You have unsaved changes. Quit without saving?"):
            return
        self.destroy()


if __name__ == "__main__":
    SaveEditor().mainloop()
