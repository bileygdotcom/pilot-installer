#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import sys
from screens.welcome_screen import WelcomeScreen
from screens.os_detection_screen import OSDectionScreen
from screens.docker_check_screen import DockerCheckScreen
from screens.docker_install_screen import DockerInstallScreen
from utils.terminal import setup_mouse, cleanup_mouse

class PilotBIMInstaller:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_screen = None
        self.running = True
        self.screens = {}
        
        setup_mouse()
        curses.curs_set(0)
        self.stdscr.keypad(True)
        
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)
        
        self.screens["welcome"] = WelcomeScreen(stdscr, self)
        self.screens["os_detection"] = OSDectionScreen(stdscr, self)
        self.screens["docker_check"] = DockerCheckScreen(stdscr, self)
        self.screens["docker_install"] = DockerInstallScreen(stdscr, self)
        
        self.current_screen = self.screens["welcome"]
    
    def switch_screen(self, screen_name):
        if screen_name in self.screens:
            self.current_screen = self.screens[screen_name]
            self.current_screen.refresh()
    
    def run(self):
        while self.running and self.current_screen:
            result = self.current_screen.handle_input()
            if result == "exit":
                self.running = False
            elif result == "next":
                # Определяем, какой экран следующий
                if isinstance(self.current_screen, WelcomeScreen):
                    self.switch_screen("os_detection")
                elif isinstance(self.current_screen, OSDectionScreen):
                    self.switch_screen("docker_check")
                elif isinstance(self.current_screen, DockerCheckScreen):
                    # Если нужно установить Docker, переходим на экран установки
                    if hasattr(self.current_screen, 'need_install') and self.current_screen.need_install:
                        self.switch_screen("docker_install")
                    else:
                        # Если Docker уже установлен, можно перейти дальше (заглушка)
                        pass
                elif isinstance(self.current_screen, DockerInstallScreen):
                    # После установки возвращаемся на проверку
                    self.switch_screen("docker_check")
            elif result == "install":
                # Специальный сигнал для запуска установки
                self.switch_screen("docker_install")
    
    def quit(self):
        self.running = False

def main(stdscr):
    stdscr.clear()
    stdscr.refresh()
    installer = PilotBIMInstaller(stdscr)
    try:
        installer.run()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_mouse()
        stdscr.clear()
        stdscr.refresh()
        curses.napms(500)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"\nОшибка: {e}")
        cleanup_mouse()
        sys.exit(1)