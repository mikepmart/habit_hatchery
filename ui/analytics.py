import tkinter as tk

from microservice_clients import gather_microservice_snapshot
from ui import theme


class Analytics(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=theme.BG)
        self.controller = controller

        header = theme.card(self)
        header.pack(fill="x", padx=16, pady=(14, 10))
        head_row = tk.Frame(header, bg=theme.CARD_BG)
        head_row.pack(fill="x", padx=14, pady=12)
        theme.heading_label(head_row, "Analytics", theme.TITLE).pack(anchor="w")
        theme.muted_label(
            head_row,
            "Live insights from the microservices: progress, streaks, activity, and trends.",
            wrap=740,
        ).pack(anchor="w", pady=(4, 0))

        buttons = tk.Frame(header, bg=theme.CARD_BG)
        buttons.pack(fill="x", padx=14, pady=(6, 6))
        theme.primary_button(buttons, "Refresh", self.refresh).pack(side="left")
        theme.ghost_button(
            buttons, "Back to Hatchery", lambda: controller.show("Hatchery")
        ).pack(side="left", padx=8)

        self.progress_var = self._section("Today's Progress")
        self.streaks_var = self._section("Streaks by Habit")
        self.activity_var = self._section("Activity Analyzer")
        self.trend_var = self._section("Trends (per week)")

    def _section(self, title: str):
        frame = theme.card(self)
        frame.pack(fill="x", padx=16, pady=8)
        tk.Label(
            frame, text=title, font=theme.HEADING, bg=theme.CARD_BG, fg=theme.TEXT
        ).pack(anchor="w", padx=12, pady=(10, 0))
        var = tk.StringVar()
        tk.Label(
            frame,
            textvariable=var,
            anchor="w",
            justify="left",
            wraplength=780,
            bg=theme.CARD_BG,
            fg=theme.TEXT,
            font=theme.BODY,
        ).pack(fill="x", padx=12, pady=8)
        return var

    def refresh(self):
        data = gather_microservice_snapshot(self.controller.repo)
        self.progress_var.set(self._render_progress(data["progress"]))
        self.streaks_var.set(self._render_streaks(data["streaks"]))
        self.activity_var.set(self._render_activity(data["activity"]))
        self.trend_var.set(self._render_trend(data["trend"]))

    # ---------- Render helpers ----------
    def _render_progress(self, progress: dict) -> str:
        error = progress.get("error")
        resp = progress.get("response")
        if error:
            return f"Progress service unavailable: {error}"
        if not resp:
            return "No progress data yet."

        single = resp.get("single_goal") or {}
        percent = single.get("percent_complete", 0)
        current = single.get("current", 0)
        target = single.get("target", 0)
        status = single.get("status", "unknown")
        lines = [
            f"Today: {percent}% ({current}/{target}) - status: {status}",
        ]

        goals = resp.get("goals_summary") or []
        if goals:
            parts = []
            for goal in goals:
                name = goal.get("label") or f"Habit {goal.get('id', '')}".strip()
                pct = goal.get("percent_complete", 0)
                cur = goal.get("current", 0)
                tgt = goal.get("target", 0)
                parts.append(f"{name}: {pct}% ({cur}/{tgt})")
            lines.append("Per habit: " + "; ".join(parts))

        return "\n".join(lines)

    def _render_streaks(self, streaks: dict) -> str:
        entries = streaks.get("entries") or []
        if not entries:
            return "No habits yet."

        lines = []
        for entry in entries:
            habit = entry["habit"]
            if entry["error"]:
                lines.append(f"{habit.name}: {entry['error']}")
            elif entry["result"]:
                current = entry["result"].get("current_streak", 0)
                longest = entry["result"].get("longest_streak", 0)
                lines.append(f"{habit.name}: current {current}, longest {longest}")
            else:
                lines.append(f"{habit.name}: No completions yet.")
        return "\n".join(lines)

    def _render_activity(self, activity: dict) -> str:
        error = activity.get("error")
        resp = activity.get("response")
        if error:
            return f"Activity analyzer unavailable: {error}"
        if not resp:
            return "No completion history yet."

        longest = resp.get("longest_run") or {}
        length = longest.get("length_days", 0)
        if length:
            run_line = f"Longest active run: {length} day(s)"
            if longest.get("start_date") and longest.get("end_date"):
                run_line += f" ({longest['start_date']} to {longest['end_date']})"
        else:
            run_line = "Longest active run: none yet."

        heatmap = resp.get("heatmap") or {}
        if heatmap:
            completed_days = sum(1 for _, count in heatmap.items() if count)
            total_events = sum(heatmap.values())
            heat_line = (
                f"Last 14 days: {total_events} completion(s) "
                f"across {completed_days} day(s)."
            )
        else:
            heat_line = "Heatmap: no data yet."

        return "\n".join([run_line, heat_line])

    def _render_trend(self, trend: dict) -> str:
        error = trend.get("error")
        resp = trend.get("response")
        if error:
            return f"Trend analyzer unavailable: {error}"
        if not resp:
            return "No trend data yet."

        bucket_type = resp.get("bucket_type", "week")
        buckets = resp.get("buckets") or {}
        if not buckets:
            return "No completions to chart yet."

        # Sort buckets chronologically by key
        lines = [f"Bucket type: {bucket_type}"]
        for key in sorted(buckets.keys()):
            lines.append(f"{key}: {buckets[key]} completion(s)")
        return "\n".join(lines)
