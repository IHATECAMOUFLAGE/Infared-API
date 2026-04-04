from flask import Flask, request, Response, stream_with_context, jsonify, render_template
import requests

app = Flask(__name__)

# We use a public Invidious instance. 
# If this one is down, you can swap it for another like: https://invidious.snopyta.org
INVIDIOUS_INSTANCE = "https://vid.puffyan.us"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-video-info', methods=['GET'])
def get_video_info():
    url = request.args.get('url')
    
    try:
        # Extract Video ID from URL (e.g., https://youtu.be/JFtlf8RoPZY -> JFtlf8RoPZY)
        if "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        else:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        # Ask Invidious for the video data
        # No cookies needed here!
        api_url = f"{INVIDIOUS_INSTANCE}/api/v1/videos/{video_id}"
        response = requests.get(api_url)
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch video info from Invidious'}), 500

        data = response.json()

        # Invidious returns 'formatStreams' which contains combined video+audio URLs
        # We pick the first one (usually the best quality for that container)
        if not data.get('formatStreams'):
             return jsonify({'error': 'No video streams found'}), 500

        best_stream = data['formatStreams'][0]
        
        return jsonify({
            'title': data.get('title'),
            'stream_url': best_stream.get('url')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/proxy-video')
def proxy_video():
    # The proxy logic remains the same to hide the Referer
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
