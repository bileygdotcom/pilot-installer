#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class DbConfirmScreen(BaseScreen):
    """
    Экран подтверждения выбранных файлов базы данных и архива.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.db_path = None
        self.fa_path = None
        self.buttons = [
            Button(0, "[ OK ]", "confirm_ok", enabled=True),
            Button(1, "[ Назад ]", "confirm_back", enabled=True)
        ]
        self.current_button = 0

    def on_enter(self):
        self.db_path = getattr(self.app, 'temp_db_path', None)
        self.fa_path = getattr(self.app, 'temp_fa_path', None)
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def draw_content(self):
        title = " ПОДТВЕРЖДЕНИЕ ВЫБОРА "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 7
        safe_addstr(self.stdscr, start_y, 4, "Файл базы данных:", curses.A_BOLD)
        start_y += 1
        db_display = self.db_path if self.db_path else "(не выбран)"
        if len(db_display) > self.width - 10:
            db_display = "..." + db_display[-(self.width-13):]
        safe_addstr(self.stdscr, start_y, 6, db_display)
        start_y += 2

        safe_addstr(self.stdscr, start_y, 4, "Файл файлового архива:", curses.A_BOLD)
        start_y += 1
        fa_display = self.fa_path if self.fa_path else "(не выбран)"
        if len(fa_display) > self.width - 10:
            fa_display = "..." + fa_display[-(self.width-13):]
        safe_addstr(self.stdscr, start_y, 6, fa_display)

        instr = "Выберите действие:"
        x = max(0, (self.width - len(instr)) // 2)
        safe_addstr(self.stdscr, self.height - 3, x, instr, curses.color_pair(4))

    def handle_action(self, action):
        if action == "confirm_ok":
            # Копируем файлы в папку стека
            stack_path = self.app.stack_path
            dest_db = os.path.join(stack_path, "databases", os.path.basename(self.db_path))
            dest_fa = os.path.join(stack_path, "databases", os.path.basename(self.fa_path))
            try:
                import shutil
                shutil.copy2(self.db_path, dest_db)
                shutil.copy2(self.fa_path, dest_fa)
                self.app.existing_db_path = dest_db
                self.app.existing_fa_path = dest_fa
            except Exception as e:
                # Здесь можно вывести сообщение об ошибке
                self.app.switch_screen("db_existing")
                return None
            # Переходим к созданию администраторов
            self.app.switch_screen("admin_creation")
            return None
        elif action == "confirm_back":
            # Возвращаемся к выбору базы данных
            self.app.switch_screen("db_existing")
            return None
        return None

    def get_screen_name(self):
        return "Подтверждение базы"