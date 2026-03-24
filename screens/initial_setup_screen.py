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

class InitialSetupScreen(BaseScreen):
    """
    Экран начальной настройки после запуска стека.
    Добавляет администратора Pilot-Server, перезапускает контейнер,
    подключает базу данных, настраивает Pilot-BIM-Server.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.stack_name = None
        self.stack_path = None
        self.admin_credentials = {}
        self.db_name = None
        self.db_path = None
        self.fa_path = None
        self.bim_required = False

        self.output_queue = queue.Queue()
        self.output_lines = []
        self.scroll_offset = 0
        self.setup_thread = None
        self.running = False
        self.setup_done = False

        self.buttons = [
            Button(0, "[ Далее ]", "continue", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - вывод, 1 - кнопки

    def on_enter(self):
        self.stack_name = getattr(self.app, 'stack_name', None)
        self.stack_path = getattr(self.app, 'stack_path', None)
        self.admin_credentials = getattr(self.app, 'admin_credentials', {})
        selected_components = getattr(self.app, 'selected_components', [])

        self.bim_required = 'Pilot-BIM-Server' in selected_components

        # Определяем пути к базе данных
        if hasattr(self.app, 'selected_demo_db') and self.app.selected_demo_db:
            # Демо-база
            self.db_name = self.app.selected_demo_db
            base_path = os.path.join(self.stack_path, "databases", "Databases", self.db_name)
            self.db_path = os.path.join(base_path, "base.dbp")
            fa_dir = os.path.join(base_path, "FileArchive")
            if os.path.exists(fa_dir):
                fa_files = [f for f in os.listdir(fa_dir) if f.endswith('.pilotfa')]
                if fa_files:
                    self.fa_path = os.path.join(fa_dir, fa_files[0])
                else:
                    self.fa_path = None
            else:
                self.fa_path = None
        elif hasattr(self.app, 'existing_db_path') and self.app.existing_db_path:
            # Существующая база
            self.db_path = self.app.existing_db_path
            self.fa_path = self.app.existing_fa_path
            self.db_name = os.path.basename(os.path.dirname(self.db_path))
        else:
            self.db_name = None

        self.output_lines = []
        self.scroll_offset = 0
        self.setup_done = False
        self.running = True
        self.buttons[0].enabled = False
        self.needs_redraw = True

        self.setup_thread = threading.Thread(target=self._run_setup, daemon=True)
        self.setup_thread.start()

    def draw_instructions(self):
        pass

    def _get_output_height(self):
        return max(1, self.height - 9)

    def draw_content(self):
        title = " НАЧАЛЬНАЯ НАСТРОЙКА "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 6
        out_height = self._get_output_height()
        end_idx = min(len(self.output_lines), self.scroll_offset + out_height)

        for i in range(self.scroll_offset, end_idx):
            y = start_y + (i - self.scroll_offset)
            if y >= self.height - 6:
                break
            line = self.output_lines[i]
            if len(line) > self.width - 8:
                line = line[:self.width-11] + "..."
            safe_addstr(self.stdscr, y, 4, line)

        if self.scroll_offset > 0:
            safe_addstr(self.stdscr, start_y - 1, 4, "↑ ...")
        if end_idx < len(self.output_lines):
            safe_addstr(self.stdscr, start_y + out_height, 4, "↓ ...")

        if self.setup_done:
            instr = "Настройка завершена. Нажмите 'Далее' для продолжения."
            x = max(0, (self.width - len(instr)) // 2)
            safe_addstr(self.stdscr, self.height - 5, x, instr, curses.color_pair(6))

        instr = "TAB: переключение на кнопки" if self.focus_mode == 0 else "TAB: переключение на вывод | Enter: выбор кнопки"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def _run_setup(self):
        self._add_admin()
        self._restart_container()
        self._attach_database()
        if self.bim_required:
            self._setup_bim()
        self.output_queue.put("\n✓ Настройка завершена.")
        self.setup_done = True
        self.buttons[0].enabled = True
        self.needs_redraw = True
        self.running = False

    def _add_admin(self):
        container = f"{self.stack_name}_pilot-server"
        creds = self.admin_credentials.get('Pilot-Server', {})
        login = creds.get('login', '')
        password = creds.get('password', '')
        if not login or not password:
            self.output_queue.put("→ Учётные данные администратора Pilot-Server не заданы.")
            return
        command = [
            "/App/Ascon.Pilot.Daemon", "--admin",
            "/usr/share/ascon/pilot-server/settings/settings.xml",
            login, password
        ]
        full_cmd = ["docker", "exec", container] + command
        self.output_queue.put(f"→ Добавление администратора {login}...")
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.output_queue.put(f"✓ Администратор {login} добавлен.")
            else:
                self.output_queue.put(f"✗ Ошибка добавления: {result.stderr.strip()}")
        except Exception as e:
            self.output_queue.put(f"✗ Исключение: {e}")

    def _restart_container(self):
        container = f"{self.stack_name}_pilot-server"
        self.output_queue.put("→ Перезапуск контейнера pilot-server...")
        try:
            subprocess.run(["docker", "restart", container], capture_output=True, text=True, timeout=30)
            self.output_queue.put("✓ Контейнер перезапущен.")
        except Exception as e:
            self.output_queue.put(f"✗ Ошибка перезапуска: {e}")

    def _attach_database(self):
        if not self.db_path or not self.fa_path:
            self.output_queue.put("→ Не указаны пути к файлам базы данных.")
            return

        container = f"{self.stack_name}_pilot-server"
        # Преобразуем хостовые пути в пути внутри контейнера
        # Базы данных монтируются в /usr/share/ascon/databases
        databases_host = os.path.join(self.stack_path, "databases")
        rel_db = os.path.relpath(self.db_path, databases_host)
        rel_fa = os.path.relpath(self.fa_path, databases_host)
        container_db = os.path.join("/usr/share/ascon/databases", rel_db)
        container_fa = os.path.join("/usr/share/ascon/databases", rel_fa)

        command = [
            "/App/Ascon.Pilot.Daemon", "--attach",
            self.db_name,
            container_db,
            container_fa
        ]
        full_cmd = ["docker", "exec", container] + command
        self.output_queue.put(f"→ Подключение базы данных {self.db_name}...")
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                self.output_queue.put(f"✓ База данных {self.db_name} подключена.")
            else:
                self.output_queue.put(f"✗ Ошибка подключения: {result.stderr.strip()}")
        except Exception as e:
            self.output_queue.put(f"✗ Исключение: {e}")

    def _setup_bim(self):
        container = f"{self.stack_name}_pilot-bim-server"
        creds = self.admin_credentials.get('Pilot-BIM-Server', {})
        login = creds.get('login', '')
        password = creds.get('password', '')
        if not login or not password:
            self.output_queue.put("→ Недостаточно данных для настройки Pilot-BIM-Server.")
            return
        command = [
            "/pBimAdmin", "-c",
            f"http://pilot-server:5545/{self.db_name}",
            login, password
        ]
        full_cmd = ["docker", "exec", container] + command
        self.output_queue.put(f"→ Настройка Pilot-BIM-Server (администратор {login})...")
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.output_queue.put(f"✓ Pilot-BIM-Server настроен (администратор {login}).")
            else:
                self.output_queue.put(f"✗ Ошибка настройки BIM: {result.stderr.strip()}")
        except Exception as e:
            self.output_queue.put(f"✗ Исключение: {e}")

    def handle_input(self):
        self.handle_resize()
        self.draw()

        # Обновляем вывод из очереди
        try:
            while True:
                line = self.output_queue.get_nowait()
                self.output_lines.append(line)
                if len(self.output_lines) > 500:
                    self.output_lines.pop(0)
                if self.scroll_offset + self._get_output_height() >= len(self.output_lines) - 1:
                    self.scroll_offset = max(0, len(self.output_lines) - self._get_output_height())
                self.needs_redraw = True
        except queue.Empty:
            pass

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            # Мышь пока не реализована
            pass
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:  # TAB
            self.focus_mode = (self.focus_mode + 1) % 2
            self.needs_redraw = True
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            if self.focus_mode == 0:
                if key == curses.KEY_UP and self.scroll_offset > 0:
                    self.scroll_offset -= 1
                    self.needs_redraw = True
                elif key == curses.KEY_DOWN and self.scroll_offset + self._get_output_height() < len(self.output_lines):
                    self.scroll_offset += 1
                    self.needs_redraw = True
        elif self.focus_mode == 1:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        return None

    def handle_action(self, action):
        if action == "continue":
            # Переход к следующему экрану (например, завершение)
            return "exit"
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Начальная настройка"