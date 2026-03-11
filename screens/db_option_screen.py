#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbOptionScreen(BaseScreen):
    """
    Экран выбора опции работы с базой данных.
    Радиокнопки: загрузить демо-базу или выбрать существующую.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.options = [
            ("Загрузить и установить демонстрационную базу Pilot.", True),  # выбрано по умолчанию
            ("Выбрать существующую базу", False)
        ]
        self.selected_index = 0  # индекс выбранной опции (для радиокнопок)
        self.selected_option = 0
        self.focus_mode = 0      # 0 - список, 1 - кнопки

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

        self.buttons = [
            Button(0, "[ Выбрать ]", "select", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def draw_instructions(self):
        # Отключаем стандартные инструкции
        pass

    def draw_content(self):
        title = " ВЫБОР БАЗЫ ДАННЫХ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 7
        for i, (text, selected) in enumerate(self.options):
            y = start_y + i * 2  # через одну строку для читаемости
            if y >= self.height - 6:
                break
            radio = "(*)" if selected else "( )"
            attr = curses.A_REVERSE if (i == self.selected_index and self.focus_mode == 0) else 0
            line = f"{radio} {text}"
            safe_addstr(self.stdscr, y, 6, line, attr)

        # Инструкция внизу (только про радиокнопки)
        instr = "↑↓: выбор опции | Пробел/Enter/клик: переключение | TAB: к кнопкам"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def handle_mouse(self):
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            # Проверяем кнопки
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

            # Проверяем область радиокнопок
            list_start_y = 7
            for i in range(len(self.options)):
                y = list_start_y + i * 2
                if y >= self.height - 6:
                    break
                # Примерная область строки (можно расширить)
                if my == y and 6 <= mx <= 6 + len(self.options[i][0]) + 4:
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        # Защита от повторных событий
                        if current_time - self._last_click_time < 0.1 and i == self._last_click_index:
                            return None
                        self._last_click_time = current_time
                        self._last_click_index = i

                        # Устанавливаем выбранную опцию (радио)
                        for j in range(len(self.options)):
                            self.options[j] = (self.options[j][0], j == i)
                        self.selected_index = i
                        self.focus_mode = 0
                        self.needs_redraw = True
                    return None
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
            if self.selected_index > 0:
                self.selected_index -= 1
                self._update_radio()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.selected_index < len(self.options) - 1:
                self.selected_index += 1
                self._update_radio()
                self.needs_redraw = True
        elif key in (ord(' '), ord('\n'), ord('\r'), curses.KEY_ENTER):
            self._update_radio()  # уже обновлено при перемещении, но на всякий случай

    def _update_radio(self):
        """Обновляет радиокнопки в соответствии с выбранным индексом"""
        for i in range(len(self.options)):
            self.options[i] = (self.options[i][0], i == self.selected_index)

    def handle_action(self, action):
        if action == "select":
            if self.selected_option == 0:
                # Переход на экран загрузки демо-базы
                self.app.switch_screen("db_demo")
            elif self.selected_option == 1:
                # Переход на экран выбора существующей базы (пока заглушка)
                self.app.switch_screen("db_existing")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Выбор базы данных"