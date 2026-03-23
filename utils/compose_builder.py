import os
import yaml

def build_compose(app):
    stack_name = app.stack_name
    stack_path = app.stack_path
    ports = getattr(app, 'assigned_ports', {})
    image_tag = getattr(app, 'image_tag', 'latest')
    selected_components = getattr(app, 'selected_components', [])

    # Пути внутри стека
    data_root = f"/usr/share/ascon/{stack_name}"
    db_volume = f"{stack_path}/databases/Databases"  # для демо
    if hasattr(app, 'existing_db_path') and app.existing_db_path:
        # Для существующей базы – монтируем папку, содержащую базу (которая уже лежит в databases/)
        db_volume = os.path.dirname(app.existing_db_path)
    elif hasattr(app, 'selected_demo_db') and app.selected_demo_db:
        db_volume = f"{stack_path}/databases/Databases"

    services = {}
    # Pilot-Server
    if 'Pilot-Server' in selected_components:
        services['pilot-server'] = {
            'image': f"registry.ascon.ru/project/pilotdev/pilot/pilot-server:{image_tag}",
            'container_name': f"{stack_name}_pilot-server",
            'hostname': 'pilot-server',
            'restart': 'unless-stopped',
            'ports': [f"{ports.get('Pilot-Server', 5551)}:5545"],
            'volumes': [
                f"{data_root}/.aspnet/pilot-server:/root/.aspnet",
                f"{data_root}/logs/pilot-server:/App/logs",
                f"{data_root}/pilot-server/settings:/usr/share/ascon/pilot-server/settings",
                f"{db_volume}:/usr/share/ascon/databases",
                f"{stack_path}/license:/usr/share/ASCON"
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
                f"{data_root}/.aspnet/pilot-bim-server:/root/.aspnet",
                f"{data_root}/logs/pilot-bim-server:/App/logs",
                f"{data_root}/pilot-bim-server:/usr/share/ASCON/Pilot-BIM-Server"
            ],
            'depends_on': ['pilot-server']
        }

    # Pilot-Web-Server
    if 'Pilot-Web-Server' in selected_components:
        db_name = None
        if hasattr(app, 'selected_demo_db') and app.selected_demo_db:
            db_name = app.selected_demo_db
        elif hasattr(app, 'existing_db_path') and app.existing_db_path:
            db_name = os.path.basename(os.path.dirname(app.existing_db_path))
        services['pilot-web-server'] = {
            'image': f"registry.ascon.ru/project/pilotdev/pilot/pilot-web-server:{image_tag}",
            'container_name': f"{stack_name}_pilot-web-server",
            'hostname': 'pilot-web-server',
            'restart': 'unless-stopped',
            'environment': {
                'PilotServer:Database': db_name or 'pilot-bim_ru',
                'PilotServer:Url': 'http://pilot-server:5545'
            },
            'ports': [f"{ports.get('Pilot-Web-Server', 5552)}:80"],
            'depends_on': ['pilot-server']
        }

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

    return {'services': services}

def write_compose_file(compose_dict, target_dir):
    file_path = os.path.join(target_dir, 'docker-compose.yml')
    with open(file_path, 'w') as f:
        yaml.dump(compose_dict, f, default_flow_style=False, sort_keys=False)
    return file_path