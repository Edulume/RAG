"""RAG chain implementation using LangChain and Ollama."""

import logging
from typing import Dict, Any

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from keiz.config import settings
from keiz.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


RAG_PROMPT_TEMPLATE = """You are a helpful educational AI assistant. Answer the question based on the context provided below.

Context from textbooks:
{context}

Question: {question}

Instructions:
- Use the context above to answer the question
- Be clear and educational in your explanation
- If the context contains relevant information, use it to provide a detailed answer
- Only say you don't know if the context truly doesn't contain any relevant information

Answer:"""


class RAGChain:
    """RAG chain for question answering over documents."""

    def __init__(self):
        """Initialize the RAG chain."""
        self.vector_store = get_vector_store()
        self.llm = self._create_llm()
        self.prompt = PromptTemplate(
            template=RAG_PROMPT_TEMPLATE,
            input_variables=["context", "question"],
        )

    def _create_llm(self) -> ChatOpenAI:
        """Create the LLM instance."""
        logger.info(f"Initializing LLM: {settings.llm_model}")
        logger.info(f"Using endpoint: {settings.llm_base_url}")

        llm = ChatOpenAI(
            model=settings.llm_model,
            openai_api_key=settings.llm_api_key,
            openai_api_base=settings.llm_base_url,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

        return llm

    def query(
        self,
        question: str,
        k: int = None,
        return_sources: bool = True,
    ) -> Dict[str, Any]:
        """
        Query the RAG system.

        Args:
            question: The question to answer
            k: Number of documents to retrieve
            return_sources: Whether to return source documents

        Returns:
            Dictionary with answer and optional sources
        """
        logger.info(f"Processing query: {question[:100]}...")

        # Retrieve relevant documents
        results = self.vector_store.similarity_search(question, k=k)

        if not results:
            logger.warning("No relevant documents found")
            return {
                "answer": "I don't have any relevant information to answer this question.",
                "sources": [],
            }

        # Prepare context
        context_parts = []
        sources = []

        for doc, score in results:
            context_parts.append(doc.page_content)
            if return_sources:
                sources.append({
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata,
                    "score": score,
                })

        context = "\n\n".join(context_parts)

        # Format prompt
        formatted_prompt = self.prompt.format(context=context, question=question)

        # Get LLM response
        logger.info("Generating answer with LLM")
        try:
            response = self.llm.invoke(formatted_prompt)
            answer = response.content

            result = {
                "answer": answer,
                "sources": sources if return_sources else [],
            }

            logger.info("Query processed successfully")
            return result

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    async def aquery(
        self,
        question: str,
        k: int = None,
        return_sources: bool = True,
    ) -> Dict[str, Any]:
        """Async version of query."""
        logger.info(f"Processing async query: {question[:100]}...")

        results = self.vector_store.similarity_search(question, k=k)

        if not results:
            return {
                "answer": "I don't have any relevant information to answer this question.",
                "sources": [],
            }

        context_parts = []
        sources = []

        for doc, score in results:
            context_parts.append(doc.page_content)
            if return_sources:
                sources.append({
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata,
                    "score": score,
                })

        context = "\n\n".join(context_parts)
        formatted_prompt = self.prompt.format(context=context, question=question)

        logger.info("Generating answer with LLM (async)")
        logger.debug(f"Prompt being sent to LLM:\n{formatted_prompt[:500]}...")
        try:
            response = await self.llm.ainvoke(formatted_prompt)
            answer = response.content
            
            logger.info(f"LLM response: {answer[:100]}...")

            return {
                "answer": answer,
                "sources": sources if return_sources else [],
            }

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise


_rag_chain = None


def get_rag_chain() -> RAGChain:
    """Get or create the global RAG chain instance."""
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = RAGChain()
    return _rag_chain
