# ui/dashboard.py
import tkinter as tk
from datetime import date

class Dashboard(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Habit Hatchery", font=("Segoe UI", 16, "bold")).pack(pady=6)
        # IH#1: benefits (tell why)
        tk.Label(self, text="Complete a habit to feed your creature and help it grow.")
        tk.Label(self, text="").pack()  # spacing

        top = tk.Frame(self); top.pack(fill="x", padx=10)
        tk.Button(top, text="➕ Create Habit", command=lambda: controller.show("CreateHabit")).pack(side="left")
        self.creature = tk.Label(top, text="🐣", font=("Segoe UI Emoji", 20))
        self.creature.pack(side="right")

        self.list_frame = tk.Frame(self); self.list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        # IH#6: explicit path hint
        self.hint = tk.Label(self, text="1) Pick a habit  2) Press Complete (Enter/Space works)  3) See feedback")
        self.hint.pack(pady=(0,8))

        # Keyboard support (Usability)
        self.bind_all("<Return>", self._activate_focused)
        self.bind_all("<space>", self._activate_focused)

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        repo = self.controller.repo
        today = date.today()
        habits = repo.habits_for_today(today)
        completed = repo.completed_ids(today)

        if not habits:
            tk.Label(self.list_frame, text="No habits yet. Click “Create Habit”.").pack(anchor="w")
            return

        for h in habits:
            row = tk.Frame(self.list_frame); row.pack(fill="x", pady=4)
            btn = tk.Button(row, text=("✓ Completed" if h.id in completed else "Complete"))
            btn.configure(width=12)
            btn["command"] = lambda b=btn, hid=h.id: self.toggle(b, hid)
            btn.pack(side="left")
            btn.configure(takefocus=True)

            tk.Label(row, text=h.name, anchor="w").pack(side="left", padx=10)

    def toggle(self, button: tk.Button, habit_id: int):
        # Toggle completion + quick feedback (<1s)
        today = date.today()
        repo = self.controller.repo
        done = (button["text"] != "✓ Completed")
        repo.set_completed(habit_id, today, done)
        button.configure(text=("✓ Completed" if done else "Complete"))

        self.creature.configure(text="✨🐣✨")
        self.after(300, lambda: self.creature.configure(text="🐣"))

    def _activate_focused(self, event):
        w = self.focus_get()
        if isinstance(w, tk.Button) and w["text"] in ("Complete", "✓ Completed"):
            w.invoke()
