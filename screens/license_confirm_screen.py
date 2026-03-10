#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import shutil
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class LicenseConfirmScreen(BaseScreen):
    """
    Экран подтверждения установки лицензии.
    Копирует выбранный файл в /usr/share/ASCON/Pilot Server/License.
    Предполагается запуск с правами root.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.license_path = None
        self.dest_dir = "/usr/share/ASCON/Pilot Server/License"
        self.dest_file = None
        self.status = "Ожидание..."
        self.error_message = None
        self.copy_success = False
        self.buttons = [
            Button(0, "[ Далее ]", "continue", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.operation_done = False

    def perform_copy(self):
        """Выполняет копирование файла лицензии"""
        self.license_path = getattr(self.app, 'license_file_path', None)
        if not self.license_path:
            self.status = "Ошибка: файл не выбран"
            self.error_message = "Вернитесь назад и выберите файл лицензии"
            self.operation_done = True
            self.needs_redraw = True
            return

        if not os.path.exists(self.license_path):
            self.status = "Ошибка: файл не существует"
            self.error_message = f"Файл {self.license_path} не найден"
            self.operation_done = True
            self.needs_redraw = True
            return

        try:
            # 1. Создаём целевую папку, если не существует
            self.status = "Проверка папки назначения..."
            self.needs_redraw = True
            os.makedirs(self.dest_dir, exist_ok=True)

            # 2. Копируем файл
            filename = os.path.basename(self.license_path)
            self.dest_file = os.path.join(self.dest_dir, filename)
            self.status = "Копирование файла..."
            self.needs_redraw = True
            shutil.copy2(self.license_path, self.dest_file)

            # Успех
            self.status = "✓ Лицензия успешно установлена"
            self.copy_success = True
            self.buttons[0].enabled = True
            self.error_message = None

        except PermissionError:
            self.status = "Ошибка прав доступа"
            self.error_message = "Запустите программу с правами root (sudo)"
        except Exception as e:
            self.status = "Ошибка копирования"
            self.error_message = str(e)

        self.operation_done = True
        self.needs_redraw = True

    def draw_content(self):
        """Отрисовывает содержимое экрана"""
        # Заголовок
        title = " УСТАНОВКА ЛИЦЕНЗИИ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 7
        line = 0

        # Информация о файле
        if self.license_path:
            safe_addstr(self.stdscr, start_y + line, 10, "Выбранный файл:", curses.A_BOLD)
            line += 1
            path_display = self.license_path
            if len(path_display) > self.width - 14:
                path_display = "..." + path_display[-(self.width-17):]
            safe_addstr(self.stdscr, start_y + line, 12, path_display)
            line += 2

        # Статус
        safe_addstr(self.stdscr, start_y + line, 10, "Статус:", curses.A_BOLD)
        status_color = curses.color_pair(6) if self.copy_success else curses.color_pair(5)
        safe_addstr(self.stdscr, start_y + line, 20, self.status, status_color)
        line += 2

        # Сообщение об ошибке
        if self.error_message:
            safe_addstr(self.stdscr, start_y + line, 10, self.error_message, curses.color_pair(5))
            line += 2

        # Путь назначения при успехе
        if self.copy_success and self.dest_file:
            safe_addstr(self.stdscr, start_y + line, 10, "Скопирован в:", curses.A_BOLD)
            line += 1
            dest_display = self.dest_file
            if len(dest_display) > self.width - 14:
                dest_display = "..." + dest_display[-(self.width-17):]
            safe_addstr(self.stdscr, start_y + line, 12, dest_display)

    def handle_input(self):
        # При первом входе выполняем копирование
        if not self.operation_done:
            self.perform_copy()
        return super().handle_input()

    def handle_action(self, action):
        if action == "continue":
            # Переход к следующему шагу (замените на нужный экран)
            self.app.switch_screen("docker_check")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Установка лицензии"