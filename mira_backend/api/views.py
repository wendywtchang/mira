"""
MIRA Django Views
Handles API endpoints for the MIRA AI assistant
"""
import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import config
from modules.agent.agent_manager import AgentManager
from modules.guardrails.guard_manager import GuardManager

# # 添加根目錄到 Python 路徑
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_dir)
# sys.path.append(project_root)
from modules.llm.groq_client import GroqClient
from modules.rag import RAGManager
from modules.websearch import SearchManager

# 模組層級初始化：防止每次收到請求都重新載入，很慢
llm_client = GroqClient()
# 用 config.DATA_DIR 產生絕對路徑，避免 Django 從 mira_backend/ 啟動時找錯位置
rag = RAGManager(persist_dir=str(config.DATA_DIR / 'vector_store'))
if rag.is_built():
    rag.load()
search = SearchManager()
guard = GuardManager()
agent = AgentManager(llm_client, rag, search)

def health_check(request):
    return JsonResponse({'status': 'ok'})

@csrf_exempt
def chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            conversation_id = data.get('conversation_id', '')
            message_history = data.get('message_history', [])
            use_rag = data.get('use_rag', False)
            use_websearch = data.get('use_websearch', False)
            use_guardrails = data.get('use_guardrails', False)
            use_agentic = data.get('use_agentic', False)

            # Guardrails input check runs for BOTH modes — no duplication needed
            if use_guardrails:
                allowed, result = guard.check_input(user_message)
                if not allowed:
                    message_history.append({"role": "user", "content": user_message})
                    message_history.append({"role": "assistant", "content": result})
                    return JsonResponse({
                        'status': 'success',
                        'response': result,
                        'conversation_id': conversation_id,
                        'message_history': message_history,
                        'guardrail_triggered': 'input',
                    })

            if use_agentic:
                # ── Agentic mode: LLM decides which tool to call ──────────────
                reply, tool_used, query_used = agent.dispatch(
                    user_message=user_message,
                    message_history=message_history,
                    system_prompt=config.SYSTEM_PROMPT,
                )
                extra = {'mode': 'agentic', 'tool_used': tool_used, 'query_used': query_used}
            else:
                # ── Manual mode: user decides which tool to use ───────────────
                # 優先序：websearch > RAG > 一般對話
                if use_websearch:
                    prompt = search.get_prompt_with_context(user_message)
                    tool_used = 'search_web'
                elif use_rag and rag.is_built():
                    prompt = rag.get_prompt_with_context(user_message)
                    tool_used = 'query_knowledge_base'
                else:
                    prompt = user_message
                    tool_used = 'none'

                reply = llm_client.generate_response_with_fallback(
                    messages=message_history + [{"role": "user", "content": prompt}],
                    system_prompt=config.SYSTEM_PROMPT
                )
                extra = {'mode': 'manual', 'tool_used': tool_used, 'query_used': None}

            # Guardrails output check runs for BOTH modes
            if use_guardrails:
                allowed, reply = guard.check_output(reply, user_message)

            # 更新對話歷史（存原始訊息，不存 RAG/agentic prompt）
            message_history.append({"role": "user", "content": user_message})
            message_history.append({"role": "assistant", "content": reply})

            return JsonResponse({
                'status': 'success',
                'response': reply,
                'conversation_id': conversation_id,
                'message_history': message_history,
                **extra,
            })

        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Only POST requests are supported.'}, status=405)