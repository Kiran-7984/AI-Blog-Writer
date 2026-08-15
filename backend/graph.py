from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from datetime import date, timedelta
from pathlib import Path
from typing import TypedDict, List, Optional, Literal, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
import operator
from langchain_core.messages import SystemMessage,HumanMessage
import os
import asyncio
from langgraph.checkpoint.sqlite import SqliteSaver , sqlite3
load_dotenv()

conn = sqlite3.connect("blog_writer.db",check_same_thread=False)
checkpointer = SqliteSaver(conn)
checkpointer.setup()

ai = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite",temperature=0)

async def safe_ainvoke(llm, messages, max_retries: int = 2, base_delay: float = 2.0):
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await llm.ainvoke(messages)
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            if any(x in error_str for x in ["resourceexhausted", "429", "503", "unavailable", "timeout"]):
                wait_time = base_delay * (2 ** attempt)
                print(f"[Retry {attempt+1}/{max_retries}] Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise e   # Non-retryable → fail immediately

    raise last_exception   # After retries exhausted → raise

class Task(BaseModel):
    task_title: str = Field(description="please mention the title of the task that is to be done by model")
    id : int
    description: str = Field(description="Mention the points that are to be mentioned in this title")

class Plan(BaseModel):
    blog_title:str = Field(description="Mention the overall blog title suitable for the input")
    blog_kind: Literal["explainer", "tutorial", "news_roundup", "comparison", "system_design"]
    tasks:List[Task]

class tavily_search(BaseModel):
    title: str
    url: str
    content: str
    source: Optional[str] = None

class searched_results(BaseModel):
    search : List[tavily_search] = Field(default_factory=list)

class router_decesion(BaseModel):
    queries : List[str]= Field(default_factory=list)
    needs_research : bool

class ReviewReport(BaseModel):
    overall_score: int = Field(...,description="rate the overall generated section")
    needs_revision: bool
    grammar_score: int
    readability_score: int
    factual_score: int
    issues: list[str]
    suggestions: list[str]

class State(TypedDict):
    topic : str
    plan: Optional[Plan]
    needs_research: bool
    Search : List[tavily_search]
    queries: List[str]
    sections : Annotated[List[tuple[int, str]], operator.add] 
    final_blog:str

from prompts import (
    route_message,
    research_message,
    orchestrator_message,
    worker_message,
    reviewer_message,
)

async def router_node(state : State):
    input = state["topic"]
    decider = ai.with_structured_output(router_decesion)
    decision =await safe_ainvoke( decider,
        [
            route_message,
            HumanMessage(content=f"Topic: {state['topic']}"),
        ]
    )

    return {"needs_research" : decision.needs_research,
            "queries": decision.queries }


async def tavily(queries,max_results):
    if not os.getenv("TAVILY_API_KEY"):
        return []
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults 
        tool = TavilySearchResults(max_results=max_results)
        results = await tool.ainvoke({"query": queries})
        out: List[dict] = []
        for r in results or []:
            out.append(
                {
                    "content": r.get("content") or "",
                    "url": r.get("url") or "",
                    "source": r.get("source"),
                }
            )
        return out
    except Exception as e:
        print("TAVILY ERROR:", e)
        return []


async def research_node(state : State) -> dict:
    queries = (state.get("queries") or [])[:10]
    raw: List[dict] = []
    print("Waiting for tavily")
    for q in queries:
        raw.extend(await tavily(q,max_results = 5))
        
    if not raw:
        return {"Search": []}
    extractor = ai.with_structured_output(searched_results)
    pack = await safe_ainvoke( extractor,
        [
            research_message,
            HumanMessage(
                content=(
                    f"Raw results:\n{raw}"
                )
            ),
        ]
    )

    dedup = {}
    for e in pack.search:
        if e.url:
            dedup[e.url] = e
    searched = list(dedup.values())

    return {"Search" : searched}

async def orchestrator_node(state: State):
    blog_topic = state.get("topic")
    web_result = state.get("Search",[]) 
    orchestrator_structured = ai.with_structured_output(Plan)
    orches_output = await safe_ainvoke(orchestrator_structured , [
        orchestrator_message ,
        HumanMessage(content=
                     f"Topic: {blog_topic}\n"
                    f"Web_searched_results:\n{[w.model_dump() for w in web_result][:16]}")
    ])
    return {"plan" : orches_output}

def fanout(state: State):
    if state["plan"] is None:
      raise ValueError("Plan was not generated before fanout().")
    return [Send("worker",{
                "task": task.model_dump(),
                "blog_topic": state["topic"],
                "plan": state["plan"].model_dump(),
                "Searched_results": [r.model_dump() for r in state.get("Search", [])],
    })for task in state["plan"].tasks]


MAX_REVIEW_ATTEMPTS = 2 

def _extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts).strip()
    return str(content).strip()

async def _generate_section(task: Task, plan: Plan, topic: str, evidence_text: str, feedback: str = "") -> str:
    feedback_block = f"\n\nPrevious reviewer feedback to address:\n{feedback}" if feedback else ""
    result = await safe_ainvoke( ai , [
        worker_message,
        HumanMessage(
            content=f"""
    Blog title: {plan.blog_title},
    Topic: {topic},
    Current Task Title : {task.task_title},
    Description : {task.description}
    Overall plan: {plan.model_dump()},
    Content : {evidence_text}
    feedback: {feedback_block}
    Please attach the urls in the ([Source](URL)) form at the end of each relevant content block"""
        ),
    ])

    return _extract_text(result.content)


async def _review_section(section_text: str) -> ReviewReport:
    review_llm = ai.with_structured_output(ReviewReport)
    return await safe_ainvoke( review_llm , [
        reviewer_message,
        HumanMessage(content=f"You are given the individual section\n\nSection content:\n{section_text}"),
    ])


async def worker_node(payload:dict):
    task = Task(**payload["task"])
    plan = Plan(**payload["plan"])
    overall_topic = payload["blog_topic"]
    evidence = [tavily_search(**e) for e in payload.get("Searched_results", [])]
    if evidence:
        evidence_text = "\n\n".join(
            f"""
        Evidence {idx}
        Title: {item.title}
        Source: {item.source or "Unknown"}
        Content:
        {item.content.strip()}

        [Source URL]({item.url})
        """.strip()
                for idx, item in enumerate(evidence[:20], start=1)
            )
    else:
        evidence_text = "No external research evidence was provided. Use reliable domain knowledge only."
    
    section = await _generate_section(task, plan, overall_topic, evidence_text)

    for _ in range(MAX_REVIEW_ATTEMPTS):
        review = await _review_section(section)
        if not review.needs_revision:
            break
        feedback = "\n\n".join(f"- {issue}" for issue in review.issues)
        if review.suggestions:
            feedback += "\n" + "\n".join(f"- {s}" for s in review.suggestions)
        section = await _generate_section(task, plan, overall_topic, section , feedback=feedback)

    return {"sections": [(task.id, section)]}

    
def route_next(state: State) -> str:
    return "research" if state["needs_research"] else "orchestrator"


def merge_content(state: State) -> dict:
    plan = state["plan"]
    if plan is None:
        raise ValueError("merge_content called without plan.")
    ordered_sections = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
    body = "\n\n".join(ordered_sections).strip()
    merged_md = f"# {plan.blog_title}\n\n{body}\n"
    
    return {"final_blog": merged_md}

graph = StateGraph(State)
graph.add_node("router", router_node)
graph.add_node("research", research_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("worker", worker_node)
graph.add_node("reducer", merge_content)

graph.add_edge(START, "router")
graph.add_conditional_edges("router", route_next, {"research": "research", "orchestrator": "orchestrator"})
graph.add_edge("research", "orchestrator")

graph.add_conditional_edges("orchestrator", fanout, ["worker"])
graph.add_edge("worker", "reducer")
graph.add_edge("reducer", END)

final_agent = graph.compile()
