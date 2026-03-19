import os
import uuid
import subprocess
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # এটি সব জায়গা থেকে রিকোয়েস্ট অ্যাক্সেপ্ট করবে
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def cleanup_files(*file_paths):
    for path in file_paths:
        if os.path.exists(path):
            os.remove(path)

@app.post("/compress")
async def compress_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    percentage: int = Form(...)
):
    task_id = str(uuid.uuid4())
    input_path = f"temp_input_{task_id}.pdf"
    output_path = f"temp_output_{task_id}.pdf"

    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    if percentage >= 70:
        pdf_settings, dpi = "/screen", 72
    elif percentage >= 40:
        pdf_settings, dpi = "/ebook", 100
    else:
        pdf_settings, dpi = "/printer", 150

    # Render লিনাক্স সার্ভার, তাই কমান্ড হবে শুধু "gs"
    gs_command = [
        "gs", 
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_settings}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",
        f"-dMonoImageResolution={dpi}",
        f"-sOutputFile={output_path}",
        input_path
    ]

    try:
        subprocess.run(gs_command, check=True)
    except subprocess.CalledProcessError:
        cleanup_files(input_path, output_path)
        return {"error": "Compression failed."}

    background_tasks.add_task(cleanup_files, input_path, output_path)

    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename=f"compressed_{file.filename}"
    )