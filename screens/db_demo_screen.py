#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import time
import threading
import urllib.request
import zipfile
import tempfile
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbDemoScreen(BaseScreen):
    """
    Экран загрузки и выбора демонстрационной базы данных.
    Скачивает архив, распаковывает, показывает список доступных баз.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.state = "downloading"  # downloading, extracting, selecting, error
        self.progress = 0
        self.status_message = ""
        self.error_message = None
        self.download_thread = None
        self.extract_thread = None
        self.databases = []          # список имён баз (папок)
        self.selected_index = 0
        self.scroll_offset = 0
        self.focus_mode = 0          # 0 - список, 1 - кнопки
        self.temp_dir = None
        self.extract_dir = "/usr/share/ascon/databases"

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

        # Кнопки: "Выбор" (изначально неактивна) и "Выход"
        self.buttons = [
            Button(0, "[ Выбор ]", "select", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

    def on_enter(self):
        """При входе на экран начинаем скачивание"""
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

        # Создаём временную директорию для скачивания
        self.temp_dir = tempfile.mkdtemp(prefix="pilot_demo_")
        self.start_download()

    def start_download(self):
        """Запускает скачивание в отдельном потоке"""
        def download():
            url = "https://pilot.ascon.ru/release/Databases.zip"
            local_path = os.path.join(self.temp_dir, "Databases.zip")
            try:
                def progress_callback(block_num, block_size, total_size):
                    if total_size > 0:
                        downloaded = block_num * block_size
                        percent = int(downloaded * 100 / total_size)
                        self.progress = min(percent, 100)
                        self.status_message = f"Скачивание... {self.progress}%"
                        self.needs_redraw = True

                self.status_message = "Скачивание... 0%"
                self.needs_redraw = True
                urllib.request.urlretrieve(url, local_path, progress_callback)

                # После успешного скачивания переходим к распаковке
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
        """Распаковывает архив в отдельном потоке с сохранением структуры папок"""
        def extract():
            try:
                # Создаём целевую папку, если не существует
                os.makedirs(self.extract_dir, exist_ok=True)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Получаем список всех файлов в архиве
                    file_list = zip_ref.namelist()
                    total_files = len(file_list)
                    for i, file_name in enumerate(file_list):
                        # Извлекаем каждый файл с сохранением пути
                        zip_ref.extract(file_name, self.extract_dir)
                        percent = int((i + 1) * 100 / total_files)
                        self.progress = percent
                        self.status_message = f"Распаковка... {percent}%"
                        self.needs_redraw = True
                        time.sleep(0.01)  # чтобы увидеть прогресс

                # После распаковки анализируем содержимое
                self.status_message = "Поиск доступных баз..."
                self.needs_redraw = True
                self.scan_databases()
            except Exception as e:
                self.error_message = f"Ошибка распаковки: {str(e)}"
                self.state = "error"
                self.needs_redraw = True
            finally:
                # Удаляем временный архив
                try:
                    os.remove(zip_path)
                except:
                    pass

        self.extract_thread = threading.Thread(target=extract, daemon=True)
        self.extract_thread.start()

    def scan_databases(self):
        """Сканирует папку /usr/share/ascon/databases на наличие подпапок (баз данных)"""
        try:
            # После распаковки внутри extract_dir появится папка "Databases" (или что-то подобное)
            # Нам нужно найти все подпапки, которые являются базами.
            # Предполагаем, что структура: extract_dir/Databases/имя_базы/файлы
            # Поэтому ищем подпапки первого уровня внутри extract_dir, которые содержат файлы .pilotcfx или просто являются базами
            items = os.listdir(self.extract_dir)
            dirs = []
            for item in items:
                full_path = os.path.join(self.extract_dir, item)
                if os.path.isdir(full_path):
                    # Проверим, есть ли внутри .pilotcfx файлы (по желанию)
                    dirs.append(item)
            dirs.sort(key=str.lower)
            self.databases = dirs
            if self.databases:
                self.selected_index = 0
                self.state = "selecting"
                self.buttons[0].enabled = True
                self.status_message = f"Найдено баз: {len(self.databases)}"
            else:
                self.error_message = "В архиве не найдено папок с базами данных"
                self.state = "error"
        except Exception as e:
            self.error_message = f"Ошибка сканирования: {str(e)}"
            self.state = "error"
        self.needs_redraw = True

    def draw_instructions(self):
        """Отключаем стандартные инструкции"""
        pass

    def _get_list_height(self):
        return max(1, self.height - 8)

    def _adjust_scroll(self):
        if not self.databases:
            return
        list_height = self._get_list_height()
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1

    def draw_content(self):
        """Отрисовывает содержимое в зависимости от состояния"""
        title = " ДЕМОНСТРАЦИОННАЯ БАЗА ДАННЫХ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 6

        if self.state in ("downloading", "extracting"):
            # Показываем прогресс-бар
            bar_width = min(50, self.width - 20)
            if bar_width > 0:
                filled = int(bar_width * self.progress / 100)
                bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
                percent = f" {self.progress}%"
                y = start_y
                x_bar = max(0, (self.width - len(bar)) // 2)
                safe_addstr(self.stdscr, y, x_bar, bar + percent)
                y += 2
                safe_addstr(self.stdscr, y, 4, self.status_message)
        elif self.state == "selecting":
            # Отображаем список баз с радио-кнопками
            list_height = self._get_list_height()
            end_idx = min(len(self.databases), self.scroll_offset + list_height)

            for i in range(self.scroll_offset, end_idx):
                y = start_y + (i - self.scroll_offset)
                if y >= self.height - 4:
                    break
                db_name = self.databases[i]
                # Радио-кнопка: (o) для выбранного, ( ) для остальных
                radio = "(o)" if i == self.selected_index else "( )"
                attr = curses.A_REVERSE if (i == self.selected_index and self.focus_mode == 0) else 0
                line = f"{radio} {db_name}"
                safe_addstr(self.stdscr, y, 4, line, attr)

            if self.scroll_offset > 0:
                safe_addstr(self.stdscr, start_y - 1, 4, "↑ ...")
            if end_idx < len(self.databases):
                safe_addstr(self.stdscr, start_y + list_height, 4, "↓ ...")

            # Инструкция
            instr = "↑↓: выбор | Пробел/Enter/клик: выбор | TAB: переключение на кнопки"
            if len(instr) > self.width:
                instr = instr[:self.width-4] + "..."
            safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

        elif self.state == "error":
            safe_addstr(self.stdscr, start_y, 4, self.error_message or "Неизвестная ошибка", curses.color_pair(5))

    def handle_mouse(self):
        """Обработка мыши в режиме выбора"""
        if self.state != "selecting":
            return None
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

            # Список
            list_start_y = 6
            list_height = self._get_list_height()
            list_end_y = list_start_y + list_height

            if list_start_y <= my < list_end_y and self.databases:
                index = self.scroll_offset + (my - list_start_y)
                if 0 <= index < len(self.databases):
                    # Защита от повторных событий
                    if current_time - self._last_click_time < 0.1 and index == self._last_click_index:
                        return None
                    self._last_click_time = current_time
                    self._last_click_index = index

                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        # Одиночный клик: выделяем элемент
                        self.selected_index = index
                        self._adjust_scroll()
                        self.focus_mode = 0
                        self.needs_redraw = True
            return None
        except:
            return None

    def handle_input(self):
        """Основной цикл обработки ввода"""
        self.handle_resize()

        # Устанавливаем таймаут для getch в зависимости от состояния
        if self.state in ("downloading", "extracting"):
            self.stdscr.timeout(100)  # 100 мс
        else:
            self.stdscr.timeout(-1)   # блокирующий режим

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
        # Если key == -1 (таймаут) — просто ничего не делаем, экран уже перерисован
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
            # Пробел или Enter переключают выбор (радио-кнопка)
            # В радио-кнопках выбор только одного, поэтому просто выделяем текущий
            self.needs_redraw = True

    def handle_action(self, action):
        if action == "select":
            if self.state == "selecting" and self.databases:
                selected_db = self.databases[self.selected_index]
                self.app.selected_demo_db = selected_db  # сохраняем выбор
                # Пока переходим обратно на экран опций (заглушка)
                self.app.switch_screen("db_option")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Демо-база данных"