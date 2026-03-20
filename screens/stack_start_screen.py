#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import threading
import subprocess
import queue
import docker
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class StackStartScreen(BaseScreen):
    """
    Экран запуска Docker-стека.
    Сначала загружает образы с прогрессом, затем запускает контейнеры.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.compose_dir = None
        self.client = None
        self.images = []               # список имён образов для загрузки
        self.image_status = {}         # статус каждого образа: 'pending', 'pulling', 'done'
        self.image_progress = {}       # прогресс загрузки (0-100)
        self.current_pull_index = 0    # индекс текущего загружаемого образа
        self.pull_thread = None
        self.pull_queue = queue.Queue()
        self.running = False
        self.started = False
        self.status_message = "Готов"
        self.spinner_frames = ['|', '/', '-', '\\']
        self.spinner_idx = 0

        # Поток для вывода docker-compose up
        self.up_output_queue = queue.Queue()
        self.up_output_lines = []
        self.max_up_lines = 500
        self.scroll_offset = 0

        self.buttons = [
            Button(0, "[ Запустить ]", "start", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - вывод (прокрутка), 1 - кнопки

    def on_enter(self):
        self.compose_dir = getattr(self.app, 'compose_dir', None)
        self.client = docker.from_env()
        self.images = self._extract_images_from_compose()
        self.image_status = {img: 'pending' for img in self.images}
        self.image_progress = {img: 0 for img in self.images}
        self.current_pull_index = 0
        self.pull_queue = queue.Queue()
        self.up_output_queue = queue.Queue()
        self.up_output_lines = []
        self.scroll_offset = 0
        self.running = False
        self.started = False
        self.status_message = "Готов"
        self.buttons = [
            Button(0, "[ Запустить ]", "start", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.needs_redraw = True

    def _extract_images_from_compose(self):
        """Извлекает имена образов из docker-compose.yml в текущей папке"""
        images = []
        compose_path = os.path.join(self.compose_dir, 'docker-compose.yml')
        if not os.path.exists(compose_path):
            return images
        try:
            import yaml
            with open(compose_path, 'r') as f:
                data = yaml.safe_load(f)
            if 'services' in data:
                for service, config in data['services'].items():
                    if 'image' in config:
                        images.append(config['image'])
            # удаляем дубликаты, сохраняя порядок
            seen = set()
            unique = []
            for img in images:
                if img not in seen:
                    seen.add(img)
                    unique.append(img)
            return unique
        except Exception:
            return images

    def _pull_images(self):
        """Загружает образы последовательно, обновляя прогресс"""
        for i, img in enumerate(self.images):
            self.current_pull_index = i
            self.image_status[img] = 'pulling'
            self.needs_redraw = True
            try:
                # Пулл образа с отслеживанием прогресса
                for line in self.client.api.pull(img, stream=True, decode=True):
                    # Парсим прогресс
                    if 'status' in line:
                        status = line['status']
                        if 'id' in line:
                            # Для каждого слоя свой прогресс, мы возьмём общий
                            pass
                        # Пытаемся извлечь процент
                        if 'progressDetail' in line and line['progressDetail']:
                            total = line['progressDetail'].get('total')
                            current = line['progressDetail'].get('current')
                            if total and total > 0:
                                percent = int(current * 100 / total)
                                self.image_progress[img] = percent
                            else:
                                # Если нет точных данных, крутим спиннер
                                self.image_progress[img] = (self.image_progress.get(img, 0) + 5) % 100
                        else:
                            self.image_progress[img] = (self.image_progress.get(img, 0) + 5) % 100
                        self.needs_redraw = True
            except Exception as e:
                self.pull_queue.put(f"Ошибка загрузки {img}: {e}")
                self.image_status[img] = 'error'
            else:
                self.image_status[img] = 'done'
                self.image_progress[img] = 100
                self.needs_redraw = True
        self.pull_queue.put("pull_done")

    def _run_up(self):
        """Запускает docker-compose up -d и читает вывод"""
        try:
            proc = subprocess.Popen(
                ["docker-compose", "up", "-d"],
                cwd=self.compose_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in proc.stdout:
                self.up_output_queue.put(line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                self.up_output_queue.put("--- Стек успешно запущен ---")
                self.status_message = "Запущен"
                self.started = True
                self.buttons = [
                    Button(0, "[ Остановить ]", "stop", enabled=True),
                    Button(1, "[ Логи ]", "logs", enabled=True),
                    Button(2, "[ Выход ]", "exit", enabled=True)
                ]
            else:
                self.up_output_queue.put(f"--- Ошибка запуска (код {proc.returncode}) ---")
                self.status_message = "Ошибка запуска"
                self.buttons = [
                    Button(0, "[ Повторить ]", "start", enabled=True),
                    Button(1, "[ Выход ]", "exit", enabled=True)
                ]
        except Exception as e:
            self.up_output_queue.put(f"--- Исключение: {e} ---")
            self.status_message = "Ошибка"
            self.buttons = [
                Button(0, "[ Повторить ]", "start", enabled=True),
                Button(1, "[ Выход ]", "exit", enabled=True)
            ]
        self.needs_redraw = True

    def _stop_stack(self):
        """Останавливает стек"""
        self.status_message = "Остановка..."
        self.needs_redraw = True
        def down():
            try:
                subprocess.run(
                    ["docker-compose", "down"],
                    cwd=self.compose_dir,
                    capture_output=True,
                    text=True
                )
                self.up_output_queue.put("--- Стек остановлен ---")
            except Exception as e:
                self.up_output_queue.put(f"--- Ошибка при остановке: {e} ---")
            finally:
                self.status_message = "Остановлен"
                self.started = False
                self.buttons = [
                    Button(0, "[ Запустить ]", "start", enabled=True),
                    Button(1, "[ Выход ]", "exit", enabled=True)
                ]
                self.needs_redraw = True
        threading.Thread(target=down, daemon=True).start()

    def _handle_pull(self):
        """Обрабатывает очередь от потока загрузки"""
        try:
            while True:
                msg = self.pull_queue.get_nowait()
                if msg == "pull_done":
                    # Загрузка завершена, запускаем up
                    self.status_message = "Загрузка образов завершена. Запуск контейнеров..."
                    self.needs_redraw = True
                    threading.Thread(target=self._run_up, daemon=True).start()
                else:
                    # сообщение об ошибке
                    self.up_output_lines.append(msg)
                    if len(self.up_output_lines) > self.max_up_lines:
                        self.up_output_lines.pop(0)
        except queue.Empty:
            pass

    def _handle_up_output(self):
        """Обрабатывает вывод docker-compose up"""
        try:
            while True:
                line = self.up_output_queue.get_nowait()
                self.up_output_lines.append(line)
                if len(self.up_output_lines) > self.max_up_lines:
                    self.up_output_lines.pop(0)
                if self.scroll_offset + self._get_output_height() >= len(self.up_output_lines) - 1:
                    self.scroll_offset = max(0, len(self.up_output_lines) - self._get_output_height())
                self.needs_redraw = True
        except queue.Empty:
            pass

    def draw_instructions(self):
        pass

    def _get_output_height(self):
        # Высота области вывода: вычитаем заголовок, строку статуса и кнопки
        return self.height - 10

    def draw_content(self):
        title = " ЗАПУСК СТЕКА "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        # Строка статуса со спиннером
        if self.running and not self.started:
            spinner = self.spinner_frames[self.spinner_idx]
            self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
            status_line = f"Статус: {self.status_message} {spinner}"
        else:
            status_line = f"Статус: {self.status_message}"
        safe_addstr(self.stdscr, 6, 4, status_line, curses.A_BOLD)

        # Список образов с прогрессом (если есть образы)
        if self.images:
            safe_addstr(self.stdscr, 7, 4, "Загрузка образов:", curses.A_BOLD)
            y = 8
            for i, img in enumerate(self.images):
                if y >= self.height - 8:
                    break
                status = self.image_status[img]
                if status == 'pending':
                    symbol = "○"
                    progress_str = ""
                elif status == 'pulling':
                    symbol = "◉"
                    progress = self.image_progress.get(img, 0)
                    progress_str = f" {progress}%"
                elif status == 'done':
                    symbol = "✓"
                    progress_str = " 100%"
                else:
                    symbol = "✗"
                    progress_str = " ошибка"
                # обрезаем имя образа
                img_short = img
                if len(img_short) > self.width - 20:
                    img_short = img_short[:self.width-23] + "..."
                safe_addstr(self.stdscr, y, 4, f"{symbol} {img_short}{progress_str}")
                y += 1
            y += 1
        else:
            y = 8

        # Область вывода (логи docker-compose up)
        out_start_y = y
        out_height = self._get_output_height() - (y - 8)  # корректировка
        if out_height < 1:
            out_height = 1
        end_idx = min(len(self.up_output_lines), self.scroll_offset + out_height)
        for i in range(self.scroll_offset, end_idx):
            yy = out_start_y + (i - self.scroll_offset)
            if yy >= self.height - 4:
                break
            line = self.up_output_lines[i]
            if len(line) > self.width - 8:
                line = line[:self.width-11] + "..."
            safe_addstr(self.stdscr, yy, 4, line)

        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, out_start_y - 1, 4, "↑ ...")
        if end_idx < len(self.up_output_lines):
            safe_addstr(self.stdscr, out_start_y + out_height, 4, "↓ ...")

        # Инструкция
        if self.focus_mode == 0:
            instr = "↑↓: прокрутка | TAB: переключение на кнопки"
        else:
            instr = "TAB: переключение на вывод | Enter: выбор кнопки"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def handle_input(self):
        self.handle_resize()
        self.draw()

        self._handle_pull()
        self._handle_up_output()

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            # можно добавить обработку мыши позже
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
            if self.scroll_offset + self._get_output_height() < len(self.up_output_lines):
                self.scroll_offset += 1
                self.needs_redraw = True
        elif key == curses.KEY_PPAGE:
            self.scroll_offset = max(0, self.scroll_offset - self._get_output_height())
            self.needs_redraw = True
        elif key == curses.KEY_NPAGE:
            self.scroll_offset = min(
                max(0, len(self.up_output_lines) - self._get_output_height()),
                self.scroll_offset + self._get_output_height()
            )
            self.needs_redraw = True

    def handle_action(self, action):
        if action == "start":
            if self.running:
                return None
            self.running = True
            self.started = False
            self.buttons = [
                Button(0, "[ Остановить ]", "stop", enabled=False),  # на время загрузки нельзя остановить
                Button(1, "[ Выход ]", "exit", enabled=False)
            ]
            self.status_message = "Загрузка образов..."
            self.needs_redraw = True
            self.pull_thread = threading.Thread(target=self._pull_images, daemon=True)
            self.pull_thread.start()
        elif action == "stop":
            if self.running:
                # останавливаем загрузку/запуск
                # но проще вызвать _stop_stack, который выполнит down
                self._stop_stack()
                self.running = False
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