# Review package R1 (rework 1, T19)

BASE=df8de66e7dc0e32d2fc5ba0dd54b78a359c7c7cc, head team/FEAT-006-rw1-r1 (85c31cd), worktree `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/agent-a498880b45a195393`.
Diff command: `git diff df8de66..team/FEAT-006-rw1-r1 -- erp_ai` (run it yourself, the repo is local; the hunks are also below).

## Commits
85c31cd fix(gateway): tat thinking cho classify, het cat max_tokens (FEAT-006)

## Stat (erp_ai only)
erp_ai/gateway/__init__.py     | 5 +
erp_ai/gateway/test_gateway.py | 13 +-

## Diff
```diff
--- a/erp_ai/gateway/__init__.py
+++ b/erp_ai/gateway/__init__.py
@@ -17,6 +17,9 @@ TASKS = ("classify", "reason")
 MIN_REMAINING_S = 5
+# Classify answers with one short JSON object. Haiku 5.5 thinks by default and its (hidden) thinking
+# tokens count against max_tokens, so with thinking on a 600 ceiling is hit about 1 call in 4.
+CLASSIFY_THINKING = {"type": "disabled"}
@@ -146,6 +149,8 @@ def call_model(task, *, system, messages, max_tokens, tools=None, deadline=None)
 		request = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
+		if task == "classify":
+			request["thinking"] = CLASSIFY_THINKING
 		if tools:
 			request["tools"] = tools
--- a/erp_ai/gateway/test_gateway.py
+++ b/erp_ai/gateway/test_gateway.py
+	def test_classify_request_turns_thinking_off(self):
+		add_credential("k1")
+		send, _ = self.run_call(ok_reply())
+		self.assertEqual(send.calls[0]["request"]["thinking"], {"type": "disabled"})
+
+	def test_reason_request_leaves_thinking_unset(self):
+		add_credential("k1", model_reason="reason-model")
+		send, _ = self.run_call(ok_reply(), task="reason")
+		self.assertNotIn("thinking", send.calls[0]["request"])
-			{**CALL, "model": "default-model", "tools": [{"name": "t"}]},
+			{**CALL, "model": "default-model", "thinking": {"type": "disabled"}, "tools": [{"name": "t"}]},
```

Task criteria (acceptance.md rework item 1): classify must stop being cut at max_tokens (CLASSIFY_MAX_TOKENS=600); fix the root cause, not just the number; E1/E2 real eval must show `max_tokens hits = 0` and at least one ticket classified. Touchpoints: erp_ai/gateway/__init__.py, runner.py, run_eval.py and their tests.
