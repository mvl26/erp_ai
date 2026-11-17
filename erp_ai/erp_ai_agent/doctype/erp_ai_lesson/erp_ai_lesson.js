const DECISION_BUTTONS = {
	"Chờ duyệt": [
		["Duyệt", "approve"],
		["Từ chối", "reject"],
	],
	"Đang dùng": [["Tắt", "disable"]],
	"Đã tắt": [["Bật", "enable"]],
};

frappe.ui.form.on("ERP AI Lesson", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		(DECISION_BUTTONS[frm.doc.lesson_status] || []).forEach(([label, action]) => {
			frm.add_custom_button(label, () => {
				frappe.call({
					method: "erp_ai.erp_ai_agent.doctype.erp_ai_lesson.erp_ai_lesson.decide",
					type: "POST",
					args: { name: frm.doc.name, action: action },
					freeze: true,
					callback: () => frm.reload_doc(),
				});
			});
		});
		frm.add_custom_button("Các lần dùng", () => {
			frappe.set_route("List", "ERP AI Log", {
				lessons_used: ["like", '%"' + frm.doc.name + '"%'],
			});
		});
	},
});
