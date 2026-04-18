from typing import Dict, Any
from agents.graph.state import ResearchState
from agents.tools.computer_use import BrowserSession, browser_search_housing_news
from agents.a2a.protocol import TaskResult
from agents.utils.sentiment import extract as extract_sentiment

async def run(state: ResearchState) -> Dict[str, Any]:
    """News Analyst node: Researches housing news and sentiment."""
    
    query = state["query"]
    session = BrowserSession(headless=True)
    completed_tasks = state.get("completed_tasks", [])
    
    try:
        # Start browser session
        await session.start()
        
        # Search for housing news across sources
        news_results = await browser_search_housing_news(session, query)
        
        # Stop browser session
        await session.stop()
        
        scored_news = []
        combined_text = ""
        for r in news_results:
            text = str(r).lower()
            score = 0.5
            if query.lower() in text: score += 0.3
            if "market" in text: score += 0.1
            if "price" in text: score += 0.1
            scored_news.append({**r, "relevance_score": min(1.0, score)})
            combined_text += " " + text

        sentiment = extract_sentiment(combined_text)
            
        # Create TaskResult
        result = TaskResult(
            task_id="news_research_task",
            agent_id="news_analyst",
            output={
                "news_summary": f"Analyzed {len(news_results)} news sources for {query}.",
                "market_sentiment": sentiment,
                "articles": scored_news
            },
            status="success"
        )
        
        return {
            "news_data": scored_news,
            "completed_tasks": completed_tasks + [result.model_dump()],
            "pending_tasks": state.get("pending_tasks", []),
            "messages": [("ai", f"News Analyst completed real estate news research from Realtor/Zillow/Redfin.")],
            "next_agent": "news_analyst"
        }
    except Exception as e:
        if session.browser:
            await session.stop()
        return {
            "messages": [("system", f"News Analyst encountered an error: {str(e)}")],
            "next_agent": "END"
        }
