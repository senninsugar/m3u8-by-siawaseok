import express from "express";
import { execFile } from "child_process";

const app = express();

const YT_DLP_PATH = "./yt-dlp";
const PROXY = "http://other.siatube.com:3007";

// yt-dlp実行
function getM3U8(url) {
  return new Promise((resolve, reject) => {
    execFile(
      YT_DLP_PATH,
      [
        "--js-runtimes", "node",
        "--proxy", PROXY,
        "-J",
        "--skip-download",
        "--no-playlist",
        "--no-progress",
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
          const formats = data.formats || [];

          // m3u8だけ抽出
          const m3u8 = formats
            .map(f => f.url)
            .filter(u => u && u.includes(".m3u8"));

          resolve({
            formats: m3u8,
            total_urls: m3u8.length
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
  const video_url = req.query.url;

  if (!video_url) {
    return res.status(400).json({
      error: "URL parameter is required"
    });
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
