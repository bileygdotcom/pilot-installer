#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import re
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class ImageTagScreen(BaseScreen):
    """
    Экран выбора тега (версии) Docker-образов Pilot.
    Позволяет выбрать latest, release или ввести свой тег.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.options = ["latest", "release", "custom"]
        self.selected_option = 0          # 0 - latest, 1 - release, 2 - custom
        self.custom_tag = ""
        self.editing_custom = False
        self.validation_error = False
        self.focus_mode = 0                # 0 - список, 1 - кнопки
        self.scroll_offset = 0

        # Для мыши
        self._last_click_time = 0
        self._last_click_index = -1

        self.buttons = [
            Button(0, "[ Далее ]", "next", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0

        # Позиция поля ввода для custom
        self.input_y = 0
        self.input_x = 0

    def on_enter(self):
        """Сброс при входе"""
        self.selected_option = 0
        self.custom_tag = ""
        self.editing_custom = False
        self.validation_error = False
        self.focus_mode = 0
        self._update_next_button()
        self.needs_redraw = True

    def _update_next_button(self):
        """Активирует кнопку 'Далее' в зависимости от выбора"""
        if self.selected_option == 2:
            # custom: нужно непустое и валидное значение
            self.buttons[0].enabled = bool(self.custom_tag and self._validate_tag(self.custom_tag))
        else:
            # latest или release — всегда можно
            self.buttons[0].enabled = True

    def _validate_tag(self, tag):
        """Проверяет, что тег состоит из допустимых символов (буквы, цифры, точка, дефис, подчёркивание, слеш)"""
        # Docker tag может содержать буквы, цифры, точки, дефисы, подчёркивания, слэши (для организации)
        return re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$', tag) is not None

    def draw_instructions(self):
        pass

    def _get_list_height(self):
        return max(1, self.height - 10)

    def _adjust_scroll(self):
        # Для трёх опций прокрутка не нужна, но оставим на будущее
        pass

    def draw_content(self):
        title = " ВЫБОР ВЕРСИИ ОБРАЗОВ "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        start_y = 7

        # Радио-кнопки для выбора опции
        for i, opt in enumerate(self.options):
            y = start_y + i * 2
            if y >= self.height - 6:
                break
            radio = "(*)" if i == self.selected_option else "( )"
            attr = curses.A_REVERSE if (i == self.selected_option and self.focus_mode == 0) else 0
            line = f"{radio} {opt.capitalize()}"
            safe_addstr(self.stdscr, y, 4, line, attr)

        # Если выбран custom, показываем поле ввода
        if self.selected_option == 2:
            custom_y = start_y + 2 * 2 + 2  # после двух пустых строк
            safe_addstr(self.stdscr, custom_y, 5, "Введите тег:", curses.A_BOLD)
            field_x = 6 + len("Введите тег:") + 1
            field_y = custom_y
            self.input_x = field_x
            self.input_y = field_y
            field_width = 30

            # Цвет фона для поля
            if self.validation_error:
                color = curses.color_pair(5) | curses.A_REVERSE
            elif self.focus_mode == 0 and self.editing_custom:
                color = curses.A_REVERSE
            else:
                color = curses.A_NORMAL

            # Очищаем область поля
            for i in range(field_width):
                safe_addstr(self.stdscr, field_y, field_x + i, " ", color)

            # Выводим текущий тег
            display_tag = self.custom_tag.ljust(field_width)
            safe_addstr(self.stdscr, field_y, field_x, display_tag, color)

            # Курсор, если редактируем
            if self.editing_custom:
                curses.curs_set(1)
                self.stdscr.move(field_y, field_x + len(self.custom_tag))
            else:
                curses.curs_set(0)

            # Сообщение об ошибке
            if self.validation_error:
                err_msg = "Недопустимые символы! Используйте a-z, 0-9, . _ -"
                x = max(0, (self.width - len(err_msg)) // 2)
                safe_addstr(self.stdscr, custom_y + 2, x, err_msg, curses.color_pair(5))
        else:
            curses.curs_set(0)

        # Инструкция
        instr = "↑↓: выбор | Enter: выбрать/редактировать | TAB: переключение на кнопки"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def handle_mouse(self):
        """Обработка мыши: клики по радио-кнопкам, полю ввода и кнопкам"""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            current_time = time.time()

            # Кнопки
            button_positions = self.get_button_positions()
            for i, pos in enumerate(button_positions):
                if my == pos['y'] and pos['x1'] <= mx <= pos['x2']:
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        if self.buttons[i].enabled:
                            self.current_button = i
                            self.focus_mode = 1
                            self.needs_redraw = True
                            return self.buttons[i].action
                    return None

            # Радио-кнопки
            start_y = 7
            for i in range(len(self.options)):
                y = start_y + i * 2
                if y >= self.height - 6:
                    break
                # Проверяем клик в пределах строки
                if my == y and 4 <= mx <= 4 + len(self.options[i]) + 4:
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        self.selected_option = i
                        self.focus_mode = 0
                        if i != 2:
                            self.editing_custom = False
                        self._update_next_button()
                        self.needs_redraw = True
                    return None

            # Если выбран custom, проверяем клик по полю ввода
            if self.selected_option == 2:
                field_x = self.input_x
                field_y = self.input_y
                field_width = 30
                if my == field_y and field_x <= mx < field_x + field_width:
                    if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                        self.focus_mode = 0
                        self.editing_custom = True
                        self.needs_redraw = True
                    return None
        except:
            pass
        return None

    def handle_input(self):
        self.handle_resize()
        self.draw()

        key = self.stdscr.getch()

        if key == curses.KEY_MOUSE:
            result = self.handle_mouse()
            if result:
                return self.handle_action(result)
        elif key == curses.KEY_RESIZE:
            self.handle_resize()
            self.needs_redraw = True
        elif key == 9:  # TAB
            if self.editing_custom:
                # Завершаем редактирование, но оставляем фокус на поле
                self.editing_custom = False
                self.needs_redraw = True
            else:
                self.focus_mode = (self.focus_mode + 1) % 2
                self.needs_redraw = True
        elif key == 27:  # ESC
            return "exit"
        else:
            if self.focus_mode == 0:
                self._handle_list_keys(key)
            else:
                result = self.handle_keyboard(key)
                if result:
                    return self.handle_action(result)
        return None

    def _handle_list_keys(self, key):
        if key == curses.KEY_UP:
            if self.selected_option > 0:
                self.selected_option -= 1
                if self.selected_option != 2:
                    self.editing_custom = False
                self._update_next_button()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.selected_option < len(self.options) - 1:
                self.selected_option += 1
                if self.selected_option != 2:
                    self.editing_custom = False
                self._update_next_button()
                self.needs_redraw = True
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            if self.selected_option == 2:
                # Переключаем режим редактирования custom
                self.editing_custom = not self.editing_custom
                self.needs_redraw = True
            else:
                # Для latest/release просто подтверждаем и переходим? Нет, переход только по кнопке.
                pass

        # Если в режиме редактирования custom, обрабатываем ввод символов
        if self.editing_custom:
            self._handle_custom_input(key)

    def _handle_custom_input(self, key):
        if key == 127 or key == curses.KEY_BACKSPACE or key == 8:
            if self.custom_tag:
                self.custom_tag = self.custom_tag[:-1]
                self.validation_error = False
                self._update_next_button()
                self.needs_redraw = True
        elif 32 <= key <= 126:
            char = chr(key)
            if len(self.custom_tag) < 128:  # Docker tag может быть до 128 символов
                new_tag = self.custom_tag + char
                if self._validate_tag(new_tag):
                    self.custom_tag = new_tag
                    self.validation_error = False
                else:
                    self.validation_error = True
                self._update_next_button()
                self.needs_redraw = True

    def handle_action(self, action):
        if action == "next":
            # Сохраняем выбранный тег
            if self.selected_option == 2:
                self.app.image_tag = self.custom_tag
            else:
                self.app.image_tag = self.options[self.selected_option]
            # Переход на выбор папки
            self.app.switch_screen("compose_created")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Выбор версии"