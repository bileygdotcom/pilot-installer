#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Установщик Pilot-BIM для Linux
Первый экран: приветствие и навигация
"""

import curses
import sys

class PilotBIMInstaller:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.current_button = 0  # 0 - Продолжить, 1 - Выйти
        
        # Настройка цветов
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Активная кнопка
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Неактивная кнопка
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Заголовок
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Инструкции
        
        # Включение поддержки мыши
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        curses.mouseinterval(0)
        
        # Скрытие курсора
        curses.curs_set(0)
        
    def draw_border(self):
        """Рисует рамку вокруг экрана"""
        self.stdscr.border(0)
        
    def draw_header(self):
        """Рисует заголовок приложения"""
        header = " УСТАНОВЩИК PILOT-BIM "
        x = max(0, (self.width - len(header)) // 2)
        if x > 0:
            self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(2, x, header)
            self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
    
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
            x = max(0, (self.width - len(msg)) // 2)
            if x > 0:
                self.stdscr.addstr(start_y + i, x, msg)
    
    def draw_buttons(self):
        """Рисует кнопки навигации"""
        button1 = "[ Продолжить ]"
        button2 = "[ Выйти ]"
        
        # Расчет позиций для центрирования кнопок
        total_width = len(button1) + len(button2) + 4  # 4 пробела между кнопками
        start_x = max(0, (self.width - total_width) // 2)
        button_y = self.height - 4
        
        # Рисуем первую кнопку
        if self.current_button == 0:
            self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        else:
            self.stdscr.attron(curses.color_pair(2))
        
        self.stdscr.addstr(button_y, start_x, button1)
        
        if self.current_button == 0:
            self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        else:
            self.stdscr.attroff(curses.color_pair(2))
        
        # Рисуем вторую кнопку
        if self.current_button == 1:
            self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        else:
            self.stdscr.attron(curses.color_pair(2))
        
        self.stdscr.addstr(button_y, start_x + len(button1) + 4, button2)
        
        if self.current_button == 1:
            self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        else:
            self.stdscr.attroff(curses.color_pair(2))
    
    def draw_instructions(self):
        """Рисует инструкции по навигации"""
        instructions = " TAB / Стрелки: навигация • ENTER: выбор • Мышь: клик "
        x = max(0, (self.width - len(instructions)) // 2)
        if x > 0:
            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(self.height - 2, x, instructions)
            self.stdscr.attroff(curses.color_pair(4))
    
    def draw_status_line(self):
        """Рисует строку состояния с информацией о размере экрана"""
        status = f" Размер экрана: {self.width}x{self.height} "
        if self.width < 80 or self.height < 24:
            status = " ! Рекомендуемый размер экрана: 80x24 или больше " + status
        
        self.stdscr.attron(curses.A_REVERSE)
        self.stdscr.addstr(self.height - 1, 0, status[:self.width - 1])
        self.stdscr.attroff(curses.A_REVERSE)
    
    def handle_mouse(self):
        """Обрабатывает события мыши"""
        try:
            _, mx, my, _, bstate = curses.getmouse()
            
            # Проверяем клик левой кнопкой мыши
            if bstate & curses.BUTTON1_CLICKED:
                button1_x = max(0, (self.width - (len("[ Продолжить ]") * 2 + 4)) // 2)
                button1_end = button1_x + len("[ Продолжить ]")
                button2_x = button1_x + len("[ Продолжить ]") + 4
                button2_end = button2_x + len("[ Выйти ]")
                button_y = self.height - 4
                
                # Проверяем клик на кнопках
                if my == button_y:
                    if button1_x <= mx < button1_end:
                        return "continue"
                    elif button2_x <= mx < button2_end:
                        return "exit"
                
                # Проверяем клик вне кнопок для переключения фокуса
                if my == button_y:
                    if mx < button1_x:
                        self.current_button = 0
                    elif mx > button2_end:
                        self.current_button = 1
        except:
            pass
        return None
    
    def run(self):
        """Основной цикл приложения"""
        while True:
            self.stdscr.clear()
            
            # Адаптивный интерфейс
            if self.height >= 24 and self.width >= 80:
                self.draw_border()
                self.draw_header()
                self.draw_welcome_message()
                self.draw_buttons()
                self.draw_instructions()
            else:
                # Упрощенный интерфейс для маленьких экранов
                msg = "Увеличьте размер терминала до 80x24"
                try:
                    self.stdscr.addstr(self.height // 2, 
                                     max(0, (self.width - len(msg)) // 2), 
                                     msg)
                except:
                    pass
            
            self.draw_status_line()
            self.stdscr.refresh()
            
            # Обработка ввода
            key = self.stdscr.getch()
            
            if key == curses.KEY_MOUSE:
                result = self.handle_mouse()
                if result == "continue":
                    return "continue"
                elif result == "exit":
                    return "exit"
            
            elif key == ord('\t') or key == curses.KEY_RIGHT or key == curses.KEY_LEFT:
                # Переключение между кнопками
                self.current_button = (self.current_button + 1) % 2
            
            elif key == ord('\n') or key == ord('\r') or key == curses.KEY_ENTER:
                # Выбор текущей кнопки
                if self.current_button == 0:
                    return "continue"
                else:
                    return "exit"
            
            elif key == ord('q') or key == ord('Q') or key == 27:  # ESC
                return "exit"

def main(stdscr):
    """Основная функция"""
    installer = PilotBIMInstaller(stdscr)
    result = installer.run()
    
    if result == "continue":
        # Здесь будет переход к следующему экрану
        stdscr.clear()
        stdscr.addstr(0, 0, "Переход к следующему экрану...")
        stdscr.addstr(2, 0, "Нажмите любую клавишу для выхода")
        stdscr.refresh()
        stdscr.getch()
    elif result == "exit":
        stdscr.clear()
        stdscr.addstr(0, 0, "Выход из программы...")
        stdscr.refresh()
        curses.napms(1000)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)