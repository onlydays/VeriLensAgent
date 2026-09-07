# -*- coding: utf-8 -*-
"""工具层单元测试：搜索用假实现替换，不发真实网络请求。"""
import pytest

from src.agent.tools.search import SearchTool


class FakeDDGS:
    instances = []

    def __init__(self):
        FakeDDGS.instances.append(self)
        self.seen = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def text(self, query, max_results=5):
        self.seen["query"] = query
        self.seen["max_results"] = max_results
        return [
            {"title": "t1", "href": "https://example.com/1", "body": "b1"},
            {"title": "t2", "href": "https://example.com/2", "body": "b2"},
        ]


@pytest.fixture
def fake_ddgs(monkeypatch):
    FakeDDGS.instances = []
    monkeypatch.setattr("src.agent.tools.search._get_ddgs_class", lambda: FakeDDGS)
    return FakeDDGS


def test_search_formats_results(fake_ddgs):
    tool = SearchTool()
    out = tool.run("技术选型", max_results=5)

    instance = fake_ddgs.instances[0]
    assert instance.seen["query"] == "技术选型"
    assert "### t1" in out
    assert "https://example.com/1" in out
    assert "b1" in out


def test_search_clamps_max_results_to_10(fake_ddgs):
    tool = SearchTool()
    tool.run("q", max_results=100)

    assert fake_ddgs.instances[0].seen["max_results"] == 10


def test_search_clamps_max_results_min_1(fake_ddgs):
    tool = SearchTool()
    tool.run("q", max_results=-5)

    assert fake_ddgs.instances[0].seen["max_results"] == 1


def test_search_empty_results_returns_notice(monkeypatch):
    """空结果必须返回明确提示文本，模型据此决定是否换关键词重搜。"""
    class EmptyDDGS(FakeDDGS):
        def text(self, query, max_results=5):
            self.seen["query"] = query
            self.seen["max_results"] = max_results
            return []

    FakeDDGS.instances = []  # 清空，避免受其他用例污染
    monkeypatch.setattr("src.agent.tools.search._get_ddgs_class", lambda: EmptyDDGS)

    out = SearchTool().run("找不到的东西")

    assert out == "未找到相关结果"
    assert FakeDDGS.instances[0].seen["query"] == "找不到的东西"


def test_to_openai_schema_shape():
    schema = SearchTool().to_openai_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "web_search"
    assert schema["function"]["parameters"]["required"] == ["query"]
