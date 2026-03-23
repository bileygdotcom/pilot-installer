#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import time
import threading
import urllib.request
import zipfile
import tempfile
import shutil
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbDemoScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.state = "downloading"
        self.progress = 0
        self.status_message = ""
        self.error_message = None
        self.download_thread = None
        self.extract_thread = None
        self.databases = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.focus_mode = 0
        self.temp_dir = None
        self.extract_dir = None
        self._last_click_time = 0
        self._last_click_index = -1

        self.buttons = [
            Button(0, "[ Выбор ]", "select", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def on_enter(self):
        stack_path = getattr(self.app, 'stack_path', None)
        if not stack_path:
            self.error_message = "Путь стека не определён. Сначала задайте имя стека."
            self.state = "error"
            self.needs_redraw = True
            return

        self.extract_dir = os.path.join(stack_path, "databases")
        self.state = "downloading"
        self.progress = 0
        self.status_message = "Подготовка к скачиванию..."
        self.error_message = None
        self.databases = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.focus_mode = 0
        self.buttons[0].enabled = False
        self.needs_redraw = True

        self.temp_dir = tempfile.mkdtemp(prefix="pilot_demo_")
        self.start_download()

    def start_download(self):
        # ... (оставляем как было, но используем self.extract_dir)
        pass

    def start_extract(self, zip_path):
        # ... (оставляем как было, но используем self.extract_dir)
        pass

    def scan_databases(self):
        # Ищем папку Databases внутри self.extract_dir
        databases_container = os.path.join(self.extract_dir, "Databases")
        if not os.path.exists(databases_container):
            self.error_message = "Папка Databases не найдена после распаковки"
            self.state = "error"
            self.needs_redraw = True
            return

        items = os.listdir(databases_container)
        dirs = [item for item in items if os.path.isdir(os.path.join(databases_container, item))]
        if dirs:
            self.databases = dirs
            self.selected_index = 0
            self.state = "selecting"
            self.buttons[0].enabled = True
        else:
            self.error_message = "В папке Databases нет подпапок с базами данных"
            self.state = "error"
        self.needs_redraw = True

    def handle_action(self, action):
        if action == "select":
            if self.state == "selecting" and self.databases:
                self.app.selected_demo_db = self.databases[self.selected_index]
                return "next"
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Демо-база данных"