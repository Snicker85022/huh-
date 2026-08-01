"""test_hpwt_graph.py - unit + smoke tests for the LangGraph orchestration layer.

Run (from repo/scripts, browser-agent venv):
    /home/taza/browser-agent-venv/bin/python3 test_hpwt_graph.py -v

Covers, per the dispatch:
  1. checkpointer selection in isolation: failing Postgres connection ->
     SqliteSaver fallback + db-mode state file + notify_nick(inform).
  2. fail-closed nick_approval in isolation: notify_nick sent=False -> interrupt
     STILL blocks AND pending-approval marker written; sent=True -> still
     blocks, no marker; Band 2 -> inform + proceed (no interrupt); resumable.
  3. smoke: graph object compiles against the real Postgres connection.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

import hpwt_graph as g


class TestCheckpointerFallback(unittest.TestCase):
    """select_checkpointer() in isolation with a failing Postgres path."""

    def test_falls_back_to_sqlite_writes_state_and_notifies(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            env = td / "db.env"
            env.write_text("# test-only\nHPWT_DB_PASSWORD=testpass123\n")
            sqlite_path = td / "fallback_checkpoints.db"
            mode_file = td / "db-mode"
            notify = mock.Mock(return_value={"sent": True, "channel": "primary",
                                             "status": 200, "url": "https://ntfy.sh/taza-ops"})
            with mock.patch.object(g, "PostgresSaver") as mock_pg:
                mock_pg.from_conn_string.side_effect = ConnectionError("simulated pg outage")
                saver, meta = g.select_checkpointer(db_env=env, fallback_sqlite=sqlite_path,
                                                    mode_file=mode_file, notify=notify,
                                                    topic="taza-ops")
            self.assertEqual(meta["mode"], "sqlite_fallback")
            self.assertIn("simulated pg outage", meta["reason"])
            self.assertIsInstance(saver, SqliteSaver)
            # state file, same shape as /var/lib/taza/llama-mode (write_state)
            content = mode_file.read_text()
            self.assertIn("mode=sqlite_fallback", content)
            self.assertIn("needs_root_cause=1", content)
            self.assertIn("simulated pg outage", content)
            self.assertRegex(content, r"(?m)^since=")
            # notify_nick fired with urgency='inform', topic from taza-ntfy.conf
            notify.assert_called_once()
            kwargs = notify.call_args.kwargs
            self.assertEqual(kwargs["urgency"], "inform")
            self.assertEqual(kwargs["topic"], "taza-ops")
            self.assertIn("simulated pg outage", kwargs["message"])
            # the failing Postgres path was attempted exactly once
            mock_pg.from_conn_string.assert_called_once()

    def test_primary_path_returns_postgres_when_connection_ok(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            env = td / "db.env"
            env.write_text("HPWT_DB_PASSWORD=testpass123\n")
            fake_saver = mock.Mock()
            with mock.patch.object(g, "PostgresSaver") as mock_pg:
                cm = mock.MagicMock()
                cm.__enter__.return_value = fake_saver
                mock_pg.from_conn_string.return_value = cm
                saver, meta = g.select_checkpointer(db_env=env, fallback_sqlite=td / "f.db",
                                                    mode_file=td / "db-mode",
                                                    notify=mock.Mock())
            self.assertEqual(meta["mode"], "postgres")
            self.assertIs(saver, fake_saver)
            fake_saver.setup.assert_called_once()


def _band1_state(**over):
    state = {"task": "test task", "risk": {"band": 1, "color": "red", "r": 4.5}}
    state.update(over)
    return state


class TestFailClosedNickApproval(unittest.TestCase):
    """nick_approval fail-closed semantics in isolation (1-node graph)."""

    def _mini_graph(self):
        builder = g.StateGraph(g.HPWTState)
        builder.add_node("nick_approval", g.nick_approval)
        builder.add_edge(g.START, "nick_approval")
        builder.add_edge("nick_approval", g.END)
        return builder.compile(checkpointer=MemorySaver())

    def test_band1_notify_failed_still_blocks_and_writes_marker(self):
        with tempfile.TemporaryDirectory() as td:
            pending = Path(td) / "pending-approval"
            with mock.patch.object(g, "notify_nick", return_value={
                    "sent": False, "channel": None,
                    "errors": {"primary": 429, "fallback": 0}}) as m:
                with mock.patch.object(g, "PENDING_DIR", pending):
                    graph = self._mini_graph()
                    result = graph.invoke(_band1_state(), config={"configurable": {"thread_id": "t-band1-fail"}})
            # BLOCKED regardless of the failed notification
            self.assertIn("__interrupt__", result)
            payload = result["__interrupt__"][0].value
            self.assertEqual(payload["node"], "nick_approval")
            self.assertFalse(payload["notification"]["sent"])
            # notify fired with urgency='pause'
            m.assert_called_once()
            self.assertEqual(m.call_args.kwargs["urgency"], "pause")
            # durable pending-approval marker written (session-start-ritual-findable)
            markers = list(pending.glob("*.json"))
            self.assertEqual(len(markers), 1)
            marker = json.loads(markers[0].read_text())
            self.assertTrue(marker["blocked"])
            self.assertEqual(marker["required_action"], "nick_approval")
            self.assertEqual(marker["notify_failed"]["errors"]["primary"], 429)

    def test_band1_notify_success_still_blocks_but_no_marker(self):
        with tempfile.TemporaryDirectory() as td:
            pending = Path(td) / "pending-approval"
            with mock.patch.object(g, "notify_nick", return_value={
                    "sent": True, "channel": "primary", "status": 200,
                    "url": "https://ntfy.sh/taza-ops"}) as m:
                with mock.patch.object(g, "PENDING_DIR", pending):
                    graph = self._mini_graph()
                    result = graph.invoke(_band1_state(), config={"configurable": {"thread_id": "t-band1-ok"}})
            # blocking is unconditional - interrupt present even on success
            self.assertIn("__interrupt__", result)
            self.assertTrue(result["__interrupt__"][0].value["notification"]["sent"])
            m.assert_called_once()
            self.assertEqual(m.call_args.kwargs["urgency"], "pause")
            # no marker when the notification went through
            self.assertEqual(len(list(pending.glob("*.json"))), 0)

    def test_band1_interrupt_is_resumable(self):
        with mock.patch.object(g, "notify_nick", return_value={
                "sent": True, "channel": "primary", "status": 200, "url": "x"}):
            with tempfile.TemporaryDirectory() as td:
                with mock.patch.object(g, "PENDING_DIR", Path(td) / "pending"):
                    graph = self._mini_graph()
                    graph.invoke(_band1_state(), config={"configurable": {"thread_id": "t-band1-resume"}})
                    final = graph.invoke(Command(resume={"decision": "approved"}), config={"configurable": {"thread_id": "t-band1-resume"}})
        self.assertEqual(final["approval"], {"decision": "approved"})

    def test_band2_notifies_inform_and_proceeds_without_blocking(self):
        with mock.patch.object(g, "notify_nick", return_value={
                "sent": True, "channel": "primary", "status": 200, "url": "x"}) as m:
            graph = self._mini_graph()
            result = graph.invoke({"task": "t", "risk": {"band": 2, "color": "coral", "r": 3.5}}, config={"configurable": {"thread_id": "t-band2"}})
        self.assertNotIn("__interrupt__", result)
        self.assertEqual(result["approval"], "band2_proceed")
        m.assert_called_once()
        self.assertEqual(m.call_args.kwargs["urgency"], "inform")


class TestSmokeBuild(unittest.TestCase):
    """Real Postgres connection: the graph object must compile and initialize."""

    def test_build_graph_against_real_postgres(self):
        saver, meta = g.select_checkpointer()
        self.assertEqual(meta["mode"], "postgres",
                         "expected postgres checkpointer, got fallback: %s" % meta)
        graph = g.build_graph(checkpointer=saver)
        self.assertTrue(hasattr(graph, "invoke"))
        graph_obj = graph.get_graph()
        nodes = getattr(graph_obj, "nodes", {})
        node_ids = set(nodes.keys()) if isinstance(nodes, dict) else \
            {getattr(n, "id", None) for n in nodes}
        expected = {"propose", "kb_gauntlet", "confidence_gate", "da_review",
                    "nick_approval", "dual_execute", "verify", "kb_update"}
        self.assertTrue(expected.issubset(node_ids), "missing nodes: %s" % (expected - node_ids))
        print("\n--- graph shape (compiled against real Postgres) ---")
        for nid in sorted(node_ids):
            print("  node:", nid)
        for e in graph_obj.edges:
            print("  edge: %s -> %s" % (e.source, e.target))


if __name__ == "__main__":
    unittest.main(verbosity=2)
