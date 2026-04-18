import sys
import pytest
from unittest.mock import patch, MagicMock


def test_episodic_memory_import_error_is_clear(tmp_path):
    """If chromadb is unavailable, EpisodicMemory raises ImportError with chromadb in message."""
    # Force chromadb to appear uninstalled
    with patch.dict(sys.modules, {"chromadb": None, "chromadb.utils": None, "chromadb.utils.embedding_functions": None}):
        # Remove cached module if already imported
        mods_to_remove = [k for k in sys.modules if k.startswith("agents.tools.memory") or k == "agents.tools.memory"]
        for mod in mods_to_remove:
            del sys.modules[mod]

        with pytest.raises((ImportError, ModuleNotFoundError)) as exc_info:
            from agents.tools.memory import EpisodicMemory
            EpisodicMemory(persist_directory=str(tmp_path))

        assert "chromadb" in str(exc_info.value).lower()


def test_episodic_memory_basic_operations(tmp_path):
    """EpisodicMemory adds and retrieves episodes when chromadb is installed."""
    pytest.importorskip("chromadb")

    # Clean up cached module to get fresh import
    mods_to_remove = [k for k in sys.modules if "agents.tools.memory" in k]
    for mod in mods_to_remove:
        del sys.modules[mod]

    from agents.tools.memory import EpisodicMemory
    mem = EpisodicMemory(persist_directory=str(tmp_path))

    mem.add_episode(
        query="Austin housing market",
        summary="Austin prices rose 5% in Q1 2026.",
        report_id="test-001",
    )
    results = mem.search_memory("Austin real estate")
    assert len(results) >= 1
    assert "Austin" in results[0]["content"]


def test_episodic_memory_module_loads_without_chromadb():
    """The memory module must be importable even if chromadb is not installed."""
    with patch.dict(sys.modules, {"chromadb": None}):
        mods_to_remove = [k for k in sys.modules if "agents.tools.memory" in k]
        for mod in mods_to_remove:
            del sys.modules[mod]

        # Should import without error — ImportError only raised when EpisodicMemory() is called
        try:
            import importlib
            import agents.tools.memory  # noqa: F401
        except ImportError as e:
            pytest.fail(f"Module should be importable without chromadb installed, got: {e}")
