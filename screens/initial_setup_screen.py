#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import time
import threading
import subprocess
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class InitialSetupScreen(BaseScreen):
    """
    Экран начальной настройки после запуска стека.
    Добавляет администратора Pilot-Server, подключает базу данных,
    и настраивает Pilot-BIM-Server (если выбран).
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.stack_name = None
        self.stack_path = None
        self.container_name = None
        self.db_name = None
        self.db_path = None
        self.fa_path = None
        self.credentials = None
        self.bim_enabled = False
        self.log_lines = []
        self.running = False
        self.setup_thread = None
        self.buttons = [
            Button(0, "[ Далее ]", "continue", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - вывод, 1 - кнопки

    def on_enter(self):
        self.stack_name = getattr(self.app, 'stack_name', None)
        self.stack_path = getattr(self.app, 'stack_path', None)
        if not self.stack_name or not self.stack_path:
            self.log_lines.append("Ошибка: стек не определён")
            return

        self.container_name = f"{self.stack_name}_pilot-server"
        self.credentials = getattr(self.app, 'admin_credentials', {})
        if not self.credentials or "Pilot-Server" not in self.credentials:
            self.log_lines.append("Учётные данные администратора Pilot-Server не заданы")
            self.buttons[0].enabled = True
            self.needs_redraw = True
            return

        # Определяем базу данных
        self.db_name = None
        self.db_path = None
        self.fa_path = None
        if hasattr(self.app, 'selected_demo_db') and self.app.selected_demo_db:
            self.db_name = self.app.selected_demo_db
            self.db_path = getattr(self.app, 'existing_db_path', None)
            self.fa_path = getattr(self.app, 'existing_fa_path', None)
        elif hasattr(self.app, 'existing_db_path') and self.app.existing_db_path:
            self.db_path = self.app.existing_db_path
            self.fa_path = getattr(self.app, 'existing_fa_path', None)
            self.db_name = os.path.splitext(os.path.basename(self.db_path))[0]

        # Проверяем, выбран ли Pilot-BIM-Server
        selected_components = getattr(self.app, 'selected_components', [])
        self.bim_enabled = "Pilot-BIM-Server" in selected_components

        self.log_lines = []
        self.running = True
        self.buttons[0].enabled = False
        self.needs_redraw = True

        self.setup_thread = threading.Thread(target=self.run_setup, daemon=True)
        self.setup_thread.start()

    def run_setup(self):
        try:
            # 1. Добавить администратора Pilot-Server
            admin_login = self.credentials["Pilot-Server"]["login"]
            admin_pass = self.credentials["Pilot-Server"]["password"]
            cmd = [
                "docker", "exec",
                self.container_name,
                "/App/Ascon.Pilot.Daemon", "--admin",
                "/usr/share/ascon/pilot-server/settings/settings.xml",
                admin_login, admin_pass
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.log_lines.append(f"Добавлен администратор сервера {admin_login}")
            else:
                self.log_lines.append(f"Ошибка добавления администратора: {result.stderr.strip()}")
            self.needs_redraw = True
            time.sleep(1)

            # 2. Перезапустить контейнер
            subprocess.run(["docker", "restart", self.container_name], capture_output=True)
            self.log_lines.append("Настройка применена (контейнер перезапущен)")
            self.needs_redraw = True
            time.sleep(2)  # даём контейнеру время запуститься

            # 3. Подключить базу данных
            if self.db_path and self.fa_path and os.path.exists(self.db_path) and os.path.exists(self.fa_path):
                cmd_attach = [
                    "docker", "exec",
                    self.container_name,
                    "/App/Ascon.Pilot.Daemon", "--attach",
                    self.db_name,
                    self.db_path,
                    self.fa_path
                ]
                result = subprocess.run(cmd_attach, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_lines.append(f"Подключена база данных {self.db_name}")
                else:
                    self.log_lines.append(f"Ошибка подключения базы: {result.stderr.strip()}")
            else:
                self.log_lines.append("Недостаточно данных для подключения базы данных")
            self.needs_redraw = True
            time.sleep(1)

            # 4. Настройка Pilot-BIM-Server
            if self.bim_enabled and "Pilot-BIM-Server" in self.credentials:
                bim_login = self.credentials["Pilot-BIM-Server"]["login"]
                bim_pass = self.credentials["Pilot-BIM-Server"]["password"]
                bim_container = f"{self.stack_name}_pilot-bim-server"
                cmd_bim = [
                    "docker", "exec",
                    bim_container,
                    "/App/pBimAdmin", "-c",
                    f"http://pilot-server:5545/{self.db_name}",
                    bim_login, bim_pass
                ]
                result = subprocess.run(cmd_bim, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_lines.append(f"Подключение Pilot-BIM-Server произведено администратором {bim_login}")
                else:
                    self.log_lines.append(f"Ошибка настройки Pilot-BIM-Server: {result.stderr.strip()}")
            elif self.bim_enabled:
                self.log_lines.append("Недостаточно данных для настройки Pilot-BIM-Server")
            self.needs_redraw = True

        except Exception as e:
            self.log_lines.append(f"Ошибка: {e}")
        finally:
            self.running = False
            self.buttons[0].enabled = True
            self.needs_redraw = True

    def draw_instructions(self):
        pass

    def _get_log_height(self):
        return max(1, self.height - 10)

    def draw_content(self):
        title = " НАСТРОЙКА КОМПОНЕНТОВ PILOT "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        log_start_y = 6
        log_height = self._get_log_height()
        scroll_offset = max(0, len(self.log_lines) - log_height)

        for i in range(scroll_offset, len(self.log_lines)):
            y = log_start_y + (i - scroll_offset)
            if y >= self.height - 5:
                break
            line = self.log_lines[i]
            if len(line) > self.width - 8:
                line = line[:self.width-11] + "..."
            safe_addstr(self.stdscr, y, 4, line)

        if len(self.log_lines) > log_height:
            safe_addstr(self.stdscr, self.height - 5, 4, "↓ ...")

        instr = "Ожидание завершения настройки..." if self.running else "TAB: переключение на кнопки | Enter: выбор"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def handle_input(self):
        self.handle_resize()
        self.draw()

        if self.running:
            # Во время выполнения не ждём ввода, просто даём время
            time.sleep(0.1)
            return None

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            # упрощённо, можно добавить
            pass
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:  # TAB
            self.focus_mode = (self.focus_mode + 1) % 2
            self.needs_redraw = True
        elif self.focus_mode == 1:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def handle_action(self, action):
        if action == "continue":
            # Можно перейти на финальный экран или завершить
            return "next"
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Настройка"