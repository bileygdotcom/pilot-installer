#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class ComponentsSelectionScreen(BaseScreen):
    """
    Экран выбора компонентов Pilot-BIM для установки.
    Отображает список компонентов с чекбоксами (галочка ✓).
    Поддерживает мышь, клавиатуру, прокрутку.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        # Список компонентов в нужном порядке: (отображаемое имя, выбрано ли по умолчанию)
        self.components = [
            ("Pilot-Server", True),
            ("Pilot-Web-myAdmin", True),
            ("Pilot-Web-Server", True),
            ("Pilot-BIM-Server", True),
            ("Pilot-TextSearch-Server", True),
            ("NGINX", True)
        ]
        self.selected_index = 0  # текущая позиция в списке
        self.scroll_offset = 0
        self.focus_mode = 0  # 0 - список, 1 - кнопки

        # Для мыши (защита от множественных событий)
        self._last_click_time = 0
        self._last_click_index = -1

        # Кнопки: Установить и Выход
        self.buttons = [
            Button(0, "[ Установить ]", "continue", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def draw_instructions(self):
        """Отключаем стандартные инструкции BaseScreen, рисуем свои в draw_content"""
        pass

    def _adjust_scroll(self):
        """Корректирует прокрутку, чтобы выделенный элемент был виден"""
        if not self.components:
            return
        list_height = self._get_list_height()
        if list_height <= 0:
            return
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1

    def _get_list_height(self):
        """Возвращает доступную высоту для списка (с учётом заголовка и места под инструкцию)"""
        # Заголовок на y=4, список начинается с y=6, заканчивается перед инструкцией (self.height-2)
        return max(1, self.height - 6 - 4)

    def draw_content(self):
        """Отрисовывает список компонентов"""
        # Заголовок
        title = " ВЫБОР КОМПОНЕНТОВ PILOT "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 6
        list_height = self._get_list_height()
        end_idx = min(len(self.components), self.scroll_offset + list_height)

        for i in range(self.scroll_offset, end_idx):
            y = start_y + (i - self.scroll_offset)
            if y >= self.height - 3:  # оставляем место для инструкции
                break
            comp_name, checked = self.components[i]
            # Используем галочку ✓ для отмеченных, пробел для пустых
            checkbox = "[✓]" if checked else "[ ]"
            attr = curses.A_REVERSE if (i == self.selected_index and self.focus_mode == 0) else 0
            line = f"{checkbox} {comp_name}"
            safe_addstr(self.stdscr, y, 4, line, attr)

        # Индикаторы прокрутки
        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, start_y - 1, 4, "↑ ...")
        if end_idx < len(self.components):
            safe_addstr(self.stdscr, start_y + list_height, 4, "↓ ...")

        # Единая инструкция внизу экрана (на предпоследней строке, над статусной строкой)
        instr = "↑↓: перемещение | Пробел/Enter/клик: выбор | TAB: переключение на кнопки"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 2, 4, instr, curses.color_pair(4))

    def handle_mouse(self):
        """Обрабатывает события мыши: клики по списку и по кнопкам"""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            # Сначала проверяем кнопки
            button_positions = self.get_button_positions()
            for i, pos in enumerate(button_positions):
                if my == pos['y'] and pos['x1'] <= mx <= pos['x2']:
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        if self.buttons[i].enabled:
                            self.current_button = i
                            self.focus_mode = 1  # переключаем фокус на кнопки
                            self.needs_redraw = True
                            return self.buttons[i].action
                    return None

            # Если не кнопка, проверяем клик в области списка
            list_start_y = 6
            list_height = self._get_list_height()
            list_end_y = list_start_y + list_height

            if list_start_y <= my < list_end_y and self.components:
                index = self.scroll_offset + (my - list_start_y)
                if 0 <= index < len(self.components):
                    # Защита от повторных событий
                    if current_time - self._last_click_time < 0.1 and index == self._last_click_index:
                        return None
                    self._last_click_time = current_time
                    self._last_click_index = index

                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        # Переключаем состояние чекбокса
                        name, checked = self.components[index]
                        self.components[index] = (name, not checked)
                        self.selected_index = index
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
            if self.selected_index > 0:
                self.selected_index -= 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.selected_index < len(self.components) - 1:
                self.selected_index += 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key in (ord(' '), ord('\n'), ord('\r'), curses.KEY_ENTER):
            # Пробел или Enter переключают чекбокс
            name, checked = self.components[self.selected_index]
            self.components[self.selected_index] = (name, not checked)
            self.needs_redraw = True

    def handle_action(self, action):
        if action == "continue":
            # Сохраняем выбранные компоненты в app
            selected = [name for name, checked in self.components if checked]
            self.app.selected_components = selected
            # Переходим к назначению портов
            self.app.switch_screen("port_assignment")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Выбор компонентов"