# ui/create_habit.py
import tkinter as tk
from tkinter import ttk

from ui import theme

try:
    from PIL import Image, ImageTk  # type: ignore
except Exception:  # pragma: no cover
    Image = None
    ImageTk = None


class CreateHabit(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=theme.BG)
        self.controller = controller
        self.bg_raw = None
        self.bg_photo = None
        self.bg_label = None

        # Background image for this screen
        if Image and ImageTk:
            try:
                self.bg_raw = Image.open("images/new_habit.png")
                self.bg_label = tk.Label(self, bd=0)
                self.bg_label.place(relwidth=1, relheight=1)
                self.bind("<Configure>", self._resize_bg)
            except Exception:
                pass
        else:
            try:
                self.bg_photo = tk.PhotoImage(file="images/new_habit.png")
                self.bg_label = tk.Label(self, image=self.bg_photo, bd=0)
                self.bg_label.place(relwidth=1, relheight=1)
            except tk.TclError:
                self.configure(bg=theme.BG)

        wrapper = theme.card(self, glass=True)
        wrapper.pack(fill="x", padx=16, pady=18)

        header = tk.Frame(wrapper, bg=wrapper.cget("bg"))
        header.pack(fill="x", padx=14, pady=(12, 2))
        theme.heading_label(header, "Create Habit", theme.TITLE).pack(anchor="w")
        theme.muted_label(
            header,
            "Pick a name and schedule. You can edit completion from the dashboard.",
            wrap=720,
        ).pack(anchor="w", pady=(4, 0))

        form = tk.Frame(wrapper, bg=wrapper.cget("bg"))
        form.pack(padx=14, pady=10, fill="x")
        tk.Label(
            form, text="Name", bg=wrapper.cget("bg"), fg=theme.TEXT, font=theme.BODY
        ).grid(row=0, column=0, sticky="w", pady=4)
        self.name = tk.Entry(
            form,
            bg="#f8fafc",
            fg=theme.TEXT,
            relief="solid",
            bd=1,
            highlightbackground=theme.BORDER,
            highlightcolor=theme.ACCENT,
            font=theme.BODY,
        )
        self.name.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        form.columnconfigure(1, weight=1)

        tk.Label(
            form, text="Schedule", bg=wrapper.cget("bg"), fg=theme.TEXT, font=theme.BODY
        ).grid(row=1, column=0, sticky="w", pady=4)
        self.schedule = ttk.Combobox(
            form,
            values=[
                "daily",
                "weekly:Mon,Wed,Fri",
                "weekly:Tue,Thu",
                "weekly:Sat,Sun",
            ],
            font=theme.BODY,
        )
        ttk.Style().configure(
            "Clean.TCombobox",
            fieldbackground="#f8fafc",
            background="#f8fafc",
            relief="flat",
        )
        self.schedule.configure(style="Clean.TCombobox")
        self.schedule.set("daily")
        self.schedule.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        theme.muted_label(
            wrapper,
            "Takes ~10 seconds. Required: name + schedule. Press Enter to save.",
            wrap=720,
        ).pack(anchor="w", padx=14, pady=(4, 10))

        controls = tk.Frame(wrapper, bg=wrapper.cget("bg"))
        controls.pack(fill="x", padx=14, pady=(0, 14))
        theme.primary_button(controls, "Save", self.save).pack(side="left")
        theme.ghost_button(
            controls, "Back to Hatchery", lambda: controller.show("Hatchery")
        ).pack(side="left", padx=8)

        self.bind_all("<Return>", lambda e: self.save())

    def _resize_bg(self, event):
        if not (self.bg_raw and ImageTk and event.width and event.height):
            return
        resized = self.bg_raw.resize((event.width, event.height), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized)
        if self.bg_label:
            self.bg_label.configure(image=self.bg_photo)

    def save(self):
        name = self.name.get().strip()
        sched = self.schedule.get().strip() or "daily"
        if not name:
            return
        self.controller.repo.add_habit(name, sched)
        self.name.delete(0, "end")
        self.controller.show("Hatchery")
