#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import shutil
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbExistingScreen(BaseScreen):
    """
    Экран выбора существующей базы данных.
    Последовательно выбирает файл базы данных (.dbp) и файл файлового архива (.pilotfa).
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.state = "selecting_db"  # selecting_db, selecting_fa, confirm
        self.selected_db_path = None
        self.selected_fa_path = None
        self.current_path = None
        self.files = []
        self.is_dir = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.filter_ext = []
        self.message = ""

        # Для диалога подтверждения
        self.dialog_message = ""
        self.dialog_buttons = []
        self.current_dialog_button = 0

        # Основные кнопки
        self.buttons = [
            Button(0, "[ Выбрать ]", "select", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - список, 1 - кнопки

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

    def on_enter(self):
        stack_path = getattr(self.app, 'stack_path', None)
        if not stack_path:
            self.state = "error"
            self.message = "Путь стека не определён. Сначала задайте имя стека."
            self.needs_redraw = True
            return
        databases_dir = os.path.join(stack_path, "databases")
        os.makedirs(databases_dir, exist_ok=True)
        self.current_path = databases_dir
        self.state = "selecting_db"
        self.filter_ext = ['.dbp']
        self._load_files()
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def _load_files(self):
        try:
            entries = os.listdir(self.current_path)
        except PermissionError:
            self.files = []
            self.is_dir = []
            self.message = "Нет доступа к директории"
            self._update_select_button_state()
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
            self.message = "Нет подходящих файлов" if self.filter_ext else "Нет файлов"

        self._update_select_button_state()

    def _update_select_button_state(self):
        if self.state in ("selecting_db", "selecting_fa") and self.files and not self.is_dir[self.selected_index]:
            self.buttons[0].enabled = True
        else:
            self.buttons[0].enabled = False

    def _adjust_scroll(self):
        if not self.files:
            self.scroll_offset = 0
            return
        list_height = self._get_list_height()
        if list_height < 1:
            list_height = 1
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1

    def _get_list_height(self):
        # Путь на строке 5, индикатор прокрутки на строке 6, список с 7 строки
        # Заканчивается перед сообщением на строке self.height - 6
        return max(1, self.height - 14)

    def _get_subtitle(self):
        if self.state == "selecting_db":
            return "Выберите файл базы данных (.dbp)"
        elif self.state == "selecting_fa":
            return "Выберите файл файлового архива (.pilotfa)"
        return ""

    def draw_content(self):
        # Подзаголовок на строке 3
        subtitle = self._get_subtitle()
        x = max(0, (self.width - len(subtitle)) // 2)
        safe_addstr(self.stdscr, 3, x, subtitle, curses.color_pair(3) | curses.A_BOLD)

        # Путь на строке 5
        path_display = self.current_path
        if len(path_display) > self.width - 10:
            path_display = "..." + path_display[-(self.width-13):]
        safe_addstr(self.stdscr, 5, 4, "Путь: " + path_display)

        # Список начиная со строки 7
        list_start_y = 7
        list_height = self._get_list_height()
        end_idx = min(len(self.files), self.scroll_offset + list_height)

        for i in range(self.scroll_offset, end_idx):
            y = list_start_y + (i - self.scroll_offset)
            if y >= self.height - 7:  # оставляем место для сообщения, инструкции и кнопок
                break
            prefix = "📁 " if self.is_dir[i] else "📄 "
            filename = self.files[i]
            max_len = self.width - 6
            if len(filename) > max_len:
                filename = filename[:max_len-3] + "..."
            attr = curses.A_REVERSE if i == self.selected_index else 0
            safe_addstr(self.stdscr, y, 4, prefix + filename, attr)

        # Индикаторы прокрутки на строке 6 и после списка
        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, 6, 4, "↑ ...")
        if end_idx < len(self.files):
            safe_addstr(self.stdscr, list_start_y + list_height, 4, "↓ ...")

        # Сообщение
        if self.message:
            safe_addstr(self.stdscr, self.height - 6, 4, self.message, curses.color_pair(5))

        # Инструкция
        instr = "↑↓: выбор | Enter: открыть папку / выбрать файл | Backspace: назад | TAB: переключение на кнопки"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 5, 4, instr, curses.color_pair(4))

    def _draw_dialog(self):
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

        lines = self.dialog_message.split('\n')
        for i, line in enumerate(lines):
            if i >= win_height - 3:
                break
            x = start_x + 2
            y = start_y + 1 + i
            safe_addstr(self.stdscr, y, x, line[:win_width-4])

        button_y = start_y + win_height - 2
        total_width = sum(len(b.text) for b in self.dialog_buttons) + 4 * (len(self.dialog_buttons) - 1)
        button_start_x = start_x + (win_width - total_width) // 2
        for i, button in enumerate(self.dialog_buttons):
            x = button_start_x + i * (len(button.text) + 4)
            is_active = (i == self.current_dialog_button)
            button.draw(self.stdscr, x, button_y, is_active)

    def _enter_folder(self, index):
        folder = self.files[index]
        full = os.path.join(self.current_path, folder)
        try:
            os.chdir(full)  # проверка доступа
            self.current_path = full
            self._load_files()
            self.selected_index = 0
            self.message = ""
        except PermissionError:
            self.message = "Нет доступа"
        self.needs_redraw = True

    def _select_file(self, index):
        selected = self.files[index]
        full = os.path.join(self.current_path, selected)
        if self.state == "selecting_db":
            self.selected_db_path = full
            # Переходим к выбору архива
            self.state = "selecting_fa"
            self.filter_ext = ['.pilotfa']
            # Начинаем с той же папки, где был выбран .dbp
            self.current_path = os.path.dirname(full)
            self._load_files()
            self.needs_redraw = True
        elif self.state == "selecting_fa":
            self.selected_fa_path = full
            # Показываем диалог
            self._show_confirm()

    def _show_confirm(self):
        self.state = "confirm"
        self.dialog_message = (
            f"Файл базы данных:\n{self.selected_db_path}\n\n"
            f"Файл файлового архива:\n{self.selected_fa_path}"
        )
        self.dialog_buttons = [
            Button(0, "[ OK ]", "confirm_ok", enabled=True),
            Button(1, "[ Назад ]", "confirm_back", enabled=True)
        ]
        self.current_dialog_button = 0
        self.needs_redraw = True
        # Принудительная перерисовка
        self.draw()
        self.stdscr.refresh()

    def _handle_dialog_action(self, action):
        if action == "confirm_ok":
            # Копируем файлы в папку стека
            stack_path = self.app.stack_path
            dest_db = os.path.join(stack_path, "databases", os.path.basename(self.selected_db_path))
            dest_fa = os.path.join(stack_path, "databases", os.path.basename(self.selected_fa_path))
            try:
                shutil.copy2(self.selected_db_path, dest_db)
                shutil.copy2(self.selected_fa_path, dest_fa)
                self.app.existing_db_path = dest_db
                self.app.existing_fa_path = dest_fa
            except Exception as e:
                self.message = f"Ошибка копирования: {e}"
                self.state = "error"
                self.needs_redraw = True
                return None
            # Переходим к созданию администраторов
            self.app.switch_screen("admin_creation")
            return None
        elif action == "confirm_back":
            # Возвращаемся к выбору базы данных
            self.state = "selecting_db"
            self.filter_ext = ['.dbp']
            self.current_path = os.path.dirname(self.selected_db_path)  # стартуем из той же папки
            self._load_files()
            self.needs_redraw = True
        return None

    def handle_mouse(self):
        if self.state == "confirm":
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
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
                            self.current_dialog_button = i
                            self.needs_redraw = True
                            self._handle_dialog_action(button.action)
                            return None
            except:
                pass
            return None

        if self.state not in ("selecting_db", "selecting_fa"):
            return None
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
            list_start_y = 7
            list_height = self._get_list_height()
            list_end_y = list_start_y + list_height
            if list_start_y <= my < list_end_y and self.files:
                index = self.scroll_offset + (my - list_start_y)
                if 0 <= index < len(self.files):
                    if current_time - self._last_click_time < 0.1 and index == self._last_click_index:
                        return None
                    self._last_click_time = current_time
                    self._last_click_index = index
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        self.selected_index = index
                        self._update_select_button_state()
                        self.needs_redraw = True
                        if bstate & curses.BUTTON1_DOUBLE_CLICKED:
                            if self.is_dir[index]:
                                self._enter_folder(index)
                            else:
                                self._select_file(index)
        except:
            pass
        return None

    def handle_input(self):
        self.handle_resize()
        self.draw()

        if self.state == "confirm":
            key = self.stdscr.getch()
            if key == curses.KEY_MOUSE:
                self.handle_mouse()
            elif key == curses.KEY_RESIZE:
                self.handle_resize()
                self.needs_redraw = True
            elif key == 9:  # TAB
                self.current_dialog_button = (self.current_dialog_button + 1) % len(self.dialog_buttons)
                self.needs_redraw = True
            elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
                action = self.dialog_buttons[self.current_dialog_button].action
                self._handle_dialog_action(action)
            return None

        # Режим выбора файла
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
            self._handle_file_keys(key)
        else:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def _handle_file_keys(self, key):
        if key == curses.KEY_UP:
            if self.selected_index > 0:
                self.selected_index -= 1
                self._adjust_scroll()
                self._update_select_button_state()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.selected_index < len(self.files) - 1:
                self.selected_index += 1
                self._adjust_scroll()
                self._update_select_button_state()
                self.needs_redraw = True
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            if self.files:
                if self.is_dir[self.selected_index]:
                    self._enter_folder(self.selected_index)
                else:
                    self._select_file(self.selected_index)
        elif key in (127, curses.KEY_BACKSPACE, 8):
            parent = os.path.dirname(self.current_path)
            if parent and parent != self.current_path:
                self.current_path = parent
                self._load_files()
                self.selected_index = 0
                self.message = ""
                self.needs_redraw = True

    def handle_action(self, action):
        if action == "select":
            if self.state in ("selecting_db", "selecting_fa") and self.files and not self.is_dir[self.selected_index]:
                self._select_file(self.selected_index)
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Выбор существующей БД"