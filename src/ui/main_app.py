from typing import Any, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout

from ui.audio_visualizer import AudioVisualizer
from ui.orb import Orb

Window.minimum_width, Window.minimum_height = 202, 360
Window.size = (405, 720)
Window.resizable = True


class MainLayout(FloatLayout):
    def __init__(self, llm_manager: Optional[Any] = None, **kwargs) -> None:
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

    def _update_bg(self, instance: Any, value: Any) -> None:
        """Update background and orb size when window resizes."""
        # Update background rectangle
        self.bg.pos = instance.pos
        self.bg.size = instance.size

        # Update orb size based on window dimensions
        if hasattr(self, "orb"):
            self.orb.base_radius = min(Window.width, Window.height) / 6
            self.orb.glow_radius = self.orb.base_radius * 1.1

    def start_llm_manager(self, dt: float) -> None:
        """Start the LLM manager on the main thread."""
        if self.llm_manager:
            print("🎬 Starting LLM Manager from UI...", flush=True)
            self.llm_manager.start()

    def update_orb_from_audio(self, dt: float) -> None:
        """Update orb visualization based on Kai's speech only."""
        if not self.llm_manager:
            self.orb.start_idle_animation(delay=0.5)
            return

        # Only move orb when Kai is actively speaking
        if self.llm_manager.gemini_speaking and self.llm_manager.viz_queue:
            audio_chunk = self.llm_manager.viz_queue.pop(0)
            amplitude = self.audio_visualizer.process_audio(audio_chunk)
            self.orb.update_from_amplitude(amplitude * 1.5)
        else:
            # Return to idle animation when Kai is not speaking
            self.orb.start_idle_animation(delay=0.5)


class TesseraApp(App):
    def __init__(self, llm_manager: Optional[Any] = None, **kwargs) -> None:
        self.llm_manager = llm_manager
        super(TesseraApp, self).__init__(**kwargs)
        self.title = "Tessera"

    def build(self) -> MainLayout:
        """Build and return the main layout."""
        return MainLayout(llm_manager=self.llm_manager)

    def on_stop(self) -> bool:
        """Clean up when app closes."""
        self.llm_manager.stop()
        return True
