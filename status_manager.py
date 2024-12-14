# status_manager.py
import threading
import time
import subprocess
import os
import json


class StatusManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.running = False
        self.status = {
            'in1': 'red',
            'in2': 'red',
            'out': 'red'
        }
        self.lock = threading.Lock()
        self.thread = None
        self.ffprobe_path = 'ffprobe'  # Pfad anpassen falls nötig

    def load_config(self):
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.loop)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def loop(self):
        while self.running:
            self.check_all_status()
            time.sleep(5)  # alle 5 Sekunden Status aktualisieren

    def check_all_status(self):
        cfg = self.load_config()
        input1_url = f"rtmp://localhost:{cfg['streams']['stream1']['port']}/{cfg['streams']['stream1']['app']}/{cfg['streams']['stream1']['key']}"
        input2_url = f"rtmp://localhost:{cfg['streams']['stream2']['port']}/{cfg['streams']['stream2']['app']}/{cfg['streams']['stream2']['key']}"
        output_url = cfg['external_rtmp_url']

        # Statusbestimmung durch ffprobe
        # green = erreichbar, live
        # yellow = erreichbar, aber Probleme (z. B. kein Audio/Video)
        # red = nicht erreichbar

        def check_stream(url):
            try:
                # ffprobe gibt bei funktionierendem Stream mindestens einen Video/Audio-Stream zurück
                cmd = [self.ffprobe_path, "-v", "quiet", "-print_format", "json", "-show_streams", url]
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
                data = json.loads(result)
                if 'streams' in data and len(data['streams']) > 0:
                    # Einfacher Check: wenn mindestens ein Video/Audio-Stream vorhanden ist, ist Status green
                    return 'green'
                else:
                    # Keine Streams gefunden -> rot
                    return 'red'
            except subprocess.CalledProcessError:
                return 'red'
            except:
                return 'red'

        in1_status = check_stream(input1_url)
        in2_status = check_stream(input2_url)
        out_status = check_stream(output_url)

        # Man könnte hier weitere Logik einfügen, um 'yellow' zu bestimmen,
        # z. B. wenn Lags, niedrige Bitrate, etc. erkannt werden.
        # Für dieses Beispiel bleibt es einfach: erreichbar => green, sonst red.
        # Als Beispiel: Wenn erreichbar aber nur 1 Streamtyp => yellow:
        # (Nur als Demonstration, hier bleiben wir bei green/red)

        with self.lock:
            self.status['in1'] = in1_status
            self.status['in2'] = in2_status
            self.status['out'] = out_status

    def get_status(self):
        with self.lock:
            return dict(self.status)
