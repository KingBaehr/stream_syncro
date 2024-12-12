import subprocess
import signal
import sys
import time
import json
import os
from synchronization import StreamSynchronizer
from flask import Flask
from webui.app import app as flask_app

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

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def main():
    config = load_config()
    generate_nginx_conf(config)
    nginx_conf = str(os.path.join(os.path.dirname(os.path.abspath(__file__)), config['nginx_conf_path']))

    # Nginx starten
    nginx_proc = subprocess.Popen([config['nginx_path'], '-c', nginx_conf])

    # Kurze Pause um sicherzustellen, dass Nginx läuft
    time.sleep(2)

    # Synchronizer starten
    sync = StreamSynchronizer(config)
    sync.start()

    # Flask Webserver starten (in diesem Beispiel einfach auf Port 8080)
    flask_app.run(host=config['webserver_host'], port=config['webserver_port'])

    # Sauberes Beenden wenn CTRL+C
    def signal_handler(sig, frame):
        sync.stop()
        nginx_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == "__main__":
    main()
