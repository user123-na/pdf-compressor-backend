import os
import uuid
import subprocess
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

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
    percentage: int = Form(...)
):
    task_id = str(uuid.uuid4())
    input_path = f"in_{task_id}.pdf"
    output_path = f"out_{task_id}.pdf"

    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    # --- প্রফেশনাল ব্রুট-ফোর্স লজিক (iLovePDF Style) ---
    
    if percentage >= 50:
        # Extreme Compression (৫০% বা তার বেশি কমালে)
        # টার্গেট: ফাইলকে যেকোনো মূল্যে ছোট করা। সাদা-কালো এবং একদম কম DPI.
        settings = "/screen"
        dpi = 40
        color_mode = "/DeviceGray" 
    elif percentage >= 40:
        # Medium Compression (৪০% থেকে ৪৯% কমালে)
        # টার্গেট: ব্যালেন্সড সাইজ, কালার ঠিক থাকবে কিন্তু কোয়ালিটি কমবে।
        settings = "/screen"
        dpi = 72
        color_mode = "/DeviceRGB"
    elif percentage >= 20:
        # Simple Compression (২০% থেকে ৩৯% কমালে)
        # টার্গেট: ভালো কোয়ালিটি, সাধারণ সাইজ কমানো।
        settings = "/ebook"
        dpi = 120
        color_mode = "/DeviceRGB"
    else:
        # Minimal (খুব কম কমালে)
        settings = "/printer"
        dpi = 150
        color_mode = "/DeviceRGB"

    gs_command = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={settings}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-dColorConversionStrategy={color_mode}",
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",
        f"-dMonoImageResolution={dpi}",
        "-dDownsampleColorImages=true",
        "-dDownsampleGrayImages=true",
        "-dDownsampleMonoImages=true",
        "-dOptimize=true",
        f"-sOutputFile={output_path}",
        input_path
    ]

    final_file = output_path

    try:
        subprocess.run(gs_command, check=True)
        # সেফটি চেক: যদি কোনো কারণে সাইজ না কমে, অরিজিনালটাই ব্যাকআপ হিসেবে থাকবে
        if os.path.getsize(output_path) >= os.path.getsize(input_path):
            final_file = input_path
    except:
        final_file = input_path

    background_tasks.add_task(cleanup_files, input_path, output_path)

    return FileResponse(
        final_file, 
        media_type="application/pdf", 
        filename=f"compressed_{file.filename}"
    )