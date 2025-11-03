# ui/dashboard.py
import tkinter as tk
from datetime import date

HILITE_BG = "#e8f1ff"   # light highlight color

class Dashboard(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Habit Hatchery", font=("Segoe UI", 16, "bold")).pack(pady=6)
        tk.Label(self, text="Complete a habit to feed your creature and help it grow.").pack()  # IH#1 benefits
        tk.Label(self, text="").pack()  # spacing

        top = tk.Frame(self); top.pack(fill="x", padx=10)
        tk.Button(top, text="➕ Create Habit", command=lambda: controller.show("CreateHabit")).pack(side="left")
        self.creature = tk.Label(top, text="🐣", font=("Segoe UI Emoji", 20))
        self.creature.pack(side="right")

        self.list_frame = tk.Frame(self); self.list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        # IH#6 explicit path hint
        self.hint = tk.Label(self, text="1) Select a habit (click or ↑/↓)  2) Press Enter/Space to Complete  3) See feedback")
        self.hint.pack(pady=(0,8))

        # keep runtime state
        self.rows = []             # list of dicts: {"frame":..., "btn":..., "id":...}
        self.selected_idx = None   # int index into self.rows

        # Global keybindings for selection & action
        self.bind_all("<Up>", self._move_up)
        self.bind_all("<Down>", self._move_down)
        self.bind_all("<Return>", self._activate_selected)
        self.bind_all("<space>", self._activate_selected)

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.rows.clear()
        self.selected_idx = None

        repo = self.controller.repo
        today = date.today()
        habits = repo.habits_for_today(today)
        completed = repo.completed_ids(today)

        if not habits:
            tk.Label(self.list_frame, text="No habits yet. Click “Create Habit”.").pack(anchor="w")
            return

        for i, h in enumerate(habits):
            row = tk.Frame(self.list_frame, highlightthickness=1, highlightbackground="#ddd")
            row.pack(fill="x", pady=4)

            # Complete/Undo button
            btn = tk.Button(row, text=("✓ Completed" if h.id in completed else "Complete"), width=12)
            btn["command"] = lambda b=btn, hid=h.id: self.toggle(b, hid)
            btn.pack(side="left")
            btn.configure(takefocus=False)  # selection is on the row, not the button

            # Clickable name that selects the row
            name = tk.Label(row, text=h.name, anchor="w")
            name.pack(side="left", padx=10, fill="x")

            # Make the whole row clickable/selectable
            def bind_select(widget, idx=i):
                widget.bind("<Button-1>", lambda e, j=idx: self._select_row(j))
            bind_select(row); bind_select(btn); bind_select(name)

            # Store row parts
            self.rows.append({"frame": row, "btn": btn, "id": h.id})

        # Auto-select first row for convenience
        self._select_row(0)

    # ---------- Selection helpers ----------
    def _clear_highlights(self):
        for r in self.rows:
            r["frame"].configure(bg=self.cget("bg"))

    def _select_row(self, idx: int):
        if not self.rows: return
        idx = max(0, min(idx, len(self.rows)-1))
        self.selected_idx = idx
        self._clear_highlights()
        self.rows[idx]["frame"].configure(bg=HILITE_BG)
        # ensure row gets focus (so ↑/↓ work immediately)
        self.rows[idx]["frame"].focus_set()

    def _move_up(self, _event=None):
        if self.selected_idx is None: return
        self._select_row(self.selected_idx - 1)

    def _move_down(self, _event=None):
        if self.selected_idx is None: return
        self._select_row(self.selected_idx + 1)

    def _activate_selected(self, _event=None):
        """Enter/Space toggles the selected row's habit."""
        if self.selected_idx is None: return
        row = self.rows[self.selected_idx]
        self.toggle(row["btn"], row["id"])

    # ---------- Completion toggle ----------
    def toggle(self, button: tk.Button, habit_id: int):
        today = date.today()
        repo = self.controller.repo
        done = (button["text"] != "✓ Completed")
        repo.set_completed(habit_id, today, done)
        button.configure(text=("✓ Completed" if done else "Complete"))

        # quick feedback (<1s)
        self.creature.configure(text="✨🐣✨")
        self.after(300, lambda: self.creature.configure(text="🐣"))