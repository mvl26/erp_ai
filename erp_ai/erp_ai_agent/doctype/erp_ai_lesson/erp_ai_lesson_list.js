frappe.listview_settings["ERP AI Lesson"] = {
	onload(listview) {
		listview.page.add_inner_button("Dạy bot một quy tắc", () => {
			frappe.prompt(
				[
					{
						fieldname: "situation",
						fieldtype: "Small Text",
						label: "Tình huống (không bắt buộc)",
					},
					{
						fieldname: "rule",
						fieldtype: "Small Text",
						label: "Quy tắc",
						reqd: 1,
					},
				],
				(values) => {
					frappe.call({
						method: "erp_ai.erp_ai_agent.doctype.erp_ai_lesson.erp_ai_lesson.teach",
						type: "POST",
						args: { situation: values.situation, rule: values.rule },
						callback: (r) => {
							if (r.message) {
								frappe.set_route("Form", "ERP AI Lesson", r.message.name);
							}
						},
					});
				},
				"Dạy bot một quy tắc",
				"Dạy"
			);
		});
	},
};
