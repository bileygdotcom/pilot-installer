#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class ComposeCreatedScreen(BaseScreen):
    """
    Экран, сообщающий об успешном создании файла docker-compose.yml.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.compose_path = None
        self.buttons = [
            Button(0, "[ Далее ]", "continue", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def on_enter(self):
        """При входе получаем путь к compose-файлу из app"""
        self.compose_path = getattr(self.app, 'compose_dir', None)
        if self.compose_path:
            self.compose_path = os.path.join(self.compose_path, 'docker-compose.yml')
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def draw_content(self):
        title = " ФАЙЛ СОЗДАН "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 7

        if self.compose_path and os.path.exists(self.compose_path):
            msg1 = "Файл docker-compose.yml успешно создан:"
            safe_addstr(self.stdscr, start_y, 4, msg1)

            # Отображаем путь (обрезаем, если слишком длинный)
            path_display = self.compose_path
            if len(path_display) > self.width - 10:
                path_display = "..." + path_display[-(self.width-13):]
            safe_addstr(self.stdscr, start_y + 1, 4, path_display, curses.A_BOLD)

            msg2 = "Теперь можно перейти к запуску стека."
            safe_addstr(self.stdscr, start_y + 3, 4, msg2)
        else:
            safe_addstr(self.stdscr, start_y, 4, "Ошибка: файл не найден.", curses.color_pair(5))

        # Инструкция (минимальная)
        instr = "Для продолжения нажмите 'Далее'"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def handle_action(self, action):
        if action == "continue":
            # Переход к следующему экрану
            self.app.switch_screen("stack_start")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Файл создан"