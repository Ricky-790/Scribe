import os
from typing import Dict, List, Literal, Union

from tavily import AsyncTavilyClient

from agents_service.tools.schemas import SearchResult


# async def get_tavily_client():
tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
# return tavily_client


async def web_search(query: str, max_results: int = 3) -> List[SearchResult] | Dict:
    """
    Performs a basic web search.

    Args:
        query (str): The search query.
        max_results (int): maximum number of results(1 <= x <= 5)

    Returns:
        List[SearchResult]: A list of search results, each containing:
            - url (str): The URL of the matching webpage.
            - content (str): A relevant text snippet from the page.
            - title (str, optional): The title of the webpage.
            - similarity_score (float, optional): Relevance score of the result to the query.
    """
    try:
        response = await tavily_client.search(query=query, max_results=max_results)
        return [
            SearchResult(
                url=result.get("url"),
                content=result.get("content"),
                title=result.get("title"),
                similarity_score=result.get("score"),
            )
            for result in response.get("results")
        ]
    except Exception as e:
        return {"error": str(e)}


async def extract_page(
    urls: Union[List[str], str],
    extract_depth: Literal["basic", "advanced"] | None = None,
    chunks_per_source: int | None = None,
    query: str | None = None,
) -> List[SearchResult] | Dict:
    """
    Extracts content from a specific or known list of URLs

    Args:
        urls (Union[List[str], str]): A single URL or a list of URLs to extract content from.
        extract_depth (Literal["basic", "advanced"], optional): depth of the extraction process. Advanced extraction retrieves more data, including tables and embedded content
        chunks_per_source (int, optional): Maximum number of relevant chunks returned per source and control the raw_content length (1 <= x <= 5).
        query (str, optional): Intent for reranking extracted content chunks. When provided, chunks are reranked based on relevance to this query.

    Returns:
        List[SearchResult]: A list of search results, each containing:
            - url (str): The URL of the matching webpage.
            - content (str): A relevant text snippet from the page.
            - title (str, optional): The title of the webpage.
            - similarity_score (float, optional): Relevance score of the result to the query. Not populated for this tool.
    """
    try:
        response = await tavily_client.extract(
            urls=urls,
            extract_depth=extract_depth,
            chunks_per_source=chunks_per_source,
            query=query,
        )
        return [
            SearchResult(
                url=result.get("url"),
                content=result.get("raw_content"),
                title=result.get("title"),
            )
            for result in response.get("results")
        ]
    except Exception as e:
        return {"error": str(e)}


async def crawl_page(
    url: str,
    instructions: str | None = None,
    chunks_per_source: int | None = None,
    max_depth: int | None = None,
    max_breadth: int | None = None,
    limit: int | None = None,
    extract_depth: Literal["basic", "advanced"] | None = None,
) -> List[SearchResult] | Dict:
    """
    Crawls a website starting from a root URL.

    Args:
        url (str): The root URL to start crawling from.
        instructions (str, optional): Natural language instructions guiding what information or pages to find.
        chunks_per_source (int, optional): Maximum number of relevant content chunks returned per source (1 <= x <= 5).
        max_depth (int, optional): Maximum depth of link traversal from the root URL.
        max_breadth (int, optional): Maximum number of links to follow per page at each level.
        limit (int, optional): Maximum total number of pages to crawl across the process.
        extract_depth (Literal["basic", "advanced"], optional): Depth of extraction. "advanced" retrieves more data, including tables and embedded content.

    Returns:
        List[SearchResult]: A list of search results, each containing:
            - url (str): The URL of the matching webpage.
            - content (str): A relevant text snippet from the page.
            - title (str, optional): The title of the webpage. Not populated for this tool.
            - similarity_score (float, optional): Relevance score of the result to the query. Not populated for this tool.
    """
    try:
        response = await tavily_client.crawl(
            url=url,
            instructions=instructions,
            chunks_per_source=chunks_per_source,
            max_depth=max_depth,
            max_breadth=max_breadth,
            limit=limit,
            extract_depth=extract_depth,
        )
        return [
            SearchResult(
                url=result.get("url"),
                content=result.get("raw_content"),
            )
            for result in response.get("results")
        ]
    except Exception as e:
        return {"error": str(e)}
