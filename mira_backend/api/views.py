from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def health_check(request):
    return JsonResponse({'status': 'ok'})

@csrf_exempt
def chat(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '')
        # 之後這裡接 Groq LLM
        return JsonResponse({'response': f'收到：{user_message}'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)