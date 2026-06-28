import json
import logging
from typing import Optional


class AgentManager:
    """
    Agentic flow: the LLM decides which tool to call based on the user's message.
    Contrast with Manual Mode where the user explicitly toggles tools.
    """

    def __init__(self, groq_client, rag_manager, search_manager):
        self.llm = groq_client
        self.rag = rag_manager
        self.search = search_manager
        self.tools = self._define_tools()

    # ── Part 1: Tool definitions ──────────────────────────────────────────────
    # The description is the ONLY signal the LLM uses to decide which tool to call.
    # Vague descriptions = wrong routing. Be explicit about when each tool applies.

    def _define_tools(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": (
                        "Search the internet for recent, real-time, or current information. "
                        "Use this when the question involves recent events, news, current data, "
                        "or anything that may have changed after the model's training cutoff."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to look up on the internet"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_knowledge_base",
                    "description": (
                        "Search the local knowledge base of uploaded PDF documents. "
                        "Use this when the question is about specific documents, academic papers, "
                        "or research materials that have been uploaded to the system."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to search within the uploaded documents"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    # ── Part 2: Tool execution ────────────────────────────────────────────────

    def _execute_tool(self, tool_name: str, query: str) -> str:
        if tool_name == "search_web":
            return self.search.get_prompt_with_context(query)
        elif tool_name == "query_knowledge_base":
            if not self.rag.is_built():
                return "Knowledge base is empty. No documents have been uploaded yet."
            return self.rag.get_prompt_with_context(query)
        return f"Unknown tool: {tool_name}"

    # ── Part 3: The two-step dispatch ─────────────────────────────────────────

    def dispatch(
        self,
        user_message: str,
        message_history: list,
        system_prompt: str
    ) -> tuple[str, str, Optional[str]]:
        """
        Let the LLM decide which tool to call, execute it, then return the final answer.

        Returns:
            answer     — the LLM's final text response
            tool_used  — "search_web" | "query_knowledge_base" | "none"
            query_used — the query passed to the tool, or None if no tool was called
        """
        # Build the message list for the first API call
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(message_history)
        messages.append({"role": "user", "content": user_message})

        # ── Step 1: First API call — let LLM decide if it needs a tool ────────
        first_response = self.llm.generate_with_tools(
            messages=messages,
            tools=self.tools,
        )

        choice = first_response.choices[0]

        # LLM decided no tool is needed — return the answer directly
        if not choice.message.tool_calls:
            logging.info("[AgentManager] No tool called. Answering directly.")
            return choice.message.content or "", "none", None

        # ── Step 2: Parse what tool the LLM wants to call ─────────────────────
        tool_call = choice.message.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        query = tool_args.get("query", user_message)

        logging.info(f"[AgentManager] Tool called: {tool_name} | Query: {query}")

        # ── Step 3: Execute the tool ───────────────────────────────────────────
        tool_result = self._execute_tool(tool_name, query)

        # ── Step 4: Second API call — feed tool result back to LLM ────────────
        # We must append the assistant's tool_call message AND the tool result
        # before calling the LLM again. This is the "role: tool" step.
        messages.append({
            "role": "assistant",
            "content": choice.message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in choice.message.tool_calls
            ]
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result
        })

        final_response = self.llm.generate_with_tools(
            messages=messages,
            tools=self.tools,
        )

        answer = final_response.choices[0].message.content or ""
        return answer, tool_name, query
