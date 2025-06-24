from audio_visualizer import AudioVisualizer
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from ui.orb import Orb

# Set window to 9:16 aspect ratio, resizable
Window.size = (405, 720)
Window.minimum_width = 202
Window.minimum_height = 360
Window.resizable = True


class MainLayout(FloatLayout):
    def __init__(self, voice_chat=None, **kwargs):
        super(MainLayout, self).__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 1)  # Black
            self.bg = Rectangle(pos=self.pos, size=self.size)

        # Update background when window resizes
        self.bind(size=self._update_bg, pos=self._update_bg)

        # Create the orb widget
        self.orb = Orb(
            size_hint=(None, None), pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.orb.base_radius = min(Window.width, Window.height) / 6
        self.add_widget(self.orb)

        # Create mode selection labels
        self.structured_button = self._create_mode_button(
            "Structured Practice", {"center_x": 0.25, "center_y": 0.5}
        )
        self.freeform_button = self._create_mode_button(
            "Freeform Training", {"center_x": 0.75, "center_y": 0.5}
        )
        self.add_widget(self.structured_button)
        self.add_widget(self.freeform_button)

        # Store reference to voice chat if provided
        self.voice_chat = voice_chat

        # Create audio visualizer for orb animation
        self.audio_visualizer = AudioVisualizer()

        # Schedule audio processing if voice chat is provided
        Clock.schedule_interval(self.update_orb_from_audio, 1 / 30)

        # Initially, show the mode selection after a delay
        Clock.schedule_once(lambda dt: self.show_mode_selection(), 2)

    def _create_mode_button(self, text, pos_hint):
        """Helper to create the mode selection labels."""
        button = Label(
            text=text,
            size_hint=(None, None),
            size=(200, 50),
            pos_hint=pos_hint,
            font_size="18sp",
            color=(1, 1, 1, 1),
            opacity=0,  # Initially invisible
        )
        button.bind(on_touch_down=self._on_mode_press)
        return button

    def _on_mode_press(self, instance, touch):
        if instance.collide_point(*touch.pos):
            if instance.text == "Structured Practice":
                self.select_mode("structured")
            else:
                self.select_mode("freeform")
            return True
        return False

    def show_mode_selection(self):
        """Animate the mode selection buttons to appear."""
        anim_structured = Animation(opacity=1, duration=1)
        anim_freeform = Animation(opacity=1, duration=1)
        anim_structured.start(self.structured_button)
        anim_freeform.start(self.freeform_button)

    def hide_mode_selection(self):
        """Animate the mode selection buttons to disappear."""
        anim_structured = Animation(opacity=0, duration=1)
        anim_freeform = Animation(opacity=0, duration=1)
        anim_structured.start(self.structured_button)
        anim_freeform.start(self.freeform_button)

    def select_mode(self, mode_name):
        """Handle mode selection."""
        print(f"Mode selected: {mode_name}")
        self.hide_mode_selection()
        # Here, you would typically notify the voice_chat or another controller
        # For example: self.voice_chat.set_mode(mode_name)

    def _update_bg(self, instance, value):
        """Update the background rectangle when the window size changes"""
        self.bg.pos = instance.pos
        self.bg.size = instance.size

        # Also update orb size based on window size
        if hasattr(self, "orb"):
            self.orb.base_radius = min(Window.width, Window.height) / 6
            self.orb.glow_radius = self.orb.base_radius * 1.1

    def update_orb_from_audio(self, dt):
        """
        Update the orb visualization based on the latest audio data
        """
        if not self.voice_chat:
            return

        # If user is speaking, orb is idle
        if (
            hasattr(self.voice_chat, "gemini_speaking")
            and self.voice_chat.gemini_speaking
        ):
            # Get the last audio chunk from voice_chat if available
            last_audio = None

            if (
                hasattr(self.voice_chat, "last_gemini_audio")
                and self.voice_chat.last_gemini_audio is not None
            ):
                last_audio = self.voice_chat.last_gemini_audio

            # Process the audio data to get amplitude
            if last_audio is not None:
                amplitude = self.audio_visualizer.process_audio(last_audio)
                self.orb.update_from_amplitude(amplitude * 2.5)

        else:
            # When not speaking, return to idle animation
            self.orb.start_idle_animation(delay=0.5)


class UnlockHearingApp(App):
    def __init__(self, voice_chat=None, **kwargs):
        super(UnlockHearingApp, self).__init__(**kwargs)
        self.voice_chat = voice_chat
        self.title = "Unlock Hearing"

    def build(self):
        """Build and return the main layout"""
        return MainLayout(voice_chat=self.voice_chat)
