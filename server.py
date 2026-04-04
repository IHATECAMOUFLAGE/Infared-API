import os
import requests
import yt_dlp
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)

# Configuration for yt-dlp to get the direct stream URL
# We specifically look for mp4 format for best browser compatibility
YDL_OPTS = {
    'format': 'best[ext=mp4]/best',
    'quiet': True,
    'no_warnings': True,
}

@app.route('/watch')
def watch():
    video_url = request.args.get('url')
    
    if not video_url:
        return "Error: No URL provided", 400

    try:
        # 1. Extract info using yt-dlp
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_url_direct = info['url']
            
        # 2. Prepare the request to YouTube
        # We pass the user's range headers (for seeking/scrubbing) to YouTube
        headers = {}
        if 'Range' in request.headers:
            headers['Range'] = request.headers['Range']

        # 3. Stream the content from YouTube to your client
        # stream=True ensures we don't download the whole video to RAM first
        req = requests.get(video_url_direct, headers=headers, stream=True)

        # 4. Generate the response
        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            content_type=req.headers['Content-Type'],
            headers={
                'Content-Length': req.headers.get('Content-Length'),
                'Accept-Ranges': 'bytes', # Important for video seeking
            }
        )

    except Exception as e:
        return f"Error processing video: {str(e)}", 500

if __name__ == '__main__':
    # Render sets the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
