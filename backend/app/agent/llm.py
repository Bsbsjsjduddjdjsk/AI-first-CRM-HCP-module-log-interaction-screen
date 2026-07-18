"""
Thin wrappers around Groq-hosted models via langchain-groq.

- fast_llm  -> gemma2-9b-it       : low-latency turns (routing, extraction, diffing)
- reasoning_llm -> llama-3.3-70b-versatile : deeper reasoning (compliance nuance,
  next-best-action suggestions) where a little extra latency is acceptable.
"""
from langchain_groq import ChatGroq

from ..config import settings

fast_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_fast_model,
    temperature=0,
)

reasoning_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_reasoning_model,
    temperature=0.2,
)
