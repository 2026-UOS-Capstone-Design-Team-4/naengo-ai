import json
import logging
import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.append(PROJECT_ROOT)

from openai import OpenAI  # noqa: E402

from app.core import config  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.chat import ChatMessage, ChatRoom  # noqa: E402, F401
from app.models.recipe import PendingRecipe, Recipe, RecipeStats  # noqa: E402, F401
from app.models.social import Like, Scrap  # noqa: E402, F401
from app.models.user import User, UserProfile  # noqa: E402, F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JSON_FILE_PATH = os.path.join(
    PROJECT_ROOT,
    "db",
    "samples",
    "legacy_youtube_recipes.json",
)

client = OpenAI(api_key=config.EMBEDDING_API_KEY)


def build_embedding_text(recipe: dict) -> str:
    difficulty_map = {"easy": "easy", "normal": "normal", "hard": "hard"}

    title = recipe.get("title", "")
    description = recipe.get("description", "")
    ingredients_raw = recipe.get("ingredients_raw", "")
    servings = recipe.get("servings")
    cooking_time = recipe.get("cooking_time")
    difficulty = difficulty_map.get(recipe.get("difficulty", ""), "")
    category = recipe.get("category", [])
    tags = recipe.get("tags", [])
    tips = recipe.get("tips", [])

    parts = []
    if title:
        parts.append(f"{title} recipe.")
    if category:
        parts.append(f"Categories: {', '.join(category)}.")
    if description:
        parts.append(description)
    if ingredients_raw:
        parts.append(f"Ingredients: {ingredients_raw}.")
    if servings:
        parts.append(f"Servings: {servings}.")
    if cooking_time:
        parts.append(f"Cooking time: about {cooking_time} minutes.")
    if difficulty:
        parts.append(f"Difficulty: {difficulty}.")
    if tags:
        parts.append(f"Tags: {', '.join(tags)}.")
    if tips:
        parts.append(f"Tips: {' '.join(tips)}")

    text = " ".join(parts)
    logger.info("Embedding text generated:\n%s\n", text)
    return text


def get_embedding(recipe: dict) -> list[float]:
    text = build_embedding_text(recipe)
    response = client.embeddings.create(input=[text], model=config.EMBEDDING_MODEL)
    return response.data[0].embedding


def import_legacy_youtube_recipes():
    if not os.path.exists(JSON_FILE_PATH):
        logger.error("%s does not exist.", JSON_FILE_PATH)
        return

    with open(JSON_FILE_PATH, encoding="utf-8") as f:
        try:
            recipes_list = json.load(f)
            if not isinstance(recipes_list, list):
                logger.error("The JSON file must contain an array.")
                return
        except json.JSONDecodeError:
            logger.exception("Failed to parse JSON.")
            return

    db = SessionLocal()
    insert_count = 0
    skip_count = 0
    fail_count = 0

    url_counts: dict[str, int] = {}
    for data in recipes_list:
        url = data.get("video_url")
        if url:
            url_counts[url] = url_counts.get(url, 0) + 1
    duplicates = {url: cnt for url, cnt in url_counts.items() if cnt > 1}
    if duplicates:
        logger.warning("Found %s duplicate video_url values in JSON.", len(duplicates))
        for url, cnt in duplicates.items():
            logger.warning("Duplicate video_url: %s (%s)", url, cnt)

    logger.info("Processing %s legacy YouTube recipes.", len(recipes_list))

    try:
        existing_urls: set[str] = {
            row[0] for row in db.query(Recipe.video_url).all() if row[0]
        }
        logger.info("Found %s existing recipe video URLs.", len(existing_urls))

        for data in recipes_list:
            video_url = data.get("video_url")
            title = data.get("title", "Untitled")

            try:
                if video_url in existing_urls:
                    skip_count += 1
                    continue

                logger.info("Creating embedding for '%s'.", title)
                embedding = get_embedding(data)

                new_recipe = Recipe(
                    title=title,
                    description=data.get("description"),
                    ingredients=data.get("ingredients"),
                    ingredients_raw=data.get("ingredients_raw"),
                    instructions=data.get("instructions"),
                    servings=data.get("servings"),
                    cooking_time=data.get("cooking_time"),
                    calories=data.get("calories"),
                    difficulty=data.get("difficulty"),
                    category=data.get("category"),
                    tags=data.get("tags", []),
                    tips=data.get("tips", []),
                    content=data.get("content"),
                    video_url=video_url,
                    image_url=data.get("image_url"),
                    author_type="ADMIN",
                    embedding=embedding,
                )
                db.add(new_recipe)
                db.commit()
                existing_urls.add(video_url)

                insert_count += 1
                logger.info("Inserted '%s'.", title)

            except Exception:
                db.rollback()
                logger.exception("Failed to import '%s'.", title)
                fail_count += 1

    except Exception:
        logger.exception("Fatal error while importing legacy YouTube recipes.")
    finally:
        db.close()

    logger.info("=" * 30)
    logger.info("Done.")
    logger.info("Inserted: %s", insert_count)
    logger.info("Skipped: %s", skip_count)
    logger.info("Failed: %s", fail_count)
    logger.info("=" * 30)


if __name__ == "__main__":
    import_legacy_youtube_recipes()
