# preview_manager.py
import subprocess
import threading
import os
import time
import json

class PreviewManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.preview_procs = {}
        self.running = False
        self.thread = None
        self.ffmpeg_path = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))  # Directory dieses Scripts

    def load_config(self):
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def start(self):
        self.running = True
        # Thread um Änderungen an config zu erkennen und procs neuzustarten
        self.thread = threading.Thread(target=self.loop)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.stop_all_previews()

    def loop(self):
        # Checkt regelmäßig ob Config geändert wurde (alle 10 sek)
        # oder ob ein Prozess ausgefallen ist und neugestartet werden muss.
        old_config = None
        while self.running:
            cfg = self.load_config()
            if self.ffmpeg_path is None:
                self.ffmpeg_path = cfg.get('ffmpeg_path', 'ffmpeg')

            # Prüfe ob Preview-Einstellungen sich geändert haben
            new_preview_in1 = cfg.get('preview_in1', False)
            new_preview_in2 = cfg.get('preview_in2', False)
            new_preview_out = cfg.get('preview_out', False)

            # Starte/Stoppe je nach Bedarf
            self.update_preview('in1', new_preview_in1, cfg['streams']['stream1']['port'], cfg['streams']['stream1']['app'], cfg['streams']['stream1']['key'])
            self.update_preview('in2', new_preview_in2, cfg['streams']['stream2']['port'], cfg['streams']['stream2']['app'], cfg['streams']['stream2']['key'])
            # Für den Output ist der Input die externe RTMP-URL
            self.update_preview('out', new_preview_out, None, None, None, output_url=cfg['external_rtmp_url'])

            time.sleep(10)

    def update_preview(self, name, enable, port=None, app=None, key=None, output_url=None):
        """Startet oder stoppt je nach Enable-Flag den Preview Stream."""
        identifier = name
        if enable:
            if identifier not in self.preview_procs or self.preview_procs[identifier].poll() is not None:
                # Prozess starten
                self.start_preview(identifier, port, app, key, output_url)
        else:
            # Ausschalten falls läuft
            if identifier in self.preview_procs:
                self.preview_procs[identifier].terminate()
                self.preview_procs[identifier].wait()
                del self.preview_procs[identifier]

    def start_preview(self, identifier, port=None, app=None, key=None, output_url=None):
        # HLS-Verzeichnis erstellen wenn nötig
        hls_dir = os.path.join(self.base_dir, '..', 'hls', identifier)
        if not os.path.exists(hls_dir):
            os.makedirs(hls_dir, exist_ok=True)

        if identifier in ['in1','in2']:
            input_url = f"rtmp://localhost:{port}/{app}/{key}"
        else:
            # out
            input_url = output_url

        # ffmpeg-befehl um ein kleines 360p HLS daraus zu machen
        cmd = [
            self.ffmpeg_path,
            '-i', input_url,
            '-vf', 'scale=-2:360', # verkleinern auf ~360p
            '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'zerolatency', '-b:v', '800k',
            '-c:a', 'aac', '-b:a', '64k',
            '-f', 'hls',
            '-hls_time', '4',
            '-hls_playlist_type', 'event',
            '-hls_flags', 'delete_segments',
            '-hls_segment_filename', os.path.join(hls_dir, 'segment_%d.ts'),
            os.path.join(hls_dir, 'index.m3u8')
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.preview_procs[identifier] = proc

    def stop_all_previews(self):
        for p in self.preview_procs.values():
            p.terminate()
        for p in self.preview_procs.values():
            p.wait()
        self.preview_procs.clear()
