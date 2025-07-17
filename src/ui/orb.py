from typing import Any

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse
from kivy.properties import ColorProperty, NumericProperty
from kivy.uix.widget import Widget


class Orb(Widget):
    """A visual orb that responds to audio and user interaction."""

    size_multiplier = NumericProperty(1.0)
    base_radius = NumericProperty(100)
    glow_radius = NumericProperty(110)
    orb_color = ColorProperty([1, 1, 1, 1])
    glow_color = ColorProperty([1, 1, 1, 0.3])

    def __init__(self, **kwargs: Any) -> None:
        super(Orb, self).__init__(**kwargs)
        self.canvas.clear()

        with self.canvas:
            self.glow_color_instr = Color(*self.glow_color)
            self.glow = Ellipse(pos=(0, 0), size=(0, 0))
            self.orb_color_instr = Color(*self.orb_color)
            self.orb = Ellipse(pos=(0, 0), size=(0, 0))

        Clock.schedule_interval(self.update_graphics, 1 / 60)
        self.anim = None
        self.idle_anim = None
        self.start_idle_animation()

    def update_graphics(self, dt: float) -> None:
        """Updates the orb's position and size for the current frame.

        Args:
            dt (float): The time elapsed since the last update.
        """
        orb_size = self.base_radius * 2 * self.size_multiplier
        glow_size = self.glow_radius * 2 * self.size_multiplier

        orb_pos = (self.center_x - orb_size / 2, self.center_y - orb_size / 2)
        glow_pos = (self.center_x - glow_size / 2, self.center_y - glow_size / 2)

        self.orb.pos = orb_pos
        self.orb.size = (orb_size, orb_size)
        self.glow.pos = glow_pos
        self.glow.size = (glow_size, glow_size)

    def update_from_amplitude(self, amplitude: float) -> None:
        """Updates the orb's size based on the audio amplitude.

        Args:
            amplitude (float): The audio amplitude to visualize.
        """
        if self.anim is not None:
            self.anim.cancel(self)

        target_size = 1.0 + min(0.5, amplitude * 0.7)

        self.anim = Animation(
            size_multiplier=target_size,
            duration=0.05,
            transition="out_quad",
        )
        self.anim.start(self)

        if amplitude > 0.05:
            self.start_idle_animation(delay=1.5)

    def start_idle_animation(self, delay: float = 0) -> None:
        """Starts a subtle pulsing idle animation after a specified delay.

        Args:
            delay (float): The delay in seconds before the animation starts.
        """
        if self.idle_anim is not None:
            self.idle_anim.cancel(self)

        Clock.schedule_once(self._begin_idle_animation, delay)

    def _begin_idle_animation(self, dt: float) -> None:
        """Sets up and starts the repeating breathing animation for the idle state.

        Args:
            dt (float): The time elapsed since the animation was scheduled.
        """
        idle_size_min = 0.97
        idle_size_max = 1.03
        idle_duration = 2.0

        self.idle_anim = Animation(
            size_multiplier=idle_size_max,
            duration=idle_duration / 2,
            transition="in_out_sine",
        ) + Animation(
            size_multiplier=idle_size_min,
            duration=idle_duration / 2,
            transition="in_out_sine",
        )
        self.idle_anim.repeat = True
        self.idle_anim.start(self)

    def on_touch_down(self, touch: Any) -> bool:
        """Handles touch down events with a pulse animation.

        Args:
            touch (Any): The touch event object.

        Returns:
            bool: True if the event is handled, otherwise propagates the event.
        """
        if self.collide_point(*touch.pos):
            Animation.cancel_all(self)

            anim1 = Animation(size_multiplier=1.2, duration=0.15, transition="out_quad")
            anim2 = Animation(
                size_multiplier=1.0, duration=0.3, transition="in_out_quad"
            )
            (anim1 + anim2).start(self)

            Clock.schedule_once(lambda dt: self.start_idle_animation(), 0.5)

            return True

        return super(Orb, self).on_touch_down(touch)
