#!/bin/bash

# Farbeinstellungen für die Anzeige
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Willkommen zum Installationsskript für das Stream-Sync-Projekt.${NC}"
echo -e "${YELLOW}Dieses Skript wird alle notwendigen Module und Konfigurationen einrichten.${NC}"

# Root-Prüfung
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Dieses Skript muss als Root ausgeführt werden! Bitte verwenden Sie 'sudo'.${NC}"
    exit 1
fi

# Abfrage des Webinterface-Ports mit Standardwert
read -p "Bitte geben Sie den gewünschten Port für das Webinterface an [Standard: 8000]: " WEBSERVER_PORT
WEBSERVER_PORT=${WEBSERVER_PORT:-8000}

# Abfrage des Admin-Passworts mit Standardwert
read -p "Möchten Sie das Standardpasswort für den Benutzer 'admin' beibehalten? (y/n) [Standard: y]: " CHANGE_PASSWORD
CHANGE_PASSWORD=${CHANGE_PASSWORD:-y}
if [[ "$CHANGE_PASSWORD" =~ ^[Nn]$ ]]; then
    read -sp "Bitte geben Sie ein neues Passwort für den Benutzer 'admin' ein: " NEW_PASSWORD
    echo ""
    read -sp "Bitte bestätigen Sie das neue Passwort: " CONFIRM_PASSWORD
    echo ""
    if [ "$NEW_PASSWORD" != "$CONFIRM_PASSWORD" ]; then
        echo -e "${RED}Die Passwörter stimmen nicht überein. Bitte starten Sie das Skript erneut.${NC}"
        exit 1
    fi
else
    NEW_PASSWORD="admin"
fi

# Update und grundlegende Pakete installieren
echo -e "${GREEN}Aktualisiere Paketliste und installiere grundlegende Pakete...${NC}"
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv build-essential libpcre3 libpcre3-dev zlib1g zlib1g-dev openssl libssl-dev git ffmpeg curl

# NGINX RTMP-Modul installieren
echo -e "${GREEN}Installiere und konfiguriere NGINX mit RTMP-Modul...${NC}"
cd /usr/local/src
git clone https://github.com/arut/nginx-rtmp-module.git
wget http://nginx.org/download/nginx-1.25.2.tar.gz
tar -zxvf nginx-1.25.2.tar.gz
cd nginx-1.25.2
./configure --add-module=../nginx-rtmp-module --with-http_ssl_module
make
make install

# Überprüfen der Installation
if [ -x "/usr/local/nginx/sbin/nginx" ]; then
    echo -e "${GREEN}NGINX erfolgreich installiert!${NC}"
else
    echo -e "${RED}Fehler bei der NGINX-Installation.${NC}"
    exit 1
fi

# Python virtuelle Umgebung einrichten
echo -e "${GREEN}Erstelle Python-Umgebung und installiere benötigte Bibliotheken...${NC}"
cd /opt
mkdir stream_sync && cd stream_sync
python3 -m venv stream_sync_env
source stream_sync_env/bin/activate
pip install flask gunicorn jinja2 requests pyyaml

# Konfigurationsdateien vorbereiten
echo -e "${GREEN}Kopiere Konfigurationsdateien und setze Berechtigungen...${NC}"
cat <<EOF > /usr/local/nginx/conf/nginx.conf
$(cat /mnt/data/nginx_modified.conf)
EOF

cat <<EOF > /opt/stream_sync/config.json
{
  "external_rtmp_url": "rtmp://youtube.com/live2/STREAMKEY",
  "streams": {
    "stream1": {
      "port": 1935,
      "app": "live",
      "key": "secret1"
    },
    "stream2": {
      "port": 1936,
      "app": "live",
      "key": "secret2"
    }
  },
  "auth_user": "admin",
  "auth_password": "${NEW_PASSWORD}",
  "ffmpeg_path": "/usr/bin/ffmpeg",
  "nginx_path": "/usr/local/nginx/sbin/nginx",
  "nginx_conf_path": "/usr/local/nginx/conf/nginx.conf",
  "final_app_name": "final",
  "auth_check_path": "/auth_check.py",
  "webserver_host": "0.0.0.0",
  "webserver_port": ${WEBSERVER_PORT}
}
EOF

# Dienste starten und konfigurieren
echo -e "${GREEN}Starte und aktiviere NGINX...${NC}"
/usr/local/nginx/sbin/nginx

# Skript zusammenfassen
echo -e "${GREEN}Installation abgeschlossen!${NC}"
echo -e "${YELLOW}Hinweise:${NC}"
echo -e "1. NGINX ist unter /usr/local/nginx/sbin/nginx verfügbar."
echo -e "2. Python Web-Server kann durch Aufruf von 'python3 app.py' in '/opt/stream_sync' gestartet werden."
echo -e "3. Das Webinterface läuft auf Port ${WEBSERVER_PORT}."
echo -e "4. Das Passwort für den Benutzer 'admin' lautet: ${NEW_PASSWORD}."
echo -e "5. Bitte die 'config.json' anpassen, falls nötig."

exit 0
