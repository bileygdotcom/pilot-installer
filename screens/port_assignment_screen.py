#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class PortAssignmentScreen(BaseScreen):
    """
    Экран назначения портов для выбранных компонентов.
    Позволяет изменить порты, нажимая Enter на компоненте.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.components = []  # список [имя, порт]
        self.init_components()
        self.selected_index = 0
        self.scroll_offset = 0
        self.focus_mode = 0  # 0 - список, 1 - кнопки
        self.edit_mode = False  # режим редактирования порта
        self.edit_buffer = ""
        self.edit_y = 0
        self.edit_x = 0

        self.buttons = [
            Button(0, "[ Назначить ]", "continue", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def init_components(self):
        """Заполняет список компонентов, для которых можно назначить порт"""
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
        """Отключаем стандартные инструкции"""
        pass

    def _get_list_height(self):
        """Доступная высота для списка"""
        return max(1, self.height - 8)  # заголовок + инструкция + кнопки

    def _adjust_scroll(self):
        if not self.components:
            return
        list_height = self._get_list_height()
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1

    def draw_content(self):
        """Отрисовывает список компонентов с портами"""
        # Заголовок
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
                if y >= self.height - 4:
                    break
                name, port = self.components[i]
                attr = curses.A_REVERSE if (i == self.selected_index and self.focus_mode == 0) else 0
                line = f"{name}: {port}"
                safe_addstr(self.stdscr, y, 4, line, attr)

            # Индикаторы прокрутки
            if self.scroll_offset > 0:
                safe_addstr(self.stdscr, start_y - 1, 4, "↑ ...")
            if end_idx < len(self.components):
                safe_addstr(self.stdscr, start_y + list_height, 4, "↓ ...")

        # Пояснение
        instr = "Выберите компонент и нажмите Enter для изменения порта"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def handle_input(self):
        if self.edit_mode:
            return self._handle_edit_input()

        self.handle_resize()
        self.draw()

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            # Пока мышь не реализуем для простоты
            pass
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
            # Вход в режим редактирования порта
            if self.components:
                self._start_edit()

    def _start_edit(self):
        """Начинает редактирование порта для выбранного компонента"""
        self.edit_mode = True
        self.edit_buffer = str(self.components[self.selected_index][1])
        # Определяем позицию для поля ввода
        self.edit_y = 6 + (self.selected_index - self.scroll_offset)
        if self.edit_y >= self.height - 4:
            self.edit_y = self.height - 5
        self.edit_x = 4 + len(self.components[self.selected_index][0]) + 2
        curses.curs_set(1)  # показываем курсор
        curses.echo()
        self.stdscr.move(self.edit_y, self.edit_x)

    def _handle_edit_input(self):
        """Обрабатывает ввод в режиме редактирования"""
        curses.echo()
        self.stdscr.move(self.edit_y, self.edit_x)
        # Ограничим ввод только цифрами, но пользователь может ввести и другое
        # Получаем строку
        s = self.stdscr.getstr(self.edit_y, self.edit_x, 5).decode('utf-8')
        curses.noecho()
        curses.curs_set(0)
        self.edit_mode = False
        # Пытаемся преобразовать в число
        try:
            new_port = int(s.strip())
            if 1 <= new_port <= 65535:
                self.components[self.selected_index][1] = new_port
            else:
                # Можно показать сообщение об ошибке, но пока игнорируем
                pass
        except ValueError:
            pass
        self.needs_redraw = True
        return None

    def handle_action(self, action):
        if action == "continue":
            # Сохраняем назначенные порты в app
            self.app.assigned_ports = {name: port for name, port in self.components}
            # Переход к следующему шагу (пока заглушка на проверку Docker)
            self.app.switch_screen("docker_check")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Назначение портов"