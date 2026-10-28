import json

import pytest
import requests

from ai.llm_client import LLMError, OpenAICompatibleClient, extract_json_object, normalize_base_url


class FakeResponse:
    def __init__(self, payload, status_code=200, text=''):
        self._payload = payload
        self.status_code = status_code
        self.text = text or json.dumps(payload)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def chat_body(content):
    return {'choices': [{'message': {'content': content}}]}


def test_normalize_base_url_adds_v1():
    assert normalize_base_url('http://localhost:11434') == 'http://localhost:11434/v1'
    assert normalize_base_url('http://localhost:11434/') == 'http://localhost:11434/v1'
    assert normalize_base_url('http://localhost:11434/v1') == 'http://localhost:11434/v1'
    assert normalize_base_url('https://api.example.com/v1/') == 'https://api.example.com/v1'


def test_normalize_base_url_accepts_full_endpoint():
    assert (
        normalize_base_url('https://api.example.com/v1/chat/completions')
        == 'https://api.example.com/v1'
    )


def test_normalize_base_url_requires_a_value():
    with pytest.raises(LLMError):
        normalize_base_url('')


def test_extract_json_object_plain():
    assert extract_json_object('{"a": 1}') == {'a': 1}


def test_extract_json_object_from_code_fence():
    raw = '```json\n{"a": 1}\n```'
    assert extract_json_object(raw) == {'a': 1}


def test_extract_json_object_with_surrounding_prose():
    raw = 'Sure! Here you go:\n{"a": 1}\nHope that helps.'
    assert extract_json_object(raw) == {'a': 1}


def test_extract_json_object_rejects_garbage():
    with pytest.raises(LLMError):
        extract_json_object('not json at all')


def test_extract_json_object_rejects_empty():
    with pytest.raises(LLMError):
        extract_json_object('')


def test_client_builds_the_expected_request(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured['url'] = url
        captured['headers'] = headers
        captured['payload'] = json
        return FakeResponse(chat_body('{"ok": true}'))

    monkeypatch.setattr(requests, 'post', fake_post)
    client = OpenAICompatibleClient('http://localhost:11434', api_key='secret', model='llama3')
    assert client.endpoint == 'http://localhost:11434/v1/chat/completions'
    result = client.complete_json('system', 'user')
    assert result == {'ok': True}
    assert captured['headers']['Authorization'] == 'Bearer secret'
    assert captured['payload']['model'] == 'llama3'
    assert captured['payload']['messages'][0]['role'] == 'system'


def test_client_without_api_key_sends_no_authorization(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured['headers'] = headers
        return FakeResponse(chat_body('{"ok": true}'))

    monkeypatch.setattr(requests, 'post', fake_post)
    client = OpenAICompatibleClient('http://localhost:11434')
    client.complete_json('system', 'user')
    assert 'Authorization' not in captured['headers']


def test_client_raises_on_http_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        return FakeResponse({}, status_code=500, text='server exploded')

    monkeypatch.setattr(requests, 'post', fake_post)
    client = OpenAICompatibleClient('http://localhost:11434')
    with pytest.raises(LLMError) as excinfo:
        client.complete_json('system', 'user')
    assert '500' in str(excinfo.value)


def test_client_raises_on_connection_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        raise requests.ConnectionError('no route to host')

    monkeypatch.setattr(requests, 'post', fake_post)
    client = OpenAICompatibleClient('http://localhost:11434')
    with pytest.raises(LLMError):
        client.complete_json('system', 'user')


def test_client_repairs_unparsable_output(monkeypatch):
    responses = [
        FakeResponse(chat_body('this is not json')),
        FakeResponse(chat_body('{"repaired": true}')),
    ]

    def fake_post(url, headers=None, json=None, timeout=None):
        return responses.pop(0)

    monkeypatch.setattr(requests, 'post', fake_post)
    client = OpenAICompatibleClient('http://localhost:11434')
    assert client.complete_json('system', 'user', 'Return only JSON') == {'repaired': True}
    assert responses == []
