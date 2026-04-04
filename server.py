from flask import Flask, request, Response, stream_with_context, jsonify, render_template
import requests
import urllib3

# Disable SSL warnings for the console logs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Fresh list of instances known to be relatively stable
INSTANCES = [
    "https://invidious.perennialte.ch",
    "https://yewtu.be",
    "https://inv.citruslimes.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.fdn.fr",
    "https://invidious.slipfox.xyz"
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-video-info', methods=['GET'])
def get_video_info():
    url = request.args.get('url')
    
    video_id = None
    if "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    # Loop through instances
    for instance in INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            
            # KEY CHANGES HERE:
            # 1. timeout=15 (Wait longer for slow servers)
            # 2. verify=False (Ignore SSL certificate errors)
            response = requests.get(api_url, timeout=15, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('formatStreams'):
                    best_stream = data['formatStreams'][0]
                    print(f"SUCCESS: Used instance {instance}") # This prints to Render Logs
                    return jsonify({
                        'title': data.get('title'),
                        'stream_url': best_stream.get('url'),
                        'instance': instance
                    })
                else:
                    print(f"FAIL {instance}: No streams found in response")
                    continue
                    
        except requests.exceptions.Timeout:
            print(f"FAIL {instance}: Timed out (server too slow)")
            continue
        except requests.exceptions.SSLError:
            print(f"FAIL {instance}: SSL Error")
            continue
        except Exception as e:
            print(f"FAIL {instance}: {str(e)}")
            continue

    return jsonify({'error': 'All instances failed. Check Render Logs for details.'}), 500

@app.route('/proxy-video')
def proxy_video():
    video_url = request.args.get('url')
    
    if not video_url:
        return "No URL provided", 400

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.youtube.com/',
        'Accept': '*/*',
    }

    try:
        req = requests.get(video_url, headers=headers, stream=True, verify=False)
    except Exception as e:
        return f"Proxy Error: {str(e)}", 500

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
