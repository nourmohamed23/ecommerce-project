import json
import re

import requests
from django.conf import settings


class HuggingFaceError(Exception):
    """Raised when the Hugging Face recommendation request cannot be completed."""


def _catalog(products):
    return [
        {
            'id': product.id,
            'name': product.name,
            'description': product.description or '',
            'category': product.category.name,
            'price': str(product.price),
            'in_stock': product.stock_quantity > 0,
        }
        for product in products
    ]


def _parse_response(content):
    text = content.strip()
    fenced_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise HuggingFaceError('The AI returned an invalid recommendation format.')
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise HuggingFaceError('The AI returned an invalid recommendation format.') from exc

    recommendations = parsed.get('recommendations') if isinstance(parsed, dict) else None
    if not isinstance(recommendations, list):
        raise HuggingFaceError('The AI response did not contain recommendations.')
    return recommendations


def recommend(products, query):
    api_token = getattr(settings, 'HUGGINGFACE_API_TOKEN', '')
    model = getattr(settings, 'HUGGINGFACE_MODEL', 'Qwen/Qwen3.8-27B:novita')
    endpoint = 'https://router.huggingface.co/v1/chat/completions'
    if not api_token:
        raise HuggingFaceError('The Hugging Face API token is not configured.')
    if not query.strip():
        raise HuggingFaceError('Please describe what you are looking for.')

    catalog = _catalog(products)
    system_prompt = (
        'You are an e-commerce shopping assistant. Recommend only products from the '
        'provided catalog. Return valid JSON only in this exact shape: '
        '{"recommendations":[{"product_id":1,"reason":"brief explanation"}]}. '
        'Use existing numeric product IDs, recommend at most 5 products, and return '
        'an empty list when nothing matches.'
    )
    user_prompt = f'User request: {query.strip()}\nCatalog:\n{json.dumps(catalog)}'
    try:
        response = requests.post(
            endpoint,
            headers={
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'max_tokens': 400,
                'temperature': 0.2,
            },
            timeout=getattr(settings, 'HUGGINGFACE_TIMEOUT', 30),
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise HuggingFaceError('The recommendation service is currently unavailable.') from exc

    try:
        content = payload['choices'][0]['message']['content']
    except (IndexError, KeyError, TypeError):
        content = ''
    if not isinstance(content, str) or not content:
        raise HuggingFaceError('The AI returned an empty recommendation response.')

    valid_ids = {product.id for product in products}
    recommendations = []
    for item in _parse_response(content):
        if not isinstance(item, dict):
            continue
        try:
            product_id = int(item.get('product_id'))
        except (TypeError, ValueError):
            continue
        reason = item.get('reason')
        if product_id in valid_ids and isinstance(reason, str) and reason.strip():
            recommendations.append({'product_id': product_id, 'reason': reason.strip()})
    return recommendations[:5]
