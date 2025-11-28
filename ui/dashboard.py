# ui/dashboard.py (Hatchery screen)
import tkinter as tk
from datetime import date
import tkinter.messagebox as mbox

from ui import theme

try:
    from PIL import Image, ImageTk  # type: ignore
except Exception:  # pragma: no cover
    Image = None
    ImageTk = None


class Hatchery(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=theme.BG)
        self.controller = controller
        self.bg_raw = None
        self.bg_photo = None
        self.bg_label = None

        # Background image (optional scaling)
        if Image and ImageTk:
            try:
                self.bg_raw = Image.open("images/hatchery.png")
                self.bg_label = tk.Label(self, bd=0)
                self.bg_label.place(relwidth=1, relheight=1)
                self.bind("<Configure>", self._resize_bg)
            except Exception:
                pass
        else:
            try:
                self.bg_photo = tk.PhotoImage(file="images/hatchery.png")
                self.bg_label = tk.Label(self, image=self.bg_photo, bd=0)
                self.bg_label.place(relwidth=1, relheight=1)
            except tk.TclError:
                self.configure(bg=theme.BG)

        main = theme.card(self, glass=True)
        main.pack(fill="both", expand=True, padx=16, pady=14)

        # Header
        header = tk.Frame(main, bg=main.cget("bg"))
        header.pack(fill="x", padx=12, pady=(12, 6))
        theme.heading_label(header, "Hatchery", theme.TITLE).pack(side="left", anchor="w")
        creature_box = tk.Frame(header, bg=main.cget("bg"))
        creature_box.pack(side="right")
        self.creature_face = tk.Label(
            creature_box,
            text="(・⊝・)",
            font=("Georgia", 18, "bold"),
            bg=main.cget("bg"),
            fg=theme.ACCENT,
        )
        self.creature_face.pack(anchor="e")
        self.creature_note = theme.muted_label(
            creature_box,
            "Waiting for a snack",
            wrap=220,
        )
        self.creature_note.pack(anchor="e")

        theme.muted_label(
            main,
            "Your daily habit dashboard. Select, complete, and manage habits.",
            wrap=700,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Controls row
        controls = tk.Frame(main, bg=main.cget("bg"))
        controls.pack(fill="x", padx=12, pady=(0, 10))
        theme.ghost_button(controls, "Start Screen", lambda: controller.show("StartScreen")).pack(
            side="left", padx=(0, 8)
        )
        theme.primary_button(controls, "Create Habit", lambda: controller.show("CreateHabit")).pack(
            side="left", padx=8
        )
        theme.ghost_button(controls, "Analytics", lambda: controller.show("Analytics")).pack(
            side="left", padx=8
        )

        # List container
        list_card = theme.card(main, glass=True)
        list_card.pack(fill="both", expand=True, padx=12, pady=(4, 6))
        self.list_container = list_card
        self.base_row_bg = list_card.cget("bg")

        theme.muted_label(
            list_card,
            "Click or use Up/Down to select. Enter/Space toggles completion. Delete removes the habit.",
            wrap=720,
        ).pack(anchor="w", pady=(0, 6))

        self.list_frame = tk.Frame(list_card, bg=list_card.cget("bg"))
        self.list_frame.pack(fill="both", expand=True)

        # keep runtime state
        self.rows = []  # list of dicts: {"frame":..., "btn":..., "id":..., "name":...}
        self.selected_idx = None  # int index into self.rows

        # Global keybindings for selection & action
        self.bind_all("<Up>", self._move_up)
        self.bind_all("<Down>", self._move_down)
        self.bind_all("<Return>", self._activate_selected)
        self.bind_all("<space>", self._activate_selected)
        self.bind_all("<Delete>", self._delete_selected)

    def _resize_bg(self, event):
        if not (self.bg_raw and ImageTk and event.width and event.height):
            return
        resized = self.bg_raw.resize((event.width, event.height), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized)
        if self.bg_label:
            self.bg_label.configure(image=self.bg_photo)

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.rows.clear()
        self.selected_idx = None

        repo = self.controller.repo
        today = date.today()
        habits = repo.habits_for_today(today)
        completed = repo.completed_ids(today)
        self._set_creature_state(False, "Waiting for a snack")

        if not habits:
            empty = theme.card(self.list_frame, glass=True)
            empty.pack(fill="x", pady=6, padx=2)
            tk.Label(
                empty,
                text="No habits yet.",
                font=theme.HEADING,
                bg=empty.cget("bg"),
                fg=theme.TEXT,
            ).pack(anchor="w", padx=12, pady=(10, 2))
            theme.muted_label(
                empty,
                "Create your first habit to start building streaks.",
                wrap=700,
            ).pack(anchor="w", padx=12, pady=(0, 12))
            return

        for i, h in enumerate(habits):
            row = tk.Frame(
                self.list_frame,
                bg=self.base_row_bg,
                highlightthickness=1,
                highlightbackground=theme.BORDER,
                padx=12,
                pady=10,
            )
            row.pack(fill="x", pady=6)

            btn_text = "Completed" if h.id in completed else "Complete"
            btn = tk.Button(
                row,
                text=btn_text,
                width=12,
                font=theme.BUTTON,
                bd=0,
                relief="flat",
                cursor="hand2",
            )
            btn["command"] = lambda b=btn, hid=h.id: self.toggle(b, hid)
            self._style_complete_button(btn, btn_text == "Completed")
            btn.pack(side="left")
            btn.configure(takefocus=False)

            name = tk.Label(
                row,
                text=h.name,
                anchor="w",
                bg=row.cget("bg"),
                fg=theme.TEXT,
                font=theme.SUBTITLE,
            )
            name.pack(side="left", padx=12, fill="x", expand=True)

            del_btn = tk.Button(
                row,
                text="Delete",
                width=8,
                font=theme.BUTTON,
                bg=theme.DANGER,
                fg="#ffffff",
                activebackground=theme.DANGER,
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                cursor="hand2",
            )
            del_btn["command"] = lambda hid=h.id: self._delete_habit(hid)
            del_btn.pack(side="right", padx=2)

            def bind_select(widget, idx=i):
                widget.bind("<Button-1>", lambda _e, j=idx: self._select_row(j))

            bind_select(row)
            bind_select(btn)
            bind_select(name)
            bind_select(del_btn)

            self.rows.append({"frame": row, "btn": btn, "id": h.id, "name": name})

        self._select_row(0)

    # ---------- Selection helpers ----------
    def _clear_highlights(self):
        for r in self.rows:
            r["frame"].configure(bg=self.base_row_bg, highlightbackground=theme.BORDER)
            r["name"].configure(bg=self.base_row_bg)

    def _select_row(self, idx: int):
        if not self.rows:
            return
        idx = max(0, min(idx, len(self.rows) - 1))
        self.selected_idx = idx
        self._clear_highlights()
        self.rows[idx]["frame"].configure(bg=theme.HILITE, highlightbackground=theme.ACCENT)
        self.rows[idx]["name"].configure(bg=theme.HILITE)
        self.rows[idx]["frame"].focus_set()

    def _move_up(self, _event=None):
        if self.selected_idx is None:
            return
        self._select_row(self.selected_idx - 1)

    def _move_down(self, _event=None):
        if self.selected_idx is None:
            return
        self._select_row(self.selected_idx + 1)

    def _activate_selected(self, _event=None):
        if self.selected_idx is None:
            return
        row = self.rows[self.selected_idx]
        self.toggle(row["btn"], row["id"])

    def _delete_habit(self, habit_id: int):
        if not mbox.askyesno(
            "Delete habit?",
            "Are you sure you want to delete this habit?\nThis removes today's completion too.",
        ):
            return
        self.controller.repo.delete_habit(habit_id)
        self.refresh()

    def _delete_selected(self, _event=None):
        if self.selected_idx is None or not self.rows:
            return
        hid = self.rows[self.selected_idx]["id"]
        self._delete_habit(hid)

    def _style_complete_button(self, button: tk.Button, done: bool):
        if done:
            button.configure(
                bg=theme.SUCCESS,
                fg="#fffaf3",
                activebackground=theme.SUCCESS,
                activeforeground="#fffaf3",
            )
        else:
            button.configure(
                bg=theme.ACCENT,
                fg="#fffaf3",
                activebackground=theme.ACCENT_DARK,
                activeforeground="#fffaf3",
            )

    # ---------- Completion toggle ----------
    def toggle(self, button: tk.Button, habit_id: int):
        today = date.today()
        repo = self.controller.repo

        will_complete = button["text"] != "Completed"
        repo.set_completed(habit_id, today, will_complete)

        button.configure(text=("Completed" if will_complete else "Complete"))
        self._style_complete_button(button, will_complete)

        if will_complete:
            self._set_creature_state(True, "It ate! Yum.")
            self.after(900, lambda: self._set_creature_state(False, "Ready for the next snack"))
        else:
            self._set_creature_state(False, "Waiting for a snack")

    # ---------- Creature feedback ----------
    def _set_creature_state(self, fed: bool, message: str):
        face = "(ᵔᴥᵔ)" if fed else "(・⊝・)"
        self.creature_face.configure(text=face, fg=theme.SUCCESS if fed else theme.ACCENT)
        self.creature_note.configure(text=message)
