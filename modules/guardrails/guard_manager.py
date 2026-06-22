import os
import sys
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import config

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config")

# Must match the bot messages defined in rails.co
_INPUT_BLOCKED_PREFIX = "I'm sorry, but I can't help with that request."
_OUTPUT_BLOCKED_PREFIX = "I'm sorry, I'm unable to provide that response."


def _extract_text(response) -> str:
    """Coerce NeMo generate() output to a plain string.
    Older versions return str; newer versions may return a dict."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return response.get("content") or response.get("response") or str(response)
    return str(response)


class GuardManager:
    """
    Guardrail layer powered by NeMo Guardrails.

    NeMo Guardrails integrates input check, LLM generation, and output check
    into a single pipeline. The primary entry point is generate().

    check_input() and check_output() are provided for callers that need to
    separate the safety checks from generation (e.g. when using GroqClient
    directly for generation). They work by running the NeMo pipeline and
    inspecting whether a rail blocked the response.
    """

    def __init__(self):
    # NeMo Guardrails calls an OpenAI-compatible API.
    # Groq provides one at api.groq.com/openai/v1.
        os.environ.setdefault("OPENAI_API_KEY", config.GROQ_API_KEY)
        os.environ.setdefault("OPENAI_API_BASE", "https://api.groq.com/openai/v1")

        try:
            from nemoguardrails import LLMRails, RailsConfig
            rails_config = RailsConfig.from_path(_CONFIG_PATH)

            # 動態注入 API key，確保從環境變數讀取而非寫死在 config.yml
            if rails_config.models and rails_config.models[0].parameters:
                rails_config.models[0].parameters["api_key"] = os.getenv("GROQ_API_KEY")

            self.rails = LLMRails(rails_config)
            self._enabled = True
            logger.info("NeMo Guardrails initialized.")
        except ImportError:
            logger.warning(
                "nemoguardrails is not installed. "
                "Run: pip install nemoguardrails"
            )
            self.rails = None
            self._enabled = False

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def generate(self, messages: list[dict]) -> str:
        """
        Full guardrail pipeline: input rail → LLM generation → output rail.

        Args:
            messages: Conversation history in OpenAI format,
                      e.g. [{"role": "user", "content": "..."}]

        Returns:
            The (possibly filtered) response string.
        """
        if not self._enabled or self.rails is None:
            raise RuntimeError(
                "GuardManager is disabled. Install nemoguardrails first."
            )
        return self.rails.generate(messages=messages)

    async def generate_async(self, messages: list[dict]) -> str:
        """Async version of generate()."""
        if not self._enabled or self.rails is None:
            raise RuntimeError(
                "GuardManager is disabled. Install nemoguardrails first."
            )
        return await self.rails.generate_async(messages=messages)

    # ------------------------------------------------------------------
    # Separate check helpers (for use with external LLM generation)
    # ------------------------------------------------------------------

    def check_input(self, user_message: str) -> tuple[bool, str]:
        """
        Run input guardrails on a user message without generating a full reply.

        How it works: NeMo Guardrails applies input rails during generate().
        We call generate() with just the user message and check whether the
        response matches the refusal string defined in rails.co.

        Returns:
            (True,  user_message)  — safe; proceed with your LLM call
            (False, refusal_msg)   — blocked; show refusal_msg to the user
        """
        if not self._enabled:
            return True, user_message

        raw = self.rails.generate(
            messages=[{"role": "user", "content": user_message}]
        )
        response = _extract_text(raw)
        if response.startswith(_INPUT_BLOCKED_PREFIX):
            return False, response
        return True, user_message

    def check_output(self, bot_response: str, user_message: str = "") -> tuple[bool, str]:
        """
        Run output guardrails on a bot response that was generated externally.

        How it works: We submit the externally generated response back to NeMo
        as a prior assistant turn, then ask for a continuation. NeMo applies
        output rails on the assistant message and either passes it through or
        replaces it with the filtered refusal string from rails.co.

        Note: For fully integrated guardrailing, prefer generate() over this
        method — it handles input and output in one pass.

        Returns:
            (True,  bot_response)  — safe; send to user
            (False, refusal_msg)   — blocked; show refusal_msg to the user
        """
        if not self._enabled:
            return True, bot_response

        messages = []
        if user_message:
            messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": bot_response})
        messages.append({"role": "user", "content": "Please confirm your previous response."})

        raw = self.rails.generate(messages=messages)
        response = _extract_text(raw)
        if response.startswith(_OUTPUT_BLOCKED_PREFIX):
            return False, response
        return True, bot_response
