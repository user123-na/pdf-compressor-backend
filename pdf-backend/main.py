import os
import uuid
import fitz  # PyMuPDF (সবচেয়ে শক্তিশালী ইঞ্জিন)
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

    # ফাইল সেভ করা
    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        # পিডিএফ ওপেন করা হচ্ছে
        doc = fitz.open(input_path)
        out_pdf = fitz.open()

        # --- ব্রুট-ফোর্স লজিক (দয়া-মায়া ছাড়া সাইজ কমানো) ---
        # পার্সেন্টেজ যত বাড়বে, জুম (Zoom) এবং কোয়ালিটি (Quality) তত কমবে
        
        if percentage >= 90:
            zoom = 0.5       # রেজোলিউশন অর্ধেক করে দেওয়া হবে
            jpg_quality = 5  # চরম বাজে কোয়ালিটি, কিন্তু সাইজ গ্যারান্টি দিয়ে কমবে
        elif percentage >= 70:
            zoom = 0.7
            jpg_quality = 20
        elif percentage >= 50:
            zoom = 0.9
            jpg_quality = 40
        elif percentage >= 30:
            zoom = 1.0
            jpg_quality = 60
        else:
            zoom = 1.2
            jpg_quality = 80

        mat = fitz.Matrix(zoom, zoom)

        # প্রতিটি পাতাকে স্ক্যান করে জোরপূর্বক ছবি (JPEG) তে কনভার্ট করা হচ্ছে
        for page in doc:
            # পাতাকে ছবি বানানো হচ্ছে
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # ছবির সাইজ পার্সেন্টেজ অনুযায়ী কমানো হচ্ছে
            img_bytes = pix.tobytes("jpeg", jpg_quality=jpg_quality)
            
            # সেই ছোট সাইজের ছবিকে আবার পিডিএফের পাতা বানানো হচ্ছে
            imgdoc = fitz.open("jpeg", img_bytes)
            pdfbytes = imgdoc.convert_to_pdf()
            imgpdf = fitz.open("pdf", pdfbytes)
            out_pdf.insert_pdf(imgpdf)

        # সর্বোচ্চ কম্প্রেশন মেথড দিয়ে সেভ করা
        out_pdf.save(output_path, garbage=4, deflate=True)
        out_pdf.close()
        doc.close()

    except Exception as e:
        # কোনো এরর হলে অরিজিনাল ফাইলটাই ব্যাকআপ হিসেবে রিটার্ন করবে
        if os.path.exists(input_path):
            os.rename(input_path, output_path)

    # কাজ শেষে ডিলিট
    background_tasks.add_task(cleanup_files, input_path, output_path)

    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename=f"compressed_{file.filename}"
    )