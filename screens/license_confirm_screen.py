#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import shutil
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class LicenseConfirmScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.license_path = None
        self.dest_dir = None
        self.dest_file = None
        self.status = "Ожидание..."
        self.error_message = None
        self.copy_success = False
        self.buttons = [
            Button(0, "[ Далее ]", "continue", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.operation_done = False

    def on_enter(self):
        self.license_path = getattr(self.app, 'license_file_path', None)
        if not self.license_path:
            self.status = "Ошибка: файл не выбран"
            self.error_message = "Вернитесь назад и выберите файл лицензии"
            self.operation_done = True
            self.needs_redraw = True
            return

        stack_path = getattr(self.app, 'stack_path', None)
        if not stack_path:
            self.status = "Ошибка: путь стека не определён"
            self.error_message = "Сначала задайте имя стека"
            self.operation_done = True
            self.needs_redraw = True
            return

        self.dest_dir = os.path.join(stack_path, "license")
        self.perform_copy()

    def perform_copy(self):
        if not os.path.exists(self.license_path):
            self.status = "Ошибка: файл не существует"
            self.error_message = f"Файл {self.license_path} не найден"
            self.operation_done = True
            self.needs_redraw = True
            return

        try:
            os.makedirs(self.dest_dir, exist_ok=True)
            filename = os.path.basename(self.license_path)
            self.dest_file = os.path.join(self.dest_dir, filename)
            shutil.copy2(self.license_path, self.dest_file)

            self.status = "✓ Лицензия успешно установлена"
            self.copy_success = True
            self.buttons[0].enabled = True
            self.error_message = None
        except Exception as e:
            self.status = "Ошибка копирования"
            self.error_message = str(e)

        self.operation_done = True
        self.needs_redraw = True

    def draw_content(self):
        title = " УСТАНОВКА ЛИЦЕНЗИИ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 7
        line = 0

        if self.license_path:
            safe_addstr(self.stdscr, start_y + line, 10, "Выбранный файл:", curses.A_BOLD)
            line += 1
            path_display = self.license_path
            if len(path_display) > self.width - 14:
                path_display = "..." + path_display[-(self.width-17):]
            safe_addstr(self.stdscr, start_y + line, 12, path_display)
            line += 2

        safe_addstr(self.stdscr, start_y + line, 10, "Статус:", curses.A_BOLD)
        status_color = curses.color_pair(6) if self.copy_success else curses.color_pair(5)
        safe_addstr(self.stdscr, start_y + line, 20, self.status, status_color)
        line += 2

        if self.error_message:
            safe_addstr(self.stdscr, start_y + line, 10, self.error_message, curses.color_pair(5))
            line += 2

        if self.copy_success and self.dest_file:
            safe_addstr(self.stdscr, start_y + line, 10, "Скопирован в:", curses.A_BOLD)
            line += 1
            dest_display = self.dest_file
            if len(dest_display) > self.width - 14:
                dest_display = "..." + dest_display[-(self.width-17):]
            safe_addstr(self.stdscr, start_y + line, 12, dest_display)

    def handle_input(self):
        if not self.operation_done:
            self.perform_copy()
        return super().handle_input()

    def handle_action(self, action):
        if action == "continue":
            return "next"
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Установка лицензии"