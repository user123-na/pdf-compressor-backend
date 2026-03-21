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
    level: str = Form(...)  # simple, medium, বা extreme
):
    task_id = str(uuid.uuid4())
    input_path = f"in_{task_id}.pdf"
    output_path = f"out_{task_id}.pdf"

    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    # --- প্রফেশনাল লেভেল এনফোর্সমেন্ট ---
    if level == "extreme":
        # টার্গেট: ~50% সাইজ কমানো
        settings = "/screen"
        dpi = 60
    elif level == "medium":
        # টার্গেট: ~40% সাইজ কমানো
        settings = "/ebook"
        dpi = 120
    else:  # simple
        # টার্গেট: ~20% সাইজ কমানো
        settings = "/printer"
        dpi = 200

    gs_command = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={settings}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        "-dColorConversionStrategy=/DeviceRGB",
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",
        f"-dMonoImageResolution={dpi}",
        "-dDownsampleColorImages=true",
        "-dOptimize=true",
        f"-sOutputFile={output_path}",
        input_path
    ]

    final_file = output_path

    try:
        subprocess.run(gs_command, check=True)
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