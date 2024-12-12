from flask import Flask, request, redirect, url_for, render_template, session
import json, os

app = Flask(__name__)
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
    return '''
    <form method="post">
      User: <input name="username"><br>
      Pass: <input name="password" type="password"><br>
      <input type="submit" value="Login">
    </form>
    '''

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    cfg = load_config()
    if request.method == 'POST':
        # Aktualisieren der Konfigurationswerte
        cfg['external_rtmp_url'] = request.form.get('external_rtmp_url', cfg['external_rtmp_url'])
        cfg['streams']['stream1']['port'] = int(request.form.get('stream1_port', cfg['streams']['stream1']['port']))
        cfg['streams']['stream1']['key'] = request.form.get('stream1_key', cfg['streams']['stream1']['key'])
        cfg['streams']['stream2']['port'] = int(request.form.get('stream2_port', cfg['streams']['stream2']['port']))
        cfg['streams']['stream2']['key'] = request.form.get('stream2_key', cfg['streams']['stream2']['key'])
        save_config(cfg)
        # Evtl. Nginx/FFmpeg neu starten
        return redirect(url_for('settings'))
    return f'''
    <form method="post">
      External RTMP URL: <input name="external_rtmp_url" value="{cfg['external_rtmp_url']}"><br>
      Stream1 Port: <input name="stream1_port" value="{cfg['streams']['stream1']['port']}"><br>
      Stream1 Key: <input name="stream1_key" value="{cfg['streams']['stream1']['key']}"><br>
      Stream2 Port: <input name="stream2_port" value="{cfg['streams']['stream2']['port']}"><br>
      Stream2 Key: <input name="stream2_key" value="{cfg['streams']['stream2']['key']}"><br>
      <input type="submit" value="Save">
    </form>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
