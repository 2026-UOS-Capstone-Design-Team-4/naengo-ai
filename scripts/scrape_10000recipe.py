"""
만개의레시피 스크래퍼 CLI.

Usage:
    uv run python scripts/scrape_10000recipe.py --limit 100
    uv run python scripts/scrape_10000recipe.py --limit 5 --dry-run
"""

import argparse
import hashlib
import json
import logging
import random
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.chat import ChatMessage, ChatRoom  # noqa: F401
from app.models.recipe_source import RecipeSource
from app.models.social import Like, Scrap  # noqa: F401
from app.models.user import User, UserProfile  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.10000recipe.com"
LIST_URL = f"{BASE_URL}/recipe/list.html"
RECIPE_URL = f"{BASE_URL}/recipe/{{recipe_id}}"
SOURCE_SITE = "10000recipe"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def fetch_recipe_ids(page: int) -> list[str]:
    try:
        response = requests.get(
            LIST_URL,
            params={"page": page},
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("목록 페이지 요청 실패 (page=%d): %s", page, exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    ids = []
    for anchor in soup.select("ul.common_sp_list_ul a.common_sp_link"):
        href = anchor.get("href", "")
        match = re.fullmatch(r"/recipe/(\d+)", href)
        if match:
            ids.append(match.group(1))
    return list(dict.fromkeys(ids))


def scrape_recipe(recipe_id: str) -> dict[str, Any] | None:
    url = RECIPE_URL.format(recipe_id=recipe_id)
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code
        if status_code in (403, 429):
            logger.error("접근 차단됨 (status=%d). 스크래핑을 중단합니다.", status_code)
            raise
        logger.warning("레시피 요청 실패 (id=%s, status=%d)", recipe_id, status_code)
        return None
    except requests.RequestException as exc:
        logger.warning("레시피 요청 실패 (id=%s): %s", recipe_id, exc)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    structured = _extract_structured_recipe(soup)
    title = _extract_title(soup)
    if not title:
        return None

    return {
        "source_recipe_id": recipe_id,
        "source_url": url,
        "title": title,
        "description": structured.get("description") or _extract_summary(soup),
        "image_url": _extract_image_url(soup),
        "ingredients": _extract_ingredients(soup),
        "instructions": _extract_instructions(soup),
        "servings_raw": _extract_servings(soup),
        "cooking_time_raw": _extract_cooking_time(soup),
        "author": _extract_author(soup),
        "published_at": structured.get("datePublished"),
        "tips": _extract_tips(soup),
        "tags": _extract_tags(soup),
        "structured_recipe": structured,
        "scraped_at": datetime.now(UTC).isoformat(),
    }


def _extract_structured_recipe(soup: BeautifulSoup) -> dict[str, Any]:
    script = soup.find("script", attrs={"type": "application/ld+json"})
    if script is None or not script.string:
        return {}
    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _extract_title(soup: BeautifulSoup) -> str:
    title_el = soup.select_one("div.view2_summary h3")
    return title_el.get_text(strip=True) if title_el else ""


def _extract_summary(soup: BeautifulSoup) -> str:
    summary_el = soup.select_one("div.view2_summary_in")
    return summary_el.get_text(strip=True) if summary_el else ""


def _extract_image_url(soup: BeautifulSoup) -> str | None:
    image_el = soup.select_one("div.centeredcrop img")
    if not image_el:
        return None
    return image_el.get("src") or None


def _extract_ingredients(soup: BeautifulSoup) -> list[dict[str, str]]:
    ingredients = []
    for item in soup.select("div.ready_ingre3 ul li"):
        name_el = item.select_one("div.ingre_list_name a")
        if name_el is None:
            name_el = item.select_one("div.ingre_list_name")
        name = name_el.get_text(strip=True) if name_el else ""
        amount_el = item.select_one("span.ingre_list_ea")
        amount = amount_el.get_text(strip=True) if amount_el else ""
        if name:
            ingredients.append(
                {
                    "name": name,
                    "amount": amount,
                    "raw_text": item.get_text(strip=True),
                }
            )
    return ingredients


def _extract_instructions(soup: BeautifulSoup) -> list[dict[str, Any]]:
    instructions = []
    for index, step in enumerate(soup.select("div.view_step_cont"), start=1):
        text_el = step.select_one("div.media-body")
        if text_el:
            # 단계 번호 요소 제거 후 텍스트 추출
            for num_el in text_el.select("div.step_list_num, span.step_num"):
                num_el.decompose()
            instruction = text_el.get_text(separator=" ", strip=True)
        else:
            instruction = step.get_text(separator=" ", strip=True)
        image_el = step.select_one("img")
        image_url = image_el.get("src", "") if image_el else ""
        if instruction:
            instructions.append(
                {
                    "step_no": index,
                    "instruction": instruction,
                    "image_url": image_url or None,
                }
            )
    return instructions


def _extract_servings(soup: BeautifulSoup) -> str:
    for row in soup.select("div.view2_summary_info span"):
        text = row.get_text(strip=True)
        if "인분" in text:
            return text
    return ""


def _extract_cooking_time(soup: BeautifulSoup) -> str:
    for row in soup.select("div.view2_summary_info span"):
        text = row.get_text(strip=True)
        if "시간" in text or ("분" in text and "인분" not in text):
            return text
    return ""


def _extract_author(soup: BeautifulSoup) -> dict[str, str]:
    author_el = soup.select_one("div.view2_summary_writer a")
    if author_el is None:
        name_el = soup.select_one("span.user_info2_name")
        if name_el is None:
            name_el = soup.select_one("div.profile_cont p.cont_name")
        return {
            "name": name_el.get_text(strip=True) if name_el else "",
            "url": "",
        }
    href = author_el.get("href", "")
    return {
        "name": author_el.get_text(strip=True),
        "url": f"{BASE_URL}{href}" if href else "",
    }


def _extract_tips(soup: BeautifulSoup) -> list[str]:
    tips = []
    for tip in soup.select("dl.view_step_tip"):
        text = tip.get_text(" ", strip=True)
        if text:
            tips.append(text)
    return tips


def _extract_tags(soup: BeautifulSoup) -> list[str]:
    tags = []
    for tag in soup.select("div.view_tag a"):
        text = tag.get_text(strip=True).lstrip("#").strip(" .")
        if text:
            tags.append(text)
    return list(dict.fromkeys(tags))


def already_exists(db, recipe_id: str) -> bool:
    return (
        db.query(RecipeSource)
        .filter(
            RecipeSource.source_site == SOURCE_SITE,
            RecipeSource.source_recipe_id == recipe_id,
        )
        .first()
        is not None
    )


def save_source(db, raw: dict[str, Any], dry_run: bool) -> None:
    content = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    source = RecipeSource(
        source_type="WEB_SCRAPE",
        source_site=SOURCE_SITE,
        parser_type="HTML",
        source_recipe_id=raw["source_recipe_id"],
        source_url=raw["source_url"],
        source_author_name=raw["author"]["name"] or None,
        source_author_url=raw["author"]["url"] or None,
        raw_payload=raw,
        raw_content_hash=content_hash,
        collection_status="COLLECTED",
        parse_status="NOT_PARSED",
        review_status="PENDING",
        import_status="NOT_IMPORTED",
    )
    if not dry_run:
        db.add(source)
        db.commit()
    logger.info("[%s] 저장: %s", "DRY-RUN" if dry_run else "SAVED", raw["title"])


def main() -> None:
    parser = argparse.ArgumentParser(description="만개의레시피 스크래퍼")
    parser.add_argument("--limit", type=int, default=100, help="수집할 최대 수")
    parser.add_argument("--start-page", type=int, default=1, help="시작 페이지")
    parser.add_argument("--delay-min", type=float, default=1.0)
    parser.add_argument("--delay-max", type=float, default=3.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    collected = 0
    page = args.start_page

    try:
        while collected < args.limit:
            logger.info("목록 페이지 %d 수집 중", page)
            recipe_ids = fetch_recipe_ids(page)
            if not recipe_ids:
                logger.info("더 이상 레시피 ID가 없습니다. 종료합니다.")
                break

            for recipe_id in recipe_ids:
                if collected >= args.limit:
                    break
                if args.resume and already_exists(db, recipe_id):
                    logger.debug("이미 존재해서 건너뜀: %s", recipe_id)
                    continue

                time.sleep(random.uniform(args.delay_min, args.delay_max))
                try:
                    raw = scrape_recipe(recipe_id)
                except requests.HTTPError:
                    logger.error("차단 감지. 즉시 중단합니다.")
                    return

                if raw is None:
                    continue
                if args.dry_run:
                    logger.info(
                        "DRY-RUN result:\n%s",
                        json.dumps(raw, ensure_ascii=False),
                    )
                else:
                    save_source(db, raw, dry_run=False)

                collected += 1
                logger.info("수집 완료: %d/%d", collected, args.limit)

            page += 1
    finally:
        db.close()

    logger.info("스크래핑 완료: 총 %d개 수집", collected)


if __name__ == "__main__":
    main()
