from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = (
    "sentence-transformers/"
    "all-MiniLM-L6-v2"
)

EMBEDDING_DIMENSION = 384


class EmbeddingError(Exception):
    pass


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(
        MODEL_NAME
    )


def _split_into_chunks(
    text: str,
    model: SentenceTransformer,
) -> list[str]:
    token_ids = model.tokenizer.encode(
        text,
        add_special_tokens=False,
    )

    chunk_size = max(
        32,
        model.max_seq_length - 2,
    )

    chunks = []

    for start in range(
        0,
        len(token_ids),
        chunk_size,
    ):
        chunk_ids = token_ids[
            start:start + chunk_size
        ]

        chunk_text = model.tokenizer.decode(
            chunk_ids,
            skip_special_tokens=True,
        ).strip()

        if chunk_text:
            chunks.append(
                chunk_text
            )

    return chunks


def create_embedding(
    text: str,
) -> list[float]:
    cleaned_text = " ".join(
        text.split()
    )

    if not cleaned_text:
        raise EmbeddingError(
            "Cannot embed empty text."
        )

    try:
        model = get_embedding_model()

        chunks = _split_into_chunks(
            cleaned_text,
            model,
        )

        if not chunks:
            raise EmbeddingError(
                "No text chunks could be created."
            )

        chunk_embeddings = model.encode(
            chunks,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        embedding = np.mean(
            chunk_embeddings,
            axis=0,
        )

        norm = np.linalg.norm(
            embedding
        )

        if norm == 0:
            raise EmbeddingError(
                "Embedding has zero magnitude."
            )

        embedding = (
            embedding / norm
        )

    except EmbeddingError:
        raise

    except Exception as exc:
        raise EmbeddingError(
            f"Embedding generation failed: {exc}"
        ) from exc

    values = embedding.tolist()

    if len(values) != EMBEDDING_DIMENSION:
        raise EmbeddingError(
            "Unexpected embedding dimension: "
            f"{len(values)}"
        )

    return values