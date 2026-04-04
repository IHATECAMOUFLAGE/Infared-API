from flask import Flask, request, Response, stream_with_context, jsonify, render_template
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# THE GOLD STANDARD LIST
# These are the most stable instances that allow API access.
INSTANCES = [
    "https://yewtu.be",                # Most reliable public instance
    "https://invidious.kavin.rocks",   # Highly maintained
    "https://invidious.perennialte.ch",# Very stable
    "https://invidious.nerdvpn.de",    # Your preferred one (kept, but lower priority)
    "https://invidious.snopyta.org"    # Backup
]

# MODERN USER AGENT
# Using an old agent (Chrome 91) gets you blocked. Using a modern one helps.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-video-info', methods=['GET'])
def get_video_info():
    url = request.args.get('url')
    
    # Extract Video ID
    video_id = None
    if "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    for instance in INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            
            # Request with the Modern User Agent
            response = requests.get(api_url, headers=HEADERS, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('formatStreams'):
                    best_stream = data['formatStreams'][0]
                    print(f"✅ SUCCESS via {instance}")
                    return jsonify({
                        'title': data.get('title'),
                        'stream_url': best_stream.get('url'),
                        'instance': instance
                    })
                else:
                    print(f"⚠️ FAIL {instance}: No streams found")
                    continue
                    
        except requests.exceptions.SSLError:
            print(f"⚠️ FAIL {instance}: SSL Error")
            continue
        except Exception as e:
            print(f"⚠️ FAIL {instance}: {str(e)}")
            continue

    return jsonify({'error': 'Failed to fetch video. All top instances are busy or blocked.'}), 500

@app.route('/proxy-video')
def proxy_video():
    video_url = request.args.get('url')
    if not video_url:
        return "No URL provided", 400

    # Use modern headers for the proxy too
    headers = {
        **HEADERS,
        'Referer': 'https://www.youtube.com/',
        'Accept': '*/*',
    }

    req = requests.get(video_url, headers=headers, stream=True, verify=False)

    def generate():
        for chunk in req.iter_content(chunk_size=8192):
            yield chunk

    return Response(
        stream_with_context(generate()),
        content_type=req.headers.get('Content-Type'),
        headers={
            'Content-Disposition': 'inline; filename=video.mp4',
            'Accept-Ranges': 'bytes',
        }
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
