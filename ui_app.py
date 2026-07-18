from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
import threading
import subprocess
import os
import sys

from ai_state import load_config, save_config, record_training_event


class HelperController(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 12
        self.config = load_config()
        self.proc = None
        self.thread = None
        self.overlay = None

        self.status = Label(text='Status: idle', font_size=16, size_hint_y=None, height=60)
        self.resource_input = TextInput(text=self.config.get('resource', 'wood'), multiline=False, hint_text='resource name')
        self.db_input = TextInput(text=self.config.get('db_path', 'assistant.db'), multiline=False, hint_text='db file')
        self.remote_input = TextInput(text=self.config.get('remote_url', ''), multiline=False, hint_text='remote URL')
        self.video_input = TextInput(text=self.config.get('video_path', ''), multiline=False, hint_text='video path')
        self.mode_spinner = Spinner(text='Loop', values=['Loop', 'One shot'], size_hint_y=None, height=48)
        self.ai_spinner = Spinner(text=self.config.get('ai_mode', 'local'), values=['local', 'remote', 'video'], size_hint_y=None, height=48)
        self.device_input = TextInput(text=self.config.get('device', 'poco_f5'), multiline=False, hint_text='device preset')

        self.enable_button = Button(text='Enable assistant', size_hint_y=None, height=56)
        self.disable_button = Button(text='Disable assistant', size_hint_y=None, height=56)
        self.settings_button = Button(text='AI settings', size_hint_y=None, height=56)
        self.train_button = Button(text='Train from remote/video', size_hint_y=None, height=56)

        self.ai_label = Label(text='AI mode: local decision engine', size_hint_y=None, height=40)

        self.add_widget(Label(text='Albion AI Helper', font_size=24))
        self.add_widget(self.ai_label)
        self.add_widget(Label(text='Target resource'))
        self.add_widget(self.resource_input)
        self.add_widget(Label(text='Database file'))
        self.add_widget(self.db_input)
        self.add_widget(Label(text='Remote URL'))
        self.add_widget(self.remote_input)
        self.add_widget(Label(text='Video path'))
        self.add_widget(self.video_input)
        self.add_widget(Label(text='Run mode'))
        self.add_widget(self.mode_spinner)
        self.add_widget(Label(text='AI mode'))
        self.add_widget(self.ai_spinner)
        self.add_widget(Label(text='Device preset'))
        self.add_widget(self.device_input)
        self.add_widget(self.enable_button)
        self.add_widget(self.disable_button)
        self.add_widget(self.settings_button)
        self.add_widget(self.train_button)
        self.add_widget(self.status)

        self.enable_button.bind(on_press=self.start_helper)
        self.disable_button.bind(on_press=self.stop_helper)
        self.settings_button.bind(on_press=self.show_settings)
        self.train_button.bind(on_press=self.train_from_sources)

    def start_helper(self, instance):
        if self.proc and self.proc.poll() is None:
            self.status.text = 'Status: already running'
            return

        self._save_config()
        resource = self.resource_input.text.strip() or 'wood'
        mode = ['--once'] if self.mode_spinner.text == 'One shot' else []
        cmd = [sys.executable, 'app.py', '--resource', resource, '--db', self.db_input.text.strip(), '--device', self.device_input.text.strip()] + mode
        self.status.text = f'Status: starting {resource}...'
        self.proc = subprocess.Popen(cmd, cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.thread = threading.Thread(target=self._read_output, daemon=True)
        self.thread.start()
        self._show_overlay('ON')

    def stop_helper(self, instance):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.status.text = 'Status: stopped'
        else:
            self.status.text = 'Status: nothing running'
        self._show_overlay('OFF')

    def show_settings(self, instance):
        self._save_config()
        popup = Popup(title='AI settings', content=Label(text='AI local memory + remote/video training hooks are enabled.\nUse the buttons below to train and store data locally.'), size_hint=(0.8, 0.4))
        popup.open()

    def train_from_sources(self, instance):
        self._save_config()
        remote = self.remote_input.text.strip()
        video = self.video_input.text.strip()
        resource = self.resource_input.text.strip() or 'wood'
        if remote:
            record_training_event(self.config, 'remote', remote, resource, 'remote training queued')
        if video:
            record_training_event(self.config, 'video', video, resource, 'video training queued')
        self.status.text = 'Status: training queued'

    def _save_config(self):
        self.config = {
            'resource': self.resource_input.text.strip() or 'wood',
            'db_path': self.db_input.text.strip() or 'assistant.db',
            'remote_url': self.remote_input.text.strip(),
            'video_path': self.video_input.text.strip(),
            'ai_mode': self.ai_spinner.text,
            'device': self.device_input.text.strip() or 'poco_f5',
        }
        save_config(self.config)

    def _read_output(self):
        assert self.proc is not None
        for line in self.proc.stdout:  # type: ignore[attr-defined]
            Clock.schedule_once(lambda dt, line=line: self._update_status(line.rstrip()))
        self.proc.wait()
        Clock.schedule_once(lambda dt: self._update_status('Finished'))

    def _update_status(self, text):
        self.status.text = f'Status: {text}'

    def _show_overlay(self, state):
        if self.overlay is None:
            from kivy.uix.floatlayout import FloatLayout
            from kivy.graphics import Color, Rectangle
            from kivy.core.window import Window
            self.overlay = FloatLayout(size_hint=(None, None), size=(90, 90), pos=(20, 20))
            with self.overlay.canvas.before:
                Color(0.1, 0.1, 0.1, 0.9)
                self.overlay_bg = Rectangle(size=self.overlay.size, pos=self.overlay.pos)
            self.overlay.add_widget(Label(text='AI', font_size=20, color=(1, 1, 1, 1)))
            Window.add_widget(self.overlay)
        self.overlay.children[0].text = f'AI {state}'


class AlbionAIApp(App):
    def build(self):
        return HelperController()


if __name__ == '__main__':
    AlbionAIApp().run()
