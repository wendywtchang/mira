"""
MIRA - Groq LLM Client
Handles communication with the Groq API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import logging
from typing import List, Dict, Optional

from groq import Groq
import config

class GroqClient:
    """
    Groq LLM Client for MIRA
    Provides methods for interacting with the Groq API
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Groq client

        Args:
            api_key: Groq API key. If not provided, retrieves from environment or config.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or config.GROQ_API_KEY
        if not self.api_key:
            logging.warning("No Groq API key provided. Some functions will be unavailable.")

        self.client = Groq(api_key=self.api_key)

        self.model = config.LLM_CONFIG["groq"]["default_model"]
        self.tool_use_model = config.LLM_CONFIG["groq"]["tool_use_model"]
        self.tool_use_fallback_model = config.LLM_CONFIG["groq"]["tool_use_fallback_model"]
        self.temperature = config.LLM_CONFIG["groq"]["temperature"]
        self.max_tokens = config.LLM_CONFIG["groq"]["max_tokens"]

        logging.info(f"Groq client initialized with model: {self.model}")

    def generate_response(self,
                          messages: List[Dict[str, str]],
                          system_prompt: Optional[str] = None) -> str:
        """
        Generate a response from the Groq LLM

        Args:
            messages: List of conversation messages [{"role": "user/assistant", "content": "..."}]
            system_prompt: Optional system prompt to guide the model's behavior

        Returns:
            Generated response text
        """
        if not self.api_key:
            return "Unable to generate response: no API key provided."

        try:
            formatted_messages = []

            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})

            for msg in messages:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            if response.choices and response.choices[0].message:
                return response.choices[0].message.content or ""
            else:
                logging.warning("Groq API returned an empty response.")
                return ""

        except Exception as e:
            logging.error(f"Error while calling Groq API: {e}")
            return f"An error occurred while generating a response: {str(e)}"

    def generate_with_tools(self,
                            messages: List[Dict],
                            tools: List[Dict],
                            system_prompt: Optional[str] = None):
        """
        Call the Groq API with tool definitions.
        Falls back to tool_use_fallback_model if the primary model fails (e.g. rate limit).
        Returns the raw response object so the caller can inspect tool_calls or text.
        """
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        try:
            return self.client.chat.completions.create(
                model=self.tool_use_model,
                messages=formatted_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0,  # deterministic output reduces malformed tool calls
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            logging.warning(
                f"[generate_with_tools] Primary model '{self.tool_use_model}' failed: {e}. "
                f"Falling back to '{self.tool_use_fallback_model}'."
            )
            return self.client.chat.completions.create(
                model=self.tool_use_fallback_model,
                messages=formatted_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0,
                max_tokens=self.max_tokens,
            )

    def generate_response_with_fallback(self,
                                        messages: List[Dict[str, str]],
                                        system_prompt: Optional[str] = None) -> str:
        """
        Attempt to generate a response, falling back to a simplified request if an error occurs.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt

        Returns:
            Generated response text
        """
        try:
            return self.generate_response(messages, system_prompt)
        except Exception as e:
            logging.error(f"Primary model failed, attempting fallback: {e}")
            try:
                if messages:
                    last_message = messages[-1]
                    simple_response = self.generate_response([last_message], system_prompt)
                    return simple_response + "\n(Note: Due to a technical issue, only the last message was processed.)"
                else:
                    return "Unable to generate a response: no messages provided."
            except Exception as e2:
                logging.error(f"Fallback also failed: {e2}")
                return "Sorry, I am unable to process your request at the moment. Please try again later."


def test_groq_client():
    """
    Test the Groq client
    """
    client = GroqClient()

    messages = [
        {"role": "user", "content": "Hello, please introduce yourself."}
    ]
    system_prompt = "You are MIRA, a helpful AI research assistant."

    try:
        response = client.generate_response(messages, system_prompt)
        print(f"Generated response: {response}")
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    test_groq_client()