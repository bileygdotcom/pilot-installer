#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
from screens.base_screen import BaseScreen
from components.os_detector import get_os_info
from components.ui import Button
from utils.terminal import safe_addstr

class OSDectionScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.os_info = get_os_info()
        self.buttons = [
            Button(0, "[ Продолжить ]", "continue"),
            Button(1, "[ Выйти ]", "exit")
        ]
    
    def draw_content(self):
        title = " ОПРЕДЕЛЕНИЕ ОПЕРАЦИОННОЙ СИСТЕМЫ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)
        
        start_y = 7
        line = 0
        info_lines = [
            ("Система: ", self.os_info.system),
            ("Версия ядра: ", self.os_info.release),
            ("Архитектура: ", self.os_info.machine),
        ]
        if self.os_info.system == 'Linux':
            if self.os_info.distro:
                info_lines.append(("Дистрибутив: ", self.os_info.distro))
            if self.os_info.distro_version:
                info_lines.append(("Версия: ", self.os_info.distro_version))
            if self.os_info.distro_codename:
                info_lines.append(("Кодовое имя: ", self.os_info.distro_codename))
        
        for label, value in info_lines:
            if start_y + line < self.height - 10:
                safe_addstr(self.stdscr, start_y + line, 10, label, curses.A_BOLD)
                safe_addstr(self.stdscr, start_y + line, 28, str(value))
                line += 1
        line += 1
        
        docker_title = "Поддержка Docker: "
        safe_addstr(self.stdscr, start_y + line, 10, docker_title, curses.A_BOLD)
        docker_status = "✓ Поддерживается" if self.os_info.docker_supported else "✗ Требуется ручная установка"
        docker_color = curses.color_pair(6) if self.os_info.docker_supported else curses.color_pair(5)
        safe_addstr(self.stdscr, start_y + line, 28, docker_status, docker_color)
        line += 1
        
        compose_title = "Docker Compose: "
        safe_addstr(self.stdscr, start_y + line, 10, compose_title, curses.A_BOLD)
        if self.os_info.docker_compose_supported:
            compose_status = "✓ Поддерживается"
            compose_color = curses.color_pair(6)
        else:
            compose_status = "⚠ Требуется доп. установка"
            compose_color = curses.color_pair(5)
        safe_addstr(self.stdscr, start_y + line, 28, compose_status, compose_color)
        line += 2
        
        if self.os_info.install_method:
            method_title = "Метод установки: "
            method_map = {
                'apt': 'APT (Debian/Ubuntu)',
                'yum': 'YUM (RHEL/CentOS 7)',
                'dnf': 'DNF (Fedora/RHEL 8+)',
                'zypper': 'Zypper (openSUSE)',
                'pacman': 'Pacman (Arch Linux)',
                'apk': 'APK (Alpine Linux)',
                'manual': 'Ручная установка'
            }
            method_text = method_map.get(self.os_info.install_method, self.os_info.install_method)
            safe_addstr(self.stdscr, start_y + line, 10, method_title, curses.A_BOLD)
            safe_addstr(self.stdscr, start_y + line, 28, method_text)
            line += 2
        
        if not self.os_info.docker_supported:
            warn_msg = "⚠ Внимание: Автоматическая установка Docker может не поддерживаться"
            x = max(0, (self.width - len(warn_msg)) // 2)
            safe_addstr(self.stdscr, start_y + line, x, warn_msg, curses.color_pair(5) | curses.A_BOLD)
    
    def on_continue(self):
        return "next"
    
    def get_screen_name(self):
        return "Определение ОС"