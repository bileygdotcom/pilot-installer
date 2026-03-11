#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class PortAssignmentScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.components = []  # будет заполнено в on_enter
        self.selected_index = 0
        self.scroll_offset = 0
        self.focus_mode = 0
        self.edit_mode = False
        self.edit_buffer = ""
        self.edit_y = 0
        self.edit_x = 0

        # Для определения двойного клика
        self._last_click_time = 0
        self._last_click_index = -1

        self.buttons = [
            Button(0, "[ Назначить ]", "continue", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def on_enter(self):
        self.components = []
        self.init_components()
        self.selected_index = 0
        self.scroll_offset = 0
        self.focus_mode = 0
        self.needs_redraw = True

    def init_components(self):
        selected = getattr(self.app, 'selected_components', [])
        default_ports = {
            "Pilot-Server": 5551,
            "Pilot-Web-myAdmin": 5552,
            "Pilot-Web-Server": 5553,
            "Pilot-TextSearch-Server": 5554
        }
        for comp in selected:
            if comp in default_ports:
                self.components.append([comp, default_ports[comp]])

    def draw_instructions(self):
        pass

    def _get_list_height(self):
        return max(1, self.height - 8)

    def _adjust_scroll(self):
        if not self.components:
            return
        list_height = self._get_list_height()
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1

    def draw_content(self):
        title = " НАЗНАЧЕНИЕ ПОРТОВ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 6
        list_height = self._get_list_height()
        end_idx = min(len(self.components), self.scroll_offset + list_height)

        if not self.components:
            safe_addstr(self.stdscr, start_y, 4, "Нет компонентов для настройки портов")
        else:
            for i in range(self.scroll_offset, end_idx):
                y = start_y + (i - self.scroll_offset)
                if y >= self.height - 3:  # оставляем место для инструкции
                    break
                name, port = self.components[i]
                attr = curses.A_REVERSE if (i == self.selected_index and self.focus_mode == 0) else 0
                line = f"{name}: {port}"
                safe_addstr(self.stdscr, y, 4, line, attr)

            if self.scroll_offset > 0:
                safe_addstr(self.stdscr, start_y - 1, 4, "↑ ...")
            if end_idx < len(self.components):
                safe_addstr(self.stdscr, start_y + list_height, 4, "↓ ...")

        # Инструкция на предпоследней строке (над статусной строкой)
        instr = "Выберите компонент и нажмите Enter для изменения порта"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 2, 4, instr, curses.color_pair(4))

    def handle_mouse(self):
        """Обрабатывает события мыши: клики по кнопкам и по списку."""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            # 1. Проверяем кнопки
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

            # 2. Если не кнопки, проверяем клик в области списка
            list_start_y = 6
            list_height = self._get_list_height()
            list_end_y = list_start_y + list_height

            if list_start_y <= my < list_end_y and self.components:
                index = self.scroll_offset + (my - list_start_y)
                if 0 <= index < len(self.components):
                    # Определяем двойной клик по времени
                    is_double_click = (index == self._last_click_index and
                                       current_time - self._last_click_time < 0.5)
                    self._last_click_time = current_time
                    self._last_click_index = index

                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        # Одиночный клик: выделяем элемент
                        self.selected_index = index
                        self._adjust_scroll()
                        self.focus_mode = 0
                        self.needs_redraw = True

                        # Двойной клик: запускаем редактирование
                        if is_double_click:
                            self._start_edit()
                    return None
            return None
        except:
            return None

    def handle_input(self):
        if self.edit_mode:
            return self._handle_edit_input()

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
                self._adjust_scroll()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.selected_index < len(self.components) - 1:
                self.selected_index += 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            if self.components:
                self._start_edit()

    def _start_edit(self):
        self.edit_mode = True
        self.edit_buffer = str(self.components[self.selected_index][1])
        self.edit_y = 6 + (self.selected_index - self.scroll_offset)
        if self.edit_y >= self.height - 3:
            self.edit_y = self.height - 4
        self.edit_x = 4 + len(self.components[self.selected_index][0]) + 2
        curses.curs_set(1)
        curses.echo()
        self.stdscr.move(self.edit_y, self.edit_x)

    def _handle_edit_input(self):
        curses.echo()
        self.stdscr.move(self.edit_y, self.edit_x)
        s = self.stdscr.getstr(self.edit_y, self.edit_x, 5).decode('utf-8')
        curses.noecho()
        curses.curs_set(0)
        self.edit_mode = False
        try:
            new_port = int(s.strip())
            if 1 <= new_port <= 65535:
                self.components[self.selected_index][1] = new_port
        except ValueError:
            pass
        self.needs_redraw = True
        return None

    def handle_action(self, action):
        if action == "continue":
            self.app.assigned_ports = {name: port for name, port in self.components}
            self.app.switch_screen("db_option")  # переход
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Назначение портов"