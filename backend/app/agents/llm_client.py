"""
Shared LLM client: Groq primary, Gemini fallback.

Why this exists as its own module: both the Critic Agent and the
Synthesizer Agent need "give me structured JSON back from an LLM,
and don't die if one provider is down." Rather than duplicating that
logic, both call `generate_json()` here.

Uses LangChain's ChatGroq / ChatGoogleGenerativeAI wrappers with
.with_fallbacks() and .with_structured_output() — this replaces what
used to be a hand-written try/except loop plus manual JSON-fence
stripping and Pydantic validation. Same behavior (Groq first, Gemini
if Groq fails, output validated against a Pydantic model), just built
on LangChain's existing implementation of that pattern instead of a
hand-rolled one.
"""
import logging
from typing import Type, TypeVar

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from google import genai
from google.genai import types as genai_types

from app.config import settings

logger = logging.getLogger("research_assistant")

T = TypeVar("T", bound=BaseModel)

class LLMUnavailableError(RuntimeError):
    """Raised when both Groq and Gemini fail (or no keys are configured)."""


def _build_fallback_chain(response_model: Type[T]):
    """
    Groq wrapped with .with_structured_output() first; Gemini as the
    .with_fallbacks() target if Groq raises for any reason. Both models
    return an already-validated instance of response_model directly —
    no manual JSON parsing needed, LangChain handles that internally.
    """
    groq_model = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
    ).with_structured_output(response_model)

    gemini_model = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
    ).with_structured_output(response_model)

    return groq_model.with_fallbacks([gemini_model])


async def generate_json(system_prompt: str, user_prompt: str, response_model: Type[T]) -> T:
    """
    Calls Groq first, falls back to Gemini, returns an already-validated
    response_model instance. Raises LLMUnavailableError if both fail,
    or if neither API key is configured at all.
    """
    if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        raise LLMUnavailableError("No LLM provider configured (GROQ_API_KEY and GEMINI_API_KEY both missing)")

    chain = _build_fallback_chain(response_model)
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    try:
        return await chain.ainvoke(messages)
    except Exception as exc:  # noqa: BLE001 - both providers in the fallback chain already failed by this point
        logger.warning(f"llm_client: both Groq and Gemini failed: {exc}")
        raise LLMUnavailableError(f"All LLM providers failed. Last error: {exc}") from exc


async def embed_text(text: str, task_type: str = "retrieval_document") -> list[float]:
    """
    Embeds text for RAG storage/retrieval. Uses Gemini's embedding model —
    since GEMINI_API_KEY is already required for the LLM fallback, this
    avoids adding a second provider just for embeddings.

    task_type matters: Gemini uses asymmetric embeddings, so a search query
    and the documents it's matched against are embedded differently for
    better retrieval accuracy.
      - "retrieval_query"    -> use when embedding the user's search query
      - "retrieval_document" -> use when embedding text going INTO storage
    """
    if not settings.GEMINI_API_KEY:
        raise LLMUnavailableError("GEMINI_API_KEY not configured (required for embeddings)")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = await client.aio.models.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        contents=text,
        config=genai_types.EmbedContentConfig(task_type=task_type, output_dimensionality=768),
    )
    return response.embeddings[0].values