#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import sys
from screens.welcome_screen import WelcomeScreen
from screens.os_detection_screen import OSDectionScreen
from screens.docker_check_screen import DockerCheckScreen
from screens.docker_install_screen import DockerInstallScreen
from screens.file_picker_screen import FilePickerScreen
from utils.terminal import setup_mouse, cleanup_mouse
from screens.license_confirm_screen import LicenseConfirmScreen
from screens.components_selection_screen import ComponentsSelectionScreen
from screens.port_assignment_screen import PortAssignmentScreen
from screens.db_option_screen import DbOptionScreen
from screens.db_demo_screen import DbDemoScreen
from screens.db_existing_screen import DbExistingScreen
from screens.admin_creation_screen import AdminCreationScreen
from screens.stack_name_screen import StackNameScreen
from screens.folder_picker_screen import FolderPickerScreen
from screens.compose_created_screen import ComposeCreatedScreen
from screens.image_tag_screen import ImageTagScreen
from screens.stack_start_screen import StackStartScreen
from screens.stack_logs_screen import StackLogsScreen

class PilotBIMInstaller:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_screen = None
        self.running = True
        self.screens = {}
        self.file_picker_result = None
        self.license_file_path = None

        # Данные, передаваемые между экранами
        self.license_file_path = None
        self.selected_components = []
        self.assigned_ports = {}
        
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
        self.screens["file_picker"] = FilePickerScreen(
            stdscr, self,
            filter_extensions=None,          # показываем все файлы
            title="Выберите файл лицензии Pilot"
        )
        self.screens["license_confirm"] = LicenseConfirmScreen(stdscr, self)
        self.screens["components_selection"] = ComponentsSelectionScreen(stdscr, self)
        self.current_screen = self.screens["welcome"]
        self.screens["port_assignment"] = PortAssignmentScreen(stdscr, self)
        self.screens["db_option"] = DbOptionScreen(stdscr, self)
        self.screens["db_demo"] = DbDemoScreen(stdscr, self)
        self.screens["db_existing"] = DbExistingScreen(stdscr, self)
        self.screens["admin_creation"] = AdminCreationScreen(stdscr, self)
        self.screens["stack_name"] = StackNameScreen(stdscr, self)
        self.screens["folder_picker"] = FolderPickerScreen(stdscr, self)
        self.screens["compose_created"] = ComposeCreatedScreen(stdscr, self)
        self.screens["image_tag"] = ImageTagScreen(stdscr, self)
        self.screens["stack_start"] = StackStartScreen(stdscr, self)
        self.screens["stack_logs"] = StackLogsScreen(stdscr, self)

    
    def switch_screen(self, screen_name):
        if screen_name in self.screens:
            self.current_screen = self.screens[screen_name]
            self.current_screen.on_enter()   # <-- важно для обновления данных
            self.current_screen.refresh()
    
    def run(self):
        while self.running and self.current_screen:
            result = self.current_screen.handle_input()
            if result == "exit":
                self.running = False
            elif result == "next":
                if isinstance(self.current_screen, WelcomeScreen):
                    self.switch_screen("os_detection")
                elif isinstance(self.current_screen, OSDectionScreen):
                    self.switch_screen("docker_check")
                elif isinstance(self.current_screen, DockerInstallScreen):
                    self.switch_screen("docker_check")
            elif result == "install":
                self.switch_screen("docker_install")
            elif result == "back":
                self.switch_screen("docker_check")
    
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