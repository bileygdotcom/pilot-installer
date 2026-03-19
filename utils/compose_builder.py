import os
import yaml

def build_compose(app):
    """
    Генерирует словарь docker-compose.yml на основе данных из app.
    Возвращает готовый словарь (структуру) для последующей записи.
    """
    stack_name = getattr(app, 'stack_name', 'pilot-stack')
    ports = getattr(app, 'assigned_ports', {})
    image_tag = getattr(app, 'image_tag', 'latest')  # тег образа, выбранный пользователем

    # Определяем путь к базам данных
    if hasattr(app, 'selected_demo_db') and app.selected_demo_db:
        db_volume = "/usr/share/ascon/databases/Databases"
    else:
        db_volume = os.path.dirname(app.existing_db_path) if getattr(app, 'existing_db_path', None) else "/usr/share/ascon/databases"

    compose = {
        'services': {
            'pilot-server': {
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
        }
    }

    # Здесь можно добавить условное добавление других сервисов
    # Например, если в app.selected_components есть Pilot-Web-Server, добавить его

    return compose

def write_compose_file(compose_dict, target_dir):
    """
    Записывает словарь compose в файл docker-compose.yml в target_dir.
    """
    file_path = os.path.join(target_dir, 'docker-compose.yml')
    with open(file_path, 'w') as f:
        yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)
    return file_path