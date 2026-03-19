#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr
from utils.compose_builder import build_compose, write_compose_file  # импортируем новый модуль

class FolderPickerScreen(BaseScreen):
    """
    Экран выбора папки (только директории) для размещения стека Pilot.
    После выбора генерирует docker-compose.yml в папке /имя_стека и переходит на экран подтверждения.
    """
    def __init__(self, stdscr, app, start_path=None, title="Выбор папки стека"):
        super().__init__(stdscr, app)
        self.title = title
        self.start_path = start_path or os.path.expanduser("~")
        self.current_path = os.path.abspath(self.start_path)
        self.files = []          # список имён папок
        self.is_dir = []         # все True
        self.selected_index = 0
        self.focus_mode = 0      # 0 - список, 1 - кнопки
        self.message = ""
        self.scroll_offset = 0

        # Для определения двойного клика
        self._last_click_time = 0
        self._last_click_index = -1

        # Кнопки: "Выбрать" (активна при наличии папок) и "Отмена"
        self.buttons = [
            Button(0, "[ Выбрать ]", "select", enabled=False),
            Button(1, "[ Отмена ]", "cancel", enabled=True)
        ]
        self.current_button = 0

        self.load_files()

    def load_files(self):
        """Загружает список папок из current_path"""
        try:
            entries = os.listdir(self.current_path)
        except PermissionError:
            self.message = "Нет доступа к директории"
            self.files = []
            self.is_dir = []
            self._update_select_button_state()
            return

        dirs = []
        for entry in entries:
            full = os.path.join(self.current_path, entry)
            try:
                if os.path.isdir(full):
                    dirs.append(entry)
            except OSError:
                continue

        dirs.sort(key=str.lower)
        self.files = dirs
        self.is_dir = [True] * len(dirs)

        if self.files:
            if self.selected_index >= len(self.files):
                self.selected_index = len(self.files) - 1
            self._adjust_scroll()
        else:
            self.selected_index = 0
            self.scroll_offset = 0
            if not self.message:
                self.message = "Нет папок"

        self._update_select_button_state()

    def _update_select_button_state(self):
        """Активирует кнопку 'Выбрать', если есть хотя бы одна папка"""
        self.buttons[0].enabled = len(self.files) > 0

    def _adjust_scroll(self):
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

    def draw_instructions(self):
        pass

    def _get_list_height(self):
        return max(1, self.height - 12)

    def draw_content(self):
        """Отрисовывает содержимое экрана"""
        # Подзаголовок (под основным заголовком BaseScreen)
        subtitle = "Выбор папки стека серверных компонентов Pilot"
        x = max(0, (self.width - len(subtitle)) // 2)
        safe_addstr(self.stdscr, 3, x, subtitle, curses.color_pair(3) | curses.A_BOLD)

        # Полный путь с именем стека
        stack_name = getattr(self.app, 'stack_name', 'pilot-stack')
        full_path = os.path.join(self.current_path, stack_name)
        path_display = full_path
        if len(path_display) > self.width - 10:
            path_display = "..." + path_display[-(self.width-13):]
        safe_addstr(self.stdscr, 5, 4, "Папка стека: " + path_display)

        # Список папок
        list_start_y = 7
        list_height = self._get_list_height()
        end_idx = min(len(self.files), self.scroll_offset + list_height)

        for i in range(self.scroll_offset, end_idx):
            y = list_start_y + (i - self.scroll_offset)
            if y >= self.height - 4:
                break
            folder_name = self.files[i]
            prefix = "📁 "
            max_len = self.width - 6
            if len(folder_name) > max_len:
                folder_name = folder_name[:max_len-3] + "..."
            attr = curses.A_REVERSE if i == self.selected_index else 0
            safe_addstr(self.stdscr, y, 4, prefix + folder_name, attr)

        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, list_start_y - 1, 4, "↑ ...")
        if end_idx < len(self.files):
            safe_addstr(self.stdscr, list_start_y + list_height, 4, "↓ ...")

        # Сообщение
        if self.message:
            safe_addstr(self.stdscr, self.height - 5, 4, self.message, curses.color_pair(5))

        # Инструкция
        instr = "↑↓: выбор | Enter: открыть папку | Backspace: назад"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def handle_mouse(self):
        """Обработка мыши: клики по списку и кнопкам"""
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
                        self.needs_redraw = True
                        if bstate & curses.BUTTON1_DOUBLE_CLICKED:
                            self._enter_folder(index)
            return None
        except:
            return None

    def _enter_folder(self, index):
        """Переходит в выбранную папку"""
        folder = self.files[index]
        full = os.path.join(self.current_path, folder)
        try:
            os.chdir(full)  # проверка доступа
            self.current_path = full
            self.load_files()
            self.selected_index = 0
            self.message = ""
        except PermissionError:
            self.message = "Нет доступа"
        self.needs_redraw = True

    def _generate_compose_file(self):
        """Генерирует docker-compose.yml, используя модуль compose_builder."""
        stack_name = getattr(self.app, 'stack_name', 'pilot-stack')
        target_dir = os.path.join(self.current_path, stack_name)
        os.makedirs(target_dir, exist_ok=True)
        self.app.compose_dir = target_dir

        # Получаем словарь compose через новый модуль
        compose_dict = build_compose(self.app)
        # Записываем файл
        write_compose_file(compose_dict, target_dir)

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
            if self.selected_index < len(self.files) - 1:
                self.selected_index += 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            if self.files:
                self._enter_folder(self.selected_index)
        elif key in (127, curses.KEY_BACKSPACE, 8):  # Backspace
            parent = os.path.dirname(self.current_path)
            if parent and parent != self.current_path:
                self.current_path = parent
                self.load_files()
                self.selected_index = 0
                self.message = ""
                self.needs_redraw = True

    def handle_action(self, action):
        if action == "select":
            try:
                self._generate_compose_file()
                self.app.switch_screen("compose_created")
            except Exception as e:
                self.message = f"Ошибка: {e}"
                self.needs_redraw = True
            return None
        elif action == "cancel":
            return "back"
        return None

    def get_screen_name(self):
        return "Выбор папки"