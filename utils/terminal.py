#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Утилиты для работы с терминалом
"""

import curses
import os
import sys

def setup_mouse():
    """Настройка поддержки мыши"""
    try:
        curses.mousemask(curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED)
        curses.mouseinterval(50)
        
        # Для XTerm и совместимых
        if os.environ.get('TERM') in ['xterm', 'xterm-256color', 'rxvt', 'rxvt-unicode']:
            sys.stdout.write("\033[?1000h")
            sys.stdout.write("\033[?1002h")
            sys.stdout.write("\033[?1015h")
            sys.stdout.flush()
    except:
        pass

def cleanup_mouse():
    """Очистка настроек мыши"""
    try:
        sys.stdout.write("\033[?1000l")
        sys.stdout.write("\033[?1002l")
        sys.stdout.write("\033[?1015l")
        sys.stdout.write("\033[?1003l")
        sys.stdout.flush()
    except:
        pass

def safe_addstr(stdscr, y, x, text, attr=0):
    """Безопасный вывод строки с проверкой границ"""
    height, width = stdscr.getmaxyx()
    
    if y < 0 or y >= height:
        return
    if x < 0:
        x = 0
    if x >= width:
        return
    
    max_len = width - x
    if max_len <= 0:
        return
    
    if len(text) > max_len:
        text = text[:max_len - 1] + ">"
    
    try:
        if attr:
            stdscr.attron(attr)
            stdscr.addstr(y, x, text)
            stdscr.attroff(attr)
        else:
            stdscr.addstr(y, x, text)
    except curses.error:
        pass