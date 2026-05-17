from app.models.recipe import RecipeMedia, RecipeStep
from app.models.recipe_source import RecipeSourceExtractedStep
from app.services.ingestion.recipe_import_service import RecipeImportService
from app.services.ingestion.recipe_text_rewrite_service import (
    RecipeTextDraft,
    StepTextDraft,
)


class FakeDb:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)


def test_import_steps_do_not_create_media_from_source_image_urls():
    db = FakeDb()
    service = RecipeImportService(db)
    draft = RecipeTextDraft(
        title="테스트 레시피",
        summary=None,
        description="테스트 설명",
        ingredients=[],
        steps=[
            StepTextDraft(
                step_no=1,
                instruction="재료를 섞습니다.",
                source_image_url="https://source.example/step.jpg",
                tip=None,
                sort_order=1,
            )
        ],
        tips=[],
    )

    service._add_steps(recipe_id=10, draft=draft)

    assert any(isinstance(item, RecipeStep) for item in db.added)
    assert not any(isinstance(item, RecipeMedia) for item in db.added)


def test_source_step_image_url_remains_available_in_staging_model():
    step = RecipeSourceExtractedStep(
        step_no=1,
        instruction="원본 조리 설명",
        source_image_url="https://source.example/step.jpg",
    )

    assert step.source_image_url == "https://source.example/step.jpg"
