#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbExistingScreen(BaseScreen):
    """
    Экран выбора существующей базы данных.
    Последовательно выбирает файл базы данных (.dbp) и файл файлового архива (.pilotfa).
    После каждого выбора показывает диалог подтверждения.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.state = "selecting_db"  # selecting_db, confirm_db, selecting_fa, confirm_fa
        self.selected_db_path = None
        self.selected_fa_path = None
        self.db_filename = None
        self.fa_filename = None
        self.last_db_path = None  # для запоминания папки после выбора .dbp

        # Для выбора файла
        self.current_path = os.path.expanduser("~")
        self.files = []
        self.is_dir = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.filter_ext = []  # текущий фильтр
        self.picker_title = "Выбор файла базы данных"  # по умолчанию

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

        # Диалог
        self.dialog_message = ""
        self.dialog_buttons = []
        self.current_dialog_button = 0

        # Основные кнопки экрана (не используются)
        self.buttons = []
        self.current_button = 0

    def on_enter(self):
        """При входе начинаем с выбора файла базы данных"""
        self.state = "selecting_db"
        self.selected_db_path = None
        self.selected_fa_path = None
        self.last_db_path = None
        self.current_path = os.path.expanduser("~")
        self.filter_ext = ['.dbp']
        self.picker_title = "Выбор файла базы данных"
        self._load_files()
        self.needs_redraw = True

    def _load_files(self):
        """Загружает список файлов и папок из current_path с учётом фильтра"""
        try:
            entries = os.listdir(self.current_path)
        except PermissionError:
            self.files = []
            self.is_dir = []
            return

        dirs = []
        files = []
        for entry in entries:
            full = os.path.join(self.current_path, entry)
            try:
                if os.path.isdir(full):
                    dirs.append(entry)
                else:
                    ext = os.path.splitext(entry)[1].lower()
                    if self.filter_ext and ext in self.filter_ext:
                        files.append(entry)
                    elif not self.filter_ext:
                        files.append(entry)
            except OSError:
                continue

        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        self.files = dirs + files
        self.is_dir = [True] * len(dirs) + [False] * len(files)

        if self.files:
            if self.selected_index >= len(self.files):
                self.selected_index = len(self.files) - 1
            self._adjust_scroll()
        else:
            self.selected_index = 0
            self.scroll_offset = 0

    def _adjust_scroll(self):
        if not self.files:
            return
        list_height = self._get_list_height()
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1

    def _get_list_height(self):
        # Высота списка: от y=8 до self.height-4 (место под инструкцию)
        return max(1, self.height - 12)

    def draw_instructions(self):
        pass

    def draw_content(self):
        """Отрисовывает содержимое в зависимости от состояния"""
        # Заголовок окна меняется в зависимости от этапа
        if self.state in ("selecting_db", "confirm_db"):
            title = self.picker_title
        elif self.state in ("selecting_fa", "confirm_fa"):
            title = self.picker_title
        else:
            title = "ВЫБОР СУЩЕСТВУЮЩЕЙ БАЗЫ"

        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        if self.state in ("selecting_db", "selecting_fa"):
            self._draw_file_picker()
        elif self.state in ("confirm_db", "confirm_fa"):
            self._draw_dialog()

    def _draw_file_picker(self):
        """Рисует интерфейс выбора файла"""
        # Текущий путь
        path_display = self.current_path
        if len(path_display) > self.width - 10:
            path_display = "..." + path_display[-(self.width-13):]
        safe_addstr(self.stdscr, 6, 4, "Путь: " + path_display)

        list_start_y = 8
        list_height = self._get_list_height()
        end_idx = min(len(self.files), self.scroll_offset + list_height)

        for i in range(self.scroll_offset, end_idx):
            y = list_start_y + (i - self.scroll_offset)
            if y >= self.height - 4:  # оставляем место для инструкции
                break
            prefix = "📁 " if self.is_dir[i] else "📄 "
            filename = self.files[i]
            max_len = self.width - 6
            if len(filename) > max_len:
                filename = filename[:max_len-3] + "..."
            attr = curses.A_REVERSE if i == self.selected_index else 0
            safe_addstr(self.stdscr, y, 4, prefix + filename, attr)

        # Индикаторы прокрутки
        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, list_start_y - 1, 4, "↑ ...")
        if end_idx < len(self.files):
            safe_addstr(self.stdscr, list_start_y + list_height, 4, "↓ ...")

        # Инструкция
        instr = "↑↓: выбор | Enter: открыть папку / выбрать файл | Backspace: назад"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def _draw_dialog(self):
        """Рисует диалог подтверждения"""
        win_height = 8
        win_width = min(60, self.width - 10)
        start_y = (self.height - win_height) // 2
        start_x = (self.width - win_width) // 2

        # Рамка
        for y in range(start_y, start_y + win_height):
            for x in range(start_x, start_x + win_width):
                try:
                    if y == start_y or y == start_y + win_height - 1:
                        self.stdscr.addch(y, x, curses.ACS_HLINE)
                    elif x == start_x or x == start_x + win_width - 1:
                        self.stdscr.addch(y, x, curses.ACS_VLINE)
                except:
                    pass
        self.stdscr.addch(start_y, start_x, curses.ACS_ULCORNER)
        self.stdscr.addch(start_y, start_x + win_width - 1, curses.ACS_URCORNER)
        self.stdscr.addch(start_y + win_height - 1, start_x, curses.ACS_LLCORNER)
        self.stdscr.addch(start_y + win_height - 1, start_x + win_width - 1, curses.ACS_LRCORNER)

        # Сообщение
        lines = self.dialog_message.split('\n')
        for i, line in enumerate(lines):
            if i >= win_height - 3:
                break
            x = start_x + 2
            y = start_y + 1 + i
            safe_addstr(self.stdscr, y, x, line[:win_width-4])

        # Кнопки
        button_y = start_y + win_height - 2
        total_width = sum(len(b.text) for b in self.dialog_buttons) + 4 * (len(self.dialog_buttons) - 1)
        button_start_x = start_x + (win_width - total_width) // 2
        for i, button in enumerate(self.dialog_buttons):
            x = button_start_x + i * (len(button.text) + 4)
            is_active = (i == self.current_dialog_button)
            button.draw(self.stdscr, x, button_y, is_active)

    def handle_input(self):
        self.handle_resize()
        self.draw()

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            result = self._handle_mouse()
            if result:
                return self.handle_action(result)
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:  # TAB
            if self.state in ("confirm_db", "confirm_fa"):
                self.current_dialog_button = (self.current_dialog_button + 1) % len(self.dialog_buttons)
                self.needs_redraw = True
        elif key == 27:  # ESC
            return "exit"
        else:
            if self.state in ("selecting_db", "selecting_fa"):
                self._handle_file_keys(key)
            elif self.state in ("confirm_db", "confirm_fa"):
                if key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
                    action = self.dialog_buttons[self.current_dialog_button].action
                    return self._handle_dialog_action(action)
        return None

    def _handle_file_keys(self, key):
        if key == curses.KEY_UP:
            if self.selected_index > 0:
                self.selected_index -= 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.selected_index < len(self.files) - 1:
                self.selected_index += 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            if self.files:
                selected = self.files[self.selected_index]
                full = os.path.join(self.current_path, selected)
                if self.is_dir[self.selected_index]:
                    # Переход в папку
                    self.current_path = full
                    self._load_files()
                    self.selected_index = 0
                    self.needs_redraw = True
                else:
                    # Выбран файл
                    if self.state == "selecting_db":
                        self.selected_db_path = full
                        self.db_filename = selected
                        self._show_confirm_db()
                    else:  # selecting_fa
                        self.selected_fa_path = full
                        self.fa_filename = selected
                        self._show_confirm_fa()
        elif key in (127, curses.KEY_BACKSPACE, 8):  # Backspace
            parent = os.path.dirname(self.current_path)
            if parent and parent != self.current_path:
                self.current_path = parent
                self._load_files()
                self.selected_index = 0
                self.needs_redraw = True

    def _handle_mouse(self):
        """Обрабатывает мышь в режиме выбора файла или диалога"""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            if self.state in ("selecting_db", "selecting_fa"):
                # Клик в области списка
                list_start_y = 8
                list_height = self._get_list_height()
                list_end_y = list_start_y + list_height
                if list_start_y <= my < list_end_y and self.files:
                    index = self.scroll_offset + (my - list_start_y)
                    if 0 <= index < len(self.files):
                        # Защита от повторных событий
                        if current_time - self._last_click_time < 0.1 and index == self._last_click_index:
                            return None
                        self._last_click_time = current_time
                        self._last_click_index = index
                        if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                            self.selected_index = index
                            self.needs_redraw = True
                            # Двойной клик по файлу или папке
                            if bstate & curses.BUTTON1_DOUBLE_CLICKED:
                                selected = self.files[index]
                                full = os.path.join(self.current_path, selected)
                                if self.is_dir[index]:
                                    self.current_path = full
                                    self._load_files()
                                    self.selected_index = 0
                                    self.needs_redraw = True
                                else:
                                    if self.state == "selecting_db":
                                        self.selected_db_path = full
                                        self.db_filename = selected
                                        self._show_confirm_db()
                                    else:
                                        self.selected_fa_path = full
                                        self.fa_filename = selected
                                        self._show_confirm_fa()
            elif self.state in ("confirm_db", "confirm_fa"):
                # Клик по кнопкам диалога
                win_height = 8
                win_width = min(60, self.width - 10)
                start_y = (self.height - win_height) // 2
                start_x = (self.width - win_width) // 2
                button_y = start_y + win_height - 2
                total_width = sum(len(b.text) for b in self.dialog_buttons) + 4 * (len(self.dialog_buttons) - 1)
                button_start_x = start_x + (win_width - total_width) // 2
                for i, button in enumerate(self.dialog_buttons):
                    x1 = button_start_x + i * (len(button.text) + 4)
                    x2 = x1 + len(button.text)
                    if my == button_y and x1 <= mx <= x2:
                        if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                            self.current_dialog_button = i
                            self.needs_redraw = True
                            # Выполняем действие немедленно, как при Enter
                            self._handle_dialog_action(button.action)
                            return None
        except:
            pass
        return None

    def _show_confirm_db(self):
        """Показывает диалог подтверждения для базы данных"""
        self.state = "confirm_db"
        self.dialog_message = f"Выбран файл базы данных:\n{self._shorten_path(self.selected_db_path)}"
        self.dialog_buttons = [
            Button(0, "[ OK ]", "confirm_db_ok", enabled=True),
            Button(1, "[ Назад ]", "confirm_db_back", enabled=True)
        ]
        self.current_dialog_button = 0
        self.needs_redraw = True

    def _show_confirm_fa(self):
        """Показывает диалог подтверждения для файлового архива"""
        self.state = "confirm_fa"
        self.dialog_message = f"Выбран файловый архив:\n{self._shorten_path(self.selected_fa_path)}"
        self.dialog_buttons = [
            Button(0, "[ OK ]", "confirm_fa_ok", enabled=True),
            Button(1, "[ Назад ]", "confirm_fa_back", enabled=True)
        ]
        self.current_dialog_button = 0
        self.needs_redraw = True

    def _shorten_path(self, path, max_len=60):
        if len(path) <= max_len:
            return path
        head, tail = os.path.split(path)
        if len(head) > max_len - len(tail) - 3:
            head = "..." + head[-(max_len - len(tail) - 6):]
        return os.path.join(head, tail)

    def _handle_dialog_action(self, action):
        if action == "confirm_db_ok":
            # Запоминаем папку, в которой лежит выбранный .dbp
            self.last_db_path = os.path.dirname(self.selected_db_path)
            # Переходим к выбору файлового архива
            self.state = "selecting_fa"
            self.current_path = self.last_db_path  # стартуем из той же папки
            self.filter_ext = ['.pilotfa']
            self.picker_title = "Выбор файла файлового архива"
            self._load_files()
            self.needs_redraw = True
        elif action == "confirm_db_back":
            # Возвращаемся к выбору базы
            self.state = "selecting_db"
            self.current_path = os.path.expanduser("~")
            self.filter_ext = ['.dbp']
            self.picker_title = "Выбор файла базы данных"
            self._load_files()
            self.needs_redraw = True
        elif action == "confirm_fa_ok":
            # Сохраняем пути и переходим к следующему экрану (заглушка)
            self.app.existing_db_path = self.selected_db_path
            self.app.existing_fa_path = self.selected_fa_path
            # Здесь можно переключиться на другой экран, например, db_option
            #self.app.switch_screen("db_option")
            self.app.switch_screen("admin_creation")
        elif action == "confirm_fa_back":
            # Возвращаемся к выбору архива
            self.state = "selecting_fa"
            # Оставляем текущий путь (или можно сбросить, но оставим)
            self.filter_ext = ['.pilotfa']
            self.picker_title = "Выбор файла файлового архива"
            self._load_files()
            self.needs_redraw = True
        return None

    def get_screen_name(self):
        return "Выбор существующей БД"