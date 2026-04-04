from flask import Flask, request, Response, stream_with_context, jsonify, render_template
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Instances known to work better on Cloud-hosted environments
# 'privacydev.net' is specifically maintained for this use case.
INSTANCES = [
    "https://api.piped.privacydev.net", # Best bet for Render/Vercel
    "https://piped-api.lunar.icu",
    "https://piped-api.adminforge.de",
    "https://pipedapi.kavin.rocks"      # Kept as last resort
]

# STEALTH HEADERS
# These headers mimic a real Chrome browser exactly. 
# Without 'sec-ch-ua', Cloudflare blocks the request immediately.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://piped.privacydev.net/',
    'Origin': 'https://piped.privacydev.net',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
}

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

    for instance in INSTANCES:
        try:
            # Note: We use the stealth HEADERS defined above
            api_url = f"{instance}/streams/{video_id}"
            
            response = requests.get(api_url, headers=HEADERS, timeout=10, verify=False)
            
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                print(f"⚠️ BLOCKED {instance}: Received HTML/Captcha")
                continue

            if response.status_code == 200:
                data = response.json()
                
                # Logic to find a stream with Audio
                target_stream = None
                
                if 'videoStreams' in data:
                    # Try to find a stream with audio
                    for stream in data['videoStreams']:
                        if not stream.get('videoOnly', True):
                            target_stream = stream
                            break
                    
                    # Fallback to video only if no combined stream
                    if not target_stream and data['videoStreams']:
                        target_stream = data['videoStreams'][0]

                if target_stream:
                    print(f"✅ SUCCESS via {instance}")
                    return jsonify({
                        'title': data.get('title', 'Video'),
                        'stream_url': target_stream.get('url'),
                        'instance': instance
                    })
                else:
                    print(f"⚠️ FAIL {instance}: No streams")
                    continue
                    
        except Exception as e:
            print(f"⚠️ FAIL {instance}: {str(e)}")
            continue

    return jsonify({'error': 'All instances blocked or offline. Render Free Tier IPs are heavily restricted.'}), 500

@app.route('/proxy-video')
def proxy_video():
    video_url = request.args.get('url')
    if not video_url:
        return "No URL provided", 400

    headers = {
        **HEADERS, # Use the stealth headers here too
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
