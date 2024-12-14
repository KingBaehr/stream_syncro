from flask import Flask, request, redirect, url_for, render_template, session, jsonify, send_from_directory
import json, os

app = Flask(__name__, static_folder=None)
app.secret_key = 'some_secret_key'

# Pfad zur config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.json')

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=4)

@app.route('/', methods=['GET', 'POST'])
def login():
    config = load_config()
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        if user == config.get('auth_user') and pw == config.get('auth_password'):
            session['logged_in'] = True
            return redirect(url_for('settings'))
        else:
            return "Login failed", 403
    return render_template('login.html')


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    cfg = load_config()

    if request.method == 'POST':
        external_server = request.form.get('external_server', cfg['external_rtmp_url'])
        external_key = request.form.get('external_key', '')

        if not external_server.endswith('/'):
            external_server += '/'
        final_rtmp = external_server + external_key

        cfg['external_rtmp_url'] = final_rtmp
        cfg['streams']['stream1']['port'] = int(request.form.get('stream1_port', cfg['streams']['stream1']['port']))
        cfg['streams']['stream1']['key'] = request.form.get('stream1_key', cfg['streams']['stream1']['key'])
        cfg['streams']['stream2']['port'] = int(request.form.get('stream2_port', cfg['streams']['stream2']['port']))
        cfg['streams']['stream2']['key'] = request.form.get('stream2_key', cfg['streams']['stream2']['key'])

        cfg['preview_in1'] = (request.form.get('preview_in1') == 'on')
        cfg['preview_in2'] = (request.form.get('preview_in2') == 'on')
        cfg['preview_out'] = (request.form.get('preview_out') == 'on')

        save_config(cfg)
        return redirect(url_for('settings'))

    # Status wird jetzt via AJAX abgefragt, hier erstmal Dummy für Initial-Load
    stream_status = {
        'in1': 'red',
        'in2': 'red',
        'out': 'red'
    }

    external_server, external_key = extract_server_and_key(cfg['external_rtmp_url'])

    return render_template('settings.html', config=cfg, stream_status=stream_status,
                           external_server=external_server, external_key=external_key)

def extract_server_and_key(url):
    if '//' in url:
        parts = url.split('//',1)
        protocol = parts[0]+'//'
        rest = parts[1]
        subparts = rest.split('/', 2)
        if len(subparts) == 3:
            server = protocol + subparts[0] + '/' + subparts[1] + '/'
            key = subparts[2]
            return server, key
    return url, ''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/hls/<path:filename>')
def hls_files(filename):
    # Streamen von HLS-Dateien aus dem hls-Verzeichnis
    hls_path = os.path.join(os.path.dirname(__file__), '..', 'hls')
    return send_from_directory(hls_path, filename)

@app.route('/status')
def status():
    # AJAX-Endpunkt für den Stream-Status
    # Der StatusManager wird vom Hauptprogramm bereitgestellt
    from run import status_manager
    st = status_manager.get_status()
    return jsonify(st)