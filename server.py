from flask import Flask, request, Response, stream_with_context
import yt_dlp
import requests

app = Flask(__name__)

@app.route('/get-video-info', methods=['GET'])
def get_video_info():
    """Gets the metadata and the direct stream URL from YouTube"""
    url = request.args.get('url')
    
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title'),
                # We return the direct GoogleVideo URL
                'stream_url': info.get('url')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy-video')
def proxy_video():
    """
    The browser requests this route.
    This route requests the video from YouTube (spoofing the referer)
    and pipes the data back to the browser.
    """
    video_url = request.args.get('url')

    if not video_url:
        return "No URL provided", 400

    # 1. Define the headers to send to YouTube
    # We pretend we are a normal browser on youtube.com
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.youtube.com/',  # This spoofs the origin
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }

    # 2. Request the video from YouTube using your Server's IP
    req = requests.get(video_url, headers=headers, stream=True)

    # 3. Stream the content back to the user
    # This ensures YouTube sees the request coming from your server, not the user's browser
    def generate():
        for chunk in req.iter_content(chunk_size=8192):
            yield chunk

    return Response(
        stream_with_context(generate()),
        content_type=req.headers.get('Content-Type'),
        headers={
            # We can optionally force the filename to download or play inline
            'Content-Disposition': 'inline; filename=video.mp4',
            'Accept-Ranges': 'bytes',
        }
    )

if __name__ == '/proxy-video':
    app.run(debug=True, port=5000)
