from typing import Any, Optional

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout

from ui.audio_visualizer import AudioVisualizer
from ui.control_overlay import ControlOverlay
from ui.orb import Orb

Window.minimum_width, Window.minimum_height = 202, 300
Window.size = (405, 600)
Window.resizable = True


class MainLayout(FloatLayout):
    """A Kivy FloatLayout that serves as the main container for the application's UI."""

    def __init__(self, llm_manager: Optional[Any] = None, **kwargs) -> None:
        super(MainLayout, self).__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 1)
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

        self.control_overlay = ControlOverlay(
            on_mute=self._handle_mute,
            on_pause=self._handle_pause,
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.add_widget(self.control_overlay)

        if self.llm_manager:
            Clock.schedule_once(self.start_llm_manager, 1)

    def _update_bg(self, instance: Any, value: Any) -> None:
        """Updates the background and orb size when the window is resized.

        Args:
            instance (Any): The instance that fired the event.
            value (Any): The new value of the property.
        """
        self.bg.pos = instance.pos
        self.bg.size = instance.size

        if hasattr(self, "orb"):
            self.orb.base_radius = min(Window.width, Window.height) / 6
            self.orb.glow_radius = self.orb.base_radius * 1.1

    def start_llm_manager(self, dt: float) -> None:
        """Starts the LLM manager's conversation loop in a separate thread.

        Args:
            dt (float): The time elapsed since the last call.
        """
        if self.llm_manager:
            import threading
            conversation_thread = threading.Thread(
                target=self.llm_manager.start_conversation,
                daemon=True
            )
            conversation_thread.start()

    def _handle_mute(self, is_muted: bool) -> None:
        """Handles a change in the mute state.

        Args:
            is_muted (bool): A boolean indicating if the audio is muted.
        """
        pass

    def _handle_pause(self, is_paused: bool) -> None:
        """Handles a change in the pause state.

        Args:
            is_paused (bool): A boolean indicating if the application is paused.
        """
        if is_paused:
            Animation.cancel_all(self.orb)
        else:
            self.orb.start_idle_animation(delay=0.1)

    def update_orb_from_audio(self, dt: float) -> None:
        """Updates the orb visualization based on audio activity.

        Args:
            dt (float): The time elapsed since the last call.
        """
        self.orb.start_idle_animation(delay=0.5)


class TesseraApp(App):
    """The main Kivy application class for Tessera."""

    def __init__(self, llm_manager: Optional[Any] = None, **kwargs) -> None:
        self.llm_manager = llm_manager
        super(TesseraApp, self).__init__(**kwargs)
        self.title = "Tessera"

    def build(self) -> MainLayout:
        """Builds and returns the main layout of the application.

        Returns:
            MainLayout: The main layout widget.
        """
        return MainLayout(llm_manager=self.llm_manager)

    def on_stop(self) -> bool:
        """Cleans up resources when the application is closed.

        Returns:
            bool: A boolean to indicate if the stopping process should continue.
        """
        if self.llm_manager:
            self.llm_manager.stop()
        return True
