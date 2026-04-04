import os
import requests
import yt_dlp
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)

# Configuration for yt-dlp
YDL_OPTS = {
    'format': 'best[ext=mp4]/best',
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {'youtube': {'player_client': ['android']}},
    'cookiefile': 'cookies.txt', # This tells it to use the public file you just added
}

@app.route('/watch')
def watch():
    video_url = request.args.get('url')
    
    if not video_url:
        return "Error: Please provide a ?url= parameter", 400

    try:
        # 1. Get the direct video URL from YouTube
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_url_direct = info['url']
        
        # 2. Request the video data from YouTube
        # We pass the 'Range' header so users can skip/seek the video
        headers = {}
        if 'Range' in request.headers:
            headers['Range'] = request.headers['Range']

        req = requests.get(video_url_direct, headers=headers, stream=True)

        # 3. Stream the data back to the user
        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            content_type=req.headers['Content-Type'],
            headers={
                'Content-Length': req.headers.get('Content-Length'),
                'Accept-Ranges': 'bytes',
            }
        )

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
