# The Brain: Coordinates LangGraph flow & state
# backend/app/services/ai/engine.py
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from app.core.config import settings
from app.services.ai.tools import get_ai_tools
from app.services.ai.prompts import SYSTEM_PROMPT
from datetime import date
import operator

# 1. Define the Agent State
class AgentState(TypedDict):
    # Annotating with operator.add allows messages to be appended rather than overwritten
    messages: Annotated[List[BaseMessage], operator.add]
    owner_id: str
    token: str

class LedgerEngine:
    def __init__(self):
        # Initialize Groq LPU inference (shared across requests)
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.LLM_MODEL,
            temperature=0
        )

    def _build_graph(self, llm_with_tools, tools):
        """Build the LangGraph workflow with request-specific tools."""
        workflow = StateGraph(AgentState)

        # Define the two nodes
        workflow.add_node("agent", self._create_call_model(llm_with_tools))
        workflow.add_node("action", ToolNode(tools))

        # Define the edges
        workflow.set_entry_point("agent")
        
        # Conditional edge: Should we call a tool or finish?
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "action",
                "end": END
            }
        )

        # After a tool runs, it always goes back to the agent to analyze the result
        workflow.add_edge("action", "agent")

        return workflow.compile()

    def _should_continue(self, state):
        messages = state["messages"]
        last_message = messages[-1]
        if not last_message.tool_calls:
            return "end"
        return "continue"

    def _create_call_model(self, llm_with_tools):
        """Create a model caller with the bound tools."""
        def call_model(state):
            messages = state["messages"]
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        return call_model

    async def run_command(self, text: str, auth_data: Dict[str, Any]):
        """The main entry point for the API to call."""
        # Extract user info from auth_data
        user = auth_data["user"]
        token = auth_data["token"]
        
        # Build tools with auth context for this request
        tools = get_ai_tools(auth_data)
        llm_with_tools = self.llm.bind_tools(tools)
        graph = self._build_graph(llm_with_tools, tools)
        
        # Format system prompt with current date
        formatted_prompt = SYSTEM_PROMPT.format(current_date=date.today().isoformat())
        
        initial_state = {
            "messages": [
                SystemMessage(content=formatted_prompt),
                HumanMessage(content=text)
            ],
            "owner_id": user.id,
            "token": token
        }
        
        final_state = await graph.ainvoke(initial_state)
        return final_state["messages"][-1].content