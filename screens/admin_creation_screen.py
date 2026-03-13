#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class AdminCreationScreen(BaseScreen):
    """
    Экран создания администраторов для выбранных компонентов.
    Отображает таблицу: компонент, логин, пароль (скрыт).
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.components = []          # список отображаемых компонентов
        self.credentials = {}          # {компонент: {"login": "", "password": ""}}
        self.selected_row = 0
        self.selected_col = 0          # 0 - логин, 1 - пароль
        self.focus_mode = 0             # 0 - таблица, 1 - кнопки
        self.editing = False            # режим редактирования ячейки
        self.edit_buffer = ""
        self.edit_y = 0
        self.edit_x = 0
        self.edit_col = 0               # для определения, пароль ли

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

        self.buttons = [
            Button(0, "[ Создать ]", "create", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def on_enter(self):
        """При входе загружаем выбранные компоненты"""
        selected = getattr(self.app, 'selected_components', [])
        # Оставляем только серверные компоненты (Pilot-Server, Pilot-BIM-Server, Pilot-TextSearch-Server)
        allowed = ["Pilot-Server", "Pilot-BIM-Server", "Pilot-TextSearch-Server"]
        self.components = [comp for comp in selected if comp in allowed]
        self.credentials = {comp: {"login": "", "password": ""} for comp in self.components}
        self.selected_row = 0
        self.selected_col = 0
        self.focus_mode = 0
        self.editing = False
        self._update_create_button()
        self.needs_redraw = True

    def _update_create_button(self):
        """Активирует кнопку 'Создать', если все поля заполнены"""
        all_filled = all(
            self.credentials[comp]["login"].strip() and self.credentials[comp]["password"].strip()
            for comp in self.components
        )
        self.buttons[0].enabled = all_filled

    def draw_instructions(self):
        pass

    def _get_table_start_y(self):
        return 6

    def _get_row_y(self, row):
        return self._get_table_start_y() + row

    def _get_login_x(self):
        # Колонка компонента теперь занимает 30 символов (от 4 до 33)
        return 34

    def _get_password_x(self):
        return 50

    def draw_content(self):
        title = " СОЗДАНИЕ АДМИНИСТРАТОРОВ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        if not self.components:
            safe_addstr(self.stdscr, 6, 4, "Нет компонентов для настройки администраторов")
            return

        # Заголовки таблицы
        safe_addstr(self.stdscr, 5, 4, "Компонент", curses.A_BOLD)
        safe_addstr(self.stdscr, 5, self._get_login_x(), "Логин", curses.A_BOLD)
        safe_addstr(self.stdscr, 5, self._get_password_x(), "Пароль", curses.A_BOLD)

        # Строки
        for i, comp in enumerate(self.components):
            y = self._get_row_y(i)
            if y >= self.height - 4:
                break

            # Компонент — выводим полностью (макс 30 символов)
            safe_addstr(self.stdscr, y, 4, comp[:30])

            # Логин
            login = self.credentials[comp]["login"]
            login_display = login if not self.editing or not (i == self.selected_row and self.selected_col == 0) else login
            attr_login = curses.A_REVERSE if (i == self.selected_row and self.selected_col == 0 and self.focus_mode == 0 and not self.editing) else 0
            safe_addstr(self.stdscr, y, self._get_login_x(), login_display.ljust(15)[:15], attr_login)

            # Пароль (скрыт звёздочками)
            pwd = self.credentials[comp]["password"]
            pwd_display = "*" * len(pwd) if pwd else ""
            attr_pwd = curses.A_REVERSE if (i == self.selected_row and self.selected_col == 1 and self.focus_mode == 0 and not self.editing) else 0
            safe_addstr(self.stdscr, y, self._get_password_x(), pwd_display.ljust(15)[:15], attr_pwd)

        # Инструкция
        instr = "↑↓: выбор строки | ←→: выбор колонки | Enter: редактировать | TAB: переключение на кнопки"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def handle_mouse(self):
        """Обработка мыши: клики по ячейкам таблицы и кнопкам"""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            # Сначала кнопки
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

            # Клик по таблице (если не редактируем)
            if not self.editing and self.focus_mode == 0:
                start_y = self._get_table_start_y()
                for i, comp in enumerate(self.components):
                    y = start_y + i
                    if y < 0 or y >= self.height:
                        continue
                    if my == y:
                        # Проверяем колонку логина (от 34 до 48)
                        if 34 <= mx <= 48:
                            self.selected_row = i
                            self.selected_col = 0
                            self.needs_redraw = True
                            if bstate & curses.BUTTON1_DOUBLE_CLICKED:
                                self._start_edit()
                            return None
                        # Проверяем колонку пароля (от 50 до 64)
                        elif 50 <= mx <= 64:
                            self.selected_row = i
                            self.selected_col = 1
                            self.needs_redraw = True
                            if bstate & curses.BUTTON1_DOUBLE_CLICKED:
                                self._start_edit()
                            return None
        except:
            pass
        return None

    def handle_input(self):
        if self.editing:
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
            self._handle_table_keys(key)
        else:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def _handle_table_keys(self, key):
        if key == curses.KEY_UP:
            if self.selected_row > 0:
                self.selected_row -= 1
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.selected_row < len(self.components) - 1:
                self.selected_row += 1
                self.needs_redraw = True
        elif key == curses.KEY_LEFT:
            if self.selected_col > 0:
                self.selected_col -= 1
                self.needs_redraw = True
        elif key == curses.KEY_RIGHT:
            if self.selected_col < 1:
                self.selected_col += 1
                self.needs_redraw = True
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            self._start_edit()

    def _start_edit(self):
        """Начинает редактирование выбранной ячейки"""
        comp = self.components[self.selected_row]
        if self.selected_col == 0:
            self.edit_buffer = self.credentials[comp]["login"]
        else:
            self.edit_buffer = self.credentials[comp]["password"]
        self.editing = True
        self.edit_col = self.selected_col
        # Определяем позицию для поля ввода
        y = self._get_row_y(self.selected_row)
        x = self._get_login_x() if self.selected_col == 0 else self._get_password_x()
        self.edit_y = y
        self.edit_x = x
        curses.curs_set(1)
        curses.echo()
        self.stdscr.move(y, x)

    def _handle_edit_input(self):
        """Обрабатывает ввод в режиме редактирования"""
        curses.echo()
        self.stdscr.move(self.edit_y, self.edit_x)
        s = self.stdscr.getstr(self.edit_y, self.edit_x, 15).decode('utf-8')
        curses.noecho()
        curses.curs_set(0)
        self.editing = False

        comp = self.components[self.selected_row]
        if self.edit_col == 0:
            self.credentials[comp]["login"] = s
        else:
            self.credentials[comp]["password"] = s

        self._update_create_button()
        self.needs_redraw = True
        return None

    def handle_action(self, action):
        if action == "create":
            # Сохраняем данные в app
            self.app.admin_credentials = self.credentials
            # Переход к следующему экрану (замените на нужный)
            self.app.switch_screen("db_option")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Создание администраторов"