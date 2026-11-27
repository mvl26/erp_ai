from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase
from werkzeug.wrappers import Response

from erp_ai import page_loader

PAGE = "<html><body><div id='app'></div></body></html>"


def request(path="/helpdesk", method="GET"):
	return SimpleNamespace(path=path, method=method)


def page(body=PAGE, status=200, content_type="text/html; charset=utf-8"):
	return Response(body, status=status, content_type=content_type)


class TestPageLoader(FrappeTestCase):
	"""ADR-052: the Helpdesk SPA page of an agent gets one script tag that starts the Miyano bot on any page."""

	def inject(self, response, req=None, agent=True, user="agent@example.com"):
		with (
			patch.object(page_loader, "is_agent", return_value=agent),
			patch.object(page_loader.frappe, "session", SimpleNamespace(user=user)),
		):
			page_loader.inject_bot_loader(response=response, request=req or request())
		return response.get_data(as_text=True)

	def test_agent_page_gets_one_loader_tag_before_the_body_ends(self):
		html = self.inject(page())
		self.assertEqual(html.count(page_loader.LOADER_PATH), 1)
		self.assertTrue(html.endswith(f"{page_loader.loader_tag()}</body></html>"))

	def test_spa_sub_routes_get_it_too(self):
		self.assertIn(page_loader.LOADER_PATH, self.inject(page(), request("/helpdesk/tickets/12")))

	def test_a_second_pass_does_not_add_a_second_tag(self):
		response = page()
		self.inject(response)
		self.assertEqual(self.inject(response).count(page_loader.LOADER_PATH), 1)

	def test_content_length_follows_the_new_body(self):
		response = page()
		html = self.inject(response)
		self.assertEqual(response.content_length, len(html.encode()))

	def test_people_who_are_not_agents_get_the_page_unchanged(self):
		self.assertEqual(self.inject(page(), agent=False), PAGE)
		self.assertEqual(self.inject(page(), user="Guest"), PAGE)

	def test_other_pages_and_answers_are_left_alone(self):
		for case, response, req in (
			("other path", page(), request("/app/home")),
			("path that only starts like it", page(), request("/helpdesks")),
			("post", page(), request(method="POST")),
			("redirect", page(status=302), request()),
			("json", page('{"a": 1}', content_type="application/json"), request()),
			("no body tag", page("<p>hi</p>"), request()),
		):
			with self.subTest(case):
				original = response.get_data(as_text=True)
				self.assertEqual(self.inject(response, req), original)

	def test_a_failure_never_breaks_the_page(self):
		response = page()
		with (
			patch.object(page_loader, "is_agent", side_effect=RuntimeError("boom")),
			patch.object(page_loader.frappe, "log_error"),
			patch.object(page_loader.frappe, "session", SimpleNamespace(user="agent@example.com")),
		):
			page_loader.inject_bot_loader(response=response, request=request())
		self.assertEqual(response.get_data(as_text=True), PAGE)
