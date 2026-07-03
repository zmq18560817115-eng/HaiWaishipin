"""
TikTok 采集器 - 网页版 UI
启动后访问 http://0.0.0.0:8890 即可使用
"""
import subprocess, sys, os, json, glob, pathlib
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="TikTok 采集器")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROJECT_ROOT = pathlib.Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"

class CollectRequest(BaseModel):
    keywords: List[str]
    limit_per_keyword: int = 20

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE

@app.post("/collect")
async def collect(req: CollectRequest):
    cmd = [
        sys.executable, "-m", "tiktok_collector.main", "collect",
        "--keywords", *req.keywords,
        "--limit", str(req.limit_per_keyword),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=600)
        return JSONResponse({
            "success": result.returncode == 0,
            "stdout": result.stdout[-3000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
        })
    except subprocess.TimeoutExpired:
        return JSONResponse({"success": False, "error": "采集超时（10分钟）"}, status_code=504)

@app.get("/results")
async def list_results():
    files = sorted(DATA_DIR.glob("*.json"), reverse=True)[:20]
    return [{"name": f.name, "size": f.stat().st_size} for f in files]

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TikTok 采集器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,system-ui,sans-serif;background:#f5f5f5;min-height:100vh;display:flex;justify-content:center;padding:40px 20px}
.container{max-width:700px;width:100%}
h1{font-size:24px;margin-bottom:8px;color:#333}
.subtitle{color:#888;margin-bottom:24px;font-size:14px}
.card{background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:20px}
label{display:block;font-weight:600;margin-bottom:6px;color:#555;font-size:14px}
textarea{width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:14px;resize:vertical;min-height:80px}
textarea:focus{outline:none;border-color:#4f46e5;box-shadow:0 0 0 3px rgba(79,70,229,.1)}
input[type=number]{padding:10px 12px;border:1px solid #ddd;border-radius:8px;width:100px;font-size:14px}
.btn{background:#4f46e5;color:#fff;border:none;padding:12px 28px;border-radius:8px;font-size:15px;cursor:pointer;margin-top:16px;font-weight:600}
.btn:hover{background:#4338ca}
.btn:disabled{background:#a5a5a5;cursor:not-allowed}
.result{margin-top:16px;padding:16px;border-radius:8px;font-size:13px;white-space:pre-wrap;word-break:break-all;max-height:400px;overflow-y:auto;display:none}
.result.ok{background:#f0fdf4;border:1px solid #86efac;color:#166534;display:block}
.result.err{background:#fef2f2;border:1px solid #fca5a5;color:#991b1b;display:block}
.spinner{display:inline-block;width:16px;height:16px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;animation:spin .6s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="container">
<h1>🎬 TikTok 采集器</h1>
<p class="subtitle">输入关键词，自动抓取 TikTok 公开视频元数据</p>
<div class="card">
<label>关键词（每行一个）</label>
<textarea id="kw" placeholder="wearable breast pump&#10;manual breast pump&#10;baby bottle"></textarea>
<label style="margin-top:12px">每个关键词抓取数量</label>
<input type="number" id="limit" value="20" min="1" max="100">
<br><button class="btn" id="btn" onclick="startCollect()">开始采集</button>
<div class="result" id="result"></div>
</div>
</div>
<script>
async function startCollect(){
const kw=document.getElementById('kw').value.trim().split('\\n').map(s=>s.trim()).filter(Boolean);
if(!kw.length){alert('请输入至少一个关键词');return}
const btn=document.getElementById('btn');
const res=document.getElementById('result');
btn.disabled=true;btn.innerHTML='<span class="spinner"></span>采集中，请稍候…';
res.className='result';res.textContent='';
try{
const r=await fetch('/collect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keywords:kw,limit_per_keyword:+document.getElementById('limit').value})});
const d=await r.json();
res.className='result '+(d.success?'ok':'err');
res.textContent=d.success?('✅ 采集完成！\\n\\n'+d.stdout):('❌ 采集失败\\n\\n'+(d.stderr||d.error||'未知错误'));
}catch(e){res.className='result err';res.textContent='请求失败: '+e.message}
finally{btn.disabled=false;btn.innerHTML='开始采集'}
}
</script>
</body></html>"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8890)
