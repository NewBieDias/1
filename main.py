from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
import threading
import subprocess
import os
import sys


class HelperController(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 12

        self.status = Label(text='Status: idle', size_hint_y=None, height=40)
        self.resource_input = TextInput(text='wood', multiline=False, hint_text='resource name')
        self.mode_spinner = Spinner(text='Loop', values=['Loop', 'One shot'], size_hint_y=None, height=48)
        self.start_button = Button(text='Start helper', size_hint_y=None, height=56)
        self.stop_button = Button(text='Stop helper', size_hint_y=None, height=56)

        self.add_widget(Label(text='Albion Helper', font_size=24))
        self.add_widget(Label(text='Resource name'))
        self.add_widget(self.resource_input)
        self.add_widget(Label(text='Mode'))
        self.add_widget(self.mode_spinner)
        self.add_widget(self.start_button)
        self.add_widget(self.stop_button)
        self.add_widget(self.status)

        self.start_button.bind(on_press=self.start_helper)
        self.stop_button.bind(on_press=self.stop_helper)
        self.proc = None
        self.thread = None

    def start_helper(self, instance):
        if self.proc and self.proc.poll() is None:
            self.status.text = 'Already running'
            return

        resource = self.resource_input.text.strip() or 'wood'
        mode = ['--once'] if self.mode_spinner.text == 'One shot' else []
        cmd = [sys.executable, 'app.py', '--resource', resource] + mode
        self.status.text = f'Starting {resource}...'
        self.proc = subprocess.Popen(cmd, cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.thread = threading.Thread(target=self._read_output, daemon=True)
        self.thread.start()

    def stop_helper(self, instance):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.status.text = 'Stopped'
        else:
            self.status.text = 'Nothing running'

    def _read_output(self):
        assert self.proc is not None
        for line in self.proc.stdout:  # type: ignore[attr-defined]
            Clock.schedule_once(lambda dt, line=line: self._update_status(line.rstrip()))
        self.proc.wait()
        Clock.schedule_once(lambda dt: self._update_status('Finished'))

    def _update_status(self, text):
        self.status.text = f'Status: {text}'


class AlbionHelperApp(App):
    def build(self):
        return HelperController()


if __name__ == '__main__':
    AlbionHelperApp().run()
