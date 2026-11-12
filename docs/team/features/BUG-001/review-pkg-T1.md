# Review package BUG-001 T1

Diff command: `git diff cda9aa1b733514654d7684a904a7ef1159e754a4..team/BUG-001-task-1`

Commits:
- 283b174 fix(gateway): treat credit-balance 400 as quota (BUG-001)

```
 erp_ai/gateway/breaker.py      |  4 ++--
 erp_ai/gateway/test_breaker.py | 10 ++++++++++
 2 files changed, 12 insertions(+), 2 deletions(-)
```

```diff
--- a/erp_ai/gateway/breaker.py
+++ b/erp_ai/gateway/breaker.py
@@ -23,7 +23,7 @@ class Action:
 
 
 SPEND_LIMIT_ERROR_CODE = "enforced_spend_limit_reached"
-QUOTA_MESSAGE_PREFIX = "You have reached your specified"
+QUOTA_MESSAGE_PREFIXES = ("You have reached your specified", "Your credit balance is too low")
 RATE_LIMIT_DEFAULT_PAUSE_S = 61
@@ -54,7 +54,7 @@ def decide(failure, error_count):
 	if status == 402:
 		return _quota()
-	if status == 400 and failure.message_prefix.startswith(QUOTA_MESSAGE_PREFIX):
+	if status == 400 and failure.message_prefix.startswith(QUOTA_MESSAGE_PREFIXES):
 		return _quota()
--- a/erp_ai/gateway/test_breaker.py
+++ b/erp_ai/gateway/test_breaker.py
@@ -5,6 +5,10 @@
 QUOTA_PREFIX = "You have reached your specified"
+CREDIT_PREFIX = (
+	"Your credit balance is too low to access the Anthropic API. "
+	"Please go to Plans & Billing to upgrade or purchase credits."
+)[:100]
@@ -49,6 +53,12 @@ (table cases)
+			(
+				"row6 400 credit balance",
+				failure(400, message_prefix=CREDIT_PREFIX),
+				1,
+				Action(QUOTA, None, True, "message", "quota"),
+			),
```
