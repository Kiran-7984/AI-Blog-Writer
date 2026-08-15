from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from graph import final_agent
from uuid import uuid4
import json
import traceback

app = FastAPI(
    title="AI Blog Writer",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


KNOWN_NODES = {"router", "research", "orchestrator", "worker", "reducer"}


class BlogRequest(BaseModel):
    topic: str


@app.get("/")
def root():
    return {
        "message": "AI Blog Writer API Running"
    }


@app.post("/generate")
async def generate_blog(request: BlogRequest):

    initial_state = {
        "topic": request.topic,
        "plan": None,
        "needs_research": False,
        "Search": [],
        "queries": [],
        "sections": [],
        "final_blog": "",
    }

    thread_id = str(uuid4())

    async def event_stream():
        try:
            final_state = None

            async for event in final_agent.astream_events(
                initial_state,
                version="v2",
                config={
                    "configurable": {
                        "thread_id": thread_id
                    }
                },
            ):
                event_name = event.get("event")
                node_name = event.get("name")

                if node_name not in KNOWN_NODES:
                    continue

                # Node Started
                if event_name == "on_chain_start":
                    yield f"data: {json.dumps({'type': 'node_start', 'node': node_name})}\n\n"

                # Node Finished
                elif event_name == "on_chain_end":
                    yield f"data: {json.dumps({'type': 'node_end', 'node': node_name})}\n\n"
                    if node_name == "reducer":
                        output = event.get("data", {}).get("output", {})
                        final_state = output.get("final_blog") if isinstance(output, dict) else None


            yield f"data: {json.dumps({'type': 'completed', 'final_blog': final_state or ''})}\n\n"

        except Exception as e:
            traceback.print_exc()
            error_msg = str(e)
            if "ResourceExhausted" in error_msg or "429" in error_msg:
                friendly = "Gemini free tier quota exceeded. Please wait a minute and try again."
            else:
                friendly = f"Generation failed: {error_msg}"
            
            yield f"data: {json.dumps({'type': 'error', 'message': friendly})}\n\n"
            

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
