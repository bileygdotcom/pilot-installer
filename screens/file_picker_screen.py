#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import os
import stat
import time
from screens.base_screen import BaseScreen
from components.ui import Button
from utils.terminal import safe_addstr

class FilePickerScreen(BaseScreen):
    """
    Экран выбора файла с навигацией по файловой системе.
    Поддерживает фильтрацию по расширениям (если задано).
    """
    def __init__(self, stdscr, app, start_path=None, filter_extensions=None, title="Выберите файл"):
        super().__init__(stdscr, app)
        self.title = title
        self.filter_extensions = filter_extensions   # None означает показывать все файлы
        self.start_path = start_path or os.path.expanduser("~")
        self.current_path = os.path.abspath(self.start_path)
        self.files = []          # список имён файлов/папок
        self.is_dir = []         # True для папок
        self.selected_index = 0
        self.focus_mode = 0      # 0 - список файлов, 1 - кнопки
        self.message = ""
        self.scroll_offset = 0   # смещение для прокрутки
        
        self.buttons = [
            Button(0, "[ Выбрать ]", "select"),
            Button(1, "[ Отмена ]", "cancel")
        ]
        self.current_button = 0
        
        self.load_files()
    
    def load_files(self):
        """Загружает список файлов и папок из current_path с учётом фильтра"""
        try:
            entries = os.listdir(self.current_path)
        except PermissionError:
            self.message = "Нет доступа к директории"
            self.files = []
            self.is_dir = []
            return
        
        dirs = []
        files = []
        for entry in entries:
            full = os.path.join(self.current_path, entry)
            try:
                if os.path.isdir(full):
                    dirs.append(entry)
                else:
                    # Если задан фильтр расширений, проверяем
                    if self.filter_extensions is not None:
                        ext = os.path.splitext(entry)[1].lower()
                        if ext in self.filter_extensions:
                            files.append(entry)
                    else:
                        files.append(entry)
            except OSError:
                continue
        
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        
        self.files = dirs + files
        self.is_dir = [True] * len(dirs) + [False] * len(files)
        
        # Корректируем выделение и прокрутку
        if self.files:
            if self.selected_index >= len(self.files):
                self.selected_index = len(self.files) - 1
            self._adjust_scroll()
        else:
            self.selected_index = 0
            self.scroll_offset = 0
            if not self.message:
                self.message = "Нет файлов"
    
    def _adjust_scroll(self):
        """Корректирует смещение прокрутки, чтобы выделенный элемент был видим"""
        if not self.files:
            self.scroll_offset = 0
            return
        
        list_height = self.height - 12
        if list_height < 1:
            list_height = 1
        
        # Если выделенный элемент выше видимой области
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        # Если выделенный элемент ниже видимой области
        elif self.selected_index >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected_index - list_height + 1
    
    def draw_content(self):
        """Отрисовывает содержимое экрана"""
        # Заголовок (только один)
        safe_addstr(self.stdscr, 2, 2, self.title, curses.color_pair(3) | curses.A_BOLD)
        
        # Текущий путь
        path_display = self.current_path
        if len(path_display) > self.width - 10:
            path_display = "..." + path_display[-(self.width-13):]
        safe_addstr(self.stdscr, 4, 2, "Путь: " + path_display)
        
        # Список файлов
        list_start_y = 6
        list_height = self.height - 12
        if list_height < 3:
            list_height = 3
        
        if self.files:
            end_idx = min(len(self.files), self.scroll_offset + list_height)
            for i in range(self.scroll_offset, end_idx):
                y = list_start_y + (i - self.scroll_offset)
                if y >= self.height - 6:
                    break
                
                prefix = "📁 " if self.is_dir[i] else "📄 "
                filename = self.files[i]
                max_len = self.width - 6
                if len(filename) > max_len:
                    filename = filename[:max_len-3] + "..."
                
                # Подсветка выделенного элемента
                if i == self.selected_index and self.focus_mode == 0:
                    attr = curses.A_REVERSE
                else:
                    attr = 0
                safe_addstr(self.stdscr, y, 4, prefix + filename, attr)
            
            # Если есть элементы выше видимой области, показываем индикатор
            if self.scroll_offset > 0:
                safe_addstr(self.stdscr, list_start_y - 1, 4, "↑ ...")
            if end_idx < len(self.files):
                safe_addstr(self.stdscr, list_start_y + list_height, 4, "↓ ...")
        else:
            safe_addstr(self.stdscr, list_start_y, 4, "(пусто)")
        
        # Информация о выбранном файле (если это файл)
        if self.files and not self.is_dir[self.selected_index]:
            full_path = os.path.join(self.current_path, self.files[self.selected_index])
            try:
                st = os.stat(full_path)
                size = st.st_size
                mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
                size_str = self._format_size(size)
                info = f"Размер: {size_str} | Изменён: {mtime}"
                safe_addstr(self.stdscr, self.height - 6, 4, info[:self.width-8])
            except:
                pass
        
        # Сообщение (ошибка/предупреждение)
        if self.message:
            safe_addstr(self.stdscr, self.height - 5, 4, self.message, curses.color_pair(5))
        
        # Инструкция для списка файлов (отдельно от кнопок)
        instr = "↑↓: выбор | Enter: открыть папку / выбрать файл | Backspace: назад"
        if len(instr) > self.width:
            instr = instr[:self.width-4] + "..."
        safe_addstr(self.stdscr, self.height - 4, 4, instr, curses.color_pair(4))
        
        # Кнопки будут нарисованы автоматически в draw_buttons, который вызывается после draw_content
        # в родительском draw(), поэтому они окажутся в самом низу, над статусной строкой.
    
    def _format_size(self, size):
        """Форматирует размер файла в человекочитаемый вид"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def handle_input(self):
        """Переопределяем обработку ввода для работы со списком файлов"""
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
            self.focus_mode = (self.focus_mode + 1) % 2
            self.needs_redraw = True
        elif self.focus_mode == 0:  # Фокус на списке файлов
            return self._handle_list_keys(key)
        else:  # Фокус на кнопках
            result = self.handle_keyboard(key)
            if result:
                return self.handle_action(result)
        
        return None
    
    def _handle_list_keys(self, key):
        """Обработка клавиш в режиме списка файлов"""
        if key == curses.KEY_UP:
            if self.files and self.selected_index > 0:
                self.selected_index -= 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key == curses.KEY_DOWN:
            if self.files and self.selected_index < len(self.files) - 1:
                self.selected_index += 1
                self._adjust_scroll()
                self.needs_redraw = True
        elif key == ord('\n') or key == ord('\r') or key == curses.KEY_ENTER:
            if self.files:
                selected = self.files[self.selected_index]
                full = os.path.join(self.current_path, selected)
                if self.is_dir[self.selected_index]:
                    try:
                        os.chdir(full)  # не обязательно, просто проверим доступ
                        self.current_path = full
                        self.load_files()
                        self.selected_index = 0
                        self.message = ""
                    except PermissionError:
                        self.message = "Нет доступа"
                    self.needs_redraw = True
                else:
                    # Выбран файл
                    self.app.file_picker_result = full
                    return self.handle_action("select")
        elif key == 127 or key == curses.KEY_BACKSPACE or key == 8:  # Backspace
            parent = os.path.dirname(self.current_path)
            if parent and parent != self.current_path:
                self.current_path = parent
                self.load_files()
                self.selected_index = 0
                self.message = ""
                self.needs_redraw = True
        return None
    
    def handle_action(self, action):
        if action == "cancel":
            self.app.file_picker_result = None
            return "back"
        elif action == "select":
            return "back"
        return None
    
    def get_screen_name(self):
        return "Выбор файла"