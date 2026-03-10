#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import time
import threading
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DockerInstallScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.progress = 0
        self.status_message = "Подготовка к установке..."
        self.installation_complete = False
        self.installation_success = False
        self.install_thread = None
        self.buttons = []  # На время установки кнопок нет
        
        # Запускаем установку в фоне
        self.start_installation()
    
    def start_installation(self):
        def install():
            steps = [
                "Обновление репозиториев...",
                "Установка Docker...",
                "Настройка Docker...",
                "Установка Docker Compose...",
                "Завершение установки..."
            ]
            for i, step in enumerate(steps):
                self.status_message = step
                self.progress = int((i + 1) * 100 / len(steps))
                self.needs_redraw = True
                time.sleep(2)  # Имитация работы
            self.installation_complete = True
            self.installation_success = True
            self.status_message = "Установка завершена успешно!"
            # После завершения показываем кнопку "Далее"
            self.buttons = [Button(0, "[ Далее ]", "continue")]
            self.needs_redraw = True
        
        self.install_thread = threading.Thread(target=install, daemon=True)
        self.install_thread.start()
    
    def draw_content(self):
        title = " УСТАНОВКА DOCKER "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)
        
        start_y = 7
        
        # Статус сообщение
        safe_addstr(self.stdscr, start_y, 10, self.status_message)
        
        # Прогресс-бар
        bar_width = min(50, self.width - 20)
        if bar_width > 0:
            filled = int(bar_width * self.progress / 100)
            bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
            percent = f" {self.progress}%"
            y = start_y + 2
            x_bar = max(0, (self.width - len(bar)) // 2)
            safe_addstr(self.stdscr, y, x_bar, bar + percent)
        
        # Если завершено и успешно
        if self.installation_complete and self.installation_success:
            y = start_y + 5
            msg = "✓ Docker и Docker Compose успешно установлены!"
            x = max(0, (self.width - len(msg)) // 2)
            safe_addstr(self.stdscr, y, x, msg, curses.color_pair(6) | curses.A_BOLD)
    
    def on_continue(self):
        # Возвращаемся на экран проверки Docker
        return "next"
    
    def get_screen_name(self):
        return "Установка Docker"