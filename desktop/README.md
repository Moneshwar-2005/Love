# LOVE Desktop Application

## Architecture Overview
The LOVE desktop application will be built using **Tauri** (Rust backend + React/TypeScript frontend).

### Key Planned Responsibilities:
- Native OS integration for Windows, macOS, and Linux.
- Global system hotkey registration (e.g. `Ctrl+Space` or `Alt+Space` quick-access palette).
- System tray minimization and background daemon execution.
- Native microphone capture for the "Hey Love" wake-word detection engine.
- Low-latency WebSocket client connecting to the LOVE backend.
- Desktop automation sidecar execution (window manipulation, screen inspection, local file access).

### Directory Structure (Planned for Future Phase):
```
desktop/
  src-tauri/
    Cargo.toml
    tauri.conf.json
    src/
      main.rs
      tray.rs
      hotkeys.rs
      audio.rs
  src/
    components/
    hooks/
    views/
```

*Note: Desktop development is scheduled for a subsequent phase after the intelligence and voice engines are established.*
