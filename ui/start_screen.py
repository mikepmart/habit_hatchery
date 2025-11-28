import tkinter as tk

from ui import theme

try:
    from PIL import Image, ImageTk  # type: ignore
except Exception:  # pragma: no cover - pillow may not be installed
    Image = None
    ImageTk = None


class StartScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=theme.BG)
        self.controller = controller
        self.bg_label = None
        self.bg_raw = None
        self.bg_photo = None

        # Background image layer with scaling if pillow is available
        if Image and ImageTk:
            try:
                self.bg_raw = Image.open("images/farmhouse.png")
                self.bg_label = tk.Label(self, bd=0)
                self.bg_label.place(relwidth=1, relheight=1)
                self.bind("<Configure>", self._resize_bg)
            except Exception:
                pass
        else:
            try:
                self.bg_photo = tk.PhotoImage(file="images/farmhouse.png")
                self.bg_label = tk.Label(self, image=self.bg_photo, bd=0)
                self.bg_label.place(relwidth=1, relheight=1)
            except tk.TclError:
                self.configure(bg=theme.BG)

        # Overlay card
        overlay = theme.card(
            self,
            glass=True,
            padx=22,
            pady=20,
        )
        overlay.place(relx=0.5, rely=0.5, anchor="center")

        theme.heading_label(overlay, "Welcome to Habit Hatchery", theme.TITLE).pack(
            anchor="center"
        )
        theme.muted_label(
            overlay,
            "Set your habits, grow your streaks, and keep your farmhouse routine thriving.",
            wrap=420,
        ).pack(anchor="center", pady=(6, 12))

        btns = tk.Frame(overlay, bg=theme.CARD_BG)
        btns.pack(pady=(6, 4))
        theme.primary_button(btns, "Enter Hatchery", lambda: controller.show("Hatchery")).pack(
            side="left", padx=6
        )
        theme.ghost_button(btns, "Create Habit", lambda: controller.show("CreateHabit")).pack(
            side="left", padx=6
        )
        theme.ghost_button(btns, "View Analytics", lambda: controller.show("Analytics")).pack(
            side="left", padx=6
        )

    def _resize_bg(self, event):
        if not (self.bg_raw and ImageTk and event.width and event.height):
            return
        resized = self.bg_raw.resize((event.width, event.height), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized)
        if self.bg_label:
            self.bg_label.configure(image=self.bg_photo)
