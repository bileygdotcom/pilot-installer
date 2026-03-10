#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Экран приветствия
"""

import curses
from screens.base_screen import BaseScreen
from components.ui import Button  # Импортируем Button здесь
from utils.terminal import safe_addstr

class WelcomeScreen(BaseScreen):
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.buttons = [
            Button(0, "[ Продолжить ]", "continue"),
            Button(1, "[ Выйти ]", "exit")
        ]
    
    def draw_content(self):
        """Рисует содержимое экрана приветствия"""
        messages = [
            "Добро пожаловать в программу установки системы Pilot-BIM!",
            "",
            "Эта программа поможет вам установить Pilot-BIM",
            "с использованием Docker-контейнеров.",
            "",
            "Для навигации используйте клавиши TAB и стрелки,",
            "для выбора - ENTER или мышь."
        ]
        
        start_y = 5
        for i, msg in enumerate(messages):
            if start_y + i < self.height - 8:
                x = max(0, (self.width - len(msg)) // 2)
                safe_addstr(self.stdscr, start_y + i, x, msg)
    
    def on_continue(self):
        """Переход к экрану определения ОС"""
        return "next"  # Возвращаем next, а main обработает переключение
    
    def get_screen_name(self):
        return "Приветствие"