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
import logging

# Configure logging for AI engine debugging
logger = logging.getLogger("ai.engine")
logger.setLevel(logging.DEBUG)

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
            logger.info("🔀 [_should_continue] No tool calls -> END")
            return "end"
        logger.info(f"🔀 [_should_continue] Tool calls detected: {[tc['name'] for tc in last_message.tool_calls]} -> CONTINUE")
        return "continue"

    def _create_call_model(self, llm_with_tools):
        """Create a model caller with the bound tools."""
        def call_model(state):
            messages = state["messages"]
            logger.info(f"🤖 [call_model] Invoking LLM with {len(messages)} messages")
            logger.debug(f"🤖 [call_model] Last message type: {type(messages[-1]).__name__}")
            response = llm_with_tools.invoke(messages)
            logger.info(f"🤖 [call_model] LLM Response type: {type(response).__name__}")
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info(f"🤖 [call_model] LLM wants to call tools: {[tc['name'] for tc in response.tool_calls]}")
            else:
                logger.info(f"🤖 [call_model] LLM final response: {response.content[:100]}...")
            return {"messages": [response]}
        return call_model

    async def run_command(self, text: str, auth_data: Dict[str, Any]):
        """The main entry point for the API to call."""
        logger.info(f"🚀 [run_command] ===== NEW REQUEST =====")
        logger.info(f"🚀 [run_command] User input: {text}")
        
        # Extract user info from auth_data
        user = auth_data["user"]
        token = auth_data["token"]
        logger.debug(f"🚀 [run_command] User ID: {user.id}")
        
        # Build tools with auth context for this request
        tools = get_ai_tools(auth_data)
        logger.info(f"🚀 [run_command] Tools bound: {[t.name for t in tools]}")
        llm_with_tools = self.llm.bind_tools(tools)
        graph = self._build_graph(llm_with_tools, tools)
        
        # Format system prompt with current date
        formatted_prompt = SYSTEM_PROMPT.format(current_date=date.today().isoformat())
        logger.debug(f"🚀 [run_command] System prompt formatted with date: {date.today().isoformat()}")
        
        initial_state = {
            "messages": [
                SystemMessage(content=formatted_prompt),
                HumanMessage(content=text)
            ],
            "owner_id": user.id,
            "token": token
        }
        
        logger.info("🚀 [run_command] Starting LangGraph execution...")
        final_state = await graph.ainvoke(initial_state)
        
        final_response = final_state["messages"][-1].content
        logger.info(f"🚀 [run_command] ===== REQUEST COMPLETE =====")
        logger.info(f"🚀 [run_command] Final response: {final_response[:200]}...")
        
        # Build execution trace
        trace = []
        messages = final_state["messages"]
        
        for i, msg in enumerate(messages):
            # Check for tool calls (AI requests)
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    trace_item = {
                        "type": "tool_call",
                        "tool": tc["name"],
                        "args": tc["args"],
                        "id": tc["id"]
                    }
                    trace.append(trace_item)
            
            # Check for tool outputs (Function results)
            if hasattr(msg, 'tool_call_id'):
                # Find the matching tool call in the trace to link them (optional, but good for UI)
                trace_item = {
                    "type": "tool_result",
                    "tool": msg.name, # LangGraph usually populates this
                    "result": msg.content,
                    "id": msg.tool_call_id
                }
                trace.append(trace_item)
        
        return {
            "answer": final_response,
            "trace": trace
        }