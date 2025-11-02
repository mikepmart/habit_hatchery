# ui/create_habit.py
import tkinter as tk
from tkinter import ttk

class CreateHabit(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Create Habit", font=("Segoe UI", 16, "bold")).pack(pady=6)

        form = tk.Frame(self); form.pack(padx=12, pady=8, fill="x")
        tk.Label(form, text="Name").grid(row=0, column=0, sticky="w")
        self.name = tk.Entry(form); self.name.grid(row=0, column=1, sticky="ew", padx=6)
        form.columnconfigure(1, weight=1)

        tk.Label(form, text="Schedule").grid(row=1, column=0, sticky="w")
        self.schedule = ttk.Combobox(form, values=[
            "daily",
            "weekly:Mon,Wed,Fri",
            "weekly:Tue,Thu",
            "weekly:Sat,Sun"
        ])
        self.schedule.set("daily")
        self.schedule.grid(row=1, column=1, sticky="ew", padx=6, pady=4)

        # IH#2: costs (what’s required; time estimate)
        tk.Label(self, text="Takes ~10 seconds. Required: name + schedule.").pack(pady=(0,6))

        controls = tk.Frame(self); controls.pack()
        tk.Button(controls, text="Save", command=self.save).pack(side="left", padx=4)
        tk.Button(controls, text="Back to Dashboard", command=lambda: controller.show("Dashboard")).pack(side="left", padx=4)

        self.bind_all("<Return>", lambda e: self.save())

    def save(self):
        name = self.name.get().strip()
        sched = self.schedule.get().strip() or "daily"
        if not name:
            return
        self.controller.repo.add_habit(name, sched)
        self.name.delete(0, "end")
        self.controller.show("Dashboard")
