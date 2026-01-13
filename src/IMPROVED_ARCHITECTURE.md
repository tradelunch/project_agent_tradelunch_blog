# 개선된 블로그 에이전트 아키텍처

## 새로운 에이전트 추가

### 1. DocumentScannerAgent

**역할**: 문서 폴더 구조 스캔 및 메타데이터 수집

**입력**:
```python
{
    "root_path": "/path/to/docs",
    "scan_depth": 3  # category/subcategory/article
}
```

**출력**:
```python
{
    "articles": [
        {
            "article_name": "langchain-guide",
            "article_path": "technology/ai/langchain-guide",
            "md_file": "technology/ai/langchain-guide/langchain-guide.md",
            "thumbnail": "technology/ai/langchain-guide/langchain-guide.png",
            "images": [
                "technology/ai/langchain-guide/diagram1.jpeg",
                "technology/ai/langchain-guide/screenshot.png"
            ],
            "category": "technology",
            "subcategory": "ai"
        },
        # ... more articles
    ],
    "category_tree": {
        "technology": {
            "ai": ["langchain-guide", "transformer-basics"],
            "web": ["react-hooks"]
        },
        "tutorial": {
            "python": ["async-basics"]
        }
    }
}
```

**주요 로직**:
1. root_path에서 재귀적으로 폴더 탐색
2. leaf 폴더 = article 폴더로 판단
3. article_name과 동일한 이름의 .md 파일 찾기
4. article_name과 동일한 이름의 이미지 = 썸네일
5. 나머지 이미지 = 본문 이미지
6. 경로에서 category/subcategory 추출

---

## 2. 개선된 ExtractingAgent

**새로운 기능**:
- ✅ 태그 생성 (5-7개)
- ✅ 3문장 요약 생성
- ✅ DB 스키마 기반 필드 추출
- ✅ 읽기 시간 계산
- ✅ 임베딩 벡터 생성 (optional)

**입력**:
```python
{
    "article_info": {  # DocumentScanner 결과
        "md_file": "...",
        "category": "technology",
        "subcategory": "ai",
        "images": [...]
    },
    "db_schema": ArticleSchema,  # 스키마 제공
    "generate_embedding": True
}
```

**출력**:
```python
{
    "title": "Complete Guide to LangChain",
    "slug": "complete-guide-to-langchain",
    "content": "# Complete Guide...",
    
    # LLM 생성
    "tags": ["langchain", "llm", "ai", "tutorial", "python"],
    "summary": "This guide covers LangChain basics. You'll learn how to build AI applications. Step-by-step examples included.",
    
    "category": "technology",
    "subcategory": "ai",
    
    "thumbnail": {...},
    "images": [...],
    
    "word_count": 2500,
    "reading_time": 10,  # 분
    
    "embedding_vector": [0.123, -0.456, ...]  # optional
}
```

**LLM 프롬프트 예시**:
```python
prompt = f"""Given this article and database schema, extract the required fields.

DATABASE SCHEMA:
{schema_description}

ARTICLE:
Title: {title}
Category: {category}/{subcategory}
Content: {content[:1000]}...

EXTRACT:
1. tags: 5-7 relevant keywords (comma-separated)
2. summary: Exactly 3 sentences describing the article (for card display)

Respond in JSON:
{{
    "tags": ["tag1", "tag2", ...],
    "summary": "Sentence 1. Sentence 2. Sentence 3."
}}
"""
```

---

## 3. 개선된 UploadingAgent

**새로운 기능**:
- ✅ 썸네일 우선 처리
- ✅ 이미지 최적화 (크기 조정)
- ✅ DB 스키마 검증
- ✅ 트랜잭션 처리

**프로세스**:
```
1. 썸네일 업로드 → S3 URL 받기
2. 나머지 이미지들 병렬 업로드
3. 마크다운 내 이미지 URL 교체
4. DB 스키마 검증
5. RDS에 INSERT (트랜잭션)
```

---

## 전체 워크플로우

```python
# 1. 사용자 명령
"scan and upload all articles in ./docs"

# 2. Project Manager가 분석
PM: "Need to scan docs, then process each article"

# 3. DocumentScanner 실행
Scanner: Found 15 articles in 3 categories

# 4. 각 article에 대해 반복
for article in articles:
    
    # 4-1. ExtractingAgent
    Extractor: 
      - Parse markdown
      - Generate tags: ['ai', 'tutorial', ...]
      - Generate summary: "This article..."
      - Calculate reading time: 8 minutes
    
    # 4-2. UploadingAgent
    Uploader:
      - Upload thumbnail: ✅
      - Upload 3 images: ✅ ✅ ✅
      - Save to DB: Article ID 123
    
    # 4-3. LoggingAgent
    Logger: ✅ langchain-guide published

# 5. 최종 결과
PM: "Successfully processed 15 articles"
```

---

## DB 스키마를 에이전트에게 제공하는 방법

### 방법 1: Pydantic 스키마를 문자열로 변환

```python
# schema.py
from pydantic import BaseModel, Field
from typing import List, Optional

class ArticleSchema(BaseModel):
    """Article database schema"""
    
    title: str = Field(description="Article title")
    slug: str = Field(description="URL-friendly slug")
    content: str = Field(description="Full markdown content")
    
    category: str = Field(description="Main category from folder structure")
    subcategory: Optional[str] = Field(description="Subcategory from folder structure")
    
    # LLM이 생성해야 할 필드들
    tags: List[str] = Field(description="5-7 relevant keywords")
    summary: str = Field(description="Exactly 3 sentences for card display")
    
    thumbnail_url: str
    image_urls: List[str]
    
    author: str = Field(default="Unknown")
    word_count: int
    reading_time: int = Field(description="Estimated reading time in minutes")


# ExtractingAgent에서 사용
def get_schema_description(schema: BaseModel) -> str:
    """Pydantic 스키마를 LLM이 이해할 수 있는 문자열로 변환"""
    fields = []
    for name, field in schema.model_fields.items():
        field_type = field.annotation.__name__ if hasattr(field.annotation, '__name__') else str(field.annotation)
        description = field.description or "No description"
        required = "required" if field.is_required() else "optional"
        
        fields.append(f"- {name} ({field_type}, {required}): {description}")
    
    return "\n".join(fields)


# LLM 프롬프트에 포함
schema_desc = get_schema_description(ArticleSchema)
prompt = f"""
Extract data according to this schema:

{schema_desc}

Article content:
{content}
"""
```

### 방법 2: JSON Schema 사용

```python
import json

schema_json = ArticleSchema.model_json_schema()

prompt = f"""
Extract data according to this JSON schema:

{json.dumps(schema_json, indent=2)}

Article content:
{content}
"""
```

---

## 폴더 구조 스캐닝 로직

```python
from pathlib import Path
from typing import Dict, List

def scan_documentation(root_path: str) -> Dict:
    """
    문서 폴더 구조를 스캔하여 article 정보 추출
    
    규칙:
    - leaf 폴더 = article 폴더
    - article_name.md 파일이 있어야 함
    - article_name과 같은 이미지 = 썸네일
    - 나머지 이미지 = 본문 이미지
    """
    root = Path(root_path)
    articles = []
    category_tree = {}
    
    for md_file in root.rglob("*.md"):
        # article 폴더인지 확인
        article_folder = md_file.parent
        article_name = md_file.stem
        
        # article_name과 파일명이 같은지 확인
        if article_folder.name != article_name:
            continue  # 이 폴더는 article 폴더가 아님
        
        # 경로에서 category 추출
        relative_path = article_folder.relative_to(root)
        path_parts = relative_path.parts
        
        category = path_parts[0] if len(path_parts) > 0 else "uncategorized"
        subcategory = path_parts[1] if len(path_parts) > 1 else None
        
        # 썸네일 찾기 (article_name과 같은 이름의 이미지)
        thumbnail = None
        for ext in ['.png', '.jpg', '.jpeg', '.webp']:
            thumb_path = article_folder / f"{article_name}{ext}"
            if thumb_path.exists():
                thumbnail = str(thumb_path)
                break
        
        # 나머지 이미지 찾기
        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
        images = []
        for img in article_folder.iterdir():
            if img.suffix.lower() in image_exts and img.stem != article_name:
                images.append(str(img))
        
        # article 정보 저장
        article_info = {
            "article_name": article_name,
            "article_path": str(relative_path),
            "md_file": str(md_file),
            "thumbnail": thumbnail,
            "images": images,
            "category": category,
            "subcategory": subcategory
        }
        
        articles.append(article_info)
        
        # category tree 구성
        if category not in category_tree:
            category_tree[category] = {}
        
        if subcategory:
            if subcategory not in category_tree[category]:
                category_tree[category][subcategory] = []
            category_tree[category][subcategory].append(article_name)
        else:
            if "_root" not in category_tree[category]:
                category_tree[category]["_root"] = []
            category_tree[category]["_root"].append(article_name)
    
    return {
        "articles": articles,
        "category_tree": category_tree,
        "total_articles": len(articles),
        "total_categories": len(category_tree)
    }


# 사용 예시
result = scan_documentation("./docs")
print(f"Found {result['total_articles']} articles")
print(f"Categories: {list(result['category_tree'].keys())}")
```

---

## 개선 사항 요약

### 추가된 기능:
1. ✅ **DocumentScannerAgent** - 폴더 구조 자동 스캔
2. ✅ **태그 생성** - 5-7개 키워드
3. ✅ **3문장 요약** - 카드 표시용
4. ✅ **DB 스키마 제공** - 정확한 필드 추출
5. ✅ **썸네일 구분** - article_name과 같은 이미지
6. ✅ **읽기 시간 계산** - 분 단위
7. ✅ **카테고리 자동 추출** - 폴더 구조에서
8. ✅ **임베딩 벡터** - 클러스터링용 (optional)

### 새 명령어:
```bash
# 전체 문서 스캔 및 업로드
blog-agent> scan ./docs

# 특정 카테고리만
blog-agent> scan ./docs/technology

# 카테고리 트리 보기
blog-agent> show categories
```

---

## 다음 단계

1. **DocumentScannerAgent 구현**
2. **ArticleSchema 정의**
3. **ExtractingAgent에 태그/요약 생성 추가**
4. **UploadingAgent에 썸네일 우선 처리 추가**
5. **테스트용 문서 구조 생성**

이 구조가 더 적합해 보이나요? 구현을 시작할까요?
