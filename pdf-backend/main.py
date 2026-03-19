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
    input_path = f"in_{task_id}.pdf"
    output_path = f"out_{task_id}.pdf"

    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    # স্লাইডারের পার্সেন্টেজ অনুযায়ী DPI এবং কোয়ালিটি ডাইনামিকভাবে সেট করা
    # ১০০% এর কাছাকাছি গেলে DPI একদম কমিয়ে দিবে (ফাইল ছোট করার জন্য)
    target_dpi = 200 - (percentage * 1.5) # ৯০% হলে DPI হবে প্রায় ৬৫
    
    if percentage >= 80:
        pdf_set = "/screen"
    elif percentage >= 50:
        pdf_set = "/ebook"
    else:
        pdf_set = "/printer"

    # অত্যন্ত শক্তিশালী কম্প্রেশন কমান্ড (টেক্সট ও ফন্ট অপ্টিমাইজেশনের জন্য)
    gs_command = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_set}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        "-dEmbedAllFonts=false", # ফন্ট পুরোপুরি এম্বেড না করে ছোট করা
        "-dSubsetFonts=true",    # শুধুমাত্র ব্যবহৃত অক্ষরগুলোর ফন্ট রাখা
        "-dCompressFonts=true", # ফন্ট কম্প্রেস করা
        "-dOptimize=true",      # ফাইল স্ট্রাকচার অপ্টিমাইজ করা
        f"-dColorImageResolution={int(target_dpi)}",
        f"-dGrayImageResolution={int(target_dpi)}",
        f"-dMonoImageResolution={int(target_dpi)}",
        f"-sOutputFile={output_path}",
        input_path
    ]

    try:
        subprocess.run(gs_command, check=True)
        
        # যদি আউটপুট ফাইল ইনপুট ফাইলের চেয়ে বড় হয় (টেক্সট ফাইলের ক্ষেত্রে হতে পারে)
        # তবে আমরা অরিজিনাল ফাইলটিই রিটার্ন করব যেন ইউজার ঠকে না যায়
        if os.path.getsize(output_path) > os.path.getsize(input_path):
            os.replace(input_path, output_path)
            
    except Exception as e:
        cleanup_files(input_path)
        return {"error": str(e)}

    background_tasks.add_task(cleanup_files, input_path, output_path)

    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename=f"compressed_{file.filename}"
    )