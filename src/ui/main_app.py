from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout

from ui.audio_visualizer import AudioVisualizer
from ui.orb import Orb

Window.size = (405, 720)
Window.minimum_width = 202
Window.minimum_height = 360
Window.resizable = True


class MainLayout(FloatLayout):
    def __init__(self, llm_manager=None, **kwargs):
        super(MainLayout, self).__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 1)  #
            self.bg = Rectangle(pos=self.pos, size=self.size)

        self.bind(size=self._update_bg, pos=self._update_bg)

        self.orb = Orb(
            size_hint=(None, None), pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.orb.base_radius = min(Window.width, Window.height) / 6
        self.add_widget(self.orb)

        self.llm_manager = llm_manager
        self.audio_visualizer = AudioVisualizer()
        Clock.schedule_interval(self.update_orb_from_audio, 1 / 30)

        # Start LLM manager when layout is ready
        if self.llm_manager:
            Clock.schedule_once(self.start_llm_manager, 1)

    def _update_bg(self, instance, value):
        """Update background and orb size when window resizes."""
        # Update background rectangle
        self.bg.pos = instance.pos
        self.bg.size = instance.size

        # Update orb size based on window dimensions
        if hasattr(self, "orb"):
            self.orb.base_radius = min(Window.width, Window.height) / 6
            self.orb.glow_radius = self.orb.base_radius * 1.1

    def start_llm_manager(self, dt):
        """Start the LLM manager on the main thread."""
        if self.llm_manager:
            print("🎬 Starting LLM Manager from UI...", flush=True)
            self.llm_manager.start()

    def update_orb_from_audio(self, dt):
        """Update orb visualization based on latest audio data."""
        if not self.llm_manager or not self.llm_manager.viz_queue:
            self.orb.start_idle_animation(delay=0.5)
            return

        # Process Gemini's output audio for visualization
        if self.llm_manager.viz_queue:
            audio_chunk = self.llm_manager.viz_queue.pop(0)
            amplitude = self.audio_visualizer.process_audio(audio_chunk)
            self.orb.update_from_amplitude(amplitude * 1.5)


class UnlockHearingApp(App):
    def __init__(self, llm_manager=None, **kwargs):
        self.llm_manager = llm_manager
        super(UnlockHearingApp, self).__init__(**kwargs)
        self.title = "Unlock Hearing"

    def build(self):
        """Build and return the main layout."""
        return MainLayout(llm_manager=self.llm_manager)

    def on_stop(self):
        """Clean up when app closes."""
        if self.llm_manager:
            print("🛑 App closing, stopping LLM Manager...", flush=True)
            self.llm_manager.stop()
        return True
