#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI компоненты для терминального интерфейса
"""

import curses
from utils.terminal import safe_addstr

class Button:
    def __init__(self, index, text, action, enabled=True):
        self.index = index
        self.text = text
        self.action = action
        self.enabled = enabled

    def draw(self, stdscr, x, y, is_active=False):
        """Рисует кнопку. Если disabled, используется серый цвет и is_active игнорируется."""
        if not self.enabled:
            attr = curses.color_pair(2)  # неактивный цвет
        elif is_active:
            attr = curses.color_pair(1) | curses.A_BOLD
        else:
            attr = curses.color_pair(2)

        safe_addstr(stdscr, y, x, self.text, attr)


def draw_border(stdscr, height, width):
    """Рисует рамку вокруг экрана"""
    if height >= 3 and width >= 3:
        try:
            stdscr.border(0)
        except curses.error:
            pass


def draw_header(stdscr, width, header_text):
    """Рисует заголовок приложения"""
    x = max(0, (width - len(header_text)) // 2)
    safe_addstr(stdscr, 2, x, header_text, curses.color_pair(3) | curses.A_BOLD)


def draw_instructions(stdscr, height, width):
    """Рисует инструкции по навигации"""
    instructions = " TAB / Стрелки: навигация • ENTER: выбор • Мышь: клик "
    x = max(0, (width - len(instructions)) // 2)
    y = height - 2
    if y > 0:
        safe_addstr(stdscr, y, x, instructions, curses.color_pair(4))


def draw_status_line(stdscr, height, width, status_text):
    """Рисует строку состояния"""
    if width < 80 or height < 24:
        status_text = " ⚠ Рекомендуемый размер: 80x24 " + status_text
        attr = curses.color_pair(5) | curses.A_REVERSE
    else:
        attr = curses.A_REVERSE

    safe_addstr(stdscr, height - 1, 0, status_text[:width - 1], attr)