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
    Экран начальной настройки Pilot:
    - Добавление администратора Pilot-Server
    - Перезапуск контейнера pilot-server
    - Подключение базы данных
    - Настройка Pilot-BIM-Server (если выбран)
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.stack_name = None
        self.stack_path = None
        self.admin_credentials = None
        self.selected_components = []
        self.db_path = None
        self.fa_path = None
        self.db_name = None

        self.log_lines = []
        self.scroll_offset = 0
        self.running = False
        self.setup_thread = None
        self.status = "Готов к настройке"

        self.buttons = [
            Button(0, "[ Далее ]", "continue", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - логи, 1 - кнопки

    def on_enter(self):
        self.stack_name = getattr(self.app, 'stack_name', None)
        self.stack_path = getattr(self.app, 'stack_path', None)
        self.admin_credentials = getattr(self.app, 'admin_credentials', {})
        self.selected_components = getattr(self.app, 'selected_components', [])
        self.db_path = getattr(self.app, 'existing_db_path', None)
        self.fa_path = getattr(self.app, 'existing_fa_path', None)
        self.db_name = getattr(self.app, 'selected_demo_db', None)

        # Если пути к базе не заданы, но есть имя демо-базы, формируем их
        if not self.db_path and self.db_name:
            self.db_path = os.path.join(self.stack_path, "databases", "Databases", self.db_name, f"{self.db_name}.dbp")
            self.fa_path = os.path.join(self.stack_path, "databases", "Databases", self.db_name, "FileArchive", f"{self.db_name}.pilotfa")
            if not os.path.exists(self.db_path):
                self.db_path = None
            if not os.path.exists(self.fa_path):
                self.fa_path = None

        self.log_lines = []
        self.scroll_offset = 0
        self.status = "Настройка..."
        self.buttons[0].enabled = False
        self.needs_redraw = True
        self._start_setup()

    def _add_log(self, msg):
        self.log_lines.append(msg)
        if len(self.log_lines) > 1000:
            self.log_lines.pop(0)
        # Автопрокрутка вниз
        self.scroll_offset = max(0, len(self.log_lines) - self._get_log_height())
        self.needs_redraw = True

    def _get_log_height(self):
        return max(1, self.height - 12)

    def _run_command(self, cmd):
        """Запускает команду, возвращает (stdout, stderr, returncode)"""
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return proc.stdout, proc.stderr, proc.returncode
        except Exception as e:
            return "", str(e), -1

    def _setup(self):
        self.running = True
        self._add_log("Начинаем настройку...")

        # 1. Добавление администратора Pilot-Server
        pilot_server_creds = self.admin_credentials.get("Pilot-Server")
        if not pilot_server_creds or not pilot_server_creds["login"] or not pilot_server_creds["password"]:
            self._add_log("Ошибка: учётные данные администратора Pilot-Server не заданы")
            self.running = False
            self.status = "Ошибка"
            self.buttons[0].enabled = False
            self.needs_redraw = True
            return

        container = f"{self.stack_name}_pilot-server"
        cmd = ["docker", "exec", container, "/App/Ascon.Pilot.Daemon", "--admin",
               "/usr/share/ascon/pilot-server/settings/settings.xml",
               pilot_server_creds["login"], pilot_server_creds["password"]]
        self._add_log(f"Добавление администратора Pilot-Server: {pilot_server_creds['login']}")
        stdout, stderr, rc = self._run_command(cmd)
        if rc != 0:
            self._add_log(f"Ошибка добавления администратора: {stderr}")
            self.running = False
            self.status = "Ошибка"
            self.buttons[0].enabled = False
            self.needs_redraw = True
            return
        self._add_log("Добавлен администратор сервера")

        # 2. Перезапуск контейнера pilot-server
        self._add_log("Перезапуск контейнера pilot-server...")
        cmd = ["docker", "restart", container]
        stdout, stderr, rc = self._run_command(cmd)
        if rc != 0:
            self._add_log(f"Ошибка перезапуска: {stderr}")
            self.running = False
            self.status = "Ошибка"
            self.buttons[0].enabled = False
            self.needs_redraw = True
            return
        self._add_log("Контейнер перезапущен")

        # 3. Подключение базы данных
        if self.db_path and self.fa_path:
            # Имя базы – из имени файла .dbp без расширения
            db_base = os.path.splitext(os.path.basename(self.db_path))[0]
            cmd = ["docker", "exec", container, "/App/Ascon.Pilot.Daemon", "--attach",
                   db_base, self.db_path, self.fa_path]
            self._add_log(f"Подключение базы данных {db_base}...")
            stdout, stderr, rc = self._run_command(cmd)
            if rc != 0:
                self._add_log(f"Ошибка подключения базы: {stderr}")
                # Не прерываем настройку, но отметим ошибку
            else:
                self._add_log(f"Подключена база данных {db_base}")
        else:
            self._add_log("Не указаны пути к базе данных, подключение пропущено")

        # 4. Настройка Pilot-BIM-Server (если выбран)
        if "Pilot-BIM-Server" in self.selected_components:
            bim_creds = self.admin_credentials.get("Pilot-BIM-Server")
            if not bim_creds or not bim_creds["login"] or not bim_creds["password"]:
                self._add_log("Недостаточно данных для настройки Pilot-BIM-Server")
            else:
                db_name = self.db_name or (os.path.splitext(os.path.basename(self.db_path))[0] if self.db_path else "pilot-bim_ru")
                # Сначала получим ID базы данных? Для простоты используем имя.
                # Команда: /pBimAdmin -c http://pilot-server:5545/имя_базы логин пароль
                bim_container = f"{self.stack_name}_pilot-bim-server"
                cmd = ["docker", "exec", bim_container, "/pBimAdmin",
                       "-c", f"http://pilot-server:5545/{db_name}",
                       bim_creds["login"], bim_creds["password"]]
                self._add_log(f"Настройка Pilot-BIM-Server администратором {bim_creds['login']}...")
                stdout, stderr, rc = self._run_command(cmd)
                if rc != 0:
                    self._add_log(f"Ошибка настройки Pilot-BIM-Server: {stderr}")
                else:
                    self._add_log(f"Подключение Pilot-BIM-Server произведено администратором {bim_creds['login']}")

        self._add_log("Настройка завершена")
        self.status = "Настройка завершена"
        self.buttons[0].enabled = True
        self.running = False
        self.needs_redraw = True

    def _start_setup(self):
        if not self.running:
            self.setup_thread = threading.Thread(target=self._setup, daemon=True)
            self.setup_thread.start()

    def draw_instructions(self):
        pass

    def _get_log_height(self):
        return max(1, self.height - 12)

    def draw_content(self):
        title = " НАСТРОЙКА КОМПОНЕНТОВ PILOT "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        safe_addstr(self.stdscr, 6, 4, f"Статус: {self.status}", curses.A_BOLD)

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

        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, log_start_y - 1, 4, "↑ ...")
        if end_idx < len(self.log_lines):
            safe_addstr(self.stdscr, log_start_y + log_height, 4, "↓ ...")

        instr = "↑↓: прокрутка логов | TAB: переключение на кнопки"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def handle_mouse(self):
        # Мышь пока не реализована для этого экрана
        pass

    def handle_input(self):
        self.handle_resize()
        self.draw()

        if self.running:
            self.stdscr.timeout(100)
        else:
            self.stdscr.timeout(-1)

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
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            if self.focus_mode == 0:
                if key == curses.KEY_UP and self.scroll_offset > 0:
                    self.scroll_offset -= 1
                    self.needs_redraw = True
                elif key == curses.KEY_DOWN and self.scroll_offset + self._get_log_height() < len(self.log_lines):
                    self.scroll_offset += 1
                    self.needs_redraw = True
        elif self.focus_mode == 1 and not self.running:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def handle_action(self, action):
        if action == "continue":
            # Переход к следующему экрану (например, финальному)
            self.app.switch_screen("stack_start")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Настройка"