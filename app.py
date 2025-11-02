import tkinter as tk
from repo_json import JSONRepo
from ui.dashboard import Dashboard
from ui.create_habit import CreateHabit

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Habit Hatchery")
        self.geometry("520x460")
        self.repo = JSONRepo("data/habits.json")

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (Dashboard, CreateHabit):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show("Dashboard")

    def show(self, name):
        frame = self.frames[name]
        if hasattr(frame, "refresh"):
            frame.refresh()
        frame.tkraise()

if __name__ == "__main__":
    App().mainloop()