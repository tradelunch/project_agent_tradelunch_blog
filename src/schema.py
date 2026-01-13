# 01_schema.py
"""
01. Schema - 데이터베이스 스키마 정의

Article의 데이터베이스 스키마를 Pydantic으로 정의합니다.
이 스키마는 LLM에게 제공되어 정확한 데이터 추출을 돕습니다.

주요 기능:
- ArticleSchema: 모든 필드 정의
- get_schema_description(): LLM용 설명 생성
- calculate_reading_time(): 읽기 시간 계산
- CREATE_TABLE_SQL: RDS 테이블 생성 SQL
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ArticleSchema(BaseModel):
    """
    블로그 Article의 데이터베이스 스키마

    이 스키마는 ExtractingAgent가 어떤 필드를 추출해야 하는지,
    UploadingAgent가 어떤 데이터를 저장해야 하는지 정의합니다.
    """

    # ==================== 필수 필드 ====================
    title: str = Field(description="Article title extracted from markdown")

    slug: str = Field(
        description="URL-friendly slug (auto-generated from title or folder name)"
    )

    content: str = Field(description="Full markdown content of the article")

    # ==================== 카테고리 (폴더 구조에서 추출) ====================
    category: str = Field(
        description="Main category from folder structure (e.g., 'technology', 'tutorial')"
    )

    subcategory: Optional[str] = Field(
        default=None,
        description="Subcategory from folder structure (e.g., 'ai', 'web')",
    )

    # ==================== LLM이 생성할 필드 ====================
    tags: List[str] = Field(
        description="5-7 relevant keywords extracted by LLM for categorization and search",
        min_length=3,
        max_length=10,
    )

    summary: str = Field(
        description="Exactly 3 sentences summarizing the article for card display. Each sentence should be concise and informative."
    )

    # ==================== 이미지 ====================
    thumbnail_url: Optional[str] = Field(
        default=None, description="S3 URL of the thumbnail image (same name as article)"
    )

    image_urls: List[str] = Field(
        default_factory=list,
        description="List of S3 URLs for images used in the article content",
    )

    # ==================== 메타데이터 ====================
    author: str = Field(
        default="Unknown", description="Article author (from frontmatter or default)"
    )

    published_at: datetime = Field(
        default_factory=datetime.now, description="Publication timestamp"
    )

    word_count: int = Field(description="Total word count of the article content")

    reading_time: int = Field(
        description="Estimated reading time in minutes (calculated from word count)"
    )

    # ==================== 클러스터링용 (Optional) ====================
    embedding_vector: Optional[List[float]] = Field(
        default=None,
        description="Vector embedding for semantic search and clustering (optional)",
    )

    # ==================== 상태 ====================
    status: str = Field(
        default="published", description="Article status: draft, published, archived"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Complete Guide to LangChain",
                "slug": "complete-guide-to-langchain",
                "content": "# Complete Guide to LangChain\n\nThis is...",
                "category": "technology",
                "subcategory": "ai",
                "tags": ["langchain", "llm", "ai", "tutorial", "python"],
                "summary": "This guide covers LangChain basics. You'll learn how to build AI applications. Step-by-step examples included.",
                "thumbnail_url": "https://s3.../langchain-guide.png",
                "image_urls": ["https://s3.../diagram1.png", "https://s3.../code.png"],
                "author": "Alex Kim",
                "word_count": 2500,
                "reading_time": 10,
                "status": "published",
            }
        }


def get_schema_description(schema: type[BaseModel]) -> str:
    """
    Pydantic 스키마를 LLM이 이해할 수 있는 문자열로 변환

    Returns:
        스키마의 각 필드에 대한 설명이 포함된 문자열
    """
    lines = [f"# {schema.__name__}", ""]

    if schema.__doc__:
        lines.append(schema.__doc__.strip())
        lines.append("")

    lines.append("## Fields:")
    lines.append("")

    for name, field in schema.model_fields.items():
        # 타입 추출
        field_type = field.annotation
        if hasattr(field_type, "__name__"):
            type_str = field_type.__name__
        else:
            type_str = str(field_type)

        # 필수/옵션 여부
        required = "required" if field.is_required() else "optional"

        # 설명
        description = field.description or "No description"

        # 기본값
        default = ""
        if not field.is_required() and field.default is not None:
            default = f" (default: {field.default})"

        lines.append(f"- **{name}** ({type_str}, {required}){default}")
        lines.append(f"  {description}")
        lines.append("")

    return "\n".join(lines)


def calculate_reading_time(word_count: int, wpm: int = 250) -> int:
    """
    단어 수에서 읽기 시간 계산

    Args:
        word_count: 총 단어 수
        wpm: 분당 읽는 단어 수 (기본값: 250)

    Returns:
        예상 읽기 시간 (분)
    """
    return max(1, round(word_count / wpm))


# RDS 테이블 생성 SQL (참고용)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    
    -- 기본 정보
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(500) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    
    -- 카테고리
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    
    -- LLM 생성 필드
    tags TEXT[] NOT NULL,  -- PostgreSQL array
    summary TEXT NOT NULL,
    
    -- 이미지
    thumbnail_url TEXT,
    image_urls TEXT[],
    
    -- 메타데이터
    author VARCHAR(200) DEFAULT 'Unknown',
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    word_count INTEGER NOT NULL,
    reading_time INTEGER NOT NULL,
    
    -- 클러스터링
    embedding_vector VECTOR(1536),  -- pgvector extension
    
    -- 상태
    status VARCHAR(20) DEFAULT 'published',
    
    -- 타임스탬프
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 인덱스
    INDEX idx_category (category),
    INDEX idx_subcategory (subcategory),
    INDEX idx_tags USING GIN (tags),
    INDEX idx_published_at (published_at)
);
"""
