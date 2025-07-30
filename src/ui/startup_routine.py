import os
import webbrowser
from pathlib import Path
from typing import Any, Callable

from kivy.animation import Animation
from kivy.graphics import Color, Line, Rectangle
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from managers.state_manager import get_app_data_dir


def is_valid_api_key(api_key: str) -> bool:
    """Validates if API key is legitimate and not a placeholder.

    Args:
        api_key: The API key string to validate

    Returns:
        True if the API key appears valid, False otherwise
    """
    if not api_key:
        return False

    key = api_key.strip()

    if not key.startswith("AIza"):
        return False

    if len(key) < 20:
        return False

    placeholder_values = {"test_key", "your_api_key", "api_key_here"}
    if key.lower() in placeholder_values:
        return False

    return True


def save_api_key_safely(api_key: str) -> bool:
    """Saves API key with atomic write to prevent corruption.

    Args:
        api_key: The API key string to save

    Returns:
        True if the API key was saved successfully, False otherwise
    """
    app_data_dir = get_app_data_dir()
    env_path = app_data_dir / ".env"
    temp_path = app_data_dir / ".env.tmp"

    with open(temp_path, "w") as f:
        f.write(f"GEMINI_API_KEY={api_key}\n")
        f.flush()
        os.fsync(f.fileno())

    temp_path.rename(env_path)

    with open(env_path) as f:
        content = f.read().strip()
        if f"GEMINI_API_KEY={api_key}" in content:
            return True

    return False


class StartupRoutine(FloatLayout):
    """Handles the complete app startup sequence including API key setup and medical disclaimer."""

    splash_opacity = NumericProperty(1.0)

    def __init__(self, on_complete: Callable[[], None], **kwargs) -> None:
        """Initialize the startup routine.

        Args:
            on_complete: Callback function to call when startup is complete
            **kwargs: Additional keyword arguments for FloatLayout
        """
        super(StartupRoutine, self).__init__(**kwargs)
        self.on_complete = on_complete

        with self.canvas.before:
            self.splash_color = Color(0, 0, 0, 1)
            self.splash_bg = Rectangle(pos=self.pos, size=self.size)

        self.bind(size=self._update_bg, pos=self._update_bg)
        self.bind(splash_opacity=self._update_splash_color)

        self._check_startup_requirements()

    def _check_startup_requirements(self) -> None:
        """Checks what startup steps are needed and begins the appropriate flow."""
        if self._needs_api_key():
            self._show_api_key_setup()
        else:
            self._show_medical_disclaimer()

    def _needs_api_key(self) -> bool:
        """Checks if API key setup is needed with robust validation.

        Returns:
            True if API key setup is needed, False otherwise
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        return not is_valid_api_key(api_key)

    def _show_api_key_setup(self) -> None:
        """Shows the API key setup interface."""
        self.clear_widgets()

        main_layout = BoxLayout(
            orientation="vertical",
            spacing=30,
            padding=[40, 40, 40, 40],
            size_hint=(0.9, 0.8),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

        title = Label(
            text="API KEY SETUP",
            font_size="24sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=50,
        )

        instructions = Label(
            text="Get your API key from Google AI Studio:",
            font_size="16sp",
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=40,
            halign="center",
        )
        instructions.bind(size=instructions.setter("text_size"))

        link_btn = Button(
            text="OPEN API KEY PAGE",
            font_size="16sp",
            size_hint_y=None,
            height=50,
            background_color=(0.2, 0.5, 1, 1),
        )
        link_btn.bind(on_press=self._open_link)

        input_label = Label(
            text="Paste your API key below:",
            font_size="16sp",
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=None,
            height=30,
            halign="center",
        )
        input_label.bind(size=input_label.setter("text_size"))

        self.api_input = TextInput(
            text="",
            font_size="16sp",
            size_hint_y=None,
            height=50,
            multiline=False,
            cursor_color=(0.2, 0.5, 1, 1),
            selection_color=(0.2, 0.5, 1, 0.3),
            background_color=(0.15, 0.15, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
        )
        self.api_input.bind(focus=self._on_input_focus)

        self.continue_btn = Button(
            text="CONTINUE",
            font_size="18sp",
            size_hint_y=None,
            height=60,
            disabled=True,
            background_color=(0.3, 0.3, 0.3, 1),
        )
        self.continue_btn.bind(on_press=self._on_continue)
        self.api_input.bind(text=self._on_text_change)

        self.status = Label(
            text="",
            font_size="14sp",
            color=(1, 0.3, 0.3, 1),
            size_hint_y=None,
            height=30,
        )

        main_layout.add_widget(title)
        main_layout.add_widget(instructions)
        main_layout.add_widget(link_btn)
        main_layout.add_widget(input_label)
        main_layout.add_widget(self.api_input)
        main_layout.add_widget(self.status)
        main_layout.add_widget(self.continue_btn)

        self.add_widget(main_layout)

    def _show_medical_disclaimer(self) -> None:
        """Shows the medical disclaimer interface."""
        self.clear_widgets()

        main_layout = BoxLayout(
            orientation="vertical",
            spacing=30,
            padding=[40, 40, 40, 40],
            size_hint=(0.9, 0.8),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

        title = Label(
            text="MEDICAL DISCLAIMER",
            font_size="24sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=50,
        )

        disclaimer = Label(
            text="This app is NOT a medical device.\n\nIt's for training and education only.\n\nConsult a healthcare professional for medical advice.",
            font_size="16sp",
            color=(0.9, 0.9, 0.9, 1),
            halign="center",
        )
        disclaimer.bind(size=disclaimer.setter("text_size"))

        proceed_btn = Button(
            text="I UNDERSTAND - PROCEED",
            font_size="18sp",
            size_hint_y=None,
            height=60,
        )
        proceed_btn.bind(on_press=self._on_proceed)

        main_layout.add_widget(title)
        main_layout.add_widget(disclaimer)
        main_layout.add_widget(proceed_btn)

        self.add_widget(main_layout)

    def _on_input_focus(self, instance: Any, focused: bool) -> None:
        """Handles focus changes for the API input to add/remove outline.

        Args:
            instance: The TextInput widget instance
            focused: Whether the input is focused
        """
        with instance.canvas.after:
            instance.canvas.after.clear()
            if focused:
                Color(0.2, 0.5, 1, 1)
                Line(
                    rectangle=(instance.x, instance.y, instance.width, instance.height),
                    width=2,
                )

    def _on_text_change(self, instance: Any, text: str) -> None:
        """Handles text changes in the API key input.

        Args:
            instance: The TextInput widget instance
            text: The current text in the input
        """
        self.status.text = ""
        is_valid = is_valid_api_key(text)
        self.continue_btn.disabled = not is_valid

        if is_valid:
            self.continue_btn.background_color = (0.2, 0.7, 0.2, 1)
        else:
            self.continue_btn.background_color = (0.3, 0.3, 0.3, 1)

    def _on_continue(self, instance: Any) -> None:
        """Handles the continue button press.

        Args:
            instance: The Button widget instance
        """
        api_key = self.api_input.text.strip()

        if not is_valid_api_key(api_key):
            self.status.text = "Invalid API key"
            return

        if not save_api_key_safely(api_key):
            self.status.text = "Error saving API key"
            return

        os.environ["GEMINI_API_KEY"] = api_key

        self.status.color = (0.3, 1, 0.3, 1)
        self.status.text = "Saved! Starting app..."

        from kivy.clock import Clock

        Clock.schedule_once(lambda dt: self._show_medical_disclaimer(), 1.0)

    def _on_proceed(self, instance: Any) -> None:
        """Handles the proceed button press.

        Args:
            instance: The Button widget instance
        """
        anim = Animation(splash_opacity=0.0, duration=0.5)
        anim.bind(on_complete=lambda *args: self.on_complete())
        anim.start(self)

    def _open_link(self, instance: Any) -> None:
        """Opens the API key link in the default browser.

        Args:
            instance: The Button widget instance
        """
        webbrowser.open("https://aistudio.google.com/app/apikey")

    def _update_bg(self, instance: Any, value: Any) -> None:
        """Updates the background when the window is resized.

        Args:
            instance: The widget instance
            value: The new value (position or size)
        """
        self.splash_bg.pos = instance.pos
        self.splash_bg.size = instance.size

    def _update_splash_color(self, *args: Any) -> None:
        """Updates the splash background color's opacity.

        Args:
            *args: Variable arguments from the property binding
        """
        self.splash_color.a = self.splash_opacity
        self.opacity = self.splash_opacity
        self.disabled = self.splash_opacity == 0.0

    def show_startup(self) -> None:
        """Shows the startup routine with an animation."""
        self.splash_opacity = 1.0
        self.disabled = False
