from flask import Flask, request, Response, stream_with_context, jsonify
import yt_dlp
import requests

app = Flask(__name__)

@app.route('/get-video-info', methods=['GET'])
def get_video_info():
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
                'stream_url': info.get('url')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

    req = requests.get(video_url, headers=headers, stream=True)

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
