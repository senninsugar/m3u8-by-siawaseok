import express from "express";
import { execFile } from "child_process";

const app = express();

const YT_DLP_PATH = "./yt-dlp";
const PROXY = "http://ytproxy-siawaseok.duckdns.org:3007";

// yt-dlp実行
function getM3U8(url) {
  return new Promise((resolve, reject) => {
    execFile(
      YT_DLP_PATH,
      [
        "--js-runtimes", "node",
        "--proxy", PROXY,
        "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "-J",
        "--skip-download",
        "--no-playlist",
        "--no-progress",
        "--flat-playlist", // 高速化：リスト全体を解析しない
        "--no-check-certificates", // 高速化：SSLチェックをスキップ
        url
      ],
      { maxBuffer: 1024 * 1024 * 10 },
      (error, stdout, stderr) => {
        if (error) {
          return reject({
            error: "yt-dlp failed",
            stderr: stderr || error.message
          });
        }

        try {
          const data = JSON.parse(stdout);
          const formatsRaw = data.formats || [];

          // 画質、フォーマット、itag(format_id)を含めて抽出
          const formats = formatsRaw
            .filter(f => f.url && f.url.includes(".m3u8"))
            .map(f => ({
              itag: f.format_id,
              url: f.url,
              ext: f.ext,
              resolution: f.resolution || `${f.width}x${f.height}`,
              vcodec: f.vcodec,
              acodec: f.acodec,
              format_note: f.format_note,
              filesize_approx: f.filesize_approx
            }));

          resolve({
            title: data.title,
            thumbnail: data.thumbnail,
            formats: formats,
            total_urls: formats.length
          });

        } catch (e) {
          reject({
            error: "JSON parse failed",
            detail: String(e)
          });
        }
      }
    );
  });
}

// API
app.get("/extract", async (req, res) => {
  let video_url = req.query.url;

  if (!video_url) {
    return res.status(400).json({
      error: "URL parameter is required"
    });
  }

  // 動画ID(11桁かつURL形式でない)の場合、YouTubeのURLに変換
  if (!video_url.includes("://") && video_url.length === 11) {
    video_url = `https://www.youtube.com/watch?v=${video_url}`;
  }

  try {
    const result = await getM3U8(video_url);
    return res.json(result);
  } catch (e) {
    return res.status(500).json(e);
  }
});

// health check
app.get("/", (req, res) => {
  res.json({ status: "ok" });
});

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {
  console.log("Server running on port", PORT);
});
