#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class FilePickerScreen(BaseScreen):
    """
    Экран выбора файла с навигацией по файловой системе.
    Поддерживает фильтрацию по расширениям (если задано).
    """
    def __init__(self, stdscr, app, start_path=None, filter_extensions=None, title="Выберите файл"):
        super().__init__(stdscr, app)
        self.title = title
        self.filter_extensions = filter_extensions
        self.start_path = start_path or os.path.expanduser("~")
        self.current_path = os.path.abspath(self.start_path)
        self.files = []
        self.is_dir = []
        self.selected_index = 0
        self.focus_mode = 0      # 0 - список, 1 - кнопки
        self.message = ""
        self.scroll_offset = 0

        # Для определения двойного клика
        self._last_click_time = 0
        self._last_click_index = -1

        # Кнопки: "Установить лицензию"
        self.buttons = [
            Button(0, "[ Установить лицензию ]", "select", enabled=False),
            Button(1, "[ Отмена ]", "cancel", enabled=True)
        ]
        self.current_button = 0

        self.load_files()

    def load_files(self):
        """Загружает список файлов и папок из current_path с учётом фильтра"""
        try:
            entries = os.listdir(self.current_path)
        except PermissionError:
            self.message = "Нет доступа к директории"
            self.files = []
            self.is_dir = []
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
                    if self.filter_extensions is not None:
                        ext = os.path.splitext(entry)[1].lower()
                        if ext in self.filter_extensions:
                            files.append(entry)
                    else:
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

        self._update_select_button_state()

    def _update_select_button_state(self):
        """Обновляет состояние кнопки 'Установить лицензию' в зависимости от выбранного элемента"""
        if self.files and not self.is_dir[self.selected_index]:
            self.buttons[0].enabled = True
        else:
            self.buttons[0].enabled = False

    def _adjust_scroll(self):
        """Корректирует смещение прокрутки, чтобы выделенный элемент был видим"""
        if not self.files:
            self.scroll_offset = 0
            return

        list_height = self.height - 12
        if list_height < 1:
            list_height = 1

        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1

    def draw_content(self):
        """Отрисовывает содержимое экрана"""
        # Заголовок
        safe_addstr(self.stdscr, 2, 2, self.title, curses.color_pair(3) | curses.A_BOLD)

        # Текущий путь
        path_display = self.current_path
        if len(path_display) > self.width - 10:
            path_display = "..." + path_display[-(self.width-13):]
        safe_addstr(self.stdscr, 4, 2, "Путь: " + path_display)

        # Список файлов
        list_start_y = 6
        list_height = self.height - 12
        if list_height < 3:
            list_height = 3

        if self.files:
            end_idx = min(len(self.files), self.scroll_offset + list_height)
            for i in range(self.scroll_offset, end_idx):
                y = list_start_y + (i - self.scroll_offset)
                if y >= self.height - 6:
                    break

                prefix = "📁 " if self.is_dir[i] else "📄 "
                filename = self.files[i]
                max_len = self.width - 6
                if len(filename) > max_len:
                    filename = filename[:max_len-3] + "..."

                # Всегда подсвечиваем выбранный элемент
                attr = curses.A_REVERSE if i == self.selected_index else 0
                safe_addstr(self.stdscr, y, 4, prefix + filename, attr)

            # Индикаторы прокрутки
            if self.scroll_offset > 0:
                safe_addstr(self.stdscr, list_start_y - 1, 4, "↑ ...")
            if end_idx < len(self.files):
                safe_addstr(self.stdscr, list_start_y + list_height, 4, "↓ ...")
        else:
            safe_addstr(self.stdscr, list_start_y, 4, "(пусто)")

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

        # Инструкция для списка
        instr = "↑↓: выбор | Enter: открыть папку / выбрать файл | Backspace: назад"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 4, 4, instr, curses.color_pair(4))

    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def handle_mouse(self):
        """Обрабатывает события мыши, включая двойной клик по файлам"""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            # 1. Проверяем, не кликнули ли по кнопкам
            button_positions = self.get_button_positions()
            for i, pos in enumerate(button_positions):
                if my == pos['y'] and pos['x1'] <= mx <= pos['x2']:
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        if self.buttons[i].enabled:
                            self.current_button = i
                            self.needs_redraw = True
                            # Если нажата кнопка "Установить лицензию", сохраняем выбранный файл
                            if self.buttons[i].action == "select":
                                if self.files and not self.is_dir[self.selected_index]:
                                    self.app.license_file_path = os.path.join(
                                        self.current_path, self.files[self.selected_index]
                                    )
                            return self.buttons[i].action
                        else:
                            # Неактивная кнопка игнорируется
                            return None
                    return None

            # 2. Если не кнопки, проверяем клик в области списка
            list_start_y = 6
            list_height = self.height - 12
            list_end_y = list_start_y + list_height

            if list_start_y <= my < list_end_y and self.files:
                index = self.scroll_offset + (my - list_start_y)
                if 0 <= index < len(self.files):
                    # Проверяем двойной клик (по времени)
                    is_double_click = (index == self._last_click_index and
                                       current_time - self._last_click_time < 0.5)

                    self._last_click_time = current_time
                    self._last_click_index = index

                    if is_double_click:
                        if self.is_dir[index]:
                            # Переход в папку
                            full = os.path.join(self.current_path, self.files[index])
                            try:
                                self.current_path = full
                                self.load_files()
                                self.selected_index = 0
                                self.message = ""
                            except PermissionError:
                                self.message = "Нет доступа"
                            self.needs_redraw = True
                            return None
                        else:
                            # Двойной клик по файлу — выбираем
                            self.selected_index = index
                            if self.buttons[0].enabled:
                                full = os.path.join(self.current_path, self.files[index])
                                self.app.license_file_path = full
                                return self.handle_action("select")
                    else:
                        # Одиночный клик — выделяем элемент
                        self.selected_index = index
                        self._update_select_button_state()
                        self.focus_mode = 0
                        self.needs_redraw = True
                        return None

            # Клик в другом месте игнорируем
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
            return self._handle_list_keys(key)
        else:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)

        return None

    def _handle_list_keys(self, key):
        if key == curses.KEY_UP:
            if self.files and self.selected_index > 0:
                self.selected_index -= 1
                self._adjust_scroll()
                self._update_select_button_state()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.files and self.selected_index < len(self.files) - 1:
                self.selected_index += 1
                self._adjust_scroll()
                self._update_select_button_state()
                self.needs_redraw = True
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            if self.files:
                selected = self.files[self.selected_index]
                full = os.path.join(self.current_path, selected)
                if self.is_dir[self.selected_index]:
                    try:
                        self.current_path = full
                        self.load_files()
                        self.selected_index = 0
                        self.message = ""
                    except PermissionError:
                        self.message = "Нет доступа"
                    self.needs_redraw = True
                else:
                    if self.buttons[0].enabled:
                        self.app.license_file_path = full
                        return self.handle_action("select")
        elif key in (127, curses.KEY_BACKSPACE, 8):  # Backspace
            parent = os.path.dirname(self.current_path)
            if parent and parent != self.current_path:
                self.current_path = parent
                self.load_files()
                self.selected_index = 0
                self.message = ""
                self.needs_redraw = True
        return None

    def handle_action(self, action):
        if action == "cancel":
            self.app.license_file_path = None
            return "back"
        elif action == "select":
            if self.files and not self.is_dir[self.selected_index]:
                # Вместо возврата "back" переходим на экран подтверждения лицензии
                self.app.switch_screen("license_confirm")
                return None
        return None

    def get_screen_name(self):
        return "Выбор файла"