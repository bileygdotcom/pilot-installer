#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import threading
import subprocess
import queue
import time
import docker
from docker.errors import APIError, NotFound
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class StackStartScreen(BaseScreen):
    """
    Экран запуска Docker-стека.
    Сначала загружает образы с прогрессом (через Docker SDK),
    затем выполняет docker-compose up -d.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.compose_dir = None
        self.status = "Готов"
        self.images = []          # список словарей: {name, status, progress, current_layer}
        self.current_image_index = 0
        self.running = False
        self.started = False
        self.docker_client = None
        self.pull_thread = None
        self.compose_thread = None
        self.spinner_chars = ['|', '/', '-', '\\']
        self.spinner_idx = 0
        self.update_spinner = False

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

        self.buttons = [
            Button(0, "[ Запустить ]", "start", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0

    def on_enter(self):
        self.compose_dir = getattr(self.app, 'compose_dir', None)
        self.status = "Готов"
        self.images = []
        self.current_image_index = 0
        self.running = False
        self.started = False
        self.update_spinner = False
        self.buttons = [
            Button(0, "[ Запустить ]", "start", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def _get_image_list(self):
        try:
            result = subprocess.run(
                ["docker-compose", "config"],
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                check=True
            )
            images = []
            prefix = "registry.ascon.ru/project/pilotdev/pilot/"
            for line in result.stdout.splitlines():
                if 'image:' in line:
                    img = line.split('image:')[1].strip().strip('"')
                    if img:
                        if img.startswith(prefix):
                            display = img[len(prefix):]
                        else:
                            display = img
                        images.append((img, display))
            return images
        except Exception as e:
            self.status = f"Ошибка чтения compose: {e}"
            return []

    def _pull_image(self, image_name, index):
        try:
            self.images[index]['status'] = "pull_start"
            self.images[index]['progress'] = 0
            self.needs_redraw = True

            for line in self.docker_client.api.pull(image_name, stream=True, decode=True):
                if not self.running:
                    return
                if 'status' in line:
                    status_text = line['status']
                    if 'Downloading' in status_text:
                        if 'progressDetail' in line:
                            current = line['progressDetail'].get('current', 0)
                            total = line['progressDetail'].get('total', 1)
                            if total > 0:
                                percent = int(current * 100 / total)
                                self.images[index]['progress'] = percent
                                self.images[index]['current_layer'] = status_text
                        else:
                            self.images[index]['current_layer'] = status_text
                    elif 'Already exists' in status_text or 'Pull complete' in status_text:
                        self.images[index]['progress'] = 100
                        self.images[index]['current_layer'] = status_text
                    elif 'Pulling from' in status_text:
                        self.images[index]['current_layer'] = status_text
                    self.needs_redraw = True
            self.images[index]['status'] = "done"
            self.images[index]['progress'] = 100
        except Exception as e:
            self.images[index]['status'] = "error"
            self.images[index]['error'] = str(e)
            self.status = f"Ошибка загрузки {image_name}: {e}"
        finally:
            self.needs_redraw = True

    def _pull_all_images(self):
        image_list = self._get_image_list()
        if not image_list:
            self.status = "Не найдены образы в compose"
            self.buttons = [
                Button(0, "[ Повторить ]", "start", enabled=True),
                Button(1, "[ Выход ]", "exit", enabled=True)
            ]
            self.running = False
            self.needs_redraw = True
            return

        self.images = []
        for img_name, display_name in image_list:
            self.images.append({
                'name': img_name,
                'display': display_name,
                'status': 'wait',
                'progress': 0,
                'current_layer': '',
                'error': ''
            })
        self.current_image_index = 0

        self.docker_client = docker.from_env()
        for idx, img_info in enumerate(self.images):
            if not self.running:
                break
            self.current_image_index = idx
            self._pull_image(img_info['name'], idx)
            if img_info['status'] == 'error':
                break

        if all(img['status'] == 'done' for img in self.images):
            self.status = "Все образы загружены. Запуск стека..."
            self.needs_redraw = True
            self._run_compose_up()
        else:
            self.status = "Загрузка образов завершена с ошибками"
            self.buttons = [
                Button(0, "[ Повторить ]", "start", enabled=True),
                Button(1, "[ Выход ]", "exit", enabled=True)
            ]
            self.running = False
            self.needs_redraw = True

    def _run_compose_up(self):
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
                output = ""
                for line in proc.stdout:
                    output += line
                    self.status = f"Запуск: {line.strip()}"
                    self.needs_redraw = True
                proc.wait()
                if proc.returncode == 0:
                    self.status = "Стек успешно запущен"
                    self.started = True
                    self.buttons = [
                        Button(0, "[ Остановить ]", "stop", enabled=True),
                        Button(1, "[ Логи ]", "logs", enabled=True),
                        Button(2, "[ Настроить ]", "setup", enabled=True),
                        Button(3, "[ Выход ]", "exit", enabled=True)
                    ]
                else:
                    self.status = f"Ошибка запуска (код {proc.returncode})"
                    self.buttons = [
                        Button(0, "[ Повторить ]", "start", enabled=True),
                        Button(1, "[ Выход ]", "exit", enabled=True)
                    ]
            except Exception as e:
                self.status = f"Ошибка запуска: {e}"
                self.buttons = [
                    Button(0, "[ Повторить ]", "start", enabled=True),
                    Button(1, "[ Выход ]", "exit", enabled=True)
                ]
            finally:
                self.running = False
                self.needs_redraw = True

        self.compose_thread = threading.Thread(target=run, daemon=True)
        self.compose_thread.start()

    def _start_stack(self):
        if self.running:
            return
        self.running = True
        self.started = False
        self.status = "Загрузка образов..."
        self.images = []
        self.current_image_index = 0
        self.buttons = [
            Button(0, "[ Остановить ]", "stop", enabled=True),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.needs_redraw = True
        self.update_spinner = True

        self.pull_thread = threading.Thread(target=self._pull_all_images, daemon=True)
        self.pull_thread.start()

    def _stop_stack(self):
        if self.running:
            self.running = False
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
                self.status = "Стек остановлен"
                self.started = False
                self.buttons = [
                    Button(0, "[ Запустить ]", "start", enabled=True),
                    Button(1, "[ Выход ]", "exit", enabled=True)
                ]
            except Exception as e:
                self.status = f"Ошибка остановки: {e}"
            finally:
                self.needs_redraw = True

        threading.Thread(target=down, daemon=True).start()

    def draw_content(self):
        title = " ЗАПУСК СТЕКА "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        status_text = self.status
        if self.update_spinner and self.running:
            self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
            status_text = f"{self.spinner_chars[self.spinner_idx]} {self.status}"
        safe_addstr(self.stdscr, 6, 4, f"Статус: {status_text}", curses.A_BOLD)

        start_y = 8
        for i, img in enumerate(self.images):
            y = start_y + i * 2
            if y >= self.height - 6:
                break
            if i == self.current_image_index and self.running:
                attr = curses.A_REVERSE
            else:
                attr = 0

            name = img['display']
            if len(name) > 40:
                name = name[:37] + "..."
            safe_addstr(self.stdscr, y, 4, name, attr)

            if img['status'] == 'wait':
                status_str = "ожидание"
            elif img['status'] == 'pull_start':
                progress = img['progress']
                status_str = f"загрузка {progress}%"
                if img.get('current_layer'):
                    status_str += f" - {img['current_layer'][:30]}"
            elif img['status'] == 'done':
                status_str = "готов"
            elif img['status'] == 'error':
                status_str = f"ошибка: {img.get('error', '')[:40]}"
            else:
                status_str = img['status']
            safe_addstr(self.stdscr, y, 50, status_str[:self.width-54])

        # Инструкция (будет нарисована в draw_instructions, но мы её не используем, так что рисуем сами)
        instr = "TAB: переключение на кнопки | ↑↓: прокрутка списка" if self.focus_mode == 0 else "TAB: переключение на список | Enter: выбор кнопки"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def handle_mouse(self):
        """Обрабатывает события мыши: клики по кнопкам"""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            # Защита от множественных событий
            current_time = time.time()
            if current_time - self._last_click_time < 0.1:
                return None
            self._last_click_time = current_time

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
        except:
            pass
        return None

    def handle_input(self):
        if self.running and not self.started:
            self.stdscr.timeout(100)
        else:
            self.stdscr.timeout(-1)

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
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            if self.focus_mode == 0 and self.images:
                if key == curses.KEY_UP and self.current_image_index > 0:
                    self.current_image_index -= 1
                    self.needs_redraw = True
                elif key == curses.KEY_DOWN and self.current_image_index < len(self.images) - 1:
                    self.current_image_index += 1
                    self.needs_redraw = True
        elif self.focus_mode == 1:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def handle_action(self, action):
        if action == "start":
            self._start_stack()
        elif action == "stop":
            self._stop_stack()
        elif action == "logs":
            if self.started:
                self.app.switch_screen("stack_logs")
        elif action == "setup":
            if self.started:
                self.app.switch_screen("initial_setup")
        elif action == "exit":
            if self.running:
                self._stop_stack()
            return "exit"
        return None

    def get_screen_name(self):
        return "Запуск стека"