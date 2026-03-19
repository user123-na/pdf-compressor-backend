import os
import uuid
import subprocess
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

# CORS সেটিংস: যাতে আপনার লোকাল কম্পিউটার থেকে রেন্ডার সার্ভার এক্সেস করা যায়
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def cleanup_files(*file_paths):
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

@app.post("/compress")
async def compress_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    percentage: int = Form(...),
    original_size: int = Form(...)
):
    # ইউনিক ফাইলনেম তৈরি
    task_id = str(uuid.uuid4())
    input_path = f"in_{task_id}.pdf"
    output_path = f"out_{task_id}.pdf"

    # আপলোড করা ফাইল সেভ করা
    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    # --- পার্সেন্টেজ অনুযায়ী ইন্টেলিজেন্ট লজিক ---
    # ইউজার যতটা বেশি কমাতে চাইবে, আমরা রেজোলিউশন তত কমিয়ে দেব
    if percentage >= 80:
        dpi = 50
        color_mode = "/DeviceGray"  # সাদা-কালো (সর্বোচ্চ কম্প্রেশন)
        settings = "/screen"
    elif percentage >= 50:
        dpi = 72
        color_mode = "/DeviceRGB"   # রঙিন কিন্তু লো-কোয়ালিটি
        settings = "/screen"
    elif percentage >= 20:
        dpi = 120
        color_mode = "/DeviceRGB"   # মিডিয়াম কোয়ালিটি
        settings = "/ebook"
    else:
        dpi = 200
        color_mode = "/DeviceRGB"   # হাই কোয়ালিটি
        settings = "/printer"

    # Ghostscript কমান্ড (Aggressive Compression)
    gs_command = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={settings}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-dColorConversionStrategy={color_mode}",
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",
        f"-dMonoImageResolution={dpi}",
        "-dDownsampleColorImages=true",
        "-dOptimize=true",
        "-dEmbedAllFonts=false",
        "-dSubsetFonts=true",
        f"-sOutputFile={output_path}",
        input_path
    ]

    try:
        subprocess.run(gs_command, check=True)
        
        # যদি কোনো কারণে আউটপুট বড় হয়, তবে অরিজিনালটাই ব্যাকআপ হিসেবে দেব
        if os.path.getsize(output_path) > os.path.getsize(input_path):
            os.replace(input_path, output_path)
            
    except Exception as e:
        cleanup_files(input_path)
        return {"error": str(e)}

    # কাজ শেষ হলে ফাইল ডিলিট করার টাস্ক
    background_tasks.add_task(cleanup_files, input_path, output_path)

    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename=f"compressed_{file.filename}"
    )