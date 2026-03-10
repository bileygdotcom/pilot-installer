#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Базовый класс для всех экранов приложения
"""

import curses
import time
from utils.terminal import safe_addstr

class BaseScreen:
    def __init__(self, stdscr, app):
        self.stdscr = stdscr
        self.app = app
        self.height, self.width = stdscr.getmaxyx()
        self.needs_redraw = True
        self.last_mouse_event = 0
        self.mouse_debounce = 0.1
        
        # Кнопки будут определены в дочерних классах
        self.buttons = []
        self.current_button = 0
    
    def refresh(self):
        """Отмечает экран для перерисовки"""
        self.needs_redraw = True
    
    def handle_resize(self):
        """Обрабатывает изменение размера терминала"""
        new_height, new_width = self.stdscr.getmaxyx()
        if new_height != self.height or new_width != self.width:
            self.height = new_height
            self.width = new_width
            curses.resizeterm(new_height, new_width)
            self.needs_redraw = True
            self.stdscr.clear()
    
    def get_button_positions(self):
        """Возвращает позиции кнопок на экране"""
        if not self.buttons:
            return []
        
        total_width = sum(len(b.text) for b in self.buttons) + 4 * (len(self.buttons) - 1)
        start_x = max(0, (self.width - total_width) // 2)
        button_y = min(self.height - 4, max(3, self.height - 4))
        
        positions = []
        current_x = start_x
        
        for button in self.buttons:
            positions.append({
                'x': current_x,
                'x1': current_x,
                'x2': current_x + len(button.text),
                'y': button_y
            })
            current_x += len(button.text) + 4
        
        return positions
    
    def draw_buttons(self):
        """Рисует кнопки"""
        if not self.buttons:
            return
            
        button_positions = self.get_button_positions()
        
        for i, (button, pos) in enumerate(zip(self.buttons, button_positions)):
            is_active = (i == self.current_button)
            button.draw(self.stdscr, pos['x'], pos['y'], is_active)
    
    def draw_border(self):
        """Рисует рамку вокруг экрана"""
        if self.height >= 3 and self.width >= 3:
            try:
                self.stdscr.border(0)
            except curses.error:
                pass
    
    def draw_header(self):
        """Рисует заголовок приложения"""
        header = " УСТАНОВЩИК PILOT-BIM "
        x = max(0, (self.width - len(header)) // 2)
        safe_addstr(self.stdscr, 2, x, header, curses.color_pair(3) | curses.A_BOLD)
    
    def draw_instructions(self):
        """Рисует инструкции по навигации"""
        instructions = " TAB / Стрелки: навигация • ENTER: выбор • Мышь: клик "
        x = max(0, (self.width - len(instructions)) // 2)
        y = self.height - 2
        if y > 0:
            safe_addstr(self.stdscr, y, x, instructions, curses.color_pair(4))
    
    def draw_status_line(self):
        """Рисует строку состояния"""
        status_text = f" Размер экрана: {self.width}x{self.height} | {self.get_screen_name()} "
        
        if self.width < 80 or self.height < 24:
            status_text = " ⚠ Рекомендуемый размер: 80x24 " + status_text
            attr = curses.color_pair(5) | curses.A_REVERSE
        else:
            attr = curses.A_REVERSE
        
        safe_addstr(self.stdscr, self.height - 1, 0, status_text[:self.width - 1], attr)
    
    def draw_content(self):
        """Абстрактный метод для отрисовки содержимого экрана"""
        pass
    
    def draw(self):
        """Основной метод отрисовки"""
        if not self.needs_redraw:
            return
        
        self.stdscr.erase()
        
        if self.height >= 20 and self.width >= 60:
            if self.height >= 24 and self.width >= 80:
                self.draw_border()
                self.draw_header()
                self.draw_content()
            else:
                self.draw_border()
                warn_msg = "⚠ Рекомендуется увеличить терминал до 80x24"
                x = max(0, (self.width - len(warn_msg)) // 2)
                safe_addstr(self.stdscr, 1, x, warn_msg, 
                          curses.color_pair(5) | curses.A_BOLD)
                self.draw_header()
                self.draw_content()
            
            self.draw_buttons()
            self.draw_instructions()
        else:
            self._draw_small_screen_message()
        
        self.draw_status_line()
        
        self.stdscr.refresh()
        self.needs_redraw = False
    
    def _draw_small_screen_message(self):
        """Рисует сообщение для маленького экрана"""
        messages = [
            "!" * min(self.width, 60),
            "ТЕРМИНАЛ СЛИШКОМ МАЛ",
            f"Текущий размер: {self.width}x{self.height}",
            "Требуемый размер: 80x24",
            "",
            "Увеличьте размер окна терминала",
            "для продолжения работы",
            "!" * min(self.width, 60)
        ]
        
        start_y = max(0, (self.height - len(messages)) // 2)
        for i, msg in enumerate(messages):
            if len(msg) > self.width:
                msg = msg[:self.width]
            x = max(0, (self.width - len(msg)) // 2)
            
            if i in [0, 7]:
                attr = curses.color_pair(5) | curses.A_BOLD
            elif i in [1, 3]:
                attr = curses.A_BOLD
            else:
                attr = 0
            
            safe_addstr(self.stdscr, start_y + i, x, msg, attr)
    
    def handle_mouse(self):
        """Обрабатывает события мыши"""
        try:
            current_time = time.time()
            if current_time - self.last_mouse_event < self.mouse_debounce:
                return None
                
            _, mx, my, _, bstate = curses.getmouse()
            
            if bstate & curses.BUTTON1_CLICKED or bstate & curses.BUTTON1_DOUBLE_CLICKED:
                button_positions = self.get_button_positions()
                
                for i, pos in enumerate(button_positions):
                    if my == pos['y'] and pos['x1'] <= mx <= pos['x2']:
                        self.last_mouse_event = current_time
                        return self.buttons[i].action
                
                # Клик вне кнопок для переключения фокуса
                if button_positions and my == button_positions[0]['y']:
                    if mx < button_positions[0]['x1']:
                        self.current_button = 0
                    elif mx > button_positions[-1]['x2']:
                        self.current_button = len(self.buttons) - 1
                    self.needs_redraw = True
                    
        except:
            pass
        return None
    
    def handle_keyboard(self, key):
        """Обрабатывает клавиатурный ввод"""
        if not self.buttons:
            return None
            
        if key == ord('\t') or key == curses.KEY_RIGHT or key == curses.KEY_LEFT:
            self.current_button = (self.current_button + 1) % len(self.buttons)
            self.needs_redraw = True
            return None
        
        elif key == ord('\n') or key == ord('\r') or key == curses.KEY_ENTER:
            return self.buttons[self.current_button].action
        
        elif key == ord('q') or key == ord('Q') or key == 27:  # ESC
            return "exit"
        
        return None
    
    def handle_input(self):
        """Основной метод обработки ввода"""
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
        
        else:
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        
        return None
    
    def handle_action(self, action):
        """Обрабатывает действия от кнопок"""
        if action == "exit":
            return "exit"
        elif action == "continue":
            return self.on_continue()
        return None
    
    def on_continue(self):
        """Вызывается при нажатии кнопки Продолжить"""
        # Должен быть переопределен в дочерних классах
        return "next"
    
    def get_screen_name(self):
        """Возвращает название текущего экрана"""
        return "Базовый экран"