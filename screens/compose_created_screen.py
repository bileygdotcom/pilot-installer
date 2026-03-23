#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr
from utils.compose_builder import build_compose, write_compose_file

class ComposeCreatedScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.compose_path = None
        self.buttons = [
            Button(0, "[ Далее ]", "continue", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def on_enter(self):
        stack_path = getattr(self.app, 'stack_path', None)
        if not stack_path:
            self.status = "Ошибка: путь стека не определён"
            self.needs_redraw = True
            return
        # Генерируем compose
        compose_dict = build_compose(self.app)
        write_compose_file(compose_dict, stack_path)
        self.compose_path = os.path.join(stack_path, 'docker-compose.yml')
        self.needs_redraw = True

    def draw_content(self):
        title = " ФАЙЛ СОЗДАН "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        if self.compose_path and os.path.exists(self.compose_path):
            msg1 = "Файл docker-compose.yml успешно создан:"
            safe_addstr(self.stdscr, 7, 4, msg1)
            path_display = self.compose_path
            if len(path_display) > self.width - 10:
                path_display = "..." + path_display[-(self.width-13):]
            safe_addstr(self.stdscr, 8, 4, path_display, curses.A_BOLD)
            safe_addstr(self.stdscr, 10, 4, "Теперь можно перейти к запуску стека.")
        else:
            safe_addstr(self.stdscr, 7, 4, "Ошибка: файл не найден.", curses.color_pair(5))

        instr = "Для продолжения нажмите 'Далее'"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def handle_action(self, action):
        if action == "continue":
            return "next"
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Файл создан"