#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для проверки наличия Docker и Docker Compose
"""

import subprocess
import shutil
from typing import Tuple, Dict

def check_docker() -> Tuple[bool, str]:
    """Проверяет наличие Docker, возвращает (установлен ли, версия или сообщение)"""
    docker_path = shutil.which('docker')
    if not docker_path:
        return False, "Docker не найден"
    
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        else:
            return False, "Ошибка при проверке Docker"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

def check_docker_compose() -> Tuple[bool, str]:
    """Проверяет наличие Docker Compose (плагин или отдельная команда)"""
    # Проверяем docker compose plugin (новый)
    docker_path = shutil.which('docker')
    if docker_path:
        try:
            result = subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, f"docker compose plugin: {version}"
        except:
            pass
    
    # Проверяем старую команду docker-compose
    compose_path = shutil.which('docker-compose')
    if compose_path:
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
        except:
            pass
    
    return False, "Docker Compose не найден"

def get_docker_status() -> Dict:
    """Возвращает словарь со статусами Docker и Docker Compose"""
    docker_installed, docker_version = check_docker()
    compose_installed, compose_version = check_docker_compose()
    
    return {
        'docker': {
            'installed': docker_installed,
            'version': docker_version
        },
        'compose': {
            'installed': compose_installed,
            'version': compose_version
        }
    }