# Habit Hatchery
A cozy, farmhouse-themed habit tracker with a Tkinter UI and ZeroMQ microservices for analytics.

## Prerequisites
- Python 3.10+ recommended
- Dependencies: `pip install pyzmq pillow` (Pillow enables background image scaling; the app still runs without it)

## Project layout
- `app.py` — Tk entry point with Start Screen, Hatchery (dashboard), Create Habit, and Analytics.
- `ui/` — All Tkinter UI frames and shared theming.
- `microservices/` — Independent ZeroMQ services:
  - `streaks_service.py` (port 5555)
  - `trend-analyzer.py` (port 5560)
  - `activity-analyzer.py` (port 5562)
  - `progress-tracker.py` (port 5564)
- `data/habits.json` — Local JSON storage (auto-created).

## Running the app
1) Start each microservice in its own terminal (from `habit_hatchery/`):
   - `python microservices/streaks_service.py 5555`
   - `python microservices/trend-analyzer.py 5560`
   - `python microservices/activity-analyzer.py 5562`
   - `python microservices/progress-tracker.py 5564`
2) Launch the UI:
   - `python app.py`
3) Flow:
   - Start Screen → enter Hatchery (dashboard)
   - Create habits, mark completions, then open Analytics to see streaks, progress, activity, and weekly trends.

## Notes
- If Pillow is installed, background images scale with the window; otherwise they load at native size.
- Data is persisted to `data/habits.json`; delete the file to reset.
- All microservice ports can be changed via CLI args or env vars in their respective scripts if needed.
