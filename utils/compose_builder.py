import os
import yaml

def build_compose(app):
    """
    Генерирует словарь docker-compose.yml на основе данных из app.
    Учитывает выбранные компоненты, порты, имя стека и базу данных.
    """
    stack_name = getattr(app, 'stack_name', 'pilot-stack')
    ports = getattr(app, 'assigned_ports', {})
    image_tag = getattr(app, 'image_tag', 'latest')
    selected_components = getattr(app, 'selected_components', [])

    # Определяем имя базы данных (для pilot-web-server)
    db_name = None
    if hasattr(app, 'selected_demo_db') and app.selected_demo_db:
        db_name = app.selected_demo_db  # например, "pilot-bim_ru"
    elif hasattr(app, 'existing_db_path') and app.existing_db_path:
        # Из пути к файлу .dbp извлекаем имя папки (предполагаем, что это имя базы)
        db_name = os.path.basename(os.path.dirname(app.existing_db_path))

    # Базовый compose со всеми сервисами, которые могут быть включены
    services = {}

    # Pilot-Server (всегда)
    if 'Pilot-Server' in selected_components:
        # Определяем путь к базам данных (для монтирования)
        if hasattr(app, 'selected_demo_db') and app.selected_demo_db:
            db_volume = "/usr/share/ascon/databases/Databases"
        else:
            db_volume = os.path.dirname(app.existing_db_path) if getattr(app, 'existing_db_path', None) else "/usr/share/ascon/databases"

        services['pilot-server'] = {
            'image': f"registry.ascon.ru/project/pilotdev/pilot/pilot-server:{image_tag}",
            'container_name': f"{stack_name}_pilot-server",
            'hostname': 'pilot-server',
            'restart': 'unless-stopped',
            'ports': [f"{ports.get('Pilot-Server', 5551)}:5545"],
            'volumes': [
                '/usr/share/ascon/.aspnet/pilot-server:/root/.aspnet',
                '/usr/share/ascon/logs/pilot-server:/App/logs',
                '/usr/share/ascon/pilot-server/settings:/usr/share/ascon/pilot-server/settings',
                f"{db_volume}:/usr/share/ascon/databases",
                '/usr/share/ASCON:/usr/share/ASCON'
            ],
            'entrypoint': ["/App/Ascon.Pilot.Daemon", "/usr/share/ascon/pilot-server/settings/settings.xml"]
        }

    # Pilot-BIM-Server
    if 'Pilot-BIM-Server' in selected_components:
        services['pilot-bim-server'] = {
            'image': f"registry.ascon.ru/project/pilotdev/pilot/pilot-bim-server:{image_tag}",
            'container_name': f"{stack_name}_pilot-bim-server",
            'hostname': 'pilot-bim-server',
            'restart': 'unless-stopped',
            'volumes': [
                '/usr/share/ascon/.aspnet/pilot-bim-server:/root/.aspnet',
                '/usr/share/ascon/logs/pilot-bim-server:/App/logs',
                '/usr/share/ascon/pilot-bim-server:/usr/share/ASCON/Pilot-BIM-Server'
            ],
            'depends_on': ['pilot-server']
        }

    # Pilot-Web-Server
    if 'Pilot-Web-Server' in selected_components:
        web_server = {
            'image': f"registry.ascon.ru/project/pilotdev/pilot/pilot-web-server:{image_tag}",
            'container_name': f"{stack_name}_pilot-web-server",
            'hostname': 'pilot-web-server',
            'restart': 'unless-stopped',
            'environment': {
                'PilotServer:Database': db_name or 'pilot-bim_ru',  # если база не выбрана, ставим значение по умолчанию
                'PilotServer:Url': 'http://pilot-server:5545'
            },
            'ports': [f"{ports.get('Pilot-Web-Server', 5552)}:80"],
            'depends_on': ['pilot-server']
        }
        services['pilot-web-server'] = web_server

    # Pilot-Web-MyAdmin
    if 'Pilot-Web-myAdmin' in selected_components:
        services['pilot-web-myadmin'] = {
            'image': f"registry.ascon.ru/project/pilotdev/pilot/pilot-web-myadmin:{image_tag}",
            'container_name': f"{stack_name}_pilot-web-myadmin",
            'hostname': 'pilot-web-myadmin',
            'restart': 'unless-stopped',
            'environment': {
                'PilotServer:Url': 'http://pilot-server:5545'
            },
            'ports': [f"{ports.get('Pilot-Web-myAdmin', 5553)}:5200"],
            'depends_on': ['pilot-server']
        }

    compose = {'services': services}
    return compose


def write_compose_file(compose_dict, target_dir):
    """
    Записывает словарь compose в файл docker-compose.yml в target_dir.
    """
    file_path = os.path.join(target_dir, 'docker-compose.yml')
    with open(file_path, 'w') as f:
        yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)
    return file_path