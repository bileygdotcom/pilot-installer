#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import shutil
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbExistingScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.state = "selecting_db"
        self.selected_db_path = None
        self.selected_fa_path = None
        self.current_path = None
        self.files = []
        self.is_dir = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.filter_ext = []
        self.dialog_message = ""
        self.dialog_buttons = []
        self.current_dialog_button = 0
        self._last_click_time = 0
        self._last_click_index = -1
        self.buttons = []
        self.current_button = 0

    def on_enter(self):
        stack_path = getattr(self.app, 'stack_path', None)
        if not stack_path:
            self.state = "error"
            self.error_message = "Путь стека не определён. Сначала задайте имя стека."
            self.needs_redraw = True
            return
        databases_dir = os.path.join(stack_path, "databases")
        os.makedirs(databases_dir, exist_ok=True)
        self.current_path = databases_dir
        self.state = "selecting_db"
        self.filter_ext = ['.dbp']
        self._load_files()
        self.needs_redraw = True

    def _load_files(self):
        # ... (такая же как раньше, но с self.current_path)
        pass

    def _show_confirm_db(self):
        self.state = "confirm_db"
        self.dialog_message = f"Выбран файл базы данных:\n{self._shorten_path(self.selected_db_path)}"
        self.dialog_buttons = [
            Button(0, "[ OK ]", "confirm_db_ok", enabled=True),
            Button(1, "[ Назад ]", "confirm_db_back", enabled=True)
        ]
        self.current_dialog_button = 0
        self.needs_redraw = True

    def _handle_dialog_action(self, action):
        if action == "confirm_db_ok":
            # Копируем выбранный файл в папку стека
            stack_path = self.app.stack_path
            dest_db = os.path.join(stack_path, "databases", os.path.basename(self.selected_db_path))
            try:
                shutil.copy2(self.selected_db_path, dest_db)
                self.app.existing_db_path = dest_db
            except Exception as e:
                self.error_message = f"Ошибка копирования: {e}"
                self.state = "error"
                self.needs_redraw = True
                return None
            # Переходим к выбору архива
            self.state = "selecting_fa"
            self.current_path = os.path.dirname(self.selected_db_path)  # та же папка
            self.filter_ext = ['.pilotfa']
            self._load_files()
            self.needs_redraw = True
        elif action == "confirm_db_back":
            self.state = "selecting_db"
            self.filter_ext = ['.dbp']
            self._load_files()
            self.needs_redraw = True
        elif action == "confirm_fa_ok":
            # Копируем архив в папку стека
            stack_path = self.app.stack_path
            dest_fa = os.path.join(stack_path, "databases", os.path.basename(self.selected_fa_path))
            try:
                shutil.copy2(self.selected_fa_path, dest_fa)
                self.app.existing_fa_path = dest_fa
            except Exception as e:
                self.error_message = f"Ошибка копирования: {e}"
                self.state = "error"
                self.needs_redraw = True
                return None
            return "next"
        # ...