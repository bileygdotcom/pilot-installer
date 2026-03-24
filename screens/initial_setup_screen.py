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
    Экран выполнения первичных настроек:
    - добавление администратора Pilot-Server
    - перезапуск контейнера pilot-server
    - подключение базы данных
    - (опционально) добавление администратора Pilot-BIM-Server
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.stack_name = None
        self.stack_path = None
        self.components = []
        self.db_name = None
        self.db_path = None
        self.fa_path = None
        self.admin_credentials = {}
        self.server_admin_login = ""
        self.server_admin_password = ""
        self.bim_admin_login = ""
        self.bim_admin_password = ""
        self.status_messages = []
        self.running = False
        self.setup_thread = None

        self.buttons = [
            Button(0, "[ Далее ]", "continue", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - вывод, 1 - кнопки

    def on_enter(self):
        # Получаем все необходимые данные из app
        self.stack_name = getattr(self.app, 'stack_name', None)
        self.stack_path = getattr(self.app, 'stack_path', None)
        self.components = getattr(self.app, 'selected_components', [])
        self.admin_credentials = getattr(self.app, 'admin_credentials', {})
        self.db_name = getattr(self.app, 'selected_demo_db', None) or \
                       (os.path.splitext(os.path.basename(getattr(self.app, 'existing_db_path', '')))[0] if getattr(self.app, 'existing_db_path', None) else None)
        self.db_path = getattr(self.app, 'existing_db_path', None)
        self.fa_path = getattr(self.app, 'existing_fa_path', None)

        # Извлекаем учётные данные для Pilot-Server и Pilot-BIM-Server
        for comp in self.components:
            if comp == "Pilot-Server":
                creds = self.admin_credentials.get(comp, {})
                self.server_admin_login = creds.get('login', '')
                self.server_admin_password = creds.get('password', '')
            elif comp == "Pilot-BIM-Server":
                creds = self.admin_credentials.get(comp, {})
                self.bim_admin_login = creds.get('login', '')
                self.bim_admin_password = creds.get('password', '')

        self.status_messages = []
        self.running = True
        self.buttons[0].enabled = False
        self.needs_redraw = True
        self._start_setup()

    def draw_instructions(self):
        pass

    def _get_output_height(self):
        return max(1, self.height - 8)

    def draw_content(self):
        title = " НАСТРОЙКА КОМПОНЕНТОВ PILOT "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 6
        max_lines = self._get_output_height()
        # Показываем последние max_lines сообщений
        visible_msgs = self.status_messages[-max_lines:] if self.status_messages else []
        for i, msg in enumerate(visible_msgs):
            y = start_y + i
            if y >= self.height - 4:
                break
            safe_addstr(self.stdscr, y, 4, msg[:self.width-8])

        # Инструкция
        if self.running:
            instr = "Выполняется настройка, пожалуйста, подождите..."
        else:
            instr = "Настройка завершена. Нажмите 'Далее' для продолжения."
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def _add_message(self, msg):
        self.status_messages.append(msg)
        self.needs_redraw = True

    def _run_docker_command(self, container, command, check=True):
        """Выполняет команду в контейнере через docker exec"""
        full_cmd = ["docker", "exec", "-i", container] + command
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0 and check:
                self._add_message(f"Ошибка: {result.stderr.strip()}")
                return False
            return True
        except subprocess.TimeoutExpired:
            self._add_message("Ошибка: команда не завершилась за 30 секунд")
            return False
        except Exception as e:
            self._add_message(f"Ошибка выполнения: {e}")
            return False

    def _restart_container(self, container):
        """Перезапускает контейнер"""
        try:
            subprocess.run(["docker", "restart", container], capture_output=True, timeout=30)
            return True
        except:
            return False

    def _setup(self):
        # 1. Добавление администратора Pilot-Server
        if self.server_admin_login and self.server_admin_password:
            self._add_message("Добавление администратора Pilot-Server...")
            container = f"{self.stack_name}_pilot-server"
            command = [
                "/App/Ascon.Pilot.Daemon", "--admin",
                "/usr/share/ascon/pilot-server/settings/settings.xml",
                self.server_admin_login,
                self.server_admin_password
            ]
            success = self._run_docker_command(container, command)
            if success:
                self._add_message(f"Добавлен администратор сервера {self.server_admin_login}")
            else:
                self._add_message("Не удалось добавить администратора Pilot-Server")
        else:
            self._add_message("Учётные данные администратора Pilot-Server не заданы")

        # 2. Перезапуск контейнера
        self._add_message("Перезапуск контейнера pilot-server...")
        if self._restart_container(f"{self.stack_name}_pilot-server"):
            self._add_message("Настройка применена")
        else:
            self._add_message("Не удалось перезапустить контейнер pilot-server")

        # 3. Подключение базы данных
        if self.db_path and self.fa_path and self.db_name:
            self._add_message("Подключение базы данных...")
            container = f"{self.stack_name}_pilot-server"
            command = [
                "/App/Ascon.Pilot.Daemon", "--attach",
                self.db_name,
                self.db_path,
                self.fa_path
            ]
            success = self._run_docker_command(container, command)
            if success:
                self._add_message(f"Подключена база данных {self.db_name}")
            else:
                self._add_message("Не удалось подключить базу данных")
        else:
            self._add_message("Не удалось определить параметры базы данных")

        # 4. Настройка Pilot-BIM-Server, если выбран
        if "Pilot-BIM-Server" in self.components:
            if self.bim_admin_login and self.bim_admin_password and self.db_name:
                self._add_message("Настройка Pilot-BIM-Server...")
                container = f"{self.stack_name}_pilot-bim-server"
                command = [
                    "/App/pBimAdmin", "-c",
                    f"http://pilot-server:5545/{self.db_name}",
                    self.bim_admin_login,
                    self.bim_admin_password
                ]
                success = self._run_docker_command(container, command)
                if success:
                    self._add_message(f"Подключение Pilot-BIM-Server произведено администратором {self.bim_admin_login}")
                else:
                    self._add_message("Не удалось настроить Pilot-BIM-Server")
            else:
                self._add_message("Недостаточно данных для настройки Pilot-BIM-Server")

        # Завершение
        self.running = False
        self.buttons[0].enabled = True
        self.needs_redraw = True

    def _start_setup(self):
        self.setup_thread = threading.Thread(target=self._setup, daemon=True)
        self.setup_thread.start()

    def handle_input(self):
        self.handle_resize()
        self.draw()

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            # Мышь пока не реализована
            pass
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:  # TAB
            if not self.running:
                self.focus_mode = (self.focus_mode + 1) % 2
                self.needs_redraw = True
        elif not self.running and self.focus_mode == 1:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def handle_action(self, action):
        if action == "continue":
            # Переход к следующему экрану (например, к экрану завершения)
            # Пока временно возвращаемся на db_option, позже заменим
            self.app.switch_screen("db_option")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Настройка компонентов"