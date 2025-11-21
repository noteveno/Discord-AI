from pypdf import PdfReader

try:
    reader = PdfReader("Instruction.pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    # Write to file with UTF-8 encoding to avoid Windows console encoding issues
    with open("pdf_content.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("PDF content extracted successfully!")
except Exception as e:
    print(f"Error reading PDF: {e}")
