from flask import Flask, request, Response, stream_with_context, jsonify, render_template
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Piped API Instances (These are generally more reliable on Render than Invidious)
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",          # Primary API
    "https://piped-api.garudalinux.org",     # Backup
    "https://api.piped.io"                    # Backup
]

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

    for instance in PIPED_INSTANCES:
        try:
            # Piped API Endpoint
            api_url = f"{instance}/streams/{video_id}"
            
            response = requests.get(api_url, headers=HEADERS, timeout=10, verify=False)
            
            # Check if we got HTML (Error page) instead of JSON
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                print(f"⚠️ FAIL {instance}: Received HTML (Likely Blocked/Captcha)")
                continue

            if response.status_code == 200:
                data = response.json()
                
                # Piped separates video and audio streams. 
                # For a simple <video> tag to work with sound, we need a "Combined" stream (muxed).
                # Usually found in 'videoStreams' where 'videoOnly' is False.
                
                target_stream = None
                
                # Look for a non-videoOnly stream (contains audio)
                if 'videoStreams' in data:
                    for stream in data['videoStreams']:
                        # We want a stream that is NOT video only
                        if not stream.get('videoOnly', True):
                            target_stream = stream
                            break
                    
                    # Fallback: If no combined stream, take the first video-only one (User will hear no sound)
                    # This is better than nothing, but usually 360p/480p are combined.
                    if not target_stream and data['videoStreams']:
                        target_stream = data['videoStreams'][0]

                if target_stream:
                    print(f"✅ SUCCESS via {instance} (Format: {target_stream.get('quality', 'unknown')})")
                    return jsonify({
                        'title': data.get('title', 'Video'),
                        'stream_url': target_stream.get('url'),
                        'instance': instance
                    })
                else:
                    print(f"⚠️ FAIL {instance}: No playable streams found")
                    continue
                    
        except Exception as e:
            print(f"⚠️ FAIL {instance}: {str(e)}")
            continue

    return jsonify({'error': 'Piped API failed. Render Free Tier IPs might be rate-limited.'}), 500

@app.route('/proxy-video')
def proxy_video():
    video_url = request.args.get('url')
    if not video_url:
        return "No URL provided", 400

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
