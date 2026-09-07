# -*- coding: utf-8 -*-
"""LLM 封装单元测试：mock OpenAI 客户端，不发真实请求。"""
from types import SimpleNamespace

import pytest

from src.agent.llm import LLM


def _make_llm(fake_response):
    """用 __new__ 跳过 __init__，只替换 client 为假实现。"""
    llm = LLM.__new__(LLM)
    llm.model = "fake-model"
    llm.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kw: fake_response)
        )
    )
    return llm


def _fake_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_final_answer_when_no_tool_calls():
    msg = SimpleNamespace(tool_calls=None, content="直接回答")
    llm = _make_llm(_fake_response(msg))

    result = llm.chat([{"role": "user", "content": "hi"}], tools=[])

    assert result.is_final is True
    assert result.text == "直接回答"
    assert result.tool_calls == []


def test_tool_calls_parsed_and_normalized():
    calls = [SimpleNamespace(
        id="c1",
        function=SimpleNamespace(
            name="web_search", arguments='{"query": "go rust"}'),
    )]
    llm = _make_llm(_fake_response(SimpleNamespace(tool_calls=calls, content=None)))

    result = llm.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])

    assert result.is_final is False
    assert result.tool_calls[0]["id"] == "c1"
    assert result.tool_calls[0]["name"] == "web_search"
    assert result.tool_calls[0]["arguments"] == {"query": "go rust"}


def test_invalid_json_arguments_falls_back_to_empty():
    """模型返回非法 JSON 参数：兜底为空 dict，交给上层与模型自愈。"""
    calls = [SimpleNamespace(
        id="c1",
        function=SimpleNamespace(name="web_search", arguments="{broken json"),
    )]
    llm = _make_llm(_fake_response(SimpleNamespace(tool_calls=calls, content=None)))

    result = llm.chat([], tools=[])

    assert result.tool_calls[0]["arguments"] == {}


def test_empty_choices_raises_readable_error():
    """空响应（无 choices）必须抛出可读错误，而不是下标越界。"""
    llm = _make_llm(SimpleNamespace(choices=[]))

    with pytest.raises(RuntimeError, match="空响应"):
        llm.chat([], tools=[])
