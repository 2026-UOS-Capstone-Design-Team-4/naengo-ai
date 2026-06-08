import base64
import re

from pydantic_ai import Agent
from pydantic_ai.messages import BinaryContent, ImageUrl, ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.core.system_prompts import MAIN_INTENT_CLASSIFIER_PROMPT
from app.agents.intent.intent_models import InputMode, MainIntentResult
from app.core import config

_DATA_URL_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL)


def _to_image_content(image: str) -> BinaryContent | ImageUrl:
    m = _DATA_URL_RE.match(image)
    if m:
        return BinaryContent(data=base64.b64decode(m.group(2)), media_type=m.group(1))
    return ImageUrl(url=image)


class MainIntentClassifier:
    def __init__(self) -> None:
        model = OpenAIChatModel(
            config.MODEL_NAME,
            provider=OpenAIProvider(api_key=config.API_KEY, base_url=config.BASE_URL),
        )
        self._agent = Agent(
            model,
            output_type=MainIntentResult,
            system_prompt=MAIN_INTENT_CLASSIFIER_PROMPT,
        )

    async def classify(
        self, message: str, history: list[ModelMessage], image: str | None = None
    ) -> MainIntentResult:
        prompt = [message, _to_image_content(image)] if image else message
        result = await self._agent.run(prompt, message_history=history)
        output = result.output
        if image and InputMode.IMAGE not in output.input_modes:
            output.input_modes.append(InputMode.IMAGE)
        return output


main_intent_classifier = MainIntentClassifier()
