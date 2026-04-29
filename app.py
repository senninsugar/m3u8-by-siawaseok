import subprocess
import os
import shutil
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_m3u8(url):
    YT_DLP_PATH = "yt-dlp"
    PROXY_URL = "http://other.siatube.com:3007"
    
    command = [
        YT_DLP_PATH,
        "--proxy", PROXY_URL,
        "--skip-download",
        "--no-check-certificate",
        "--youtube-include-hls-manifest",
        "--no-check-formats",
        "--no-cache-dir",
        "--no-playlist",
        "--ignore-config",
        "--extractor-args", "youtube:player_client=mweb,ios;skip=dash,hls",
        "--print", "%(formats.:.url)s",
        url
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            timeout=25
        )

        if result.returncode != 0:
            return {"error": "yt-dlp failed", "stderr": result.stderr}, 500

        all_urls = result.stdout.strip().split('\n')
        m3u8_urls = [u for u in all_urls if 'index.m3u8' in u or '/hls_playlist/' in u]

        if not m3u8_urls:
            return {"error": "m3u8 not found", "count": len(all_urls)}, 404

        return {
            "m3u8_urls": list(set(m3u8_urls))
        }, 200

    except subprocess.TimeoutExpired:
        return {"error": "Internal Timeout"}, 504
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/extract', methods=['GET'])
def extract():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "URL parameter is required"}), 400
    
    result, status_code = get_m3u8(video_url)
    return jsonify(result), status_code

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
