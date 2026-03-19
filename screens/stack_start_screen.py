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

class StackStartScreen(BaseScreen):
    """
    Экран запуска Docker-стека. Показывает процесс up -d, затем позволяет
    перейти к просмотру логов или остановить стек.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.compose_dir = None
        self.output_queue = queue.Queue()
        self.output_lines = []
        self.max_lines = 500
        self.scroll_offset = 0
        self.process = None
        self.monitor_thread = None
        self.status = "Готов"
        self.running = False  # идёт ли процесс up/down
        self.started = False  # успешно ли запущен стек

        self.buttons = [
            Button(0, "[ Запустить ]", "start", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - вывод (прокрутка), 1 - кнопки

    def on_enter(self):
        self.compose_dir = getattr(self.app, 'compose_dir', None)
        self.output_lines = []
        self.scroll_offset = 0
        self.status = "Готов"
        self.running = False
        self.started = False
        self.buttons = [
            Button(0, "[ Запустить ]", "start", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def _get_output_height(self):
        return self.height - 9

    def draw_content(self):
        title = " ЗАПУСК СТЕКА "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        safe_addstr(self.stdscr, 6, 4, f"Статус: {self.status}", curses.A_BOLD)

        out_start_y = 8
        out_height = self._get_output_height()
        end_idx = min(len(self.output_lines), self.scroll_offset + out_height)
        for i in range(self.scroll_offset, end_idx):
            y = out_start_y + (i - self.scroll_offset)
            if y >= self.height - 4:
                break
            line = self.output_lines[i]
            if len(line) > self.width - 8:
                line = line[:self.width-11] + "..."
            safe_addstr(self.stdscr, y, 4, line)

        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, out_start_y - 1, 4, "↑ ...")
        if end_idx < len(self.output_lines):
            safe_addstr(self.stdscr, out_start_y + out_height, 4, "↓ ...")

        if self.focus_mode == 0:
            instr = "↑↓: прокрутка | TAB: переключение на кнопки"
        else:
            instr = "TAB: переключение на вывод | Enter: выбор кнопки"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def _start_stack(self):
        if self.running:
            return
        self.output_lines = []
        self.scroll_offset = 0
        self.status = "Запуск..."
        self.running = True
        self.started = False
        self.buttons = [
            Button(0, "[ Остановить ]", "stop", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.needs_redraw = True

        def run():
            try:
                proc = subprocess.Popen(
                    ["docker-compose", "up", "-d"],
                    cwd=self.compose_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                self.process = proc
                for line in proc.stdout:
                    if not self.running:
                        break
                    self.output_queue.put(line.rstrip())
                proc.wait()
                if proc.returncode == 0:
                    self.output_queue.put("--- Стек успешно запущен ---")
                    self.status = "Запущен"
                    self.started = True
                    self.buttons = [
                        Button(0, "[ Остановить ]", "stop", enabled=True),
                        Button(1, "[ Логи ]", "logs", enabled=True),
                        Button(2, "[ Выход ]", "exit", enabled=True)
                    ]
                else:
                    self.output_queue.put(f"--- Ошибка запуска (код {proc.returncode}) ---")
                    self.status = "Ошибка"
                    self.buttons = [
                        Button(0, "[ Повторить ]", "start", enabled=True),
                        Button(1, "[ Выход ]", "exit", enabled=True)
                    ]
            except Exception as e:
                self.output_queue.put(f"--- Исключение: {e} ---")
                self.status = "Ошибка"
                self.buttons = [
                    Button(0, "[ Повторить ]", "start", enabled=True),
                    Button(1, "[ Выход ]", "exit", enabled=True)
                ]
            finally:
                self.running = False
                self.needs_redraw = True

        self.monitor_thread = threading.Thread(target=run, daemon=True)
        self.monitor_thread.start()

    def _stop_stack(self):
        if self.running:
            self.running = False
            if self.process:
                self.process.terminate()
        self.status = "Остановка..."
        self.needs_redraw = True

        def down():
            try:
                subprocess.run(
                    ["docker-compose", "down"],
                    cwd=self.compose_dir,
                    capture_output=True,
                    text=True
                )
                self.output_queue.put("--- Стек остановлен ---")
            except Exception as e:
                self.output_queue.put(f"--- Ошибка при остановке: {e} ---")
            finally:
                self.status = "Остановлен"
                self.started = False
                self.buttons = [
                    Button(0, "[ Запустить ]", "start", enabled=True),
                    Button(1, "[ Выход ]", "exit", enabled=True)
                ]
                self.needs_redraw = True

        t = threading.Thread(target=down, daemon=True)
        t.start()

    def handle_input(self):
        self.handle_resize()
        self.draw()

        try:
            while True:
                line = self.output_queue.get_nowait()
                self.output_lines.append(line)
                if len(self.output_lines) > self.max_lines:
                    self.output_lines.pop(0)
                if self.scroll_offset + self._get_output_height() >= len(self.output_lines) - 1:
                    self.scroll_offset = max(0, len(self.output_lines) - self._get_output_height())
                self.needs_redraw = True
        except queue.Empty:
            pass

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            pass
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:  # TAB
            self.focus_mode = (self.focus_mode + 1) % 2
            self.needs_redraw = True
        elif self.focus_mode == 0:
            self._handle_output_keys(key)
        else:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def _handle_output_keys(self, key):
        if key == curses.KEY_UP:
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.scroll_offset + self._get_output_height() < len(self.output_lines):
                self.scroll_offset += 1
                self.needs_redraw = True
        elif key == curses.KEY_PPAGE:
            self.scroll_offset = max(0, self.scroll_offset - self._get_output_height())
            self.needs_redraw = True
        elif key == curses.KEY_NPAGE:
            self.scroll_offset = min(
                max(0, len(self.output_lines) - self._get_output_height()),
                self.scroll_offset + self._get_output_height()
            )
            self.needs_redraw = True

    def handle_action(self, action):
        if action == "start":
            self._start_stack()
        elif action == "stop":
            self._stop_stack()
        elif action == "logs":
            if self.started:
                self.app.switch_screen("stack_logs")
        elif action == "exit":
            if self.running:
                self._stop_stack()
            return "exit"
        return None

    def get_screen_name(self):
        return "Запуск стека"