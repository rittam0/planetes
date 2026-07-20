"""LangGraph ReAct agent workflow."""
import os
import time
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from backend.agents.tools import GetObjectTool, GetConjunctionsTool, ExplainEncounterTool
from backend.agents.rag import retrieve_context


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    investigation_id: str
    latency_ms: float


# Initialize tools
tools = [GetObjectTool(), GetConjunctionsTool(), ExplainEncounterTool()]
tool_node = ToolNode(tools)

# Initialize LLM with tools
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    api_key=os.getenv("OPENAI_API_KEY")
)
llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState) -> AgentState:
    """The agent decides what to do next."""
    start = time.time()

    # Retrieve relevant NASA context for grounding
    last_human_msg = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_human_msg = msg.content
            break

    context = ""
    if last_human_msg:
        chunks = retrieve_context(last_human_msg, k=2)
        context = "\n\nRELEVANT NASA DOCUMENTATION:\n" + "\n---\n".join(chunks)

    # Build messages with context
    messages = list(state["messages"])
    if context:
        messages.append(AIMessage(content=f"[System context: {context}]"))

    response = llm_with_tools.invoke(messages)

    latency = (time.time() - start) * 1000
    return {
        "messages": list(state["messages"]) + [response],
        "investigation_id": state.get("investigation_id", ""),
        "latency_ms": state.get("latency_ms", 0) + latency
    }


def should_continue(state: AgentState) -> str:
    """Determine if the agent should continue or end."""
    messages = state["messages"]
    last_message = messages[-1]

    # If the last message has tool calls, route to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # Otherwise end
    return END


# Build the graph
workflow_graph = StateGraph(AgentState)
workflow_graph.add_node("agent", agent_node)
workflow_graph.add_node("tools", tool_node)
workflow_graph.set_entry_point("agent")
workflow_graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow_graph.add_edge("tools", "agent")

# Compile
agent_executor = workflow_graph.compile()


def run_investigation(query: str, investigation_id: str = "") -> dict:
    """Run a full investigation and return structured results."""
    start = time.time()

    result = agent_executor.invoke({
        "messages": [HumanMessage(content=query)],
        "investigation_id": investigation_id,
        "latency_ms": 0
    })

    total_latency = (time.time() - start) * 1000

    # Extract the final AI message
    final_messages = result["messages"]
    final_response = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and not msg.content.startswith("[System context:"):
            final_response = msg.content
            break

    return {
        "investigation_id": investigation_id or f"inv_{int(time.time())}",
        "query": query,
        "response": final_response,
        "latency_ms": round(total_latency, 1),
        "tool_calls": sum(1 for m in final_messages if hasattr(m, "tool_calls") and m.tool_calls)
    }
