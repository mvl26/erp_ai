frappe.ui.form.on("ERP AI Setting", {
	refresh(frm) {
		frm.add_custom_button(__("Kiểm tra khóa"), () => {
			frappe.call({
				method: "erp_ai.erp_ai_agent.doctype.erp_ai_setting.erp_ai_setting.check_keys",
				freeze: true,
				freeze_message: __("Đang thử từng khóa..."),
				callback: (response) => {
					show_key_check_results(response.message || []);
					frm.reload_doc();
				},
			});
		});
	},
});

function show_key_check_results(results) {
	const rows = results
		.map(
			(item) =>
				`<tr><td>${frappe.utils.escape_html(item.label || "")}</td>` +
				`<td>${item.ok ? __("Dùng được") : __("Lỗi")}</td>` +
				`<td>${frappe.utils.escape_html(item.error_kind || "")}</td>` +
				`<td>${frappe.utils.escape_html(
					item.status == null ? "" : String(item.status)
				)}</td></tr>`
		)
		.join("");
	frappe.msgprint({
		title: __("Kết quả kiểm tra khóa"),
		wide: true,
		message:
			`<table class="table table-bordered"><thead><tr><th>${__("Nhãn khóa")}</th>` +
			`<th>${__("Kết quả")}</th><th>${__("Loại lỗi")}</th><th>${__(
				"Mã HTTP"
			)}</th></tr></thead>` +
			`<tbody>${rows}</tbody></table>`,
	});
}
