// Buttons are only a convenience: the server checks role and state again (AC-5).
const BRANCH_NOTE_PREFIX = "Commit sẽ vào nhánh ";
const CORE_WARNING_PREFIX = "Cảnh báo app lõi: ";

frappe.ui.form.on("ERP AI Change Proposal", {
	refresh(frm) {
		decide_from_link(frm);
		const notes = (frm.doc.__onload && frm.doc.__onload.change_notes) || [];
		frm.set_intro(
			notes.map(frappe.utils.escape_html).join("<br>"),
			frm.doc.is_core_app ? "orange" : "blue"
		);
		if (!frappe.user.has_role("ERP AI Instructor")) {
			return;
		}
		if (frm.doc.change_status === "Chờ duyệt") {
			add_action_button(
				frm,
				__("Duyệt"),
				approve_confirm_message(frm, notes),
				"erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.approve"
			);
			add_action_button(
				frm,
				__("Từ chối"),
				frappe.utils.escape_html(
					__("Từ chối đề xuất này? Không có file nào được ghi, không có lệnh nào chạy.")
				),
				"erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.reject"
			);
		}
		if (frm.doc.change_status === "Đã áp dụng" && frm.doc.change_kind === "Thay đổi code") {
			add_action_button(
				frm,
				__("Hoàn tác"),
				frappe.utils.escape_html(
					__(
						"Hoàn tác thay đổi này? File trở lại như trước khi áp dụng (file mới thì bị xóa) và có một commit hoàn tác."
					)
				),
				"erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.undo"
			);
		}
	},
});

// The signed Duyệt / Từ chối link of the ticket comment opens this form (ADR-023 QĐ 1): one click
// decides, so no confirmation here. The address is cleaned first, so a refresh or reload never sends it again.
function decide_from_link(frm) {
	const params = new URLSearchParams(window.location.search);
	const action = params.get("action");
	const signature = params.get("_signature");
	if (!action || !signature) {
		return;
	}
	window.history.replaceState(null, "", window.location.pathname);
	if (frm.doc.change_status === "Chờ duyệt") {
		frappe.call({
			method: "erp_ai.change_decision.decide",
			args: { name: frm.doc.name, action, _signature: signature },
			type: "POST",
			freeze: true,
			callback: () => frm.reload_doc(),
		});
	}
}

function approve_confirm_message(frm, notes) {
	// A bench command runs and cannot be undone; only a code change writes a file and commits.
	const lines =
		frm.doc.change_kind === "Lệnh bench"
			? [__("Duyệt đề xuất này? Lệnh bench sẽ chạy."), __("Lệnh bench không hoàn tác được.")]
			: [__("Duyệt đề xuất này? File sẽ được ghi và có một commit.")];
	const branch_note = notes.find((note) => note.startsWith(BRANCH_NOTE_PREFIX));
	if (branch_note) {
		lines.push(branch_note);
	}
	const core_warning = notes.find((note) => note.startsWith(CORE_WARNING_PREFIX));
	if (frm.doc.is_core_app && core_warning) {
		lines.push(core_warning.split(". ")[0] + ".");
	}
	return lines.map(frappe.utils.escape_html).join("<br>");
}

function add_action_button(frm, label, message, method) {
	frm.add_custom_button(label, () => {
		frappe.confirm(message, () => {
			frappe.call({
				method,
				args: { name: frm.doc.name },
				type: "POST",
				freeze: true,
				callback: () => frm.reload_doc(),
			});
		});
	});
}
