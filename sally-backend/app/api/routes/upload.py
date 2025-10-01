from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.api.dependencies import get_current_admin
from app.domain.entities import Admin, KnowledgeBaseArticle, ArticleStatus, ArticleTag
import os
import uuid
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import openpyxl
import markdown
from app.infrastructure.langchain_utils import langchain_service

router = APIRouter()


async def generate_metadata_from_ai(title: str, content: str):
    """Generate metadata from AI for uploaded file content using LangChain."""
    try:
        return await langchain_service.generate_metadata(title, content)
    except Exception as e:
        # Return default metadata if AI fails
        return {
            "summary": f"محتوای استخراج شده از فایل: {title}",
            "tags": ["آپلود شده", "فایل"],
            "suggested_category": "عمومی",
            "suggested_visibility": "internal"
        }


async def get_or_create_tags(tag_names):
    """Get or create tags and return ArticleTag objects."""
    from app.domain.entities import Tag
    article_tags = []
    for tag_name in tag_names:
        # Check if tag exists
        tag = await Tag.find_one(Tag.name == tag_name)
        if not tag:
            # Create new tag
            tag = Tag(name=tag_name)
            await tag.insert()
        article_tags.append(ArticleTag(id=str(tag.id), name=tag.name, color=tag.color))
    return article_tags

# Create upload directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from DOCX file."""
    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting DOCX text: {str(e)}"


def extract_text_from_excel(file_path: Path) -> str:
    """Extract text from Excel file."""
    try:
        wb = openpyxl.load_workbook(file_path)
        text = ""
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            text += f"Sheet: {sheet_name}\n"
            for row in sheet.iter_rows(values_only=True):
                row_text = "\t".join(str(cell) for cell in row if cell is not None)
                if row_text.strip():
                    text += row_text + "\n"
            text += "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting Excel text: {str(e)}"


def extract_text_from_csv(file_path: Path) -> str:
    """Extract text from CSV file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            return f"Error extracting CSV text: {str(e)}"
    except Exception as e:
        return f"Error extracting CSV text: {str(e)}"

@router.post("/upload", tags=["File Upload"])
async def upload_file(
    file: UploadFile = File(...),
    current_user: Admin = Depends(get_current_admin)
):
    """Upload a file for processing."""
    
    # Check file extension
    allowed_extensions = {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".doc", ".txt"}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_extension} not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    file_size = 0
    
    # Read file to check size
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)  # Reset file pointer
    
    if file_size > max_size:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    file_extension = Path(original_filename).suffix.lower()
    new_filename = f"{file_id}{file_extension}"
    
    # Save file
    file_path = UPLOAD_DIR / new_filename
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    # Process file content for knowledge base
    article_content = ""
    article_title = original_filename

    print(f"📁 شروع آپلود فایل در upload.py: {original_filename}")

    if file_extension == ".txt":
        # For TXT files, read content directly
        try:
            article_content = contents.decode("utf-8")
            print(f"📄 فایل TXT خوانده شد، طول: {len(article_content)} کاراکتر")
        except UnicodeDecodeError:
            article_content = "Unable to decode file content"
            print("❌ خطا در دیکد فایل TXT")
    elif file_extension == ".pdf":
        article_content = extract_text_from_pdf(file_path)
        print(f"📄 متن از PDF استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension in [".docx", ".doc"]:
        article_content = extract_text_from_docx(file_path)
        print(f"📄 متن از DOCX استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension in [".xlsx", ".xls"]:
        article_content = extract_text_from_excel(file_path)
        print(f"📄 متن از Excel استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension == ".csv":
        article_content = extract_text_from_csv(file_path)
        print(f"📄 متن از CSV استخراج شد، طول: {len(article_content)} کاراکتر")
    else:
        # For unsupported files, store file path info
        article_content = f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {file_size} bytes\n\nContent extraction not supported for {file_extension} files."
        print(f"⚠️ نوع فایل پشتیبانی نمی‌شود: {file_extension}")

    # Generate AI metadata if content was extracted
    ai_metadata = None
    print(f"🔍 شروع تولید فراداده AI برای فایل: {original_filename}")
    print(f"📄 طول محتوا استخراج شده: {len(article_content) if article_content else 0} کاراکتر")

    if article_content and article_content != f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {file_size} bytes\n\nContent extraction not supported for {file_extension} files.":
        print("🤖 شروع فراخوانی AI برای تولید فراداده...")
        try:
            ai_metadata = await generate_metadata_from_ai(article_title, article_content)
            print(f"✅ AI فراداده تولید کرد: {bool(ai_metadata)}")
        except Exception as e:
            # Continue with default metadata if AI generation fails
            print(f"❌ خطا در تولید فراداده AI: {str(e)}")
            pass
    else:
        print("⚠️ محتوا استخراج نشد یا نامعتبر است - از فراداده پیش‌فرض استفاده می‌شود")

    # Generate HTML from markdown if not provided (for text content)
    content_html = markdown.markdown(article_content) if article_content else ""

    # Handle tags from AI metadata
    tag_names = ai_metadata.get("tags", []) if ai_metadata else ["آپلود شده", file_extension[1:]]
    tags = await get_or_create_tags(tag_names)

    # Create knowledge base article
    try:
        article = KnowledgeBaseArticle(
            title=article_title,
            content_markdown=article_content,
            content_html=content_html,
            summary=ai_metadata.get("summary") if ai_metadata else f"محتوای استخراج شده از فایل: {original_filename}",
            author_id=str(current_user.id),
            status=ArticleStatus.DRAFT,
            tags=tags
        )
        await article.insert()
        article_id = str(article.id)
        print(f"✅ مقاله ایجاد شد با ID: {article_id}")
        
        # Sync to Weaviate فقط برای مقالات منتشر شده
        if article.status == ArticleStatus.PUBLISHED:
            try:
                from app.infrastructure.knowledge_base_repository import KnowledgeBaseRepository
                repo = KnowledgeBaseRepository()
                await repo._sync_to_weaviate(article, "create")
                print(f"✅ Article {article_id} synced to Weaviate (PUBLISHED)")
            except Exception as sync_error:
                print(f"⚠️ خطا در sync با Weaviate: {str(sync_error)}")
        else:
            print(f"ℹ️ Article {article_id} is {article.status} - not synced to Weaviate")
            
    except Exception as e:
        print(f"❌ خطا در ایجاد مقاله: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating article: {str(e)}")

    return {
        "success": True,
        "file_id": file_id,
        "article_id": article_id,
        "filename": original_filename,
        "file_size": file_size,
        "message": "File uploaded and article created successfully."
    }