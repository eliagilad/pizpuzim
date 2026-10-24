from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.prompts import SYSTEM_PROMPT, system_prompt
from agent.state import AgentState
from config import Settings, load_settings
from tools import AGENT_TOOLS


class AgentError(Exception):
    pass


def build_openai_model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)


def build_graph(model: BaseChatModel, tools: list[BaseTool]) -> CompiledStateGraph:
    def agent(state: AgentState) -> dict:
        llm = model.bind_tools(tools) if tools else model
        response = llm.invoke([SystemMessage(content=system_prompt()), *state["messages"]])
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_edge(START, "agent")
    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
    else:
        graph.add_edge("agent", END)
    return graph.compile()


def run_turn(graph: CompiledStateGraph, messages: list[AnyMessage]) -> str:
    try:
        result = graph.invoke({"messages": messages})
    except Exception as exc:
        raise AgentError(type(exc).__name__) from exc
    for message in reversed(result["messages"]):
        if isinstance(message, AIMessage) and not message.tool_calls:
            if isinstance(message.content, str):
                return message.content
            raise AgentError("Model returned a non-text reply")
    raise AgentError("Model returned no reply")


def build_app(settings: Settings | None = None) -> CompiledStateGraph:
    settings = settings or load_settings()
    return build_graph(build_openai_model(settings), AGENT_TOOLS)
