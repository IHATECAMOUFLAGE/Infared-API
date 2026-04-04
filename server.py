from flask import Flask, request, Response, stream_with_context, jsonify, render_template
import requests

app = Flask(__name__)

# List of Invidious instances to try.
# Your requested instance is first. If it fails, it tries the others automatically.
INSTANCES = [
    "https://invidious.nerdvpn.de",
    "https://yewtu.be",
    "https://invidious.fdn.fr",
    "https://inv.bp.projectsegfau.lt",
    "https://invidious.io",
    "https://vid.puffyan.us"
]

@app.route('/')
def home():
    """Serves the HTML page"""
    return render_template('index.html')

@app.route('/get-video-info', methods=['GET'])
def get_video_info():
    """
    Gets video metadata (title, stream URL) from Invidious.
    Loops through instances until one responds successfully.
    """
    url = request.args.get('url')
    
    # 1. Extract Video ID from various URL formats
    video_id = None
    if "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    # 2. Try fetching from instances
    for instance in INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            
            # Timeout of 5 seconds ensures we don't wait for dead servers
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if streams exist
                if data.get('formatStreams'):
                    best_stream = data['formatStreams'][0]
                    return jsonify({
                        'title': data.get('title'),
                        'stream_url': best_stream.get('url'),
                        'instance': instance # Optional: helps debug which one worked
                    })
                
        except requests.exceptions.RequestException:
            # Connection failed (Timeout, DNS error, etc.), try next instance
            continue
        except Exception:
            # JSON decode error or other issue, try next instance
            continue

    return jsonify({'error': 'All Invidious instances failed to respond.'}), 500

@app.route('/proxy-video')
def proxy_video():
    """
    Proxies the video stream.
    The browser requests this route, and this route requests the video from GoogleVideo.
    This hides the user's IP and Referer from YouTube.
    """
    video_url = request.args.get('url')
    
    if not video_url:
        return "No URL provided", 400

    # Headers to send to YouTube to pretend we are a normal browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.youtube.com/',
        'Accept': '*/*',
    }

    # Request the video stream
    req = requests.get(video_url, headers=headers, stream=True)

    # Generator function to stream chunks to the browser
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
