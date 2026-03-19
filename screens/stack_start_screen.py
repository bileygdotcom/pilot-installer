#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import time
import threading
import subprocess
import queue
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class StackStartScreen(BaseScreen):
    """
    Экран запуска Docker-стека с отображением логов в реальном времени.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.compose_dir = None
        self.log_queue = queue.Queue()
        self.log_lines = []
        self.max_log_lines = 1000  # ограничим количество хранимых строк
        self.scroll_offset = 0
        self.process = None
        self.monitor_thread = None
        self.running = False
        self.status = "Готов к запуску"

        self.buttons = [
            Button(0, "[ Запустить ]", "start", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - логи (прокрутка), 1 - кнопки

    def on_enter(self):
        """При входе получаем путь к compose-файлу"""
        self.compose_dir = getattr(self.app, 'compose_dir', None)
        self.status = "Готов к запуску"
        self.log_lines = []
        self.scroll_offset = 0
        self.running = False
        self.buttons[0].text = "[ Запустить ]"
        self.buttons[0].action = "start"
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def _get_log_height(self):
        """Высота области логов (с учётом заголовка и кнопок)"""
        return self.height - 8

    def draw_content(self):
        title = " ЗАПУСК СТЕКА "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        # Статус
        safe_addstr(self.stdscr, 6, 4, f"Статус: {self.status}", curses.A_BOLD)

        # Область логов
        log_start_y = 8
        log_height = self._get_log_height()
        end_idx = min(len(self.log_lines), self.scroll_offset + log_height)
        for i in range(self.scroll_offset, end_idx):
            y = log_start_y + (i - self.scroll_offset)
            if y >= self.height - 4:
                break
            line = self.log_lines[i]
            if len(line) > self.width - 8:
                line = line[:self.width-11] + "..."
            safe_addstr(self.stdscr, y, 4, line)

        # Индикаторы прокрутки
        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, log_start_y - 1, 4, "↑ ...")
        if end_idx < len(self.log_lines):
            safe_addstr(self.stdscr, log_start_y + log_height, 4, "↓ ...")

        # Инструкция
        if self.focus_mode == 0:
            instr = "↑↓: прокрутка логов | TAB: переключение на кнопки"
        else:
            instr = "TAB: переключение на логи | Enter: выбор кнопки"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def _start_stack(self):
        """Запускает стек в отдельном потоке и начинает мониторинг логов"""
        if not self.compose_dir or not os.path.exists(self.compose_dir):
            self.status = "Ошибка: папка compose не найдена"
            self.needs_redraw = True
            return

        def run():
            # Запускаем docker-compose up -d
            self.status = "Запуск контейнеров..."
            self.needs_redraw = True
            try:
                proc = subprocess.Popen(
                    ["docker-compose", "up", "-d"],
                    cwd=self.compose_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = proc.communicate()
                if proc.returncode != 0:
                    self.log_queue.put(f"Ошибка запуска: {stderr}")
                    self.status = "Ошибка запуска"
                    self.buttons[0].text = "[ Повторить ]"
                    self.buttons[0].action = "start"
                    self.needs_redraw = True
                    return

                self.status = "Контейнеры запущены, читаем логи..."
                self.needs_redraw = True

                # Теперь читаем логи через docker-compose logs -f
                self.process = subprocess.Popen(
                    ["docker-compose", "logs", "-f"],
                    cwd=self.compose_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                self.running = True
                self.buttons[0].text = "[ Остановить ]"
                self.buttons[0].action = "stop"

                # Читаем вывод построчно
                for line in self.process.stdout:
                    if not self.running:
                        break
                    self.log_queue.put(line.rstrip())
                self.process.wait()
            except Exception as e:
                self.log_queue.put(f"Исключение: {e}")
                self.status = "Ошибка"
                self.needs_redraw = True
            finally:
                self.running = False
                self.buttons[0].text = "[ Запустить ]"
                self.buttons[0].action = "start"
                self.needs_redraw = True

        self.monitor_thread = threading.Thread(target=run, daemon=True)
        self.monitor_thread.start()

    def _stop_stack(self):
        """Останавливает стек (docker-compose down)"""
        self.status = "Остановка..."
        self.needs_redraw = True
        self.running = False
        if self.process:
            self.process.terminate()
        try:
            subprocess.run(
                ["docker-compose", "down"],
                cwd=self.compose_dir,
                capture_output=True,
                text=True
            )
            self.log_queue.put("Стек остановлен.")
        except Exception as e:
            self.log_queue.put(f"Ошибка при остановке: {e}")
        self.status = "Остановлен"
        self.buttons[0].text = "[ Запустить ]"
        self.buttons[0].action = "start"
        self.needs_redraw = True

    def handle_input(self):
        self.handle_resize()
        self.draw()

        # Обновляем логи из очереди
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log_lines.append(line)
                if len(self.log_lines) > self.max_log_lines:
                    self.log_lines.pop(0)
                # Автопрокрутка, если мы внизу
                if self.scroll_offset + self._get_log_height() >= len(self.log_lines) - 1:
                    self.scroll_offset = max(0, len(self.log_lines) - self._get_log_height())
                self.needs_redraw = True
        except queue.Empty:
            pass

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            # Мышь пока не реализуем для простоты
            pass
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:  # TAB
            self.focus_mode = (self.focus_mode + 1) % 2
            self.needs_redraw = True
        elif self.focus_mode == 0:
            self._handle_log_keys(key)
        else:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def _handle_log_keys(self, key):
        if key == curses.KEY_UP:
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.scroll_offset + self._get_log_height() < len(self.log_lines):
                self.scroll_offset += 1
                self.needs_redraw = True
        elif key == curses.KEY_PPAGE:  # Page Up
            self.scroll_offset = max(0, self.scroll_offset - self._get_log_height())
            self.needs_redraw = True
        elif key == curses.KEY_NPAGE:  # Page Down
            self.scroll_offset = min(
                max(0, len(self.log_lines) - self._get_log_height()),
                self.scroll_offset + self._get_log_height()
            )
            self.needs_redraw = True

    def handle_action(self, action):
        if action == "start":
            self._start_stack()
        elif action == "stop":
            self._stop_stack()
        elif action == "exit":
            # Если стек запущен, сначала остановим
            if self.running:
                self._stop_stack()
            return "exit"
        return None

    def get_screen_name(self):
        return "Запуск стека"