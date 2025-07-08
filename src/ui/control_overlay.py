from typing import Any, Callable, Optional

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class ControlOverlay(FloatLayout):
    is_muted = BooleanProperty(False)
    is_paused = BooleanProperty(False)
    overlay_opacity = NumericProperty(0.0)

    def __init__(
        self,
        on_mute: Optional[Callable] = None,
        on_pause: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        super(ControlOverlay, self).__init__(**kwargs)

        # Initialize callbacks
        self.on_mute_callback = on_mute
        self.on_pause_callback = on_pause

        # Setup dark overlay background
        with self.canvas.before:
            self.overlay_color = Color(0, 0, 0, 0)
            self.overlay_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(size=self._update_overlay, pos=self._update_overlay)
        self.bind(overlay_opacity=self._update_overlay_color)

        # Create control button
        self.control_button = Button(
            text="MUTE",
            size_hint=(None, None),
            size=(70, 70),
            pos_hint={"right": 0.98, "y": 0.02},
            background_color=(0.1, 0.1, 0.1, 0.9),
            color=(1, 1, 1, 1),
            font_size=14,
        )
        self.control_button.bind(on_press=self._on_control_press)
        self.add_widget(self.control_button)

        # Create pause button
        self.pause_button = Button(
            text="||",
            size_hint=(None, None),
            size=(70, 70),
            pos_hint={"x": 0.02, "y": 0.02},
            background_color=(0.1, 0.1, 0.1, 0.9),
            color=(1, 1, 1, 1),
            font_size=20,
        )
        self.pause_button.bind(on_press=self._on_pause_press)
        self.add_widget(self.pause_button)

        # Create center status icon
        self.status_icon = Label(
            text="",
            font_size=80,
            size_hint=(None, None),
            size=(120, 120),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            opacity=0.0,
        )
        self.add_widget(self.status_icon)

    def _update_overlay(self, *args) -> None:
        """Update overlay rectangle size and position."""
        self.overlay_rect.pos = self.pos
        self.overlay_rect.size = self.size

    def _update_overlay_color(self, *args) -> None:
        """Update overlay color opacity."""
        self.overlay_color.a = self.overlay_opacity

    def _on_control_press(self, button: Button) -> None:
        """Handle mute button press."""
        # Check current state and respond appropriately
        if self.is_paused:
            self._unpause()
        else:
            self._toggle_mute()

    def _on_pause_press(self, button: Button) -> None:
        """Handle pause button press."""
        # Toggle pause state
        if self.is_paused:
            self._unpause()
        else:
            self._pause()

    def _toggle_mute(self) -> None:
        """Toggle mute state."""
        # Switch between muted and unmuted
        if self.is_muted:
            self._unmute()
        else:
            self._mute()

    def _mute(self) -> None:
        """Enter muted state."""
        # Update state flags
        self.is_muted = True
        self.is_paused = False

        # Update button text
        self.control_button.text = "UNMUTE"

        # Show overlay with mute status
        self.status_icon.text = "MUTE"
        self._show_overlay()

        # Trigger callback
        if self.on_mute_callback:
            self.on_mute_callback(True)

    def _unmute(self) -> None:
        """Exit muted state."""
        # Update state flags
        self.is_muted = False

        # Reset button text
        self.control_button.text = "MUTE"

        # Hide overlay
        self._hide_overlay()

        # Trigger callback
        if self.on_mute_callback:
            self.on_mute_callback(False)

    def _pause(self) -> None:
        """Enter paused state."""
        # Update state flags
        self.is_paused = True
        self.is_muted = False

        # Update button text
        self.control_button.text = "UNMUTE"
        self.pause_button.text = ">"

        # Show overlay with pause status
        self.status_icon.text = "PAUSED"
        self._show_overlay()

        # Trigger callback
        if self.on_pause_callback:
            self.on_pause_callback(True)

    def _unpause(self) -> None:
        """Exit paused state."""
        # Update state flags
        self.is_paused = False

        # Reset button text
        self.control_button.text = "MUTE"
        self.pause_button.text = "||"

        # Hide overlay
        self._hide_overlay()

        # Trigger callback
        if self.on_pause_callback:
            self.on_pause_callback(False)

    def _show_overlay(self) -> None:
        """Show dark overlay with animation."""
        # Animate overlay appearance
        overlay_anim = Animation(
            overlay_opacity=0.6, duration=0.3, transition="out_quad"
        )
        overlay_anim.start(self)

        # Animate status icon appearance
        icon_anim = Animation(opacity=1.0, duration=0.3, transition="out_quad")
        icon_anim.start(self.status_icon)

    def _hide_overlay(self) -> None:
        """Hide overlay with animation."""
        # Animate overlay disappearance
        overlay_anim = Animation(
            overlay_opacity=0.0, duration=0.3, transition="in_quad"
        )
        overlay_anim.start(self)

        # Animate status icon disappearance
        icon_anim = Animation(opacity=0.0, duration=0.3, transition="in_quad")
        icon_anim.start(self.status_icon)

    def force_reset(self) -> None:
        """Force reset to default state."""
        # Reset all state flags
        self.is_muted = False
        self.is_paused = False

        # Reset button text
        self.control_button.text = "MUTE"
        self.pause_button.text = "||"

        # Hide overlay
        self._hide_overlay()
