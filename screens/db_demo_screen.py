#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import time
import threading
import urllib.request
import zipfile
import tempfile
import shutil
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbDemoScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.state = "downloading"
        self.progress = 0
        self.status_message = ""
        self.error_message = None
        self.download_thread = None
        self.extract_thread = None
        self.databases = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.focus_mode = 0
        self.temp_dir = None
        self.extract_dir = None
        self._last_click_time = 0
        self._last_click_index = -1

        self.buttons = [
            Button(0, "[ Выбор ]", "select", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def on_enter(self):
        stack_path = getattr(self.app, 'stack_path', None)
        if not stack_path:
            self.error_message = "Путь стека не определён. Сначала задайте имя стека."
            self.state = "error"
            self.needs_redraw = True
            return
        self.extract_dir = os.path.join(stack_path, "databases")
        self.state = "downloading"
        self.progress = 0
        self.status_message = "Подготовка к скачиванию..."
        self.error_message = None
        self.databases = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.focus_mode = 0
        self.buttons[0].enabled = False
        self.needs_redraw = True

        self.temp_dir = tempfile.mkdtemp(prefix="pilot_demo_")
        self.start_download()

    def start_download(self):
        def download():
            url = "https://pilot.ascon.ru/release/Databases.zip"
            local_path = os.path.join(self.temp_dir, "Databases.zip")
            try:
                def progress_callback(block_num, block_size, total_size):
                    if total_size > 0:
                        downloaded = block_num * block_size
                        percent = int(downloaded * 100 / total_size)
                        self.progress = min(percent, 100)
                        self.needs_redraw = True

                self.status_message = "Скачивание..."
                self.needs_redraw = True
                urllib.request.urlretrieve(url, local_path, progress_callback)

                self.status_message = "Скачивание завершено. Начинаем распаковку..."
                self.needs_redraw = True
                self.state = "extracting"
                self.progress = 0
                self.start_extract(local_path)
            except Exception as e:
                self.error_message = f"Ошибка скачивания: {str(e)}"
                self.state = "error"
                self.needs_redraw = True

        self.download_thread = threading.Thread(target=download, daemon=True)
        self.download_thread.start()

    def start_extract(self, zip_path):
        def extract():
            try:
                os.makedirs(self.extract_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    total_files = len(file_list)
                    for i, file_name in enumerate(file_list):
                        norm_name = file_name.replace('\\', '/')
                        parts = norm_name.split('/')
                        clean_parts = [p for p in parts if p and p != '.' and p != '..']
                        if not clean_parts:
                            continue
                        target_path = os.path.join(self.extract_dir, *clean_parts)
                        if norm_name.endswith('/') or file_name.endswith('\\'):
                            os.makedirs(target_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with zip_ref.open(file_name) as source, open(target_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                        percent = int((i + 1) * 100 / total_files)
                        self.progress = percent
                        self.status_message = f"Распаковка... {percent}%"
                        self.needs_redraw = True
                        time.sleep(0.01)

                self.status_message = "Поиск доступных баз..."
                self.needs_redraw = True
                self.scan_databases()
            except Exception as e:
                self.error_message = f"Ошибка распаковки: {str(e)}"
                self.state = "error"
                self.needs_redraw = True
            finally:
                try:
                    os.remove(zip_path)
                except:
                    pass

        self.extract_thread = threading.Thread(target=extract, daemon=True)
        self.extract_thread.start()

    def scan_databases(self):
        databases_container = os.path.join(self.extract_dir, "Databases")
        if not os.path.exists(databases_container):
            self.error_message = "Папка Databases не найдена после распаковки"
            self.state = "error"
            self.needs_redraw = True
            return

        items = os.listdir(databases_container)
        dirs = [item for item in items if os.path.isdir(os.path.join(databases_container, item))]
        if dirs:
            self.databases = dirs
            self.selected_index = 0
            self.state = "selecting"
            self.buttons[0].enabled = True
        else:
            self.error_message = "В папке Databases нет подпапок с базами данных"
            self.state = "error"
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def _get_list_height(self):
        return max(1, self.height - 12)

    def _adjust_scroll(self):
        if not self.databases:
            return
        list_height = self._get_list_height()
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1

    def draw_content(self):
        title = " ДЕМОНСТРАЦИОННАЯ БАЗА ДАННЫХ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 6

        if self.state in ("downloading", "extracting"):
            if self.state == "downloading":
                op_text = "Скачивание демо-баз:"
            else:
                op_text = "Распаковка архива:"
            safe_addstr(self.stdscr, start_y, 4, op_text, curses.A_BOLD)
            start_y += 1

            bar_width = min(50, self.width - 20)
            if bar_width > 0:
                filled = int(bar_width * self.progress / 100)
                bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
                percent = f" {self.progress}%"
                y = start_y
                x_bar = max(0, (self.width - len(bar)) // 2)
                safe_addstr(self.stdscr, y, x_bar, bar + percent)
                y += 2
                if self.status_message and "Скачивание" not in self.status_message and "Распаковка" not in self.status_message:
                    safe_addstr(self.stdscr, y, 4, self.status_message)
        elif self.state == "selecting":
            list_height = self._get_list_height()
            end_idx = min(len(self.databases), self.scroll_offset + list_height)

            for i in range(self.scroll_offset, end_idx):
                y = start_y + (i - self.scroll_offset)
                if y >= self.height - 4:
                    break
                db_name = self.databases[i]
                radio = "(*)" if i == self.selected_index else "( )"
                attr = curses.A_REVERSE if (i == self.selected_index and self.focus_mode == 0) else 0
                line = f"{radio} {db_name}"
                safe_addstr(self.stdscr, y, 4, line, attr)

            if self.scroll_offset > 0:
                safe_addstr(self.stdscr, start_y - 1, 4, "↑ ...")
            if end_idx < len(self.databases):
                safe_addstr(self.stdscr, start_y + list_height, 4, "↓ ...")

            instr = "↑↓: выбор | Пробел/Enter/клик: выбор | TAB: переключение на кнопки"
            if len(instr) > self.width:
                instr = instr[:self.width-4] + "..."
            safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

        elif self.state == "error":
            safe_addstr(self.stdscr, start_y, 4, self.error_message or "Неизвестная ошибка", curses.color_pair(5))

    def handle_mouse(self):
        if self.state != "selecting":
            return None
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

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

            list_start_y = 6
            list_height = self._get_list_height()
            list_end_y = list_start_y + list_height

            if list_start_y <= my < list_end_y and self.databases:
                index = self.scroll_offset + (my - list_start_y)
                if 0 <= index < len(self.databases):
                    if current_time - self._last_click_time < 0.1 and index == self._last_click_index:
                        return None
                    self._last_click_time = current_time
                    self._last_click_index = index

                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        self.selected_index = index
                        self.needs_redraw = True
            return None
        except:
            return None

    def handle_input(self):
        self.handle_resize()

        if self.state in ("downloading", "extracting"):
            self.stdscr.timeout(100)
        else:
            self.stdscr.timeout(-1)

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
            if self.state == "selecting":
                self.focus_mode = (self.focus_mode + 1) % 2
                self.needs_redraw = True
        elif self.state == "selecting" and self.focus_mode == 0:
            self._handle_list_keys(key)
        elif self.state == "selecting" and self.focus_mode == 1:
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
            if self.selected_index < len(self.databases) - 1:
                self.selected_index += 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key in (ord(' '), ord('\n'), ord('\r'), curses.KEY_ENTER):
            self.needs_redraw = True

    def handle_action(self, action):
        if action == "select":
            if self.state == "selecting" and self.databases:
                selected_db = self.databases[self.selected_index]
                self.app.selected_demo_db = selected_db
                return "next"
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Демо-база данных"