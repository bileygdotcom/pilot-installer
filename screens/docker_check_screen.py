#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import shutil
import subprocess
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DockerCheckScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.docker_installed = False
        self.compose_installed = False
        self.need_install = False  # Флаг для main
        self.check_docker()
        self.update_buttons()
    
    def check_docker(self):
        """Проверяет наличие docker и docker-compose"""
        self.docker_installed = shutil.which("docker") is not None
        # Проверяем docker-compose (отдельно или как плагин)
        self.compose_installed = (shutil.which("docker-compose") is not None or
                                  self._check_compose_plugin())
    
    def _check_compose_plugin(self):
        try:
            result = subprocess.run(["docker", "compose", "version"],
                                   capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def update_buttons(self):
        """Обновляет кнопки в зависимости от статуса"""
        if self.docker_installed and self.compose_installed:
            self.buttons = [
                Button(0, "[ Далее ]", "continue"),
                Button(1, "[ Выход ]", "exit")
            ]
            self.need_install = False
        else:
            self.buttons = [
                Button(0, "[ Установить ]", "install"),
                Button(1, "[ Выход ]", "exit")
            ]
            self.need_install = True
    
    def draw_content(self):
        title = " ПРОВЕРКА DOCKER "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)
        
        start_y = 7
        line = 0
        
        # Docker
        docker_label = "Docker:"
        safe_addstr(self.stdscr, start_y + line, 10, docker_label, curses.A_BOLD)
        if self.docker_installed:
            status = "✓ Установлен"
            color = curses.color_pair(6)
        else:
            status = "✗ Не установлен"
            color = curses.color_pair(5)
        safe_addstr(self.stdscr, start_y + line, 28, status, color)
        line += 2
        
        # Docker Compose
        compose_label = "Docker Compose:"
        safe_addstr(self.stdscr, start_y + line, 10, compose_label, curses.A_BOLD)
        if self.compose_installed:
            status = "✓ Установлен"
            color = curses.color_pair(6)
        else:
            status = "✗ Не установлен"
            color = curses.color_pair(5)
        safe_addstr(self.stdscr, start_y + line, 28, status, color)
        line += 3
        
        # Информационное сообщение
        if not (self.docker_installed and self.compose_installed):
            msg = "Для работы Pilot-BIM необходимы Docker и Docker Compose."
            x = max(0, (self.width - len(msg)) // 2)
            safe_addstr(self.stdscr, start_y + line, x, msg)
            line += 1
            msg2 = "Нажмите 'Установить' для автоматической установки."
            x = max(0, (self.width - len(msg2)) // 2)
            safe_addstr(self.stdscr, start_y + line, x, msg2)
    
    def on_continue(self):
        # Если всё установлено, переходим дальше (пока заглушка)
        return "next"
    
    def get_screen_name(self):
        return "Проверка Docker"