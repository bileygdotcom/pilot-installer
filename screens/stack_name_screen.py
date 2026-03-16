#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import re
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class StackNameScreen(BaseScreen):
    """
    Экран задания имени стека компонентов Pilot.
    Имя должно содержать только латинские буквы, цифры и дефис, максимум 8 символов.
    """
    def __init__(self, stdscr, app):
        super().__init__(stdscr, app)
        self.stack_name = ""
        self.editing = False
        self.input_y = 0
        self.input_x = 0
        self.validation_error = False

        self.buttons = [
            Button(0, "[ Задать ]", "set", enabled=False),
            Button(1, "[ Выход ]", "exit", enabled=True)
        ]
        self.current_button = 0
        self.focus_mode = 0  # 0 - поле ввода, 1 - кнопки

    def on_enter(self):
        """Сбрасываем поле при входе на экран"""
        self.stack_name = ""
        self.editing = False
        self.validation_error = False
        self.focus_mode = 0
        self.buttons[0].enabled = False
        self.needs_redraw = True

    def draw_instructions(self):
        pass

    def draw_content(self):
        title = " ЗАДАНИЕ ИМЕНИ СТЕКА "
        x = max(0, (self.width - len(title)) // 2)
        safe_addstr(self.stdscr, 4, x, title, curses.color_pair(3) | curses.A_BOLD)

        # Пояснение
        instruction = "Задайте имя стека серверных компонентов Pilot"
        x = max(0, (self.width - len(instruction)) // 2)
        safe_addstr(self.stdscr, 6, x, instruction)
        instruction2 = "(максимум 8 символов, только латинские буквы, цифры и тире):"
        x = max(0, (self.width - len(instruction2)) // 2)
        safe_addstr(self.stdscr, 7, x, instruction2)

        # Поле ввода (без рамки, только заливка)
        field_label = "Имя стека:"
        safe_addstr(self.stdscr, 9, 10, field_label, curses.A_BOLD)
        field_x = 10 + len(field_label) + 1
        field_y = 9
        self.input_x = field_x
        self.input_y = field_y
        field_width = 10  # 8 символов + немного места

        # Выбираем цвет фона
        if self.validation_error:
            color = curses.color_pair(5) | curses.A_REVERSE
        elif self.focus_mode == 0 and not self.editing:
            color = curses.A_REVERSE  # инверсный, когда поле в фокусе
        else:
            color = curses.A_NORMAL

        # Очищаем область поля (заливаем фоном)
        for i in range(field_width):
            safe_addstr(self.stdscr, field_y, field_x + i, " ", color)

        # Выводим текущее имя
        display_name = self.stack_name.ljust(8)
        safe_addstr(self.stdscr, field_y, field_x, display_name, color)

        # Курсор в режиме редактирования
        if self.editing:
            curses.curs_set(1)
            self.stdscr.move(field_y, field_x + len(self.stack_name))
        else:
            curses.curs_set(0)

        # Сообщение об ошибке
        if self.validation_error:
            err_msg = "Недопустимые символы! Используйте a-z, 0-9, -"
            x = max(0, (self.width - len(err_msg)) // 2)
            safe_addstr(self.stdscr, 11, x, err_msg, curses.color_pair(5))

        # Инструкция по управлению
        instr = "Ввод: буквы/цифры/дефис | Backspace: удалить | Enter: завершить ввод | TAB: переключение на кнопки"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 3, 4, instr, curses.color_pair(4))

    def validate(self, name):
        """Проверяет, что имя состоит только из допустимых символов"""
        return re.match(r'^[a-zA-Z0-9-]*$', name) is not None

    def handle_mouse(self):
        """Обработка мыши: клик по полю ввода или по кнопкам"""
        try:
            _, mx, my, _, bstate = curses.getmouse()

            # Сначала кнопки
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

            # Клик по полю ввода
            field_x = self.input_x
            field_y = self.input_y
            field_width = 10
            if my == field_y and field_x <= mx < field_x + field_width:
                if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                    self.focus_mode = 0
                    self.editing = True
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
            if self.editing:
                # Если редактируем, сначала завершаем редактирование
                self.editing = False
                self.needs_redraw = True
            else:
                self.focus_mode = (self.focus_mode + 1) % 2
                self.needs_redraw = True
        elif key == 27:  # ESC
            return "exit"
        else:
            if self.focus_mode == 0:
                self._handle_input_field(key)
            else:
                result = self.handle_keyboard(key)
                if result:
                    return self.handle_action(result)
        return None

    def _handle_input_field(self, key):
        if key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            # Завершаем редактирование
            self.editing = False
            self.needs_redraw = True
        elif key == 127 or key == curses.KEY_BACKSPACE or key == 8:
            # Удаление символа
            if self.stack_name:
                self.stack_name = self.stack_name[:-1]
                self.validation_error = False
                self._update_button_state()
                self.needs_redraw = True
        elif 32 <= key <= 126:  # Печатные символы
            char = chr(key)
            if len(self.stack_name) < 8:
                new_name = self.stack_name + char
                if self.validate(new_name):
                    self.stack_name = new_name
                    self.validation_error = False
                else:
                    self.validation_error = True
                self._update_button_state()
                self.needs_redraw = True

    def _update_button_state(self):
        """Активирует кнопку 'Задать', если имя не пустое и валидно"""
        if self.stack_name and self.validate(self.stack_name):
            self.buttons[0].enabled = True
        else:
            self.buttons[0].enabled = False

    def handle_action(self, action):
        if action == "set":
            # Сохраняем имя стека в app
            self.app.stack_name = self.stack_name
            # Пока следующего экрана нет, переходим на db_option (заглушка)
            self.app.switch_screen("folder_picker")
            return None
        elif action == "exit":
            return "exit"
        return None

    def get_screen_name(self):
        return "Задание имени стека"