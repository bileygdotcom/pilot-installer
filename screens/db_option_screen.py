#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbOptionScreen(BaseScreen):
    """
    Экран выбора опции базы данных:
    - Загрузить и установить демонстрационную базу Pilot.
    - Выбрать существующую базу.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.options = [
            "Загрузить и установить демонстрационную базу Pilot.",
            "Выбрать существующую базу"
        ]
        self.selected_option = 0
        self.scroll_offset = 0
        self.focus_mode = 0  # 0 - список, 1 - кнопки

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

        self.buttons = [
            Button(0, "[ Выбрать ]", "select", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def draw_instructions(self):
        pass

    def _get_list_height(self):
        return max(1, self.height - 8)

    def _adjust_scroll(self):
        list_height = self._get_list_height()
        if self.selected_option < self.scroll_offset:
            self.scroll_offset = self.selected_option
        elif self.selected_option >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_option - list_height + 1

    def draw_content(self):
        title = " ВЫБОР БАЗЫ ДАННЫХ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 6
        list_height = self._get_list_height()
        end_idx = min(len(self.options), self.scroll_offset + list_height)

        for i in range(self.scroll_offset, end_idx):
            y = start_y + (i - self.scroll_offset)
            if y >= self.height - 4:
                break
            option = self.options[i]
            # Радио-кнопка: (*) для выбранного, ( ) для остальных
            radio = "(*)" if i == self.selected_option else "( )"
            attr = curses.A_REVERSE if (i == self.selected_option and self.focus_mode == 0) else 0
            line = f"{radio} {option}"
            safe_addstr(self.stdscr, y, 4, line, attr)

        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, start_y - 1, 4, "↑ ...")
        if end_idx < len(self.options):
            safe_addstr(self.stdscr, start_y + list_height, 4, "↓ ...")

        instr = "↑↓: выбор | Пробел/Enter/клик: выбор | TAB: переключение на кнопки"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def handle_mouse(self):
        """Обрабатывает мышь: клики по списку и кнопкам"""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            # Кнопки
            button_positions = self.get_button_positions()
            for i, pos in enumerate(button_positions):
                if my == pos['y'] and pos['x1'] <= mx <= pos['x2']:
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        if self.buttons[i].enabled:
                            self.current_button = i
                            self.focus_mode = 1
                            self.needs_redraw = True
                            return self.buttons[i].action
                    return None

            # Список
            list_start_y = 6
            list_height = self._get_list_height()
            list_end_y = list_start_y + list_height
            if list_start_y <= my < list_end_y and self.options:
                index = self.scroll_offset + (my - list_start_y)
                if 0 <= index < len(self.options):
                    # Защита от повторных событий
                    if current_time - self._last_click_time < 0.1 and index == self._last_click_index:
                        return None
                    self._last_click_time = current_time
                    self._last_click_index = index
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        self.selected_option = index
                        self._adjust_scroll()
                        self.focus_mode = 0
                        self.needs_redraw = True
            return None
        except:
            return None

    def handle_input(self):
        self.handle_resize()
        self.draw()

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            result = self.handle_mouse()
            if result:
                return self.handle_action(result)
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:  # TAB
            self.focus_mode = (self.focus_mode + 1) % 2
            self.needs_redraw = True
        elif self.focus_mode == 0:
            self._handle_list_keys(key)
        else:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def _handle_list_keys(self, key):
        if key == curses.KEY_UP:
            if self.selected_option > 0:
                self.selected_option -= 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.selected_option < len(self.options) - 1:
                self.selected_option += 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key in (ord(' '), ord('\n'), ord('\r'), curses.KEY_ENTER):
            # Пробел или Enter просто подтверждают выбор (фактически выделение уже есть)
            self.needs_redraw = True

    def handle_action(self, action):
        if action == "select":
            if self.selected_option == 0:
                self.app.switch_screen("db_demo")
            elif self.selected_option == 1:
                self.app.switch_screen("db_existing")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Выбор базы данных"