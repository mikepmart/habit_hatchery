"""Shared visual style helpers for the Tk UI (warm farmhouse palette)."""

import tkinter as tk

# Palette (warm, storybook farmhouse)
BG = "#f8f1e7"
CARD_BG = "#fffaf3"
GLASS_BG = "#fff4e6"
BORDER = "#e3d6c8"
TEXT = "#2f241d"
MUTED = "#7a675b"
ACCENT = "#d48a52"       # warm copper
ACCENT_DARK = "#b26a39"
SUCCESS = "#6c8f52"      # muted sage
DANGER = "#b75c4a"       # clay red
HILITE = "#f3e2cf"       # pale parchment

# Typography
FONT_FAMILY = "Georgia"
TITLE = (FONT_FAMILY, 20, "bold")
SUBTITLE = (FONT_FAMILY, 12)
HEADING = (FONT_FAMILY, 13, "bold")
BODY = (FONT_FAMILY, 11)
BUTTON = (FONT_FAMILY, 10, "bold")


def card(parent, glass: bool = False, **kwargs):
    """Lightweight card frame with border."""
    bg_color = GLASS_BG if glass else CARD_BG
    return tk.Frame(
        parent,
        bg=bg_color,
        bd=0,
        highlightbackground=BORDER,
        highlightthickness=1,
        **kwargs,
    )


def heading_label(parent, text, font=TITLE):
    return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=TEXT, font=font)


def muted_label(parent, text, font=BODY, wrap=None):
    return tk.Label(
        parent,
        text=text,
        bg=parent.cget("bg"),
        fg=MUTED,
        font=font,
        justify="left",
        wraplength=wrap,
        anchor="w",
    )


def primary_button(parent, text, command):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=ACCENT,
        fg="#fffaf3",
        activebackground=ACCENT_DARK,
        activeforeground="#fffaf3",
        relief="flat",
        bd=0,
        font=BUTTON,
        padx=14,
        pady=8,
        cursor="hand2",
        highlightthickness=0,
    )
    return btn


def ghost_button(parent, text, command):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=CARD_BG,
        fg=ACCENT,
        activebackground=HILITE,
        activeforeground=ACCENT_DARK,
        relief="solid",
        bd=1,
        highlightbackground=ACCENT,
        font=BUTTON,
        padx=12,
        pady=7,
        cursor="hand2",
    )
    return btn


def pill(parent, text, fg=ACCENT, bg=HILITE):
    """Small tag-style label."""
    return tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=(FONT_FAMILY, 9, "bold"),
        padx=8,
        pady=2,
    )
