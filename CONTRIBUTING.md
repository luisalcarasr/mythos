# Contributing to Mythos

Thank you for your interest in contributing to Mythos!

---

## Prerequisites

### System dependencies

#### Fedora (this project is developed in a Fedora Toolbx container)
```bash
sudo dnf install rust cargo scdoc make git \
                 gtk4-devel libadwaita-devel gobject-introspection-devel
```

#### Arch Linux / Manjaro
```bash
sudo pacman -S rust cargo scdoc make git \
               gtk4 libadwaita gobject-introspection
```

#### macOS (Homebrew)
```bash
brew install pygobject3 gtk4 libadwaita pkg-config gobject-introspection
xcode-select --install
```

#### Debian / Ubuntu
```bash
sudo apt install cargo scdoc make git \
                 gir1.2-gtk-4.0 gir1.2-adw-1 gobject-introspection
```

---

## Setup

### 1. Install uv

[**uv**](https://docs.astral.sh/uv/) is the project's dependency manager:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/mythos.git
cd mythos
uv sync
```

This will:
- Create a virtual environment
- Install Python packages (legendary-gl, pygobject, etc.)
- Clone and build `umu-launcher` from GitHub (requires Rust + scdoc)

### 3. Run

```bash
# With fake adapters (no Epic account required)
uv run python -m mythos --fake

# Production mode
uv run python -m mythos
```

---

## Development

### Tests

```bash
uv run pytest
```

### Auto-reload

```bash
uv run python -m mythos.dev.watcher --fake
```

### Code style

- PEP 8, type hints for all function signatures
- Domain layer: pure Python, no I/O, no external deps
- Unit tests for new use cases

### Commits

[Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add cloud save sync for offline games
fix: prevent crash when cover image fails to load
docs: update installation instructions
refactor: extract wine runner selection to use case
test: add unit tests for LaunchGame use case
```

---

## Architecture

```
[GTK4/Adwaita]   driving adapter    adapters/input/gtk/
       ↓
[Use Cases]      application        application/
       ↓
[Domain]         pure Python        domain/
       ↑
[Ports]          ABC interfaces     ports/
       ↑
[Legendary]      driven adapter     adapters/output/legendary/
[umu-launcher]                       adapters/output/umu/
[Storage]                            adapters/output/storage/
```

Key principles:
- Domain has **zero imports** from GTK, Legendary, or any I/O library
- All external interactions go through **ports** (abstract interfaces)
- Adapters can be swapped without touching domain/application code
- Tests use **fake adapters** (in-memory implementations)

### Project structure

```
mythos/
├── domain/              Pure domain logic
├── ports/               Input/output port interfaces
├── application/         Use cases (orchestration)
├── adapters/
│   ├── input/gtk/       GTK4 UI (driving adapter)
│   └── output/          Driven adapters (legendary, umu, storage, fakes)
└── config/              DI container, paths, i18n
tests/
├── unit/                Domain + use-case tests
├── fakes/               In-memory fake adapters
└── integration/         Real-adapter tests (opt-in)
```

---

## Troubleshooting

### `umu-launcher` build fails

Ensure native build tools:
```bash
# Fedora
sudo dnf install rust cargo scdoc make git

# Arch
sudo pacman -S rust cargo scdoc make git

# Debian/Ubuntu
sudo apt install cargo scdoc make git
```

### GTK warnings in console

Harmless GTK4/libadwaita warnings can be ignored.

### `ModuleNotFoundError: gi`

Run `uv sync` and ensure system GTK4 libraries are installed.

---

## Questions?

Open an issue or discussion on GitHub.
