# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
LoginView — Epic Games OAuth login using WebKitGTK.

Flow:
  1. Open the Epic authorisation URL in a WebKitGTK WebView.
  2. Watch for a redirect to the Heroic / EGL redirect URI that contains
     the ``code`` query parameter.
  3. Extract the code and call ``LoginUseCase.execute(code)``.
  4. Invoke *on_login* callback with the session dict.

WebKitGTK may not be available on all systems.  If the import fails,
a fallback text-entry view is shown instead.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable
from urllib.parse import parse_qs, urlparse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from mythos.config.container import Container  # noqa: E402

logger = logging.getLogger(__name__)

# Derive auth URL from Legendary's own EGCAPI to stay in sync
def _get_epic_auth_url() -> str:
    from legendary.api.egs import EPCAPI
    return EPCAPI().get_auth_url()

_REDIRECT_HOST = "www.epicgames.com"
_REDIRECT_PATH = "/id/api/redirect"


def _try_webkit() -> bool:
    try:
        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit  # noqa: F401
        return True
    except Exception:
        try:
            gi.require_version("WebKit2", "4.1")
            from gi.repository import WebKit2  # noqa: F401
            return True
        except Exception:
            return False


class LoginView(Gtk.Box):
    """
    Handles Epic Games login.

    Uses WebKitGTK when available; falls back to a manual code-entry
    form otherwise (useful on minimal installations).
    """

    def __init__(
        self,
        container: Container,
        on_login: Callable[[dict], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._c = container
        self._on_login = on_login

        if _try_webkit():
            self._build_webkit()
        else:
            self._build_fallback()

    # ---------------------------------------------------------------- #
    # WebKit view                                                        #
    # ---------------------------------------------------------------- #

    def _build_webkit(self) -> None:
        try:
            try:
                gi.require_version("WebKit", "6.0")
                from gi.repository import WebKit
                webview = WebKit.WebView()
            except Exception:
                gi.require_version("WebKit2", "4.1")
                from gi.repository import WebKit2 as WebKit
                webview = WebKit.WebView()

            webview.set_vexpand(True)
            webview.load_uri(_get_epic_auth_url())
            webview.connect("load-changed", self._on_load_changed)
            self.append(webview)
            logger.debug("LoginView: using WebKitGTK.")
        except Exception as exc:
            logger.warning("WebKit build failed (%s); using fallback.", exc)
            self._build_fallback()

    def _on_load_changed(self, webview: object, event: object) -> None:
        """Monitor navigation to catch the redirect with the auth code."""
        try:
            uri = webview.get_uri()  # type: ignore[attr-defined]
            if not uri:
                return
            parsed = urlparse(uri)
            if parsed.netloc == _REDIRECT_HOST and parsed.path == _REDIRECT_PATH:
                params = parse_qs(parsed.query)
                code = params.get("code", [None])[0]
                if code:
                    logger.info("Auth code captured via WebKit redirect.")
                    GLib.idle_add(self._do_login, code)
        except Exception as exc:
            logger.error("Error in _on_load_changed: %s", exc)

    # ---------------------------------------------------------------- #
    # Fallback: manual code entry                                        #
    # ---------------------------------------------------------------- #

    def _build_fallback(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(32)
        box.set_margin_bottom(32)
        box.set_margin_start(32)
        box.set_margin_end(32)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        # Icon
        icon = Gtk.Image.new_from_icon_name("avatar-default-symbolic")
        icon.set_pixel_size(64)
        box.append(icon)

        # Title
        title = Gtk.Label(label="Sign in to Epic Games")
        title.add_css_class("title-1")
        box.append(title)

        subtitle = Gtk.Label()
        subtitle.set_markup(
            "Open the link below in your browser and paste the authorisation code:"
        )
        subtitle.set_wrap(True)
        subtitle.set_max_width_chars(55)
        box.append(subtitle)

        # URL button
        url_btn = Gtk.LinkButton(uri=_get_epic_auth_url(), label="Open Epic Games login page")
        box.append(url_btn)

        # Code entry
        self._code_entry = Gtk.Entry()
        self._code_entry.set_placeholder_text("Paste authorisation code here…")
        self._code_entry.set_hexpand(True)
        self._code_entry.connect("activate", self._on_code_entered)
        box.append(self._code_entry)

        # Login button
        btn = Gtk.Button(label="Sign in")
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.connect("clicked", self._on_code_entered)
        box.append(btn)

        # Status label
        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("error")
        box.append(self._status_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(box)
        scrolled.set_vexpand(True)
        self.append(scrolled)

        logger.debug("LoginView: using fallback code-entry form.")

    def _on_code_entered(self, widget: object) -> None:
        code = self._code_entry.get_text().strip()
        if not code:
            self._status_label.set_text("Please enter the authorisation code.")
            return
        self._do_login(code)

    # ---------------------------------------------------------------- #
    # Login execution                                                    #
    # ---------------------------------------------------------------- #

    def _do_login(self, code: str) -> bool:
        """
        Run the login use case in a background thread to avoid blocking
        the GTK main loop.
        """
        def _worker() -> None:
            try:
                session = self._c.login_use_case.execute(code)
                GLib.idle_add(self._on_success, session)
            except Exception as exc:
                GLib.idle_add(self._on_error, str(exc))

        threading.Thread(target=_worker, daemon=True, name="login-thread").start()
        return GLib.SOURCE_REMOVE

    def _on_success(self, session: dict) -> bool:
        logger.info("Login successful: %s", session.get("display_name"))
        self._on_login(session)
        return GLib.SOURCE_REMOVE

    def _on_error(self, message: str) -> bool:
        logger.error("Login failed: %s", message)
        if hasattr(self, "_status_label"):
            self._status_label.set_text(f"Login failed: {message}")
        return GLib.SOURCE_REMOVE
