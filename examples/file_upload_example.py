from ignyx import Ignyx, UploadFile

app = Ignyx()

@app.post("/upload")
async def upload_file(request):
    file: UploadFile = request.files.get("file")
    if not file:
        return {"error": "No file provided"}, 400
    return {"filename": file.filename, "size": len(file.content)}
