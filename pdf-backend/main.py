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
            os.remove(path)

@app.post("/compress")
async def compress_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    percentage: int = Form(...)
):
    task_id = str(uuid.uuid4())
    input_path = f"temp_{task_id}_in.pdf"
    output_path = f"temp_{task_id}_out.pdf"

    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    # স্লাইডার অনুযায়ী গ্র্যানুলার কম্প্রেশন সেটিংস
    # পার্সেন্টেজ যত বেশি, কোয়ালিটি তত কম (ফাইলের সাইজ তত ছোট)
    if percentage >= 80:
        pdf_settings, dpi = "/screen", 60   # সর্বোচ্চ কম্প্রেশন
    elif percentage >= 60:
        pdf_settings, dpi = "/screen", 90   # হাই কম্প্রেশন
    elif percentage >= 40:
        pdf_settings, dpi = "/ebook", 120   # মিডিয়াম কম্প্রেশন
    elif percentage >= 20:
        pdf_settings, dpi = "/printer", 150 # লো কম্প্রেশন
    else:
        pdf_settings, dpi = "/prepress", 300 # নামমাত্র কম্প্রেশন

    gs_command = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_settings}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",
        f"-dMonoImageResolution={dpi}",
        f"-sOutputFile={output_path}",
        input_path
    ]

    try:
        subprocess.run(gs_command, check=True)
    except Exception as e:
        cleanup_files(input_path)
        return {"error": str(e)}

    background_tasks.add_task(cleanup_files, input_path, output_path)

    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename=f"compressed_{file.filename}"
    )