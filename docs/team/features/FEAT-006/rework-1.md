# Rework 1 sau verify — FEAT-006

Nguồn: `acceptance.md` mục "Danh sách rework" (Verdict: rework). Chạy `/team:build FEAT-006 --decide`, tuần tự, mỗi việc một dev + một reviewer. Mục 7 (thông báo "ma") không sửa: team-leader đã nhận là giới hạn.

progress:
- [x] R1 (mục 1, T19) — BASE=df8de66, nhánh team/FEAT-006-rw1-r1b (đầu 5fc7a8b), 2 vòng review, merge 780a08d, `review-R1.md` approve. Gốc: Haiku 5.5 mặc định chạy adaptive thinking, token thinking tính vào `max_tokens`; sửa: classify gửi `thinking: disabled` cho model `claude-haiku-`. E2: max_tokens hits 0, Unclassified 0.
- [x] R2 (mục 2+5+6, T21) — BASE=91d8903, nhánh team/FEAT-006-rw1-r2 (0c9661e), 1 vòng, `review-R2.md` approve. Chỉ đổi test, có phá-thử đỏ/xanh.
- [x] R3 (mục 3+4, T22/T22b) — BASE=f2ba6b8, nhánh team/FEAT-006-rw1-r3 (bb9ddf2), 1 vòng, `review-R3.md` approve.
- [x] R4 (nhỏ) — BASE=8c8741d, nhánh team/FEAT-006-rw1-r4 (7002d0f), 1 vòng, merge 661eca9, `review-R4.md` approve. (a) `(model or "")` trước `startswith`, model rỗng vẫn ra GatewayError `bad_request`; (b) description `model_classify` / `model_classify_default` nói rõ chỉ `claude-haiku-*` tắt thinking, model khác có thể bị cắt ở trần token.

cmd.test trên đầu nhánh dev R4 (7002d0f, cây `erp_ai/` giống hệt đầu merge 661eca9): `Ran 885 tests in 161.130s` / `OK`. Lint (`pre-commit run --files` 5 file đổi): pass.

FEAT-003 (d425faa, trần 400, không gửi `thinking`) có cùng lỗi cắt phân loại (nhật ký site `output_tokens=400`, `stop_reason=unparseable`).

Bước tiếp: `/team:verify FEAT-006` (qa chạy lại E1/E2 trên site với phiếu thật có nhãn và R1).
