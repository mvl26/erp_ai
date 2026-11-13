# Review package R1 round 2 (scoped re-review)

FIX_BASE=85c31cd, head team/FEAT-006-rw1-r1b (5fc7a8b). Original task BASE=df8de66.
Diff command: `git diff 85c31cd..team/FEAT-006-rw1-r1b -- erp_ai` (local repo; hunks below). Commit: 5fc7a8b fix(gateway): chi tat thinking cho model claude-haiku-, model khac khong gui (FEAT-006).

Old finding to mark ADDRESSED / NOT ADDRESSED:
major | STD-DESIGN-3 | erp_ai/gateway/__init__.py:152-153 | Classify always sends `thinking: {"type": "disabled"}` whatever the model; Sonnet 5.5/Opus 5.5/Fable reject it with 400 and the gateway then gives up with `bad_request`. Fix wanted: send `disabled` only to models that accept it, plus a test that a non-Haiku classify request has no `thinking`.
(The minor STD-DOC-4 about design.md D-8 is deferred, out of this round.)

```diff
--- a/erp_ai/gateway/__init__.py
+++ b/erp_ai/gateway/__init__.py
+# Only Haiku accepts `disabled`; Sonnet, Opus and Fable answer 400 to it, so other models get no field.
 CLASSIFY_THINKING = {"type": "disabled"}
+THINKING_OFF_MODEL_PREFIX = "claude-haiku-"
@@ call_model
-		if task == "classify":
+		if task == "classify" and model.startswith(THINKING_OFF_MODEL_PREFIX):
 			request["thinking"] = CLASSIFY_THINKING
--- a/erp_ai/gateway/test_gateway.py
-	def test_classify_request_turns_thinking_off(self):
-		add_credential("k1")
+	def test_classify_request_turns_thinking_off_for_haiku(self):
+		add_credential("k1", model_classify="claude-haiku-5-5")
+	def test_classify_request_leaves_thinking_unset_for_non_haiku(self):
+		add_credential("k1", model_classify="claude-sonnet-5-5")
+		send, _ = self.run_call(ok_reply())
+		self.assertNotIn("thinking", send.calls[0]["request"])
-			{**CALL, "model": "default-model", "thinking": {"type": "disabled"}, "tools": [{"name": "t"}]},
+			{**CALL, "model": "default-model", "tools": [{"name": "t"}]},
```
