# Mythos

**Mythos** is a free, open-source Epic Games launcher built with Python and GTK4.

It follows a strict **hexagonal architecture** (ports and adapters): the domain and
use-case layers are completely independent of GTK and Legendary so they can be
tested without any system libraries installed.

> Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
> License: GNU General Public License v3 — see [COPYING](COPYING)

---

## Features

- Login with your Epic Games account (OAuth via embedded WebView)
- Browse your full game library with cover art
- Install, update, repair, move and uninstall games
- Launch games natively (macOS / Linux) or via Wine / Proton (Linux)
- Download queue with real-time progress
- Cloud save synchronisation
- Wine / Proton runtime manager (Linux)
- Per-game launch options and environment variables
- App-wide settings (language, default install path, Wine runner…)
- Internationalisation — English and Spanish included

---

## Architecture

```
[GTK4/Adwaita]        driving adapter    adapters/input/gtk/
       ↓
[Use Cases]           application        application/
       ↓
[Domain]              pure Python        domain/
       ↑
[Ports]               ABC interfaces     ports/
       ↑
[Legendary adapter]   driven adapter     adapters/output/legendary/
[Wine adapter]                           adapters/output/wine/
[Storage adapter]                        adapters/output/storage/
```

The domain layer has **zero external dependencies** — no GTK, no Legendary, no I/O.
Every external interaction is behind a port (abstract interface) implemented by a
concrete adapter. Swapping Legendary for a different backend requires only writing a
new adapter that satisfies the same port contract.

---

## Requirements

### System libraries

```bash
# macOS (Homebrew)
brew install pygobject3 gtk4 libadwaita webkitgtk

# Fedora / RHEL
sudo dnf install python3-gobject gtk4 libadwaita webkit2gtk4.1

# Debian / Ubuntu
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-webkit-6.0
```

### Python packages

```bash
pip install legendary-gl platformdirs requests
# — or —
pip install -e ".[dev]"
```

---

## Running

```bash
python -m mythos
# — or, after pip install —
mythos
```

---

## Running tests

The unit and fake tests run without any GTK / Legendary installed:

```bash
pytest tests/unit tests/fakes
```

Integration tests (require Legendary installed and a valid Epic session):

```bash
pytest tests/integration -m integration
```

---

## Project layout

```
mythos/
├── domain/          Pure domain: entities, value objects, events, exceptions, services
├── ports/           Abstract interfaces (ports) — input and output
├── application/     Use cases that orchestrate domain + ports
├── adapters/
│   ├── input/gtk/   GTK4 / Adwaita UI (driving adapter)
│   └── output/      Legendary, Wine, storage, subprocess, event bus (driven adapters)
└── config/          Composition root, XDG paths, i18n
tests/
├── unit/            Domain + use-case tests (no system deps)
├── fakes/           In-memory fake adapters for testing
└── integration/     Real-adapter tests (marked, opt-in)
```
