#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для определения операционной системы
"""

import platform
import distro
import subprocess
from dataclasses import dataclass
from typing import Optional

@dataclass
class OSSystem:
    """Класс для хранения информации об ОС"""
    system: str
    release: str
    version: str
    machine: str
    processor: str
    distro: Optional[str] = None
    distro_id: Optional[str] = None
    distro_version: Optional[str] = None
    distro_codename: Optional[str] = None
    distro_like: Optional[str] = None
    install_method: Optional[str] = None
    docker_supported: bool = False
    docker_compose_supported: bool = False

def get_os_info() -> OSSystem:
    """Определяет операционную систему и возвращает структуру с информацией"""
    os_info = OSSystem(
        system=platform.system(),
        release=platform.release(),
        version=platform.version(),
        machine=platform.machine(),
        processor=platform.processor()
    )
    
    # Для Linux систем используем distro для детальной информации
    if os_info.system == 'Linux':
        try:
            os_info.distro = distro.name(pretty=True)
            os_info.distro_id = distro.id()
            os_info.distro_version = distro.version()
            os_info.distro_codename = distro.codename()
            os_info.distro_like = distro.like()
        except:
            _parse_os_release(os_info)
    
    # Определяем метод установки Docker
    _determine_install_method(os_info)
    
    return os_info

def _parse_os_release(os_info: OSSystem):
    """Парсит /etc/os-release как запасной вариант"""
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    value = value.strip('"')
                    if key == 'NAME':
                        os_info.distro = value
                    elif key == 'VERSION_ID':
                        os_info.distro_version = value
                    elif key == 'VERSION_CODENAME':
                        os_info.distro_codename = value
                    elif key == 'ID':
                        os_info.distro_id = value
                    elif key == 'ID_LIKE':
                        os_info.distro_like = value
    except:
        pass

def _determine_install_method(os_info: OSSystem):
    """Определяет метод установки Docker в зависимости от ОС"""
    distro_id = (os_info.distro_id or '').lower()
    distro_like = (os_info.distro_like or '').lower()
    
    # Семейство Debian/Ubuntu
    if distro_id in ['debian', 'ubuntu'] or 'debian' in distro_like:
        os_info.install_method = 'apt'
        os_info.docker_supported = True
        os_info.docker_compose_supported = True
    
    # Семейство RHEL/CentOS/Fedora
    elif distro_id in ['rhel', 'centos', 'fedora'] or 'rhel' in distro_like or 'fedora' in distro_like:
        os_info.install_method = 'yum' if distro_id in ['rhel', 'centos'] else 'dnf'
        os_info.docker_supported = True
        os_info.docker_compose_supported = True
    
    # Семейство openSUSE/SUSE
    elif distro_id in ['opensuse', 'suse'] or 'suse' in distro_like:
        os_info.install_method = 'zypper'
        os_info.docker_supported = True
        os_info.docker_compose_supported = True
    
    # Arch Linux
    elif distro_id in ['arch', 'manjaro'] or 'arch' in distro_like:
        os_info.install_method = 'pacman'
        os_info.docker_supported = True
        os_info.docker_compose_supported = True
    
    # Alpine Linux
    elif distro_id == 'alpine':
        os_info.install_method = 'apk'
        os_info.docker_supported = True
        os_info.docker_compose_supported = False
    
    # Неподдерживаемые дистрибутивы
    else:
        os_info.install_method = 'manual'
        os_info.docker_supported = False
        os_info.docker_compose_supported = False