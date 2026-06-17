"""
MIRA Django Views
Handles API endpoints for the MIRA AI assistant
"""
import os
import sys
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# # 添加根目錄到 Python 路徑
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_dir)
# sys.path.append(project_root)

from modules.llm.groq_client import GroqClient
from modules.rag import RAGManager
import config

# 模組層級初始化：防止每次收到請求都重新載入，很慢
llm_client = GroqClient()
# 用 config.DATA_DIR 產生絕對路徑，避免 Django 從 mira_backend/ 啟動時找錯位置
rag = RAGManager(persist_dir=str(config.DATA_DIR / 'vector_store'))
if rag.is_built():
    rag.load()

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

            # RAG 開啟時用注入知識庫的 prompt，否則直接用原始訊息
            # 送給 LLM 的 prompt 和存入 history 的 message 分開處理：
            # history 只存原始訊息，避免 RAG prompt 污染對話紀錄
            if use_rag and rag.is_built():
                prompt = rag.get_prompt_with_context(user_message)
            else:
                prompt = user_message

            # 呼叫 Groq LLM
            reply = llm_client.generate_response_with_fallback(
                messages=message_history + [{"role": "user", "content": prompt}],
                system_prompt=config.SYSTEM_PROMPT
            )

            # 更新對話歷史（存原始訊息，不存 RAG prompt）
            message_history.append({"role": "user", "content": user_message})
            message_history.append({"role": "assistant", "content": reply})

            return JsonResponse({
                'status': 'success',
                'response': reply,
                'conversation_id': conversation_id,
                'message_history': message_history
            })

        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Only POST requests are supported.'}, status=405)