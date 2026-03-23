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
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.state = "selecting_db"  # selecting_db, confirm_db, selecting_fa, confirm_fa
        self.selected_db_path = None
        self.selected_fa_path = None
        self.current_path = None
        self.files = []
        self.is_dir = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.filter_ext = []
        self.dialog_message = ""
        self.dialog_buttons = []
        self.current_dialog_button = 0
        self.message = ""
        self.error_message = None

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

        # Кнопки для выбора (не используются напрямую, т.к. управление через диалоги)
        self.buttons = []
        self.current_button = 0

    def on_enter(self):
        stack_path = getattr(self.app, 'stack_path', None)
        if not stack_path:
            self.state = "error"
            self.error_message = "Путь стека не определён. Сначала задайте имя стека."
            self.needs_redraw = True
            return
        databases_dir = os.path.join(stack_path, "databases")
        os.makedirs(databases_dir, exist_ok=True)
        self.current_path = databases_dir
        self.state = "selecting_db"
        self.filter_ext = ['.dbp']
        self.message = ""
        self.error_message = None
        self.load_files()
        self.needs_redraw = True

    def load_files(self):
        try:
            entries = os.listdir(self.current_path)
        except PermissionError:
            self.message = "Нет доступа к директории"
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
            if not self.message:
                self.message = "Нет файлов"

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
        return max(1, self.height - 12)

    def _enter_folder(self, index):
        folder = self.files[index]
        full = os.path.join(self.current_path, folder)
        try:
            # Проверяем, что это папка и есть доступ
            if os.path.isdir(full):
                self.current_path = full
                self.load_files()
                self.selected_index = 0
                self.message = ""
        except PermissionError:
            self.message = "Нет доступа"
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def draw_content(self):
        title = " ВЫБОР СУЩЕСТВУЮЩЕЙ БАЗЫ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        if self.state == "error":
            safe_addstr(self.stdscr, 6, 4, self.error_message or "Ошибка", curses.color_pair(5))
            return

        if self.state in ("selecting_db", "selecting_fa"):
            self._draw_file_picker()
        elif self.state in ("confirm_db", "confirm_fa"):
            self._draw_dialog()

    def _draw_file_picker(self):
        # Подзаголовок
        if self.state == "selecting_db":
            subtitle = "Выберите файл базы данных (*.dbp)"
        else:
            subtitle = "Выберите файл файлового архива (*.pilotfa)"
        x = max(0, (self.width - len(subtitle)) // 2)
        safe_addstr(self.stdscr, 5, x, subtitle, curses.color_pair(3) | curses.A_BOLD)

        # Текущий путь
        path_display = self.current_path
        if len(path_display) > self.width - 10:
            path_display = "..." + path_display[-(self.width-13):]
        safe_addstr(self.stdscr, 7, 4, "Путь: " + path_display)

        list_start_y = 9
        list_height = self._get_list_height()
        end_idx = min(len(self.files), self.scroll_offset + list_height)

        for i in range(self.scroll_offset, end_idx):
            y = list_start_y + (i - self.scroll_offset)
            if y >= self.height - 5:
                break
            prefix = "📁 " if self.is_dir[i] else "📄 "
            name = self.files[i]
            max_len = self.width - 6
            if len(name) > max_len:
                name = name[:max_len-3] + "..."
            attr = curses.A_REVERSE if i == self.selected_index else 0
            safe_addstr(self.stdscr, y, 4, prefix + name, attr)

        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, list_start_y - 1, 4, "↑ ...")
        if end_idx < len(self.files):
            safe_addstr(self.stdscr, list_start_y + list_height, 4, "↓ ...")

        # Информация о выбранном файле
        if self.files and not self.is_dir[self.selected_index]:
            full_path = os.path.join(self.current_path, self.files[self.selected_index])
            try:
                st = os.stat(full_path)
                size = st.st_size
                mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
                size_str = self._format_size(size)
                info = f"Размер: {size_str} | Изменён: {mtime}"
                safe_addstr(self.stdscr, self.height - 6, 4, info[:self.width-8])
            except:
                pass

        # Сообщение
        if self.message:
            safe_addstr(self.stdscr, self.height - 5, 4, self.message, curses.color_pair(5))

        # Инструкция
        instr = "↑↓: выбор | Enter: открыть папку / выбрать файл | Backspace: назад"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 4, 4, instr, curses.color_pair(4))

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

    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def handle_mouse(self):
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            if self.state in ("selecting_db", "selecting_fa"):
                # Кнопки (в этом экране нет кнопок, поэтому пропускаем)
                # Список
                list_start_y = 9
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
                            self.needs_redraw = True
                            # Двойной клик по папке или файлу
                            if bstate & curses.BUTTON1_DOUBLE_CLICKED:
                                if self.is_dir[index]:
                                    self._enter_folder(index)
                                else:
                                    # Выбор файла
                                    if self.state == "selecting_db":
                                        self.selected_db_path = os.path.join(self.current_path, self.files[index])
                                        self._show_confirm_db()
                                    else:
                                        self.selected_fa_path = os.path.join(self.current_path, self.files[index])
                                        self._show_confirm_fa()
                            else:
                                # Одиночный клик – просто выделяем
                                pass
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
                            # Действие выполняется здесь, не возвращаясь в main
                            self._handle_dialog_action(button.action)
                            return None
        except:
            pass
        return None

    def handle_input(self):
        self.handle_resize()
        self.draw()

        # Обрабатываем события мыши до клавиатуры, чтобы не пропустить
        # Но мы не можем вызывать handle_mouse из getch, поэтому перехватываем ключ мыши
        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            result = self.handle_mouse()
            if result:
                return self.handle_action(result)
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 27:  # ESC
            return "exit"
        else:
            if self.state in ("selecting_db", "selecting_fa"):
                self._handle_list_keys(key)
            elif self.state in ("confirm_db", "confirm_fa"):
                if key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
                    action = self.dialog_buttons[self.current_dialog_button].action
                    self._handle_dialog_action(action)
        return None

    def _handle_list_keys(self, key):
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
                    self._enter_folder(self.selected_index)
                else:
                    if self.state == "selecting_db":
                        self.selected_db_path = full
                        self._show_confirm_db()
                    else:
                        self.selected_fa_path = full
                        self._show_confirm_fa()
        elif key in (127, curses.KEY_BACKSPACE, 8):  # Backspace
            parent = os.path.dirname(self.current_path)
            if parent and parent != self.current_path:
                self.current_path = parent
                self.load_files()
                self.selected_index = 0
                self.message = ""
                self.needs_redraw = True

    def _show_confirm_db(self):
        self.state = "confirm_db"
        self.dialog_message = f"Выбран файл базы данных:\n{self._shorten_path(self.selected_db_path)}"
        self.dialog_buttons = [
            Button(0, "[ OK ]", "confirm_db_ok", enabled=True),
            Button(1, "[ Назад ]", "confirm_db_back", enabled=True)
        ]
        self.current_dialog_button = 0
        self.needs_redraw = True

    def _show_confirm_fa(self):
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
            # Копируем выбранный файл базы в папку стека
            stack_path = self.app.stack_path
            dest_db = os.path.join(stack_path, "databases", os.path.basename(self.selected_db_path))
            try:
                shutil.copy2(self.selected_db_path, dest_db)
                self.app.existing_db_path = dest_db
            except Exception as e:
                self.error_message = f"Ошибка копирования: {e}"
                self.state = "error"
                self.needs_redraw = True
                return None
            # Переходим к выбору архива
            self.state = "selecting_fa"
            self.filter_ext = ['.pilotfa']
            self.current_path = os.path.dirname(self.selected_db_path)  # та же папка, где был dbp
            self.load_files()
            self.needs_redraw = True
        elif action == "confirm_db_back":
            self.state = "selecting_db"
            self.filter_ext = ['.dbp']
            self.current_path = os.path.dirname(self.selected_db_path)  # возвращаемся к папке, где выбирали базу
            self.load_files()
            self.needs_redraw = True
        elif action == "confirm_fa_ok":
            # Копируем архив в папку стека
            stack_path = self.app.stack_path
            dest_fa = os.path.join(stack_path, "databases", os.path.basename(self.selected_fa_path))
            try:
                shutil.copy2(self.selected_fa_path, dest_fa)
                self.app.existing_fa_path = dest_fa
            except Exception as e:
                self.error_message = f"Ошибка копирования: {e}"
                self.state = "error"
                self.needs_redraw = True
                return None
            return "next"  # переход к следующему экрану
        elif action == "confirm_fa_back":
            self.state = "selecting_fa"
            self.filter_ext = ['.pilotfa']
            self.current_path = os.path.dirname(self.selected_fa_path)  # возвращаемся к папке, где выбирали архив
            self.load_files()
            self.needs_redraw = True
        return None

    def get_screen_name(self):
        return "Выбор существующей БД"