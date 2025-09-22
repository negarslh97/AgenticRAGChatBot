from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import sys
import os
import uuid
import openai
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import text extraction libraries
try:
    from PyPDF2 import PdfReader
    from docx import Document
    import openpyxl
    TEXT_EXTRACTION_AVAILABLE = True
except ImportError:
    TEXT_EXTRACTION_AVAILABLE = False

from app.domain.entities_refactored import KnowledgeBaseArticle, ArticleStatus, Admin, ArticleVisibility, AdminRole
from app.api.dependencies import get_current_admin
from app.core.permissions import get_current_admin_with_permission, Permission
from app.core.config import settings

router = APIRouter()

# --- Helper Functions for Text Extraction and AI Generation ---

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file."""
    if not TEXT_EXTRACTION_AVAILABLE:
        return "Text extraction libraries not available"

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
    if not TEXT_EXTRACTION_AVAILABLE:
        return "Text extraction libraries not available"

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
    if not TEXT_EXTRACTION_AVAILABLE:
        return "Text extraction libraries not available"

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


async def generate_metadata_from_ai(title: str, content: str) -> dict:
    """Generate metadata from AI for uploaded file content."""
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(
            api_key=settings.openai_api_key_loaded,
            base_url=settings.openai_base_url_loaded,
        )

        prompt_template = f"""
You are an expert content strategist for a knowledge base. Your task is to analyze the following article and generate structured metadata in Persian (Farsi).

**Instructions:**
1. Generate a concise, professional **summary**.
2. Generate 3 to 5 relevant **tags**.
3. Suggest a **category** from the provided list.
4. Suggest a **visibility** level based on the content.
5. Your output **MUST** be a single, valid JSON object and nothing else.

**Available Options:**
- Categories: ["راهنمای محصول", "مشکلات فنی", "حساب کاربری و صورتحساب", "عمومی"]
- Visibility: ["public", "customer", "internal"]

**Article to Analyze:**
- Title: {title}
- Content: {content}

**Required JSON Output:**
{{
  "summary": "...",
  "tags": ["...", "..."],
  "suggested_category": "...",
  "suggested_visibility": "..."
}}
"""

        # Make API call
        response = client.chat.completions.create(
            model=settings.openai_model_loaded or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates metadata for knowledge base articles."},
                {"role": "user", "content": prompt_template}
            ],
            max_tokens=500,
            temperature=0.7,
        )

        # Parse AI response
        ai_response = response.choices[0].message.content.strip()
        metadata = json.loads(ai_response)
        return metadata

    except openai.OpenAIError as e:
        # Return default metadata if AI fails
        return {
            "summary": f"محتوای استخراج شده از فایل: {title}",
            "tags": ["آپلود شده", "فایل"],
            "suggested_category": "عمومی",
            "suggested_visibility": "internal"
        }
    except Exception as e:
        # Return default metadata if parsing fails
        return {
            "summary": f"محتوای استخراج شده از فایل: {title}",
            "tags": ["آپلود شده", "فایل"],
            "suggested_category": "عمومی",
            "suggested_visibility": "internal"
        }

# --- Pydantic Schemas for admin Knowledge Base ---

class ArticleCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = []

class ArticleUpdate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = []

class ArticleResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    status: ArticleStatus
    visibility: Optional[ArticleVisibility] = None
    author_id: str
    version: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

class ArticlePublishRequest(BaseModel):
    visibility: ArticleVisibility


# --- API Endpoints ---

@router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_data: ArticleCreate,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Create a new knowledge base article as a draft.
    Accessible by admin and SuperAdmin.
    """
    new_article = KnowledgeBaseArticle(
        title=article_data.title,
        content=article_data.content,
        summary=article_data.summary,
        category_id=article_data.category_id,
        tags=article_data.tags,
        author_id=str(current_user.id),
        status=ArticleStatus.DRAFT,
        visibility=None  # Visibility set only when published
    )
    await new_article.insert()
    new_article.id = str(new_article.id)
    return new_article

@router.post("/articles/upload", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def upload_kb_file(
    file: UploadFile = File(...),
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Upload a file to create a new knowledge base article as a draft with AI-generated metadata.
    Accessible by SuperAdmin only.
    """
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    file_extension = Path(original_filename).suffix.lower()
    new_filename = f"{file_id}{file_extension}"
    file_path = upload_dir / new_filename

    # Save file to uploads directory
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Extract text content based on file type
    article_content = ""
    article_title = original_filename

    if file_extension == ".txt":
        # For TXT files, read content directly
        try:
            article_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            article_content = "Unable to decode file content"
    elif file_extension == ".pdf":
        article_content = extract_text_from_pdf(file_path)
    elif file_extension in [".docx", ".doc"]:
        article_content = extract_text_from_docx(file_path)
    elif file_extension in [".xlsx", ".xls"]:
        article_content = extract_text_from_excel(file_path)
    elif file_extension == ".csv":
        article_content = extract_text_from_csv(file_path)
    else:
        # For unsupported files, store file path info
        article_content = f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {len(file_content)} bytes\n\nContent extraction not supported for {file_extension} files."

    # Generate AI metadata if content was extracted
    ai_metadata = None
    if article_content and article_content != f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {len(file_content)} bytes\n\nContent extraction not supported for {file_extension} files.":
        try:
            ai_metadata = await generate_metadata_from_ai(article_title, article_content)
        except Exception as e:
            # Continue with default metadata if AI generation fails
            pass

    # Create article with extracted content and AI-generated metadata
    new_article = KnowledgeBaseArticle(
        title=article_title,
        content=article_content,
        summary=ai_metadata.get("summary") if ai_metadata else f"محتوای استخراج شده از فایل: {original_filename}",
        category_id=ai_metadata.get("suggested_category") if ai_metadata else None,
        tags=ai_metadata.get("tags") if ai_metadata else ["آپلود شده", file_extension[1:]],
        author_id=str(current_user.id),
        status=ArticleStatus.DRAFT,
        visibility=None
    )
    await new_article.insert()
    new_article.id = str(new_article.id)
    return new_article

@router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
async def publish_article(
    article_id: str,
    publish_request: ArticlePublishRequest,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.PUBLISH_ARTICLES))
):
    """
    Publish a draft article with specified visibility.
    Accessible only by SuperAdmin.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    
    if article.status != ArticleStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft articles can be published"
        )
    
    article.status = ArticleStatus.PUBLISHED
    article.visibility = publish_request.visibility
    article.published_at = datetime.utcnow()
    article.published_by = str(current_user.id)
    
    await article.save()
    article.id = str(article.id)
    return article

@router.get("/articles", response_model=List[ArticleResponse])
async def list_articles(
    status_filter: Optional[ArticleStatus] = None,
    current_user: Admin = Depends(get_current_admin)
):
    """
    List all knowledge base articles. admins can see all articles.
    Can be filtered by status (e.g., 'draft', 'published').
    """
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    articles = await KnowledgeBaseArticle.find(query).sort(-KnowledgeBaseArticle.updated_at).to_list()
    # Convert ObjectId to string for response
    for article in articles:
        article.id = str(article.id)
    return articles

@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Get a single article by its ID.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article.id = str(article.id)
    return article

@router.put("/articles/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: str,
    article_data: ArticleUpdate,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Update an article.
    - admins can only update their own DRAFT articles.
    - SuperAdmins can update any article.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    if current_user.role_name != "SuperAdmin":
        if article.author_id != str(current_user.id) or article.status != ArticleStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own draft articles."
            )

    article.title = article_data.title
    article.content = article_data.content
    article.summary = article_data.summary
    article.category_id = article_data.category_id
    article.tags = article_data.tags
    article.updated_at = datetime.utcnow()
    article.version += 1
    
    await article.save()
    return article

@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.DELETE_ARTICLES))
):
    """
    Delete an article.
    Accessible only by SuperAdmin.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    
    await article.delete()
    return None
