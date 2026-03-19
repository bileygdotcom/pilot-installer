#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import threading
import subprocess
import queue
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class StackLogsScreen(BaseScreen):
    """
    Экран просмотра логов работающего стека.
    Запускает docker-compose logs -f и отображает вывод.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.compose_dir = None
        self.log_queue = queue.Queue()
        self.log_lines = []
        self.max_log_lines = 1000
        self.scroll_offset = 0
        self.process = None
        self.running = False
        self.monitor_thread = None

        self.buttons = [
            Button(0, "[ Назад ]", "back", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0

    def on_enter(self):
        self.compose_dir = getattr(self.app, 'compose_dir', None)
        self.log_lines = []
        self.scroll_offset = 0
        self.running = False
        self._start_logging()
        self.needs_redraw = True

    def _start_logging(self):
        if not self.compose_dir or not os.path.exists(self.compose_dir):
            self.log_queue.put("Ошибка: папка compose не найдена")
            return

        def run():
            try:
                self.process = subprocess.Popen(
                    ["docker-compose", "logs", "-f"],
                    cwd=self.compose_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                self.running = True
                for line in self.process.stdout:
                    if not self.running:
                        break
                    self.log_queue.put(line.rstrip())
                self.process.wait()
            except Exception as e:
                self.log_queue.put(f"Ошибка: {e}")
            finally:
                self.running = False

        self.monitor_thread = threading.Thread(target=run, daemon=True)
        self.monitor_thread.start()

    def _stop_logging(self):
        self.running = False
        if self.process:
            self.process.terminate()

    def draw_instructions(self):
        pass

    def _get_log_height(self):
        return self.height - 7

    def draw_content(self):
        title = " ЛОГИ СТЕКА "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        log_start_y = 6
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

        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, log_start_y - 1, 4, "↑ ...")
        if end_idx < len(self.log_lines):
            safe_addstr(self.stdscr, log_start_y + log_height, 4, "↓ ...")

        instr = "↑↓: прокрутка | TAB: переключение на кнопки" if self.focus_mode == 0 else "TAB: переключение на логи | Enter: выбор кнопки"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def handle_input(self):
        self.handle_resize()
        self.draw()

        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log_lines.append(line)
                if len(self.log_lines) > self.max_log_lines:
                    self.log_lines.pop(0)
                if self.scroll_offset + self._get_log_height() >= len(self.log_lines) - 1:
                    self.scroll_offset = max(0, len(self.log_lines) - self._get_log_height())
                self.needs_redraw = True
        except queue.Empty:
            pass

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            pass
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:
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
        elif key == curses.KEY_PPAGE:
            self.scroll_offset = max(0, self.scroll_offset - self._get_log_height())
            self.needs_redraw = True
        elif key == curses.KEY_NPAGE:
            self.scroll_offset = min(
                max(0, len(self.log_lines) - self._get_log_height()),
                self.scroll_offset + self._get_log_height()
            )
            self.needs_redraw = True

    def handle_action(self, action):
        if action == "back":
            self._stop_logging()
            self.app.switch_screen("stack_start")
            return None
        elif action == "exit":
            self._stop_logging()
            return "exit"
        return None

    def get_screen_name(self):
        return "Логи стека"