"""
Tests for ICARUS Intent Router
================================
Each test verifies a specific routing decision.
No LLM, no API calls — pure logic testing.

Run with:
    pytest tests/unit/brain/test_intent_router.py -v
"""

import pytest
from app.brain.intent_router import IntentRouter, RouteResult
from app.config.constants import INTENT, TOOL


@pytest.fixture
def router():
    return IntentRouter()


# ══════════════════════════════════════════════════════════════════
# MUSIC
# ══════════════════════════════════════════════════════════════════

class TestMusicRouting:

    @pytest.mark.asyncio
    async def test_english_play(self, router):
        result = await router.route("play Kesariya")
        assert result.intent == INTENT.MUSIC_PLAY
        assert result.use_llm is False
        assert result.tool == TOOL.MUSIC
        assert "Kesariya" in result.params.get("query", "")

    @pytest.mark.asyncio
    async def test_hinglish_play(self, router):
        result = await router.route("gana baja Tum Hi Ho")
        assert result.intent == INTENT.MUSIC_PLAY
        assert result.use_llm is False
        assert "Tum Hi Ho" in result.params.get("query", "")

    @pytest.mark.asyncio
    async def test_hindi_play(self, router):
        result = await router.route("Kesariya chalao")
        assert result.intent == INTENT.MUSIC_PLAY
        assert result.use_llm is False

    @pytest.mark.asyncio
    async def test_pause(self, router):
        result = await router.route("pause")
        assert result.intent == INTENT.MUSIC_PAUSE
        assert result.use_llm is False

    @pytest.mark.asyncio
    async def test_stop_hinglish(self, router):
        result = await router.route("music band kar")
        assert result.intent == INTENT.MUSIC_STOP
        assert result.use_llm is False

    @pytest.mark.asyncio
    async def test_next(self, router):
        result = await router.route("next song")
        assert result.intent == INTENT.MUSIC_NEXT
        assert result.use_llm is False


# ══════════════════════════════════════════════════════════════════
# GITHUB
# ══════════════════════════════════════════════════════════════════

class TestGitHubRouting:

    @pytest.mark.asyncio
    async def test_create_repo(self, router):
        result = await router.route("create repo called my-project")
        assert result.intent == INTENT.GITHUB_CREATE
        assert result.tool == TOOL.GITHUB
        assert result.params.get("repo_name") == "my-project"

    @pytest.mark.asyncio
    async def test_push_to_github(self, router):
        result = await router.route("push to github")
        assert result.intent == INTENT.GITHUB_PUSH
        assert result.use_llm is False
        assert result.tool == TOOL.GITHUB

    @pytest.mark.asyncio
    async def test_list_repos(self, router):
        result = await router.route("list repos")
        assert result.intent == INTENT.GITHUB_LIST
        assert result.use_llm is False

    @pytest.mark.asyncio
    async def test_hinglish_push(self, router):
        result = await router.route("github pe daal")
        assert result.intent == INTENT.GITHUB_PUSH


# ══════════════════════════════════════════════════════════════════
# BROWSER
# ══════════════════════════════════════════════════════════════════

class TestBrowserRouting:

    @pytest.mark.asyncio
    async def test_open_website(self, router):
        result = await router.route("open youtube.com")
        assert result.intent == INTENT.BROWSER_OPEN
        assert result.use_llm is False
        assert result.params.get("is_url") is True

    @pytest.mark.asyncio
    async def test_open_app_hinglish(self, router):
        result = await router.route("chrome khol")
        assert result.intent in (INTENT.BROWSER_OPEN, INTENT.SYSTEM_OPEN)
        assert result.use_llm is False

    @pytest.mark.asyncio
    async def test_web_search(self, router):
        result = await router.route("search Python tutorials")
        assert result.intent == INTENT.WEB_SEARCH
        assert "Python tutorials" in result.params.get("query", "")


# ══════════════════════════════════════════════════════════════════
# PERSONALITY
# ══════════════════════════════════════════════════════════════════

class TestPersonalityRouting:

    @pytest.mark.asyncio
    async def test_switch_developer(self, router):
        result = await router.route("switch to developer mode")
        assert result.intent == INTENT.PERSONALITY_SWITCH
        assert result.use_llm is False
        assert result.params.get("profile") == "developer"

    @pytest.mark.asyncio
    async def test_switch_bro(self, router):
        result = await router.route("enable bro mode")
        assert result.intent == INTENT.PERSONALITY_SWITCH
        assert result.params.get("profile") == "bro"

    @pytest.mark.asyncio
    async def test_switch_night_owl(self, router):
        result = await router.route("switch to night owl")
        assert result.intent == INTENT.PERSONALITY_SWITCH
        assert result.params.get("profile") == "night_owl"


# ══════════════════════════════════════════════════════════════════
# CONVERSATION FALLBACK
# ══════════════════════════════════════════════════════════════════

class TestConversationFallback:

    @pytest.mark.asyncio
    async def test_general_question(self, router):
        result = await router.route("What is machine learning?")
        assert result.intent == INTENT.CONVERSATION
        assert result.use_llm is True
        assert result.tool is None

    @pytest.mark.asyncio
    async def test_hinglish_question(self, router):
        result = await router.route("bhai binary search tree kya hota hai")
        assert result.use_llm is True

    @pytest.mark.asyncio
    async def test_empty_like_input(self, router):
        result = await router.route("hmm")
        assert result.use_llm is True


# ══════════════════════════════════════════════════════════════════
# ROUTE RESULT PROPERTIES
# ══════════════════════════════════════════════════════════════════

class TestRouteResult:

    @pytest.mark.asyncio
    async def test_is_direct_tool(self, router):
        result = await router.route("play Kesariya")
        assert result.is_direct_tool is True

    @pytest.mark.asyncio
    async def test_needs_llm_only(self, router):
        result = await router.route("explain how recursion works")
        assert result.needs_llm_only is True