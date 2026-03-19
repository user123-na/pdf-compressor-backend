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

    # ফাইলটি সেভ করা হচ্ছে
    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    # --- ইন্টেলিজেন্ট কোয়ালিটি কন্ট্রোল লজিক ---
    # ইউজার যতটা পার্সেন্টেজ চাইবে, ইঞ্জিন ততটা চেষ্টা করবে, কিন্তু ফাইল ধ্বংস করবে না।
    if percentage >= 80:
        settings = "/screen"
        dpi = 72    # ম্যাক্সিমাম কম্প্রেশন, কিন্তু পড়ার যোগ্য থাকবে
    elif percentage >= 50:
        settings = "/ebook"
        dpi = 100   # স্ট্যান্ডার্ড কম্প্রেশন
    elif percentage >= 20:
        settings = "/printer"
        dpi = 150   # ভালো কোয়ালিটি
    else:
        settings = "/prepress"
        dpi = 300   # হাই কোয়ালিটি

    gs_command = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={settings}",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        "-dColorConversionStrategy=/DeviceRGB", # কালার নষ্ট হবে না
        f"-dColorImageResolution={dpi}",
        f"-dGrayImageResolution={dpi}",
        f"-dMonoImageResolution={dpi}",
        "-dDownsampleColorImages=true",
        "-dOptimize=true", # ফাইলের স্ট্রাকচার অপ্টিমাইজ করবে
        f"-sOutputFile={output_path}",
        input_path
    ]

    final_file_to_send = output_path

    try:
        # Ghostscript দিয়ে কম্প্রেশন করার চেষ্টা
        subprocess.run(gs_command, check=True)
        
        # --- সেফটি চেক (ম্যাজিক লজিক) ---
        # যদি কম্প্রেস করার পর ফাইল আগের চেয়েও বড় হয়ে যায় (অনেক পিডিএফ-এ এমন হয়)
        if os.path.getsize(output_path) >= os.path.getsize(input_path):
            final_file_to_send = input_path # সেফলি অরিজিনাল ফাইলটি সিলেক্ট করা হলো
            
    except subprocess.CalledProcessError:
        # যদি ইঞ্জিন কোনো কারণে ফেল করে (যেমন ফাইল করাপ্টেড), তবুও এরর দেবে না!
        final_file_to_send = input_path

    # ফাইল পাঠানোর পর সার্ভার থেকে ডিলিট করার টাস্ক
    background_tasks.add_task(cleanup_files, input_path, output_path)

    # সবশেষে ফাইলটি ফ্রন্টএন্ডে পাঠানো
    return FileResponse(
        final_file_to_send, 
        media_type="application/pdf", 
        filename=f"compressed_{file.filename}"
    )