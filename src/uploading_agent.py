# agents/04_uploading_agent.py
"""
04. UploadingAgent - S3 이미지 업로드 및 RDS 데이터 저장 에이전트

외부 시스템(S3, RDS)과 통신하여 데이터를 저장합니다.

역할:
- 썸네일 S3 업로드 (우선)
- 본문 이미지 S3 업로드
- 마크다운 내 URL 교체
- Article 데이터 RDS 저장
- 스키마 검증
"""

import asyncio
from typing import Dict, Any, List
from pathlib import Path
from .base import BaseAgent


class UploadingAgent(BaseAgent):
    """
    S3 이미지 업로드 및 RDS 데이터 저장 에이전트

    작업:
    1. 이미지를 S3에 업로드
    2. 문서 데이터를 RDS에 저장
    3. URL 매핑 및 반환
    """

    def __init__(self, s3_bucket: str = "my-blog-bucket"):
        super().__init__(
            name="UploadingAgent", description="S3 image upload and RDS data storage"
        )
        self.s3_bucket = s3_bucket
        self.mcp_client = None  # MCP 클라이언트 (나중에 연결)

    def set_mcp_client(self, mcp_client):
        """MCP 클라이언트 설정"""
        self.mcp_client = mcp_client

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        작업 실행

        Expected task actions:
            - upload_images: 이미지들을 S3에 업로드
            - save_article: 문서를 RDS에 저장
            - full_upload: 이미지 업로드 + 문서 저장
        """
        action = task.get("action")
        data = task.get("data", {})

        try:
            if action == "upload_images":
                return await self._upload_images(data.get("images", []))

            elif action == "save_article":
                return await self._save_article(data)

            elif action == "full_upload":
                # 썸네일 업로드
                thumbnail = data.get("thumbnail")
                thumbnail_url = None

                if thumbnail:
                    self._log("Uploading thumbnail...")
                    upload_result = await self._upload_images([], thumbnail)
                    if not upload_result["success"]:
                        return upload_result
                    thumbnail_url = upload_result["data"]["thumbnail_url"]

                # 이미지 업로드
                images = data.get("images", [])
                if images:
                    self._log(f"Uploading {len(images)} image(s) to S3...")
                    upload_result = await self._upload_images(images)
                    if not upload_result["success"]:
                        return upload_result

                    # S3 URL을 데이터에 업데이트
                    data["image_urls"] = upload_result["data"]["s3_urls"]
                    data["images"] = upload_result["data"]["images"]
                else:
                    data["image_urls"] = []

                # 썸네일 URL 추가
                if thumbnail_url:
                    data["thumbnail_url"] = thumbnail_url

                # 문서 저장
                self._log("Saving article to database...")
                return await self._save_article(data)

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "error": str(e), "agent": self.name}

    async def _upload_images(
        self, images: List[Dict[str, str]], thumbnail: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        이미지들을 S3에 업로드 (썸네일 우선 처리)

        Args:
            images: [{"local_path": "...", "alt": "...", "s3_url": None}, ...]
            thumbnail: {"local_path": "...", "alt": "...", "s3_url": None} (옵션)

        Returns:
            {
                "success": bool,
                "data": {
                    "thumbnail_url": str,
                    "images": [...],  # 업데이트된 이미지 정보
                    "s3_urls": [...]  # S3 URLs 목록
                }
            }
        """
        s3_urls = []
        updated_images = []
        thumbnail_url = None

        # 1. 썸네일 먼저 업로드 (있는 경우)
        if thumbnail:
            self._log("Uploading thumbnail...")
            local_path = thumbnail["local_path"]

            if self.mcp_client:
                thumbnail_url = await self._upload_to_s3_via_mcp(local_path)
            else:
                # 시뮬레이션
                await asyncio.sleep(0.2)
                filename = Path(local_path).name
                thumbnail_url = (
                    f"https://s3.amazonaws.com/{self.s3_bucket}/thumbnails/{filename}"
                )

            self._log(f"Thumbnail uploaded: {Path(local_path).name}")

        # 2. 나머지 이미지들 업로드
        if not images:
            return {
                "success": True,
                "data": {"thumbnail_url": thumbnail_url, "images": [], "s3_urls": []},
            }

        for img in images:
            local_path = img["local_path"]

            # MCP 사용 가능하면 실제 업로드
            if self.mcp_client:
                s3_url = await self._upload_to_s3_via_mcp(local_path)
            else:
                # 시뮬레이션 (개발용)
                await asyncio.sleep(0.2)  # 업로드 시뮬레이션
                filename = Path(local_path).name
                s3_url = f"https://s3.amazonaws.com/{self.s3_bucket}/images/{filename}"

            s3_urls.append(s3_url)
            updated_images.append({**img, "s3_url": s3_url})

            self._log(f"Uploaded: {Path(local_path).name}")

        return {
            "success": True,
            "data": {
                "thumbnail_url": thumbnail_url,
                "images": updated_images,
                "s3_urls": s3_urls,
            },
            "agent": self.name,
        }

    async def _upload_to_s3_via_mcp(self, local_path: str) -> str:
        """
        MCP를 통해 실제로 S3에 업로드
        (MCP 서버 구현 후 활성화)
        """
        try:
            result = await self.mcp_client.call_tool(
                "upload_image_to_s3",
                {"image_path": local_path, "bucket": self.s3_bucket},
            )
            return result.get("s3_url")
        except Exception as e:
            self._log(f"MCP upload failed: {e}", "error")
            raise

    async def _save_article(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        문서를 RDS에 저장

        Args:
            data: {
                "title": str,
                "content": str,
                "category": str,
                "slug": str,
                "tags": [str],
                "image_urls": [str],
                "author": str,
                ...
            }

        Returns:
            {
                "success": bool,
                "data": {
                    "article_id": int,
                    "slug": str,
                    "published_url": str
                }
            }
        """
        required_fields = ["title", "content", "slug"]
        missing_fields = [f for f in required_fields if not data.get(f)]

        if missing_fields:
            return {
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}",
            }

        # MCP 사용 가능하면 실제 저장
        if self.mcp_client:
            article_id = await self._save_to_rds_via_mcp(data)
        else:
            # 시뮬레이션 (개발용)
            await asyncio.sleep(0.3)
            import random

            article_id = random.randint(100, 999)

        slug = data["slug"]
        published_url = f"https://myblog.com/posts/{slug}"

        self._log(f"Article saved with ID: {article_id}")

        return {
            "success": True,
            "data": {
                "article_id": article_id,
                "title": data["title"],
                "slug": slug,
                "category": data.get("category", "General"),
                "published_url": published_url,
                "image_count": len(data.get("image_urls", [])),
            },
            "agent": self.name,
        }

    async def _save_to_rds_via_mcp(self, data: Dict[str, Any]) -> int:
        """
        MCP를 통해 실제로 RDS에 저장
        (MCP 서버 구현 후 활성화)
        """
        try:
            result = await self.mcp_client.call_tool(
                "save_article_to_rds",
                {
                    "title": data["title"],
                    "content": data["content"],
                    "category": data.get("category", "General"),
                    "slug": data["slug"],
                    "tags": data.get("tags", []),
                    "image_urls": data.get("image_urls", []),
                    "author": data.get("author", "Unknown"),
                    "status": "published",
                },
            )
            return result.get("article_id")
        except Exception as e:
            self._log(f"MCP save failed: {e}", "error")
            raise
