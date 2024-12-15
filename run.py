# run.py
import subprocess
import signal
import sys
import time
import json
import os
from synchronization import StreamSynchronizer
from preview_manager import PreviewManager
from status_manager import StatusManager
from webui.app import app as flask_app
from threading import Thread

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def generate_nginx_conf(config):
    base_dir = str(os.path.join(os.path.dirname(os.path.abspath(__file__))))
    nginx_conf = str(base_dir + config['nginx_conf_path'])
    auth_check_path_full = str(base_dir + config['auth_check_path'])
    with open("nginx.conf.template", "r") as f:
        template = f.read()
    conf = template.replace('{{stream1_port}}', str(config['streams']['stream1']['port']))
    conf = conf.replace('{{stream1_app}}', config['streams']['stream1']['app'])
    conf = conf.replace('{{stream1_key}}', config['streams']['stream1']['key'])
    conf = conf.replace('{{stream2_port}}', str(config['streams']['stream2']['port']))
    conf = conf.replace('{{stream2_app}}', config['streams']['stream2']['app'])
    conf = conf.replace('{{stream2_key}}', config['streams']['stream2']['key'])
    conf = conf.replace('{{final_app_name}}', config['final_app_name'])
    conf = conf.replace('{{auth_check_path}}', auth_check_path_full)

    with open(nginx_conf, 'w') as f:
        f.write(conf)

config = load_config()
generate_nginx_conf(config)

# Nginx starten
nginx_conf = str(os.path.join(os.path.dirname(os.path.abspath(__file__)), config['nginx_conf_path']))
nginx_proc = subprocess.Popen([config['nginx_path'], '-c', nginx_conf])
time.sleep(2)

# Synchronisierung starten
sync = StreamSynchronizer(config)
sync.start()

# Preview Manager starten (HLS-Previews)
preview_manager = PreviewManager("config.json")
preview_manager.start()

# Status Manager starten
status_manager = StatusManager("config.json")
status_manager.start()

# Flask in separatem Thread starten
def run_flask():
    flask_app.run(host=config['webserver_host'], port=config['webserver_port'])

flask_thread = Thread(target=run_flask)
flask_thread.start()

def signal_handler(sig, frame):
    sync.stop()
    preview_manager.stop()
    status_manager.stop()
    nginx_proc.terminate()
    nginx_proc.wait()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.pause()
