from typing import Any, Callable, Optional

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class ControlOverlay(FloatLayout):
    """A widget that overlays controls for muting and pausing on top of the main UI."""

    is_muted = BooleanProperty(False)
    is_paused = BooleanProperty(False)
    overlay_opacity = NumericProperty(0.0)

    def __init__(
        self,
        on_mute: Optional[Callable[[bool], None]] = None,
        on_pause: Optional[Callable[[bool], None]] = None,
        **kwargs: Any,
    ) -> None:
        super(ControlOverlay, self).__init__(**kwargs)

        self.on_mute_callback = on_mute
        self.on_pause_callback = on_pause

        with self.canvas.before:
            self.overlay_color = Color(0, 0, 0, 0)
            self.overlay_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(size=self._update_overlay, pos=self._update_overlay)
        self.bind(overlay_opacity=self._update_overlay_color)

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

        self.status_icon = Label(
            text="",
            font_size=80,
            size_hint=(None, None),
            size=(120, 120),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            opacity=0.0,
        )
        self.add_widget(self.status_icon)

    def _update_overlay(self, *args: Any) -> None:
        """Updates the overlay rectangle's size and position to match the layout."""
        self.overlay_rect.pos = self.pos
        self.overlay_rect.size = self.size

    def _update_overlay_color(self, *args: Any) -> None:
        """Updates the overlay color's opacity."""
        self.overlay_color.a = self.overlay_opacity

    def _on_control_press(self, button: Button) -> None:
        """
        Handles the press event for the main control button.

        Args:
            button (Button): The button instance that was pressed.
        """
        if self.is_paused:
            self._unpause()
        else:
            self._toggle_mute()

    def _on_pause_press(self, button: Button) -> None:
        """
        Handles the press event for the pause button.

        Args:
            button (Button): The button instance that was pressed.
        """
        if self.is_paused:
            self._unpause()
        else:
            self._pause()

    def _toggle_mute(self) -> None:
        """Toggles the mute state."""
        if self.is_muted:
            self._unmute()
        else:
            self._mute()

    def _mute(self) -> None:
        """Enters the muted state and shows the overlay."""
        self.is_muted = True
        self.is_paused = False
        self.control_button.text = "UNMUTE"
        self.status_icon.text = "MUTE"
        self._show_overlay()
        if self.on_mute_callback:
            self.on_mute_callback(True)

    def _unmute(self) -> None:
        """Exits the muted state and hides the overlay."""
        self.is_muted = False
        self.control_button.text = "MUTE"
        self._hide_overlay()
        if self.on_mute_callback:
            self.on_mute_callback(False)

    def _pause(self) -> None:
        """Enters the paused state and shows the overlay."""
        self.is_paused = True
        self.is_muted = False
        self.control_button.text = "UNMUTE"
        self.pause_button.text = ">"
        self.status_icon.text = "PAUSED"
        self._show_overlay()
        if self.on_pause_callback:
            self.on_pause_callback(True)

    def _unpause(self) -> None:
        """Exits the paused state and hides the overlay."""
        self.is_paused = False
        self.control_button.text = "MUTE"
        self.pause_button.text = "||"
        self._hide_overlay()
        if self.on_pause_callback:
            self.on_pause_callback(False)

    def _show_overlay(self) -> None:
        """Shows the dark overlay and status icon with an animation."""
        overlay_anim = Animation(
            overlay_opacity=0.6, duration=0.3, transition="out_quad"
        )
        overlay_anim.start(self)
        icon_anim = Animation(opacity=1.0, duration=0.3, transition="out_quad")
        icon_anim.start(self.status_icon)

    def _hide_overlay(self) -> None:
        """Hides the dark overlay and status icon with an animation."""
        overlay_anim = Animation(
            overlay_opacity=0.0, duration=0.3, transition="in_quad"
        )
        overlay_anim.start(self)
        icon_anim = Animation(opacity=0.0, duration=0.3, transition="in_quad")
        icon_anim.start(self.status_icon)

    def force_reset(self) -> None:
        """Resets the overlay to its default non-muted and non-paused state."""
        self.is_muted = False
        self.is_paused = False
        self.control_button.text = "MUTE"
        self.pause_button.text = "||"
        self._hide_overlay()
