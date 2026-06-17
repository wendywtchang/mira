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
import config

llm_client = GroqClient()

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

            # 加入用戶訊息到歷史
            message_history.append({"role": "user", "content": user_message})

            # 呼叫 Groq LLM
            reply = llm_client.generate_response_with_fallback(
                messages=message_history,
                system_prompt=config.SYSTEM_PROMPT
            )

            # 加入助手回應到歷史
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