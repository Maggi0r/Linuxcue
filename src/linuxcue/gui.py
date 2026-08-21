from __future__ import annotations

import json
import sys
from datetime import datetime

TK_IMPORT_ERROR: Exception | None = None
try:
    from tkinter import BooleanVar, Frame, IntVar, Label, StringVar, Tk, colorchooser, filedialog, messagebox, simpledialog
    from tkinter import ttk
    from tkinter.scrolledtext import ScrolledText
except Exception as exc:
    TK_IMPORT_ERROR = exc

from .k95_backend import K95_LAYOUT
from .models import LightingZone
from .service import LinuxCueService


class LinuxCueGui:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.service = LinuxCueService()
        self.selected_profile = StringVar(value="")
        self.status_text = StringVar(value="Ready")

        self.root.title("linuxcue Control Center")
        self.root.geometry("1280x820")
        self.root.minsize(1080, 700)
        self.root.configure(bg="#0e1714")
        self.current_profile = None
        self.editor_vars: dict[str, object] = {}

        self._configure_style()
        self._build_layout()
        self.refresh_profiles()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("App.TFrame", background="#0e1714")
        style.configure("Card.TFrame", background="#182721", relief="flat")
        style.configure("DeviceCard.TFrame", background="#101f1b", relief="flat")
        style.configure("ActionDock.TFrame", background="#101817", relief="flat")
        style.configure("EditorSurface.TFrame", background="#0b1512", relief="flat")
        style.configure("Inspector.TFrame", background="#14241f", relief="flat")
        style.configure("Sidebar.TFrame", background="#07110e")
        style.configure("Header.TLabel", background="#0e1714", foreground="#f2f7ed", font=("Segoe UI", 27, "bold"))
        style.configure("Subhead.TLabel", background="#0e1714", foreground="#91a79d", font=("Segoe UI", 11))
        style.configure("SidebarTitle.TLabel", background="#07110e", foreground="#eaffd6", font=("Segoe UI", 15, "bold"))
        style.configure("SidebarBody.TLabel", background="#07110e", foreground="#9fbbb0", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#182721", foreground="#eaffd6", font=("Segoe UI", 14, "bold"))
        style.configure("CardBody.TLabel", background="#182721", foreground="#b7c9c1", font=("Segoe UI", 10))
        style.configure("DeviceTitle.TLabel", background="#101f1b", foreground="#f1ffe6", font=("Segoe UI", 11, "bold"))
        style.configure("DeviceBody.TLabel", background="#101f1b", foreground="#94aaa1", font=("Segoe UI", 9))
        style.configure("Glow.TLabel", background="#101f1b", foreground="#d7ff37", font=("Segoe UI", 13, "bold"))
        style.configure("EditorTitle.TLabel", background="#0b1512", foreground="#f1ffe6", font=("Segoe UI", 17, "bold"))
        style.configure("EditorBody.TLabel", background="#0b1512", foreground="#a9beb5", font=("Segoe UI", 10))
        style.configure("InspectorTitle.TLabel", background="#14241f", foreground="#eaffd6", font=("Segoe UI", 12, "bold"))
        style.configure("InspectorBody.TLabel", background="#14241f", foreground="#a9beb5", font=("Segoe UI", 10))
        style.configure("Dark.TLabel", background="#101817", foreground="#a9beb5", font=("Segoe UI", 10))
        style.configure("Panel.TFrame", background="#101817")
        style.configure("TLabelframe", background="#101817", foreground="#eaffd6")
        style.configure("TLabelframe.Label", background="#101817", foreground="#eaffd6", font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground="#0b1512", foreground="#edf8f1", insertcolor="#d7ff37")
        style.configure("TCombobox", fieldbackground="#0b1512", foreground="#edf8f1")
        style.configure("TNotebook", background="#0e1714", borderwidth=0)
        style.configure("TNotebook.Tab", background="#182721", foreground="#b7c9c1", padding=(14, 7))
        style.map("TNotebook.Tab", background=[("selected", "#d7ff37")], foreground=[("selected", "#07110e")])
        style.configure("Treeview", background="#0b1512", fieldbackground="#0b1512", foreground="#dcece4", rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading", background="#182721", foreground="#eaffd6", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#214c52")], foreground=[("selected", "#ffffff")])
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=9, background="#d7ff37", foreground="#07110e")
        style.map("Accent.TButton", background=[("active", "#ecff7a")])
        style.configure("Soft.TButton", font=("Segoe UI", 10), padding=8, background="#263a32", foreground="#eef6e8")
        style.map("Soft.TButton", background=[("active", "#345448")])
        style.configure("Slim.Horizontal.TScale", background="#f6f0e6", troughcolor="#d6d0c4")

    def _build_layout(self) -> None:
        shell = ttk.Frame(self.root, style="App.TFrame", padding=20)
        shell.pack(fill="both", expand=True)

        header = ttk.Frame(shell, style="App.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="linuxcue Control Center", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Profile Sets, per-key lighting, DPI und Virtuoso EQ in einer Linux-first Arbeitsoberflaeche",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(4, 14))

        body = ttk.Frame(shell, style="App.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_main(body)

        footer = ttk.Frame(shell, style="App.TFrame")
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, textvariable=self.status_text, style="Subhead.TLabel").pack(side="left")

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        sidebar = ttk.Frame(parent, style="Sidebar.TFrame", padding=18)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 18))
        sidebar.configure(width=300)

        ttk.Label(sidebar, text="Profiles", style="SidebarTitle.TLabel").pack(anchor="w")
        ttk.Label(sidebar, text="iCUE-Sets und Geraeteprofile", style="SidebarBody.TLabel").pack(
            anchor="w", pady=(4, 12)
        )

        self.profile_list = ttk.Treeview(sidebar, columns=("target", "companion"), show="tree headings", height=18)
        self.profile_list.heading("#0", text="Name")
        self.profile_list.heading("target", text="Target")
        self.profile_list.heading("companion", text="Companion")
        self.profile_list.column("#0", width=170)
        self.profile_list.column("target", width=90, anchor="center")
        self.profile_list.column("companion", width=120, anchor="center")
        self.profile_list.pack(fill="both", expand=True)
        self.profile_list.bind("<<TreeviewSelect>>", self._on_profile_selected)
        self.profile_list.bind("<Delete>", lambda _event: self.delete_selected_profile())
        self.profile_list.bind("<BackSpace>", lambda _event: self.delete_selected_profile())

        actions = ttk.Frame(sidebar, style="Sidebar.TFrame")
        actions.pack(fill="x", pady=(10, 0))
        actions.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(actions, text="Delete", command=self.delete_selected_profile, style="Soft.TButton").grid(
            row=0, column=0, sticky="ew", padx=(0, 4), pady=3
        )
        ttk.Button(actions, text="Rename", command=self.rename_selected_profile, style="Soft.TButton").grid(
            row=0, column=1, sticky="ew", padx=4, pady=3
        )
        ttk.Button(actions, text="Duplicate", command=self.duplicate_selected_profile, style="Soft.TButton").grid(
            row=0, column=2, sticky="ew", padx=(4, 0), pady=3
        )
        ttk.Button(actions, text="Refresh Profiles", command=self.refresh_profiles, style="Accent.TButton").grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(4, 8)
        )

        ttk.Label(sidebar, text="Create Starter", style="SidebarBody.TLabel").pack(anchor="w", pady=(10, 4))
        starter_actions = ttk.Frame(sidebar, style="Sidebar.TFrame")
        starter_actions.pack(fill="x")
        starter_actions.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(starter_actions, text="K95", command=lambda: self.create_starter("k95"), style="Accent.TButton").grid(
            row=0, column=0, sticky="ew", padx=(0, 4), pady=3
        )
        ttk.Button(starter_actions, text="M65", command=lambda: self.create_starter("m65"), style="Accent.TButton").grid(
            row=0, column=1, sticky="ew", padx=4, pady=3
        )
        ttk.Button(
            starter_actions,
            text="Virtuoso",
            command=lambda: self.create_starter("virtuoso-se"),
            style="Accent.TButton",
        ).grid(row=0, column=2, sticky="ew", padx=(4, 0), pady=3)

    def _build_main(self, parent: ttk.Frame) -> None:
        main = ttk.Frame(parent, style="App.TFrame")
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        cards = ttk.Frame(main, style="App.TFrame")
        cards.grid(row=0, column=0, sticky="ew")
        cards.columnconfigure((0, 1, 2, 3), weight=1)

        self.summary_vars = {
            "name": StringVar(value="No profile selected"),
            "target": StringVar(value="Target: -"),
            "description": StringVar(value="Description: -"),
            "companion": StringVar(value="Companion: -"),
            "devices": StringVar(value="Devices: not checked"),
        }
        self._make_card(cards, 0, "Selected Profile", self.summary_vars["name"])
        self._make_card(cards, 1, "Target Scope", self.summary_vars["target"])
        self._make_card(cards, 2, "Companion", self.summary_vars["companion"])
        self._make_card(cards, 3, "Device Check", self.summary_vars["devices"])

        self.device_strip = ttk.Frame(main, style="App.TFrame")
        self.device_strip.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.device_strip.columnconfigure((0, 1, 2, 3), weight=1)
        self._populate_device_strip()

        toolbar = ttk.Frame(main, style="ActionDock.TFrame", padding=10)
        toolbar.grid(row=2, column=0, sticky="ew", pady=(14, 12))
        ttk.Label(toolbar, text="Live Control", style="Dark.TLabel").pack(side="left", padx=(2, 18))
        ttk.Button(toolbar, text="Live Write", command=self.write_selected_live, style="Accent.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Save", command=self.save_selected_profile, style="Soft.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Preview", command=self.preview_selected, style="Soft.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Simulation", command=self.apply_selected, style="Soft.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Import iCUE", command=self.import_icue_profile, style="Soft.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(toolbar, text="Refresh Devices", command=self.refresh_device_status, style="Soft.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(toolbar, text="K95 Hardware", command=self.k95_hardware_mode, style="Soft.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(toolbar, text="Diagnostics", command=self.map_devices, style="Soft.TButton").pack(side="right")

        notebook = ttk.Notebook(main)
        notebook.grid(row=3, column=0, sticky="nsew")

        editor_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
        preview_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
        json_tab = ttk.Frame(notebook, style="App.TFrame", padding=10)
        notebook.add(editor_tab, text="Editor")
        notebook.add(preview_tab, text="Preview")
        notebook.add(json_tab, text="Profile JSON")

        self.editor_canvas = ttk.Frame(editor_tab, style="Panel.TFrame", padding=14)
        self.editor_canvas.pack(fill="both", expand=True)

        self.preview_box = ScrolledText(preview_tab, wrap="word", font=("Consolas", 10), bg="#0b1512", fg="#dcece4", insertbackground="#d7ff37")
        self.preview_box.pack(fill="both", expand=True)

        self.profile_box = ScrolledText(json_tab, wrap="word", font=("Consolas", 10), bg="#0b1512", fg="#dcece4", insertbackground="#d7ff37")
        self.profile_box.pack(fill="both", expand=True)

    def _make_card(self, parent: ttk.Frame, column: int, title: str, variable: StringVar) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=variable, style="CardBody.TLabel", wraplength=260, justify="left").pack(
            anchor="w", pady=(10, 0)
        )

    def _populate_device_strip(self) -> None:
        self._populate_device_strip_cards()
        return

    def _populate_device_strip_cards(self) -> None:
        for child in self.device_strip.winfo_children():
            child.destroy()
        devices = [
            ("K95 RGB Platinum", "Keyboard", "k95", "#04ff00"),
            ("M65 Pro RGB", "Mouse DPI/RGB", "m65", "#00c2ff"),
            ("Virtuoso SE", "EQ + Headset", "virtuoso-se", "#f0c15a"),
            ("Wireless Receiver", "Link path", "receiver", "#d7ff37"),
        ]
        status = self.service.live_status()
        for column, (title, subtitle, slug, color) in enumerate(devices):
            matches = [
                item for item in status["devices"]
                if slug in str(item.get("target", "")).casefold() or slug in str(item.get("family", "")).casefold()
            ]
            state = "online" if matches else "offline"
            card = ttk.Frame(self.device_strip, style="DeviceCard.TFrame", padding=12)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
            ttk.Label(card, text="*", style="Glow.TLabel", foreground=color).pack(anchor="w")
            ttk.Label(card, text=title, style="DeviceTitle.TLabel").pack(anchor="w")
            ttk.Label(card, text=f"{subtitle} / {state}", style="DeviceBody.TLabel").pack(anchor="w", pady=(4, 0))
        return

        for child in self.device_strip.winfo_children():
            child.destroy()
        devices = [
            ("K95 RGB Platinum", "Keyboard", "k95", "#04ff00"),
            ("M65 Pro RGB", "Mouse DPI/RGB", "m65", "#00c2ff"),
            ("Virtuoso SE", "EQ + Headset", "virtuoso-se", "#f0c15a"),
            ("Wireless Receiver", "Link path", "receiver", "#d7ff37"),
        ]
        status = self.service.live_status()
        connected_text = "offline"
        for column, (title, subtitle, slug, color) in enumerate(devices):
            matches = [
                item for item in status["devices"]
                if slug in str(item.get("target", "")).casefold() or slug in str(item.get("family", "")).casefold()
            ]
            state = "online" if matches else connected_text
            card = ttk.Frame(self.device_strip, style="DeviceCard.TFrame", padding=12)
            card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
            ttk.Label(card, text="●", style="Glow.TLabel", foreground=color).pack(anchor="w")
            ttk.Label(card, text=title, style="DeviceTitle.TLabel").pack(anchor="w")
            ttk.Label(card, text=f"{subtitle} · {state}", style="DeviceBody.TLabel").pack(anchor="w", pady=(4, 0))

    def refresh_profiles(self) -> None:
        for item in self.profile_list.get_children():
            self.profile_list.delete(item)

        summaries = self.service.list_profile_summaries()
        inserted: set[str] = set()
        for profile in summaries:
            if profile["target_device"] != "profile-set":
                continue
            self.profile_list.insert(
                "",
                "end",
                iid=profile["name"],
                text=profile["name"],
                values=("set", profile["companion"]),
                open=True,
            )
            inserted.add(str(profile["name"]))

        for profile in summaries:
            if profile["name"] in inserted:
                continue
            parent = ""
            group = str(profile.get("profile_group") or "")
            if group in inserted:
                parent = group
            self.profile_list.insert(
                parent,
                "end",
                iid=profile["name"],
                text=profile["name"],
                values=(profile["target_device"], profile["companion"]),
            )

        self.refresh_device_status(show_popup=False)
        self.status_text.set(f"Refreshed {len(self.service.list_profile_summaries())} profiles at {datetime.now():%H:%M:%S}")

    def refresh_device_status(self, show_popup: bool = True) -> None:
        profile = self.current_profile
        status = self.service.live_status(profile)
        if hasattr(self, "device_strip"):
            self._populate_device_strip()
        text = (
            f"{status['connected_count']} connected / "
            f"{status['writable_count']} writable / "
            f"{status['matching_count']} matching"
        )
        self.summary_vars["devices"].set(text)
        self.status_text.set(f"Device check: {text}")
        if show_popup:
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", json.dumps(status, indent=2))

    def create_starter(self, target: str) -> None:
        timestamp = datetime.now().strftime("%H%M%S")
        name = f"{target}-{timestamp}"
        profile = self.service.create_profile_for_target(target, name)
        self.service.save_profile(profile)
        self.refresh_profiles()
        self.profile_list.selection_set(name)
        self.profile_list.focus(name)
        self._show_profile(name)
        self.status_text.set(f"Created starter profile {name}")

    def _on_profile_selected(self, event: object) -> None:
        selection = self.profile_list.selection()
        if not selection:
            return
        self._show_profile(selection[0])

    def _selected_profile_name(self) -> str:
        selection = self.profile_list.selection()
        if selection:
            return str(selection[0])
        focused = self.profile_list.focus()
        if focused:
            return str(focused)
        return self.selected_profile.get()

    def _show_profile(self, name: str) -> None:
        profile = self.service.load_profile(name)
        if profile is None:
            return

        self.selected_profile.set(name)
        self.current_profile = profile
        self.summary_vars["name"].set(profile.name)
        self.summary_vars["target"].set(f"{profile.target_device} / {profile.target_family}")
        self.summary_vars["companion"].set(self.service.profile_companion_label(profile) or "No companion device")
        self.summary_vars["description"].set(profile.description or "No description")
        self.refresh_device_status(show_popup=False)
        self._populate_editor(profile)
        self.profile_box.delete("1.0", "end")
        self.profile_box.insert("1.0", json.dumps(profile.to_dict(), indent=2))
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", "Select Preview or Apply Simulation to inspect packets.")

    def _populate_editor(self, profile) -> None:
        for child in self.editor_canvas.winfo_children():
            child.destroy()

        self.editor_vars = {}
        self._make_editor_header(profile)
        if profile.target_device == "k95":
            self._build_k95_editor(profile)
        elif profile.target_device == "profile-set":
            self._build_profile_set_editor(profile)
        elif profile.target_device == "m65":
            self._build_m65_editor(profile)
        elif profile.target_device == "virtuoso-se":
            self._build_virtuoso_editor(profile)
        else:
            self._build_generic_editor(profile)

    def _make_editor_header(self, profile) -> None:
        header = ttk.Frame(self.editor_canvas, style="Panel.TFrame")
        header.pack(fill="x", pady=(0, 14))

        ttk.Label(header, text="Profile Editor", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(header, text=f"{profile.name}  |  {profile.target_device}", style="CardBody.TLabel").pack(anchor="w", pady=(4, 8))

        description_var = StringVar(value=profile.description)
        self.editor_vars["description"] = description_var
        ttk.Label(header, text="Description", style="CardBody.TLabel").pack(anchor="w")
        ttk.Entry(header, textvariable=description_var).pack(fill="x", pady=(4, 0))

    def _build_generic_editor(self, profile) -> None:
        box = ttk.Frame(self.editor_canvas, style="Panel.TFrame")
        box.pack(fill="x")
        ttk.Label(
            box,
            text="Dieses Profil nutzt noch keinen geraetespezifischen Editor. Du kannst aber Beschreibung und JSON-Ansicht nutzen.",
            style="CardBody.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w")

    def _build_profile_set_editor(self, profile) -> None:
        box = ttk.LabelFrame(self.editor_canvas, text="iCUE Profile Set")
        box.pack(fill="x", pady=(0, 12))
        members = self.service.profiles_in_group(profile.profile_group or profile.name)
        ttk.Label(
            box,
            text="Dieses Gesamtprofil schaltet alle importierten Geraeteprofile gemeinsam.",
            style="CardBody.TLabel",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(8, 4))
        for member in members:
            ttk.Label(
                box,
                text=f"{member.group_role or member.target_family}: {member.name} ({member.target_device})",
                style="CardBody.TLabel",
            ).pack(anchor="w", padx=8, pady=2)

    def _build_k95_editor(self, profile) -> None:
        self._ensure_k95_per_key_lighting(profile)
        frame = ttk.Frame(self.editor_canvas, style="EditorSurface.TFrame", padding=16)
        frame.pack(fill="both", expand=True, pady=(0, 12))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="K95 RGB Platinum", style="EditorTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            frame,
            text="Per-key lighting: Taste anklicken, Palette waehlen, dann Save oder Live Write.",
            style="EditorBody.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(32, 12))
        zone_vars: list[dict[str, StringVar]] = []
        key_zones = {zone.keys[0]: zone for zone in profile.lighting if len(zone.keys) == 1}
        selected_key = StringVar(value="Keine Taste ausgewaehlt")
        selected: dict[str, object] = {"zone": None, "color_var": None, "button": None}

        controls = ttk.Frame(frame, style="Inspector.TFrame", padding=14)
        controls.grid(row=1, column=1, sticky="nsew", padx=(18, 0), pady=(6, 0))
        Label(
            controls,
            text="Selected Key",
            bg="#14241f",
            fg="#eaffd6",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        Label(
            controls,
            textvariable=selected_key,
            bg="#14241f",
            fg="#d7ff37",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(6, 14))
        Label(
            controls,
            text="Palette",
            bg="#14241f",
            fg="#a9beb5",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 6))
        palette = Frame(controls, bg="#14241f")
        palette.pack(anchor="w")

        def select_zone(zone, color_var: StringVar, button: Label, key: str) -> None:
            old_button = selected.get("button")
            if isinstance(old_button, Label):
                old_button.configure(highlightbackground="#294237", highlightthickness=1)
            selected["zone"] = zone
            selected["color_var"] = color_var
            selected["button"] = button
            selected_key.set(f"Ausgewaehlt: {key.upper()}  {color_var.get()}")
            button.configure(highlightbackground="#d7ff37", highlightthickness=3)

        def apply_palette_color(color: str) -> None:
            color_var = selected.get("color_var")
            zone = selected.get("zone")
            if not isinstance(color_var, StringVar) or zone is None:
                self.status_text.set("Bitte zuerst eine K95-Taste anklicken.")
                return
            color_var.set(color)
            zone.color = color
            selected_key.set(f"Ausgewaehlt: {zone.keys[0].upper()}  {color}")
            self.status_text.set(f"K95 key {zone.keys[0]} set to {color}. Save or Live Write to apply.")

        for index, color in enumerate(("#04ff00", "#00c2ff", "#1ecfdf", "#eb1fe3", "#ff0400", "#fff000", "#0064ff", "#ffffff", "#000000")):
            swatch = Label(
                palette,
                text="",
                width=4,
                height=2,
                bg=color,
                relief="flat",
                highlightthickness=1,
                highlightbackground="#294237",
            )
            swatch.grid(row=index // 3, column=index % 3, padx=4, pady=4)
            swatch.bind("<Button-1>", lambda _event, value=color: apply_palette_color(value))

        def apply_to_all() -> None:
            color_var = selected.get("color_var")
            if not isinstance(color_var, StringVar):
                self.status_text.set("Bitte zuerst eine Quellfarbe ueber eine K95-Taste auswaehlen.")
                return
            chosen = color_var.get()
            for values in zone_vars:
                values["color"].set(chosen)
                values["zone"].color = chosen
            self.status_text.set(f"All K95 keys set to {chosen}. Save or Live Write to apply.")

        ttk.Button(controls, text="Apply To All Keys", command=apply_to_all, style="Accent.TButton").pack(
            fill="x", pady=(18, 8)
        )
        ttk.Button(controls, text="Pick Custom Color", command=lambda: self._pick_selected_k95_color(selected, selected_key), style="Soft.TButton").pack(
            fill="x", pady=(0, 8)
        )
        ttk.Label(
            controls,
            text="Tipp: Preview und Live Write speichern automatisch die aktuelle GUI-Auswahl vor dem Senden.",
            style="InspectorBody.TLabel",
            wraplength=220,
            justify="left",
        ).pack(anchor="w", pady=(12, 0))
        rows = [
            ["esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12", "stop", "prev", "play", "next", "brightness", "mute", "vol_wheel"],
            ["grave", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "minus", "equals", "backspace", "insert", "home", "pageup"],
            ["tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "lbracket", "rbracket", "backslash", "delete", "end", "pagedown"],
            ["caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", "semicolon", "quote", "enter"],
            ["lshift", "z", "x", "c", "v", "b", "n", "m", "comma", "period", "slash", "rshift", "up"],
            ["lctrl", "lwin", "lalt", "space", "ralt", "menu", "rctrl", "left", "down", "right"],
            ["g1", "g2", "g3", "g4", "g5", "g6", "numlock", "kp_slash", "kp_star", "kp_minus", "kp7", "kp8", "kp9", "kp_plus", "kp4", "kp5", "kp6", "kp1", "kp2", "kp3", "kp_enter", "kp0", "kp_dot"],
        ]
        keyboard = Frame(frame, bg="#0b1512", padx=12, pady=12)
        keyboard.grid(row=1, column=0, sticky="nw", padx=0, pady=(6, 0))
        used_zone_ids: set[int] = set()
        wide_keys = {
            "backspace": 9,
            "tab": 7,
            "caps": 8,
            "enter": 8,
            "lshift": 8,
            "rshift": 8,
            "space": 26,
            "kp_plus": 7,
            "kp_enter": 8,
            "brightness": 10,
            "vol_wheel": 9,
            "numlock": 8,
        }
        row_offsets = [0, 0, 10, 18, 28, 38, 0]
        for row_index, keys in enumerate(rows):
            row = Frame(keyboard, bg="#0b1512")
            row.grid(row=row_index, column=0, sticky="w", padx=(row_offsets[row_index], 0), pady=3)
            for key in keys:
                zone = key_zones.get(key)
                if zone is None:
                    continue
                used_zone_ids.add(id(zone))
                color_var = StringVar(value=zone.color)
                mode_var = StringVar(value=zone.mode)
                button = Label(
                    row,
                    text=key.upper(),
                    width=wide_keys.get(key, max(4, min(10, len(key) + 1))),
                    relief="flat",
                    background=self._valid_color(color_var.get()),
                    foreground="#ffffff",
                    font=("Segoe UI", 8, "bold"),
                    padx=4,
                    pady=5,
                    borderwidth=1,
                    highlightthickness=1,
                    highlightbackground="#294237",
                )
                button.pack(side="left", padx=2)
                button.bind("<Button-1>", lambda _event, z=zone, var=color_var, widget=button, key_name=key: select_zone(z, var, widget, key_name))
                button.bind("<Double-Button-1>", lambda _event, var=color_var: self.pick_color(var))
                color_var.trace_add("write", lambda *_args, widget=button, var=color_var: widget.configure(background=self._valid_color(var.get())))
                zone_vars.append({"zone": zone, "color": color_var, "mode": mode_var})
        leftovers = [zone for zone in profile.lighting if id(zone) not in used_zone_ids]
        if leftovers:
            extra = ttk.LabelFrame(frame, text="Additional Zones")
            extra.grid(row=2, column=0, sticky="ew", padx=0, pady=(12, 4))
        for index, zone in enumerate(leftovers):
            row = ttk.Frame(extra)
            row.grid(row=index, column=0, sticky="ew", padx=8, pady=4)
            color_var = StringVar(value=zone.color)
            mode_var = StringVar(value=zone.mode)
            ttk.Label(row, text=zone.name, width=18).pack(side="left")
            self._color_control(row, color_var).pack(side="left", padx=(0, 8))
            ttk.Combobox(row, textvariable=mode_var, values=("static", "wave", "rain"), width=12, state="readonly").pack(side="left")
            zone_vars.append({"zone": zone, "color": color_var, "mode": mode_var})
        self.editor_vars["k95_lighting"] = zone_vars

    def _ensure_k95_per_key_lighting(self, profile) -> None:
        all_keys = [key for keys in K95_LAYOUT.values() for key in keys if key != "fn"]
        existing_single = {
            zone.keys[0]: zone
            for zone in profile.lighting
            if len(zone.keys) == 1 and zone.keys[0] in all_keys
        }
        if len(existing_single) == len(all_keys):
            return

        key_colors = {key: "#04ff00" for key in all_keys}
        key_modes = {key: "static" for key in all_keys}
        for zone in profile.lighting:
            keys = [key for key in zone.keys if key in key_colors]
            if not keys:
                keys = [key for key in K95_LAYOUT.get(zone.name, []) if key in key_colors]
            if len(zone.keys) == 1 and zone.name.startswith("key_") and zone.name[4:] in key_colors:
                keys = [zone.name[4:]]
            for key in keys:
                key_colors[key] = zone.color
                key_modes[key] = zone.mode

        profile.lighting = [
            LightingZone(name=f"key_{key}", color=key_colors[key], mode=key_modes[key], keys=[key])
            for key in all_keys
        ]

    def _pick_selected_k95_color(self, selected: dict[str, object], selected_key: StringVar) -> None:
        color_var = selected.get("color_var")
        zone = selected.get("zone")
        if not isinstance(color_var, StringVar) or zone is None:
            self.status_text.set("Bitte zuerst eine K95-Taste anklicken.")
            return
        color = colorchooser.askcolor(color=color_var.get(), title="Choose K95 key color")
        if color and color[1]:
            color_var.set(color[1])
            zone.color = color[1]
            selected_key.set(f"Ausgewaehlt: {zone.keys[0].upper()}  {color[1]}")
            self.status_text.set(f"K95 key {zone.keys[0]} set to {color[1]}.")

    def _build_m65_editor(self, profile) -> None:
        light_frame = ttk.LabelFrame(self.editor_canvas, text="RGB")
        light_frame.pack(fill="x", pady=(0, 12))
        lighting_vars: list[StringVar] = []
        for index, zone in enumerate(profile.lighting):
            row = ttk.Frame(light_frame)
            row.grid(row=index, column=0, sticky="ew", padx=8, pady=4)
            ttk.Label(row, text=zone.name, width=18).pack(side="left")
            color_var = StringVar(value=zone.color)
            self._color_control(row, color_var).pack(side="left")
            lighting_vars.append(color_var)
        self.editor_vars["m65_lighting"] = lighting_vars

        dpi_frame = ttk.LabelFrame(self.editor_canvas, text="DPI Stages")
        dpi_frame.pack(fill="x")
        dpi_vars: list[dict[str, object]] = []
        for index, stage in enumerate(profile.dpi):
            row = ttk.Frame(dpi_frame)
            row.grid(row=index, column=0, sticky="ew", padx=8, pady=4)
            active_var = BooleanVar(value=stage.active)
            x_var = IntVar(value=stage.x)
            y_var = IntVar(value=stage.y)
            color_var = StringVar(value=stage.color)
            ttk.Checkbutton(row, variable=active_var).pack(side="left")
            ttk.Label(row, text=stage.name, width=12).pack(side="left")
            self._slider_spin(row, x_var, 100, 26000).pack(side="left", padx=(0, 8))
            self._slider_spin(row, y_var, 100, 26000).pack(side="left", padx=(0, 8))
            self._color_control(row, color_var).pack(side="left")
            dpi_vars.append({"active": active_var, "x": x_var, "y": y_var, "color": color_var})
        self.editor_vars["m65_dpi"] = dpi_vars

    def _build_virtuoso_editor(self, profile) -> None:
        audio_frame = ttk.LabelFrame(self.editor_canvas, text="EQ Presets")
        audio_frame.pack(fill="x", pady=(0, 12))
        frequencies = ("32", "64", "125", "250", "500", "1k", "2k", "4k", "8k", "16k")
        header = ttk.Frame(audio_frame)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        ttk.Label(header, text="Active", width=7).pack(side="left")
        ttk.Label(header, text="Preset", width=12).pack(side="left")
        for frequency in frequencies:
            ttk.Label(header, text=frequency, width=6, anchor="center").pack(side="left", padx=(0, 4))
        audio_vars: list[dict[str, object]] = []
        for index, preset in enumerate(profile.audio):
            row = ttk.Frame(audio_frame)
            row.grid(row=index + 1, column=0, sticky="ew", padx=8, pady=4)
            active_var = BooleanVar(value=preset.active)
            band_values = list(preset.bands[:10]) if preset.bands else self._legacy_eq_bands(preset)
            band_values.extend([0] * (10 - len(band_values)))
            band_vars = [IntVar(value=value) for value in band_values[:10]]
            ttk.Checkbutton(row, variable=active_var).pack(side="left")
            ttk.Label(row, text=preset.name, width=12).pack(side="left")
            for band_var in band_vars:
                ttk.Spinbox(row, from_=-12, to=12, textvariable=band_var, width=5).pack(side="left", padx=(0, 4))
            audio_vars.append({"active": active_var, "bands": band_vars})
        self.editor_vars["virtuoso_audio"] = audio_vars

        control_frame = ttk.LabelFrame(self.editor_canvas, text="Headset Controls")
        control_frame.pack(fill="x", pady=(0, 12))
        accent_var = StringVar(value=profile.lighting[0].color if profile.lighting else "#ffffff")
        sidetone_var = IntVar(value=profile.headset.sidetone)
        mic_var = IntVar(value=profile.headset.mic_level)
        sleep_var = IntVar(value=profile.headset.sleep_timer_minutes)
        prompt_var = BooleanVar(value=profile.headset.voice_prompt_enabled)
        self.editor_vars["virtuoso_controls"] = {
            "accent": accent_var,
            "sidetone": sidetone_var,
            "mic": mic_var,
            "sleep": sleep_var,
            "prompt": prompt_var,
        }
        self._labeled_color(control_frame, "Accent Color", accent_var, 0)
        self._labeled_slider(control_frame, "Sidetone", sidetone_var, 1, 0, 100)
        self._labeled_slider(control_frame, "Mic Level", mic_var, 2, 0, 100)
        self._labeled_slider(control_frame, "Sleep Timer", sleep_var, 3, 1, 120)
        ttk.Checkbutton(control_frame, text="Voice Prompts Enabled", variable=prompt_var).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=6)

    def _labeled_entry(self, parent, label: str, variable: StringVar, row: int, button_command=None) -> None:
        ttk.Label(parent, text=label, width=18).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(parent, textvariable=variable, width=16).grid(row=row, column=1, sticky="w", padx=8, pady=4)
        if button_command is not None:
            ttk.Button(parent, text="Pick", command=button_command, style="Soft.TButton").grid(row=row, column=2, sticky="w", padx=8, pady=4)

    def _labeled_spin(self, parent, label: str, variable: IntVar, row: int, minimum: int, maximum: int) -> None:
        ttk.Label(parent, text=label, width=18).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Spinbox(parent, from_=minimum, to=maximum, textvariable=variable, width=10).grid(row=row, column=1, sticky="w", padx=8, pady=4)

    def _labeled_color(self, parent, label: str, variable: StringVar, row: int) -> None:
        ttk.Label(parent, text=label, width=18).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self._color_control(parent, variable).grid(row=row, column=1, sticky="w", padx=8, pady=4)

    def _labeled_slider(self, parent, label: str, variable: IntVar, row: int, minimum: int, maximum: int) -> None:
        ttk.Label(parent, text=label, width=18).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self._slider_spin(parent, variable, minimum, maximum, width=260).grid(row=row, column=1, sticky="w", padx=8, pady=4)

    def _color_control(self, parent, variable: StringVar):
        frame = ttk.Frame(parent)
        swatch = Label(frame, width=3, relief="groove", background=self._valid_color(variable.get()))
        swatch.pack(side="left", padx=(0, 6))
        entry = ttk.Entry(frame, textvariable=variable, width=10)
        entry.pack(side="left", padx=(0, 6))
        ttk.Button(frame, text="Pick", command=lambda: self.pick_color(variable), style="Soft.TButton").pack(side="left")
        variable.trace_add("write", lambda *_: swatch.configure(background=self._valid_color(variable.get())))
        return frame

    def _slider_spin(self, parent, variable: IntVar, minimum: int, maximum: int, width: int = 180):
        frame = ttk.Frame(parent)
        syncing = {"active": False}

        def update_from_scale(value: str) -> None:
            if syncing["active"]:
                return
            syncing["active"] = True
            variable.set(int(float(value)))
            syncing["active"] = False

        scale = ttk.Scale(
            frame,
            from_=minimum,
            to=maximum,
            command=update_from_scale,
            style="Slim.Horizontal.TScale",
            length=width,
        )
        scale.set(variable.get())
        scale.pack(side="left", padx=(0, 6))
        ttk.Spinbox(frame, from_=minimum, to=maximum, textvariable=variable, width=7).pack(side="left")

        def update_from_var(*_: object) -> None:
            if syncing["active"]:
                return
            syncing["active"] = True
            scale.set(variable.get())
            syncing["active"] = False

        variable.trace_add("write", update_from_var)
        return frame

    def preview_selected(self) -> None:
        name = self.selected_profile.get()
        if not name:
            messagebox.showinfo("linuxcue", "Bitte zuerst ein Profil auswaehlen.")
            return
        if not self._apply_editor_to_current_profile():
            return
        if self.current_profile is not None:
            self.service.save_profile(self.current_profile)
        preview = self.service.preview_profile(name)
        if preview is None:
            messagebox.showwarning("linuxcue", "Fuer dieses Profil ist keine direkte Vorschau verfuegbar.")
            return
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", json.dumps(preview, indent=2))
        self.status_text.set(f"Preview generated for {name}")

    def apply_selected(self) -> None:
        name = self.selected_profile.get()
        if not name:
            messagebox.showinfo("linuxcue", "Bitte zuerst ein Profil auswaehlen.")
            return
        if not self._apply_editor_to_current_profile():
            return
        if self.current_profile is not None:
            self.service.save_profile(self.current_profile)
        result = self.service.apply_profile(name)
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", json.dumps(
            {
                "profile": result.profile_name,
                "devices": result.device_count,
                "message": result.message,
                "actions": result.actions,
            },
            indent=2,
        ))
        self.status_text.set(f"Applied simulation for {name}")

    def map_devices(self) -> None:
        self.status_text.set("Mapping HID endpoints...")
        mapping = self.service.map_hid_endpoints()
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", json.dumps(mapping, indent=2))
        open_count = sum(1 for endpoint in mapping["endpoints"] if endpoint.get("open_ok"))
        self.status_text.set(f"Mapped {mapping['device_count']} HID endpoints; {open_count} opened successfully")

    def capture_descriptors(self) -> None:
        self.status_text.set("Capturing HID descriptors...")
        descriptors = self.service.capture_hid_descriptors()
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", json.dumps(descriptors, indent=2))
        self.status_text.set(f"Captured {descriptors['descriptor_count']} HID descriptors")

    def import_icue_profile(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Import iCUE profile",
            filetypes=(("iCUE profiles", "*.cueprofile"), ("All files", "*.*")),
        )
        if not path:
            return
        preview = self.service.preview_icue_import(path)
        if not preview["imported_count"]:
            messagebox.showwarning("linuxcue", "No supported EQ/DPI profile data was found in this iCUE profile.")
            return
        if not messagebox.askyesno(
            "Import iCUE Profile",
            f"Import {preview['imported_count']} linuxcue profile(s) from '{preview['icue_profile_name']}'?",
            parent=self.root,
        ):
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", json.dumps(preview, indent=2))
            self.status_text.set("iCUE import preview loaded")
            return
        result = self.service.import_icue_profiles(path)
        self.refresh_profiles()
        if result["profile_names"]:
            first = result["profile_names"][0]
            self.profile_list.selection_set(first)
            self.profile_list.focus(first)
            self._show_profile(first)
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", json.dumps(result, indent=2))
        self.status_text.set(f"Imported/updated {result['saved_count']} iCUE profile(s)")

    def show_capabilities(self) -> None:
        self.status_text.set("Loading linuxcue capability map...")
        matrix = self.service.capability_matrix()
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", json.dumps(matrix, indent=2))
        mapped_count = sum(len(items) for items in matrix["capability_map"].values())
        self.status_text.set(f"Loaded {mapped_count} mapped capability entries")

    def k95_hardware_mode(self) -> None:
        try:
            result = self.service.write_k95_hardware_mode_live()
        except Exception as exc:
            messagebox.showerror("linuxcue", str(exc))
            self.status_text.set("K95 hardware mode failed")
            return
        payload = {
            "profile": result.profile_name,
            "device": result.device,
            "packet_count": result.packet_count,
            "message": result.message,
        }
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", json.dumps(payload, indent=2))
        self.status_text.set("K95 hardware lighting mode sent")

    def _apply_editor_to_current_profile(self) -> bool:
        name = self.selected_profile.get()
        profile = self.current_profile
        if not name or profile is None:
            messagebox.showinfo("linuxcue", "Bitte zuerst ein Profil auswaehlen.")
            return False

        description_var = self.editor_vars.get("description")
        if isinstance(description_var, StringVar):
            profile.description = description_var.get().strip()

        if profile.target_device == "k95":
            zone_vars = self.editor_vars.get("k95_lighting", [])
            for values in zone_vars:
                zone = values.get("zone")
                if zone is None:
                    continue
                zone.color = values["color"].get().strip()
                zone.mode = values["mode"].get().strip()
        elif profile.target_device == "m65":
            lighting_vars = self.editor_vars.get("m65_lighting", [])
            for zone, color_var in zip(profile.lighting, lighting_vars):
                zone.color = color_var.get().strip()
            dpi_vars = self.editor_vars.get("m65_dpi", [])
            active_seen = False
            for stage, values in zip(profile.dpi, dpi_vars):
                stage.x = int(values["x"].get())
                stage.y = int(values["y"].get())
                stage.color = values["color"].get().strip()
                requested_active = bool(values["active"].get())
                stage.active = requested_active and not active_seen
                active_seen = active_seen or stage.active
        elif profile.target_device == "virtuoso-se":
            audio_vars = self.editor_vars.get("virtuoso_audio", [])
            active_seen = False
            for preset, values in zip(profile.audio, audio_vars):
                bands = [int(band.get()) for band in values["bands"]]
                profile_bands = [max(-12, min(12, value)) for value in bands[:10]]
                preset.bands = profile_bands
                preset.bass = round(sum(profile_bands[:3]) / 3)
                preset.mids = round(sum(profile_bands[3:7]) / 4)
                preset.treble = round(sum(profile_bands[7:]) / 3)
                requested_active = bool(values["active"].get())
                preset.active = requested_active and not active_seen
                active_seen = active_seen or preset.active
            controls = self.editor_vars.get("virtuoso_controls", {})
            if profile.lighting:
                profile.lighting[0].color = controls["accent"].get().strip()
            profile.headset.sidetone = int(controls["sidetone"].get())
            profile.headset.mic_level = int(controls["mic"].get())
            profile.headset.sleep_timer_minutes = int(controls["sleep"].get())
            profile.headset.voice_prompt_enabled = bool(controls["prompt"].get())
        return True

    def save_selected_profile(self) -> None:
        if not self._apply_editor_to_current_profile():
            return

        profile = self.current_profile
        if profile is None:
            return

        saved_path = self.service.save_profile(profile)
        self._show_profile(profile.name)
        self.refresh_profiles()
        self.profile_list.selection_set(profile.name)
        self.profile_list.focus(profile.name)
        self.status_text.set(f"Saved profile {profile.name} to {saved_path}")

    def pick_color(self, variable: StringVar) -> None:
        color = colorchooser.askcolor(color=variable.get(), title="Choose accent color")
        if color and color[1]:
            variable.set(color[1])

    @staticmethod
    def _valid_color(value: str) -> str:
        if len(value) == 7 and value.startswith("#"):
            return value
        return "#ffffff"

    def duplicate_selected_profile(self) -> None:
        name = self._selected_profile_name()
        if not name:
            messagebox.showinfo("linuxcue", "Bitte zuerst ein Profil auswaehlen.")
            return
        new_name = simpledialog.askstring("Duplicate Profile", "New profile name:", initialvalue=f"{name}-copy", parent=self.root)
        if not new_name:
            return
        if not self.service.duplicate_profile(name, new_name.strip()):
            messagebox.showerror("linuxcue", "Profile could not be duplicated.")
            return
        self.refresh_profiles()
        self.profile_list.selection_set(new_name.strip())
        self._show_profile(new_name.strip())
        self.status_text.set(f"Duplicated profile to {new_name.strip()}")

    def rename_selected_profile(self) -> None:
        name = self._selected_profile_name()
        if not name:
            messagebox.showinfo("linuxcue", "Bitte zuerst ein Profil auswaehlen.")
            return
        new_name = simpledialog.askstring("Rename Profile", "New profile name:", initialvalue=name, parent=self.root)
        if not new_name or new_name.strip() == name:
            return
        if not self.service.rename_profile(name, new_name.strip()):
            messagebox.showerror("linuxcue", "Profile could not be renamed.")
            return
        self.refresh_profiles()
        self.profile_list.selection_set(new_name.strip())
        self._show_profile(new_name.strip())
        self.status_text.set(f"Renamed profile to {new_name.strip()}")

    def delete_selected_profile(self) -> None:
        name = self._selected_profile_name()
        if not name:
            messagebox.showinfo("linuxcue", "Bitte zuerst ein Profil auswaehlen.")
            return
        if not messagebox.askyesno("Delete Profile", f"Delete profile '{name}'?", parent=self.root):
            return
        if not self.service.delete_profile(name):
            messagebox.showerror(
                "linuxcue",
                (
                    "Profile could not be deleted.\n\n"
                    f"Profile directory: {self.service.profile_root()}\n"
                    "If you started linuxcue with sudo before, the file may be owned by root."
                ),
            )
            return
        self.selected_profile.set("")
        self.current_profile = None
        self.refresh_profiles()
        self.summary_vars["name"].set("No profile selected")
        self.summary_vars["target"].set("Target: -")
        self.summary_vars["companion"].set("Companion: -")
        self.preview_box.delete("1.0", "end")
        self.profile_box.delete("1.0", "end")
        self.status_text.set(f"Deleted profile {name}")

    def write_selected_live(self) -> None:
        name = self._selected_profile_name()
        if not name:
            messagebox.showinfo("linuxcue", "Bitte zuerst ein Profil auswaehlen.")
            return
        if not self._apply_editor_to_current_profile():
            return
        self.status_text.set(f"Preparing live write for {name}...")
        self.root.update_idletasks()
        if self.current_profile is not None:
            self.service.save_profile(self.current_profile)
            profile = self.current_profile
        else:
            profile = self.service.load_profile(name)
        if profile is None:
            messagebox.showwarning("linuxcue", "Profil konnte nicht geladen werden.")
            return
        status = self.service.live_status(profile)
        if profile.target_device == "profile-set":
            members = self.service.profiles_in_group(profile.profile_group or profile.name)
            matching_count = sum(int(self.service.live_status(member)["matching_count"]) for member in members)
        else:
            matching_count = int(status["matching_count"])
        if matching_count == 0:
            messagebox.showwarning(
                "linuxcue",
                (
                    "Kein passendes Live-HID-Geraet fuer dieses Profil gefunden.\n\n"
                    "In VirtualBox muss das echte Corsair-USB-Geraet an die VM durchgereicht sein.\n"
                    "Nutze 'Refresh Devices' oder 'linuxcue doctor', um zu sehen, was erkannt wird."
                ),
            )
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", json.dumps(status, indent=2))
            self.status_text.set(f"No matching live device for {name}")
            return
        try:
            if profile.target_device == "profile-set":
                set_results = self.service.write_profile_set_live(name)
                result = set_results[0]
                set_payload = [
                    {
                        "profile": item.profile_name,
                        "device": item.device,
                        "packet_count": item.packet_count,
                        "message": item.message,
                    }
                    for item in set_results
                ]
            elif profile.target_device == "k95":
                result = self.service.write_k95_profile_live(name)
                set_payload = None
            elif profile.target_device == "m65":
                result = self.service.write_m65_profile_live(name)
                set_payload = None
            elif profile.target_device == "virtuoso-se":
                result = self.service.write_virtuoso_profile_live(name)
                set_payload = None
            else:
                raise RuntimeError("Live Write ist nur fuer gezielte Geraeteprofile verfuegbar.")
        except Exception as exc:
            messagebox.showerror("linuxcue", str(exc))
            self.status_text.set(f"Live write failed for {name}")
            return

        self.preview_box.delete("1.0", "end")
        self.preview_box.insert(
            "1.0",
            json.dumps(
                {
                    "profile": result.profile_name,
                    "device": result.device,
                    "packet_count": result.packet_count,
                    "message": result.message,
                    "profile_set_results": set_payload,
                    "note": (
                        "Live Write reached hidapi. Visible hardware changes are still experimental "
                        "until the real Corsair feature reports are mapped for this firmware."
                    ),
                },
                indent=2,
            ),
        )
        messagebox.showinfo(
            "linuxcue",
            (
                f"Live Write wurde fuer '{name}' ausgefuehrt.\n\n"
                "Hinweis: Sichtbare Effekte sind noch experimentell, weil die echten Corsair-Feature-Reports "
                "pro Firmware noch gemappt werden muessen."
            ),
        )
        self.status_text.set(f"Live write executed for {name}; hardware-visible effect is experimental")

    @staticmethod
    def _legacy_eq_bands(preset) -> list[int]:
        return [
            preset.bass,
            preset.bass,
            round((preset.bass + preset.mids) / 2),
            preset.mids,
            preset.mids,
            preset.mids,
            round((preset.mids + preset.treble) / 2),
            preset.treble,
            preset.treble,
            preset.treble,
        ]


def launch_gui() -> None:
    if TK_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Tkinter/Tcl-Tk is missing or broken. On CachyOS install it with: "
            "sudo pacman -S --needed tk tcl"
        ) from TK_IMPORT_ERROR
    try:
        root = Tk()
    except Exception as exc:
        raise RuntimeError(
            "Tkinter GUI could not be started in this environment. "
            "If libtk is missing, run: sudo pacman -S --needed tk tcl"
        ) from exc
    app = LinuxCueGui(root)
    if app.profile_list.get_children():
        first = app.profile_list.get_children()[0]
        app.profile_list.selection_set(first)
        app.profile_list.focus(first)
        app._show_profile(first)
    root.mainloop()


def main() -> int:
    try:
        launch_gui()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
