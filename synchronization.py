import subprocess
import threading
import time
import json
import re
import os


class StreamSynchronizer:
    def __init__(self, config):
        self.config = config
        self.ffmpeg_process = None
        self.monitor_thread = None
        self.running = False

        # Zustandsvariablen
        self.input1_active = False
        self.input2_active = False
        self.last_restart_time = 0

        # Pfade zu den Inputs
        self.input1_url = f"rtmp://localhost:{self.config['streams']['stream1']['port']}/{self.config['streams']['stream1']['app']}/{self.config['streams']['stream1']['key']}"
        self.input2_url = f"rtmp://localhost:{self.config['streams']['stream2']['port']}/{self.config['streams']['stream2']['app']}/{self.config['streams']['stream2']['key']}"

    def start(self):
        """Startet den Synchronisierungsprozess mit beiden Inputs, falls verfügbar."""
        self.running = True

        # Initial versuchen beide einzubinden
        self.start_ffmpeg(both=True)

        self.monitor_thread = threading.Thread(target=self.monitor_streams)
        self.monitor_thread.start()

    def start_ffmpeg(self, both=True):
        """Startet den FFmpeg-Prozess. Wenn both=True, werden beide Inputs verwendet.
           Ansonsten wird nur der verfügbare Input genutzt."""

        if self.ffmpeg_process is not None and self.ffmpeg_process.poll() is None:
            # Falls noch ein alter Prozess läuft, diesen beenden:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()

        # Basis-Command
        cmd = [self.config["ffmpeg_path"], "-y"]

        # Inputs definieren
        if both:
            cmd += ["-i", self.input1_url, "-i", self.input2_url]
            # Beispielhafter Filter:
            # Wir nehmen an, dass beide Inputs identische Inhalte haben, aber leicht asynchron sein können.
            # Mit 'asetpts' und 'aresample' kann man Audio leicht korrigieren, mit 'fifo' Frames puffern.
            # Dieses Beispiel versucht Video minimal zu puffer, um leichte Differenzen auszugleichen.
            filter_complex = (
                "[0:v]fifo[av0];"  # Puffert Video von Input 1 minimal
                "[1:v]fifo[av1];"  # Puffert Video von Input 2 minimal
                # Audio anpassen, falls nötig:
                "[0:a]aresample=async=1:first_pts=0[a0];"
                "[1:a]aresample=async=1:first_pts=0[a1];"
                # Hier könnte man noch komplexere Logik einbauen, z.B. anhand von Timestamps einen anpassen.
                # Für Demonstration: Wir nehmen einfach Input 1 als Hauptquelle. Sollte Input1 ausfallen, wollen wir auf Input2 umschalten.
                # Eine echte "Synchronisation" ist schwierig ohne gemeinsame Timecodes oder externe Signals.
                # Daher hier nur ein rudimentärer Merge: z. B. per 'amix' Audio mischen oder einfach nur erstes Audio nutzen.
                # Hier als Beispiel: Wenn beide da sind, nutzen wir einfach Input1, sonst Input2.
                # Da wir nicht wissen, ob Input1/2 gerade ausfallen, ist echte Laufzeitumschaltung schwierig.
                # Eine Idee: Nur Video von Input1, fallback auf Input2 bei Ausfall durch Prozessneustart.

                # Hier also nur Pass-Through von erstem Input:
                "[av0][a0]concat=n=1:v=1:a=1[outv][outa]"
            )
            # Der concat-Filter oben ist eigentlich redundant, da wir nur einen Input streamen.
            # Man könnte komplexere Filter implementieren, z.B.:
            # Ein Ansatz: Erstes Input ist Master, zweites Input wird ignoriert, es sei denn der erste fällt aus.
            # Die Umschaltung bei Ausfall erfolgt durch Prozessneustart, nicht im Filter selbst.

            cmd += [
                "-filter_complex", filter_complex,
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "copy", "-c:a", "aac",  # Kopiere Video, Audio enkodieren falls nötig
                "-f", "flv", self.config["external_rtmp_url"]
            ]
        else:
            # Nur ein Input (Fallback)
            active_input = self.input1_url if self.input1_active else self.input2_url
            cmd += [
                "-i", active_input,
                "-c:v", "copy", "-c:a", "aac",
                "-f", "flv", self.config["external_rtmp_url"]
            ]

        self.ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def monitor_streams(self):
        """Überwacht die Streams und FFmpeg.
        Erkennt Ausfälle, versucht diese zu beheben, und wechselt ggf. den Modus von dual-input zu single-input.
        """
        # Um festzustellen, ob Streams ausfallen, könnte man ffprobe oder die FFmpeg-Logs analysieren.
        # Hier ein vereinfachter Ansatz:
        # - Wir lesen ffmpeg stderr aus.
        # - Wenn sich ffmpeg beendet, versuchen wir neu zu starten.
        # - In regelmäßigen Intervallen prüfen wir zusätzlich mit ffprobe, ob die Inputs erreichbar sind.

        ffprobe_path = self.config["ffmpeg_path"].replace("ffmpeg", "ffprobe")
        if not os.path.isfile(ffprobe_path):
            ffprobe_path = "ffprobe"  # hoffen wir, dass es im PATH ist

        def check_input(url):
            # Prüft mit ffprobe, ob der Input erreichbar ist
            # Gibt True zurück, wenn Video/Audio Streams gefunden werden
            probe_cmd = [ffprobe_path, "-v", "error", "-show_entries", "stream=index", "-of", "json", url]
            try:
                probe_output = subprocess.check_output(probe_cmd, stderr=subprocess.STDOUT, text=True)
                if '"streams"' in probe_output:
                    return True
            except:
                pass
            return False

        # Warte kurz nach Start, damit FFmpeg anläuft
        time.sleep(5)

        while self.running:
            # Check ob Prozess noch läuft
            ret = self.ffmpeg_process.poll()
            if ret is not None:
                # Prozess beendet -> neu starten
                # Bevor wir neu starten, checken wir die Inputs
                self.input1_active = check_input(self.input1_url)
                self.input2_active = check_input(self.input2_url)

                if self.input1_active and self.input2_active:
                    # Beide verfügbar, also mit beiden neu starten
                    self.start_ffmpeg(both=True)
                else:
                    # Mindestens einer nicht verfügbar
                    if self.input1_active or self.input2_active:
                        # Nur ein Input verfügbar -> Single Mode
                        self.start_ffmpeg(both=False)
                    else:
                        # Keiner erreichbar -> Kurz warten und erneut versuchen
                        time.sleep(5)
                        continue

            # Wenn Prozess läuft, lesen wir ein Stück stderr aus, um Fehler/Ausfall zu erkennen
            # (Nicht-blockierend)
            line = self.ffmpeg_process.stderr.readline()
            if line:
                # Optional: Aus den Logs Fehler erkennen.
                # Wenn z.B. "Input #0 error" oder "Connection refused"
                # kann man Zustände aktualisieren. Hier ein grobes Beispiel:
                if "Connection refused" in line or "Input/output error" in line or "No route to host" in line:
                    # Einer der Inputs ist wohl ausgefallen
                    # Wir warten kurz und triggern dann einen Neustart
                    time.sleep(2)
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait()

                    self.input1_active = check_input(self.input1_url)
                    self.input2_active = check_input(self.input2_url)

                    # Neu starten je nach Verfügbarkeit
                    if self.input1_active and self.input2_active:
                        self.start_ffmpeg(both=True)
                    elif self.input1_active or self.input2_active:
                        self.start_ffmpeg(both=False)
                    else:
                        # Keine Inputs erreichbar, nochmal warten
                        time.sleep(5)
                        self.start_ffmpeg(
                            both=False)  # Startet mit einem Input, falls dieser nicht da ist, nächster Versuch später

            # Regelmäßige Input Checks
            # Alle 30 Sekunden Inputs checken, ob sich etwas verbessert hat
            # Falls nur einer genutzt wird und der zweite wieder da ist, neu starten mit beiden
            current_time = time.time()
            if current_time - self.last_restart_time > 30:
                self.last_restart_time = current_time
                was_one_input = not (self.input1_active and self.input2_active)
                self.input1_active = check_input(self.input1_url)
                self.input2_active = check_input(self.input2_url)
                if was_one_input and self.input1_active and self.input2_active:
                    # Jetzt sind wieder beide da, FFmpeg neu starten mit beiden
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait()
                    self.start_ffmpeg(both=True)

            time.sleep(2)

    def stop(self):
        self.running = False
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
        if self.monitor_thread:
            self.monitor_thread.join()
