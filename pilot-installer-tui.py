#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Установщик Pilot-BIM для Linux
Экран определения операционной системы
"""

import curses
import sys
import os
import time
import subprocess
import platform
import distro  # Для детального определения Linux дистрибутивов

class PilotBIMInstaller:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.current_button = 0  # 0 - Продолжить, 1 - Выйти
        self.running = True
        self.needs_redraw = True
        self.last_mouse_event = 0
        self.mouse_debounce = 0.1
        self.current_screen = "os_detection"  # Текущий экран
        self.os_info = {}  # Информация об ОС
        
        # Настройка цветов
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Активная кнопка
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Неактивная кнопка
            curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Заголовок
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Инструкции
            curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)    # Ошибка/Предупреждение
            curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Успех/Информация
        
        # Настройка мыши
        try:
            curses.mousemask(curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED)
            curses.mouseinterval(50)
        except:
            pass
            
        # Скрытие курсора
        try:
            curses.curs_set(0)
        except:
            pass
        
        self.stdscr.keypad(True)
        self.stdscr.nodelay(False)
        
        # Для XTerm и совместимых
        if os.environ.get('TERM') in ['xterm', 'xterm-256color', 'rxvt', 'rxvt-unicode']:
            sys.stdout.write("\033[?1000h")
            sys.stdout.write("\033[?1002h")
            sys.stdout.write("\033[?1015h")
            sys.stdout.flush()
        
        # Определяем ОС при инициализации
        self.detect_os()
    
    def detect_os(self):
        """Определяет операционную систему и её версию"""
        self.os_info = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'distro': None,
            'distro_version': None,
            'distro_codename': None,
            'docker_supported': False,
            'docker_compose_supported': False,
            'install_method': None
        }
        
        # Для Linux систем используем distro для детальной информации
        if self.os_info['system'] == 'Linux':
            try:
                self.os_info['distro'] = distro.name(pretty=True)
                self.os_info['distro_id'] = distro.id()
                self.os_info['distro_version'] = distro.version()
                self.os_info['distro_codename'] = distro.codename()
                self.os_info['distro_like'] = distro.like()
            except:
                # Fallback на чтение /etc/os-release
                self._parse_os_release()
        
        # Определяем метод установки Docker
        self._determine_install_method()
    
    def _parse_os_release(self):
        """Парсит /etc/os-release как запасной вариант"""
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        value = value.strip('"')
                        if key == 'NAME':
                            self.os_info['distro'] = value
                        elif key == 'VERSION_ID':
                            self.os_info['distro_version'] = value
                        elif key == 'VERSION_CODENAME':
                            self.os_info['distro_codename'] = value
                        elif key == 'ID':
                            self.os_info['distro_id'] = value
                        elif key == 'ID_LIKE':
                            self.os_info['distro_like'] = value
        except:
            pass
    
    def _determine_install_method(self):
        """Определяет метод установки Docker в зависимости от ОС"""
        distro_id = self.os_info.get('distro_id', '').lower()
        distro_like = self.os_info.get('distro_like', '').lower()
        
        # Семейство Debian/Ubuntu
        if distro_id in ['debian', 'ubuntu'] or 'debian' in distro_like:
            self.os_info['install_method'] = 'apt'
            self.os_info['docker_supported'] = True
            self.os_info['docker_compose_supported'] = True
        
        # Семейство RHEL/CentOS/Fedora
        elif distro_id in ['rhel', 'centos', 'fedora'] or 'rhel' in distro_like or 'fedora' in distro_like:
            self.os_info['install_method'] = 'yum' if distro_id in ['rhel', 'centos'] else 'dnf'
            self.os_info['docker_supported'] = True
            self.os_info['docker_compose_supported'] = True
        
        # Семейство openSUSE/SUSE
        elif distro_id in ['opensuse', 'suse'] or 'suse' in distro_like:
            self.os_info['install_method'] = 'zypper'
            self.os_info['docker_supported'] = True
            self.os_info['docker_compose_supported'] = True
        
        # Arch Linux
        elif distro_id in ['arch', 'manjaro'] or 'arch' in distro_like:
            self.os_info['install_method'] = 'pacman'
            self.os_info['docker_supported'] = True
            self.os_info['docker_compose_supported'] = True
        
        # Alpine Linux
        elif distro_id == 'alpine':
            self.os_info['install_method'] = 'apk'
            self.os_info['docker_supported'] = True
            self.os_info['docker_compose_supported'] = False  # Нужна отдельная установка
        
        # Неподдерживаемые дистрибутивы
        else:
            self.os_info['install_method'] = 'manual'
            self.os_info['docker_supported'] = False
            self.os_info['docker_compose_supported'] = False
    
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
    
    def draw_os_detection_screen(self):
        """Рисует экран определения ОС"""
        # Заголовок экрана
        title = " ОПРЕДЕЛЕНИЕ ОПЕРАЦИОННОЙ СИСТЕМЫ "
        x = max(0, (self.width - len(title)) // 2)
        self.safe_addstr(4, x, title, curses.color_pair(3) | curses.A_BOLD)
        
        start_y = 7
        line = 0
        
        # Основная информация
        info_lines = [
            ("Система:", self.os_info.get('system', 'Неизвестно')),
            ("Версия ядра:", self.os_info.get('release', 'Неизвестно')),
            ("Архитектура:", self.os_info.get('machine', 'Неизвестно')),
        ]
        
        # Информация о дистрибутиве для Linux
        if self.os_info['system'] == 'Linux':
            if self.os_info.get('distro'):
                info_lines.append(("Дистрибутив:", self.os_info['distro']))
            if self.os_info.get('distro_version'):
                info_lines.append(("Версия:", self.os_info['distro_version']))
            if self.os_info.get('distro_codename'):
                info_lines.append(("Кодовое имя:", self.os_info['distro_codename']))
        
        for label, value in info_lines:
            if start_y + line < self.height - 10:
                # Выводим label
                self.safe_addstr(start_y + line, 10, label, curses.A_BOLD)
                # Выводим значение
                value_x = 25
                self.safe_addstr(start_y + line, value_x, str(value))
                line += 1
        
        line += 1  # Пустая строка
        
        # Информация о поддержке Docker
        docker_title = "Поддержка Docker:"
        self.safe_addstr(start_y + line, 10, docker_title, curses.A_BOLD)
        
        docker_status = "✓ Поддерживается" if self.os_info['docker_supported'] else "✗ Требуется ручная установка"
        docker_color = curses.color_pair(6) if self.os_info['docker_supported'] else curses.color_pair(5)
        self.safe_addstr(start_y + line, 25, docker_status, docker_color)
        line += 1
        
        # Информация о Docker Compose
        compose_title = "Docker Compose:"
        self.safe_addstr(start_y + line, 10, compose_title, curses.A_BOLD)
        
        if self.os_info['docker_compose_supported']:
            compose_status = "✓ Поддерживается"
            compose_color = curses.color_pair(6)
        else:
            compose_status = "⚠ Требуется доп. установка"
            compose_color = curses.color_pair(5)
        self.safe_addstr(start_y + line, 25, compose_status, compose_color)
        line += 2
        
        # Метод установки
        if self.os_info.get('install_method'):
            method_title = "Метод установки:"
            method_map = {
                'apt': 'APT (Debian/Ubuntu)',
                'yum': 'YUM (RHEL/CentOS 7)',
                'dnf': 'DNF (Fedora/RHEL 8+)',
                'zypper': 'Zypper (openSUSE)',
                'pacman': 'Pacman (Arch Linux)',
                'apk': 'APK (Alpine Linux)',
                'manual': 'Ручная установка'
            }
            method_text = method_map.get(self.os_info['install_method'], self.os_info['install_method'])
            self.safe_addstr(start_y + line, 10, method_title, curses.A_BOLD)
            self.safe_addstr(start_y + line, 25, method_text)
            line += 2
        
        # Предупреждение для неподдерживаемых систем
        if not self.os_info['docker_supported']:
            warn_msg = "⚠ Внимание: Автоматическая установка Docker может не поддерживаться"
            x = max(0, (self.width - len(warn_msg)) // 2)
            self.safe_addstr(start_y + line, x, warn_msg, curses.color_pair(5) | curses.A_BOLD)
    
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
        status = f" Размер экрана: {self.width}x{self.height} | Экран: определение ОС "
        if self.width < 80 or self.height < 24:
            status = " ⚠ Рекомендуемый размер: 80x24 " + status
            attr = curses.color_pair(5) | curses.A_REVERSE
        else:
            attr = curses.A_REVERSE
        
        self.safe_addstr(self.height - 1, 0, status[:self.width - 1], attr)
    
    def handle_mouse(self):
        """Обрабатывает события мыши"""
        try:
            current_time = time.time()
            if current_time - self.last_mouse_event < self.mouse_debounce:
                return None
                
            _, mx, my, _, bstate = curses.getmouse()
            
            if bstate & curses.BUTTON1_CLICKED or bstate & curses.BUTTON1_DOUBLE_CLICKED:
                button1_rect, button2_rect = self.get_button_positions()
                
                if my == button1_rect['y']:
                    if button1_rect['x1'] <= mx <= button1_rect['x2']:
                        self.last_mouse_event = current_time
                        return "continue"
                    elif button2_rect['x1'] <= mx <= button2_rect['x2']:
                        self.last_mouse_event = current_time
                        return "exit"
                
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
            self.handle_resize()
            
            if self.needs_redraw:
                self.stdscr.erase()
                
                if self.height >= 20 and self.width >= 60:
                    if self.height >= 24 and self.width >= 80:
                        self.draw_border()
                        self.draw_header()
                        self.draw_os_detection_screen()
                    else:
                        self.draw_border()
                        warn_msg = "⚠ Рекомендуется увеличить терминал до 80x24"
                        x = max(0, (self.width - len(warn_msg)) // 2)
                        self.safe_addstr(1, x, warn_msg, curses.color_pair(5) | curses.A_BOLD)
                        self.draw_header()
                        self.draw_os_detection_screen()
                    
                    self.draw_buttons()
                    self.draw_instructions()
                else:
                    self.draw_small_screen_message()
                
                self.draw_status_line()
                self.stdscr.refresh()
                self.needs_redraw = False
            
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
            
            elif key == ord('q') or key == ord('Q') or key == 27:
                return "exit"

def main(stdscr):
    """Основная функция"""
    stdscr.clear()
    stdscr.refresh()
    
    installer = PilotBIMInstaller(stdscr)
    result = installer.run()
    
    stdscr.clear()
    stdscr.refresh()
    
    if result == "continue":
        # Здесь будет переход к следующему экрану
        stdscr.addstr(0, 0, "Переход к следующему экрану...")
        stdscr.addstr(2, 0, "Нажмите любую клавишу для выхода")
        stdscr.refresh()
        stdscr.getch()
    elif result == "exit":
        stdscr.addstr(0, 0, "Выход из программы...")
        stdscr.refresh()
        curses.napms(1000)

if __name__ == "__main__":
    # Убедимся, что установлен пакет distro
    try:
        import distro
    except ImportError:
        print("Установка зависимостей...")
        os.system("pip3 install distro")
        import distro
    
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\033[?1000l\033[?1002l\033[?1015l\033[?1003l", end="", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"\nОшибка: {e}")
        print("\033[?1000l\033[?1002l\033[?1015l\033[?1003l", end="", flush=True)
        sys.exit(1)
    finally:
        print("\033[?1000l\033[?1002l\033[?1015l\033[?1003l", end="", flush=True)