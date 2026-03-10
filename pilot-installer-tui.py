#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Установщик Pilot-BIM для Linux
Первый экран: приветствие и навигация (исправленная версия с поддержкой мыши)
"""

import curses
import sys
import os
import time

class PilotBIMInstaller:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.current_button = 0  # 0 - Продолжить, 1 - Выйти
        self.running = True
        self.needs_redraw = True
        self.last_mouse_event = 0
        self.mouse_debounce = 0.1  # Защита от множественных событий мыши
        
        # Настройка цветов
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Активная кнопка
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Неактивная кнопка
            curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Заголовок
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Инструкции
            curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)    # Ошибка/Предупреждение
        
        # Настройка мыши (более простая и надежная)
        try:
            # Включаем только события кликов, без отслеживания движения
            curses.mousemask(curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED)
            curses.mouseinterval(50)  # Интервал для двойного клика в мс
        except:
            pass
            
        # Скрытие курсора
        try:
            curses.curs_set(0)
        except:
            pass
        
        # Включаем специальные режимы
        self.stdscr.keypad(True)
        self.stdscr.nodelay(False)  # Блокирующий ввод
        
        # Для XTerm и совместимых
        if os.environ.get('TERM') in ['xterm', 'xterm-256color', 'rxvt', 'rxvt-unicode']:
            sys.stdout.write("\033[?1000h")  # Включаем отчет о мыши
            sys.stdout.write("\033[?1002h")  # Включаем отслеживание движения
            sys.stdout.write("\033[?1015h")  # Включаем расширенный формат
            sys.stdout.flush()
    
    def __del__(self):
        """Деструктор для восстановления терминала"""
        try:
            # Отключаем отчет о мыши
            sys.stdout.write("\033[?1000l")
            sys.stdout.write("\033[?1002l")
            sys.stdout.write("\033[?1015l")
            sys.stdout.write("\033[?1003l")
            sys.stdout.flush()
        except:
            pass
    
    def safe_addstr(self, y, x, text, attr=0):
        """Безопасный вывод строки с проверкой границ"""
        if y < 0 or y >= self.height:
            return
        if x < 0:
            x = 0
        if x >= self.width:
            return
        
        max_len = self.width - x
        if max_len <= 0:
            return
        
        if len(text) > max_len:
            text = text[:max_len - 1] + ">"
        
        try:
            if attr:
                self.stdscr.attron(attr)
                self.stdscr.addstr(y, x, text)
                self.stdscr.attroff(attr)
            else:
                self.stdscr.addstr(y, x, text)
        except curses.error:
            pass
    
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
        self.safe_addstr(2, x, header, curses.color_pair(3) | curses.A_BOLD)
    
    def draw_welcome_message(self):
        """Рисует приветственное сообщение"""
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
                self.safe_addstr(start_y + i, x, msg)
    
    def get_button_positions(self):
        """Возвращает координаты кнопок"""
        button1_text = "[ Продолжить ]"
        button2_text = "[ Выйти ]"
        total_width = len(button1_text) + len(button2_text) + 4
        start_x = max(0, (self.width - total_width) // 2)
        button_y = min(self.height - 4, max(3, self.height - 4))
        
        button1_rect = {
            'x1': start_x,
            'x2': start_x + len(button1_text),
            'y': button_y,
            'action': 'continue'
        }
        
        button2_rect = {
            'x1': start_x + len(button1_text) + 4,
            'x2': start_x + len(button1_text) + 4 + len(button2_text),
            'y': button_y,
            'action': 'exit'
        }
        
        return button1_rect, button2_rect
    
    def draw_buttons(self):
        """Рисует кнопки навигации"""
        button1_text = "[ Продолжить ]"
        button2_text = "[ Выйти ]"
        
        button1_rect, button2_rect = self.get_button_positions()
        
        # Рисуем первую кнопку
        if self.current_button == 0:
            btn_attr = curses.color_pair(1) | curses.A_BOLD
        else:
            btn_attr = curses.color_pair(2)
        
        self.safe_addstr(button1_rect['y'], button1_rect['x1'], button1_text, btn_attr)
        
        # Рисуем вторую кнопку
        if self.current_button == 1:
            btn_attr = curses.color_pair(1) | curses.A_BOLD
        else:
            btn_attr = curses.color_pair(2)
        
        self.safe_addstr(button2_rect['y'], button2_rect['x1'], button2_text, btn_attr)
    
    def draw_instructions(self):
        """Рисует инструкции по навигации"""
        instructions = " TAB / Стрелки: навигация • ENTER: выбор • Мышь: клик "
        x = max(0, (self.width - len(instructions)) // 2)
        y = self.height - 2
        if y > 0:
            self.safe_addstr(y, x, instructions, curses.color_pair(4))
    
    def draw_small_screen_message(self):
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
                self.safe_addstr(start_y + i, x, msg, curses.color_pair(5) | curses.A_BOLD)
            elif i in [1, 3]:
                self.safe_addstr(start_y + i, x, msg, curses.A_BOLD)
            else:
                self.safe_addstr(start_y + i, x, msg)
    
    def draw_status_line(self):
        """Рисует строку состояния с информацией о размере экрана"""
        status = f" Размер экрана: {self.width}x{self.height} "
        if self.width < 80 or self.height < 24:
            status = " ⚠ Рекомендуемый размер: 80x24 " + status
            attr = curses.color_pair(5) | curses.A_REVERSE
        else:
            attr = curses.A_REVERSE
        
        self.safe_addstr(self.height - 1, 0, status[:self.width - 1], attr)
    
    def handle_mouse(self):
        """Обрабатывает события мыши без мерцания"""
        try:
            # Защита от множественных событий
            current_time = time.time()
            if current_time - self.last_mouse_event < self.mouse_debounce:
                return None
                
            _, mx, my, _, bstate = curses.getmouse()
            
            # Проверяем только клики левой кнопкой
            if bstate & curses.BUTTON1_CLICKED or bstate & curses.BUTTON1_DOUBLE_CLICKED:
                button1_rect, button2_rect = self.get_button_positions()
                
                # Проверяем клик на кнопках
                if my == button1_rect['y']:
                    if button1_rect['x1'] <= mx <= button1_rect['x2']:
                        self.last_mouse_event = current_time
                        return "continue"
                    elif button2_rect['x1'] <= mx <= button2_rect['x2']:
                        self.last_mouse_event = current_time
                        return "exit"
                
                # Клик вне кнопок - меняем фокус без перерисовки
                if my == button1_rect['y']:
                    if mx < button1_rect['x1']:
                        self.current_button = 0
                    elif mx > button2_rect['x2']:
                        self.current_button = 1
                    self.needs_redraw = True
                    
        except:
            pass
        return None
    
    def handle_resize(self):
        """Обрабатывает изменение размера терминала"""
        new_height, new_width = self.stdscr.getmaxyx()
        if new_height != self.height or new_width != self.width:
            self.height = new_height
            self.width = new_width
            curses.resizeterm(new_height, new_width)
            self.needs_redraw = True
            self.stdscr.clear()
    
    def run(self):
        """Основной цикл приложения"""
        while self.running:
            # Проверяем изменение размера
            self.handle_resize()
            
            # Перерисовываем только при необходимости
            if self.needs_redraw:
                self.stdscr.erase()  # Используем erase вместо clear для уменьшения мерцания
                
                if self.height >= 20 and self.width >= 60:
                    if self.height >= 24 and self.width >= 80:
                        self.draw_border()
                        self.draw_header()
                        self.draw_welcome_message()
                    else:
                        self.draw_border()
                        warn_msg = "⚠ Рекомендуется увеличить терминал до 80x24"
                        x = max(0, (self.width - len(warn_msg)) // 2)
                        self.safe_addstr(1, x, warn_msg, curses.color_pair(5) | curses.A_BOLD)
                        self.draw_header()
                        self.draw_welcome_message()
                    
                    self.draw_buttons()
                    self.draw_instructions()
                else:
                    self.draw_small_screen_message()
                
                self.draw_status_line()
                self.stdscr.refresh()
                self.needs_redraw = False
            
            # Обработка ввода (блокирующий режим)
            key = self.stdscr.getch()
            
            if key == curses.KEY_MOUSE:
                result = self.handle_mouse()
                if result == "continue":
                    return "continue"
                elif result == "exit":
                    return "exit"
            
            elif key == curses.KEY_RESIZE:
                self.handle_resize()
                self.needs_redraw = True
            
            elif key == ord('\t') or key == curses.KEY_RIGHT or key == curses.KEY_LEFT:
                self.current_button = (self.current_button + 1) % 2
                self.needs_redraw = True
            
            elif key == ord('\n') or key == ord('\r') or key == curses.KEY_ENTER:
                if self.current_button == 0:
                    return "continue"
                else:
                    return "exit"
            
            elif key == ord('q') or key == ord('Q') or key == 27:  # ESC
                return "exit"

def main(stdscr):
    """Основная функция"""
    # Очищаем экран при старте
    stdscr.clear()
    stdscr.refresh()
    
    installer = PilotBIMInstaller(stdscr)
    result = installer.run()
    
    # Очищаем экран перед выходом
    stdscr.clear()
    stdscr.refresh()
    
    if result == "continue":
        # Здесь будет переход к следующему экрану
        stdscr.addstr(0, 0, "Переход к следующему экрану...")
        stdscr.addstr(2, 0, "Нажмите любую клавишу для выхода")
        stdscr.refresh()
        stdscr.getch()
    elif result == "exit":
        # Показываем сообщение о выходе
        stdscr.addstr(0, 0, "Выход из программы...")
        stdscr.refresh()
        curses.napms(1000)

if __name__ == "__main__":
    try:
        # Сохраняем настройки терминала
        curses.wrapper(main)
    except KeyboardInterrupt:
        # Восстанавливаем терминал при прерывании
        print("\033[?1000l\033[?1002l\033[?1015l\033[?1003l", end="", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"\nОшибка: {e}")
        # Восстанавливаем терминал при ошибке
        print("\033[?1000l\033[?1002l\033[?1015l\033[?1003l", end="", flush=True)
        sys.exit(1)
    finally:
        # Гарантированное восстановление терминала
        print("\033[?1000l\033[?1002l\033[?1015l\033[?1003l", end="", flush=True)