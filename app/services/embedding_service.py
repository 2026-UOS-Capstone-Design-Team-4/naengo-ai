from openai import OpenAI

from app.core import config

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class EmbeddingService:
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def embed_query(self, query: str) -> list[float]:
        response = self.client.embeddings.create(
            input=[query.replace("\n", " ")],
            model=self.model,
        )
        return response.data[0].embedding


embedding_service = EmbeddingService(
    client=OpenAI(api_key=config.EMBEDDING_API_KEY),
    model=config.EMBEDDING_MODEL or DEFAULT_EMBEDDING_MODEL,
)
