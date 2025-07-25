from typing import Any, Callable

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label


class SplashScreen(FloatLayout):
    """
    Displays a medical device disclaimer overlay that must be acknowledged before proceeding.
    """

    splash_opacity = NumericProperty(1.0)

    def __init__(self, on_acknowledge: Callable[[], None], **kwargs) -> None:
        super(SplashScreen, self).__init__(**kwargs)
        self.on_acknowledge = on_acknowledge

        with self.canvas.before:
            self.splash_color = Color(0, 0, 0, 1)
            self.splash_bg = Rectangle(pos=self.pos, size=self.size)

        self.bind(size=self._update_bg, pos=self._update_bg)
        self.bind(splash_opacity=self._update_splash_color)

        main_layout = BoxLayout(
            orientation="vertical",
            spacing=20,
            padding=[30, 40, 30, 40],
            size_hint=(0.85, 0.75),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )

        title_label = Label(
            text="MEDICAL DEVICE DISCLAIMER",
            font_size="22sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=80,
            halign="center",
            valign="middle",
        )
        title_label.bind(size=title_label.setter("text_size"))

        disclaimer_text = (
            "IMPORTANT: This application is NOT a medical device and is NOT intended "
            "for medical diagnosis, treatment, or intervention of any kind.\n\n"
            "This software is designed for auditory training and educational purposes only. "
            "It should not be used as a substitute for professional medical advice, "
            "diagnosis, or treatment.\n\n"
            "If you have hearing difficulties or concerns about your auditory health, "
            "please consult with a qualified healthcare professional or audiologist.\n\n"
            "By proceeding, you acknowledge that you understand this disclaimer and "
            "agree to use this application for educational purposes only."
        )

        disclaimer_label = Label(
            text=disclaimer_text,
            font_size="14sp",
            color=(0.9, 0.9, 0.9, 1),
            text_size=(None, None),
            halign="left",
            valign="top",
            markup=True,
        )
        disclaimer_label.bind(size=disclaimer_label.setter("text_size"))

        acknowledge_button = Button(
            text="I UNDERSTAND - PROCEED",
            font_size="16sp",
            bold=True,
            size_hint=(None, None),
            size=(450, 80),
            pos_hint={"center_x": 0.5},
            background_color=(0.2, 0.7, 0.2, 1),
            color=(1, 1, 1, 1),
            border=(2, 2, 2, 2),
        )
        acknowledge_button.bind(on_press=self._on_acknowledge)

        main_layout.add_widget(title_label)
        main_layout.add_widget(disclaimer_label)
        main_layout.add_widget(acknowledge_button)

        self.add_widget(main_layout)

    def _update_bg(self, instance: Any, value: Any) -> None:
        """
        Updates the background when the window is resized.

        Args:
            instance: The instance that fired the event.
            value: The new value (size or position).
        """
        self.splash_bg.pos = instance.pos
        self.splash_bg.size = instance.size

    def _update_splash_color(self, *args: Any) -> None:
        """
        Updates the splash background color's opacity and widget visibility.
        """
        self.splash_color.a = self.splash_opacity
        self.opacity = self.splash_opacity
        self.disabled = self.splash_opacity == 0.0

    def _on_acknowledge(self, instance: Any) -> None:
        """
        Handles the acknowledge button press and hides the splash screen.

        Args:
            instance: The button instance that was pressed.
        """
        self._hide_splash()
        self.on_acknowledge()

    def _hide_splash(self) -> None:
        """
        Hides the splash screen with an animation.
        """
        splash_anim = Animation(splash_opacity=0.0, duration=0.5, transition="in_quad")
        splash_anim.start(self)

    def show_splash(self) -> None:
        """
        Shows the splash screen with an animation.
        """
        self.splash_opacity = 1.0
        self.disabled = False
        splash_anim = Animation(splash_opacity=1.0, duration=0.3, transition="out_quad")
        splash_anim.start(self)


if __name__ == "__main__":
    from kivy.app import App

    class SplashTestApp(App):
        """Test app for the splash screen."""

        def build(self) -> SplashScreen:
            """Builds and returns the splash screen for testing."""

            def dummy_acknowledge():
                print("Disclaimer acknowledged!")
                self.stop()

            return SplashScreen(on_acknowledge=dummy_acknowledge)

    SplashTestApp().run()
