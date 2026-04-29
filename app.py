import subprocess
import json
import os
import shutil
import sys
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_m3u8(url):
    YT_DLP_PATH = "yt-dlp"
    PROXY_URL = "http://other.siatube.com:3007"
    
    node_path = shutil.which("node")
    
    command = [
        YT_DLP_PATH,
        "--js-runtimes", "node",
        "--proxy", PROXY_URL,
        "-J",
        "--skip-download",
        "--no-progress",
        "--youtube-include-hls-manifest",
        "--no-check-certificate",
        "-f", "hls-fastly/hls-akamai/hls/bestvideo+bestaudio/best",
        url
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            timeout=60
        )

        if result.returncode != 0:
            return {"error": "yt-dlp execution failed", "stderr": result.stderr}, 500

        if not result.stdout or not result.stdout.strip():
            return {"error": "No output from yt-dlp", "stderr": result.stderr}, 500

        data = json.loads(result.stdout)
        formats = data.get("formats", [])
        
        m3u8_urls = []
        
        for f in formats:
            f_url = f.get('url', '')
            protocol = f.get('protocol', '')
            
            if 'm3u8' in protocol or 'hls' in protocol or 'manifest' in f_url or '.m3u8' in f_url:
                m3u8_urls.append({
                    "format_id": f.get("format_id"),
                    "resolution": f.get("resolution"),
                    "url": f_url,
                    "protocol": protocol,
                    "ext": f.get("ext")
                })

        if not m3u8_urls:
            hls_manifest_url = data.get('url')
            if hls_manifest_url and ('manifest' in hls_manifest_url or '.m3u8' in hls_manifest_url):
                m3u8_urls.append({
                    "format_id": "direct_manifest",
                    "url": hls_manifest_url
                })

        return {
            "title": data.get("title"),
            "m3u8_urls": m3u8_urls
        }, 200

    except subprocess.TimeoutExpired:
        return {"error": "yt-dlp timed out"}, 504
    except json.JSONDecodeError:
        return {"error": "Failed to parse yt-dlp output", "raw": result.stdout[:500]}, 500
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
