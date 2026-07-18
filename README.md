# Albion Helper

This project contains:
- a Python helper for screen-based resource detection;
- a Kivy UI with enable/disable controls and AI settings;
- a local database for learned data and training events;
- a Buildozer spec to build an Android APK.

## 1. Install dependencies
Run this in the project folder:
- python -m pip install -r requirements.txt

## 2. Start the assistant UI
Run:
- python ui_app.py

## 3. How to use the UI
After the window opens:
- Enter the target resource name, for example `wood`.
- Choose the database file, for example `assistant.db`.
- Optionally enter a remote URL and a video file path.
- Choose the AI mode: `local`, `remote`, or `video`.
- Enter the device preset, for example `poco_f5`.
- Press `Enable assistant` to start the helper.
- Press `Disable assistant` to stop it.
- Press `AI settings` to open the settings popup.
- Press `Train from remote/video` to register remote or video training input.

## 4. Run from terminal without UI
Use these commands:
- python app.py --resource wood
- python app.py --resource wood --device poco_f5
- python app.py --resource wood --db assistant.db --once

## 5. Useful command examples
- Start in loop mode:
  - python app.py --resource wood --device poco_f5
- Run one cycle only:
  - python app.py --resource wood --device poco_f5 --once
- Use a custom database file:
  - python app.py --resource wood --db my_assistant.db
- Use a custom config file:
  - python app.py --config albion_resources.json

## 6. Files created by the assistant
- `assistant.db` — local SQLite database with resources, events and learning samples.
- `agent_memory.db` — local memory for the decision engine.
- `assistant_settings.json` — saved UI settings.
- `training_history.json` — training events from remote/video sources.
- `screenshots/` — screenshots captured during runs.

## 7. Screen presets
- Poco F5 preset is available via `--device poco_f5`.
- It uses a default mobile-oriented profile for a 2712x1220 display.

## 8. Build Android APK
Run:
- buildozer -v android debug

> Note: full Android build requires Android SDK/NDK and a working environment. This workspace contains the project skeleton and code needed to build it.
