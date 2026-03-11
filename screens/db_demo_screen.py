#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DBDemoScreen(BaseScreen):
    """Экран выбора демонстрационной базы данных (заглушка)."""
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.buttons = [
            Button(0, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def draw_instructions(self):
        pass

    def draw_content(self):
        title = " ВЫБОР ДЕМОНСТРАЦИОННОЙ БАЗЫ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        msg = "Здесь будет список доступных демо-баз."
        x = max(0, (self.width - len(msg)) // 2)
        safe_addstr(self.stdscr, 7, x, msg)

        instr = "В разработке. Нажмите Выход для возврата."
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, 9, x, instr, curses.color_pair(4))

    def get_screen_name(self):
        return "Выбор демо-базы"