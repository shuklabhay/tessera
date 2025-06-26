from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, InstructionGroup
from kivy.properties import ColorProperty, NumericProperty
from kivy.uix.widget import Widget


class Orb(Widget):
    size_multiplier = NumericProperty(1.0)
    base_radius = NumericProperty(100)
    glow_radius = NumericProperty(110)
    orb_color = ColorProperty([1, 1, 1, 1])
    glow_color = ColorProperty([1, 1, 1, 0.3])

    def __init__(self, **kwargs):
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

    def update_graphics(self, dt):
        """Update orb position and size for current frame."""
        # Calculate sizes based on radius and multiplier
        orb_size = self.base_radius * 2 * self.size_multiplier
        glow_size = self.glow_radius * 2 * self.size_multiplier

        # Calculate centered positions
        orb_pos = (self.center_x - orb_size / 2, self.center_y - orb_size / 2)
        glow_pos = (self.center_x - glow_size / 2, self.center_y - glow_size / 2)

        # Update ellipse graphics
        self.orb.pos = orb_pos
        self.orb.size = (orb_size, orb_size)
        self.glow.pos = glow_pos
        self.glow.size = (glow_size, glow_size)

    def update_from_amplitude(self, amplitude):
        """Update orb size based on audio amplitude."""
        # Cancel any existing animation
        if self.anim is not None:
            self.anim.cancel(self)

        # Calculate target size with limits
        target_size = 1.0 + min(0.5, amplitude * 0.7)

        # Create and start animation
        self.anim = Animation(
            size_multiplier=target_size,
            duration=0.05,
            transition="out_quad",
        )
        self.anim.start(self)

        # Reset idle timer if significant audio detected
        if amplitude > 0.05:
            self.start_idle_animation(delay=1.5)

    def start_idle_animation(self, delay=0):
        """Start subtle pulsing idle animation after delay."""
        # Cancel any existing idle animation
        if self.idle_anim is not None:
            self.idle_anim.cancel(self)

        # Schedule idle animation to start
        Clock.schedule_once(self._begin_idle_animation, delay)

    def _begin_idle_animation(self, dt):
        """Set up and start the breathing idle animation."""
        # Breathing effect parameters
        idle_size_min = 0.97
        idle_size_max = 1.03
        idle_duration = 2.0

        # Create repeating breathing animation
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

    def on_touch_down(self, touch):
        """Handle touch events with pulse animation."""
        if self.collide_point(*touch.pos):
            # Cancel all animations
            Animation.cancel_all(self)

            # Create pulse effect: expand then contract
            anim1 = Animation(size_multiplier=1.2, duration=0.15, transition="out_quad")
            anim2 = Animation(
                size_multiplier=1.0, duration=0.3, transition="in_out_quad"
            )
            (anim1 + anim2).start(self)

            # Restart idle animation after pulse completes
            Clock.schedule_once(lambda dt: self.start_idle_animation(), 0.5)

            return True

        return super(Orb, self).on_touch_down(touch)
