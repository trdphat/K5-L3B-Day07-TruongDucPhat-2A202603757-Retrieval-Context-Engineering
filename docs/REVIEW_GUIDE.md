# Đối chiếu nhãn

`results/{dev,test}/{config}/reviews.json` chứa nhãn, lý do và trang nguồn cho từng query. Nhãn do Codex kiểm tra từ text đã index; sinh viên cần xác nhận với bản gốc. Mở file PDF ở repo Day 6, đi tới trang PDF trong `evidence_pages` (không dùng số trang in).

Đã soát bổ sung 79 mục trong 7 file bằng PDF gốc và trace. `ai_reviewed: true` ghi nhận lượt AI review này; `human_verified: true` chỉ ghi xác nhận của người làm bài. File dev/hybrid_wide với 17 nhãn người làm bài đã xác nhận được giữ nguyên. Các file được AI soát thêm có `citation_review` (trang, kiểm tra ID/text, đúng/sai và lý do), `citation_pages`, hash trace và hash PDF để đối chiếu. Script tạo nhãn không ghi đè file đã có một trong hai loại review hoàn tất.

Phân biệt answer grade và citation: dev/hybrid/q04 có đủ bằng chứng trong context trang 52–53 nên answer grade được sửa thành 2, nhưng citation chỉ dẫn trang 53, thiếu nguồn cho phần bổ sung từ trang 52, nên citation vẫn false. Không đổi cấu hình agent theo kết quả soát nhãn.

1. Đọc `question`, `answer`, `context` và từng citation trong `traces.json`.
2. Với câu có đáp án, chấm `answer_grade`: 0 sai/thiếu evidence hoặc từ chối; 1 đúng một phần; 2 đúng và đủ, không thêm khẳng định không được hỗ trợ.
3. Với từng citation, xác nhận ID có trong context và nội dung nguồn hỗ trợ khẳng định. `citation_support` có đúng một boolean cho mỗi citation theo cùng thứ tự.
4. Chấm `context_grade`: 0 không có evidence, 1 thiếu điều kiện/nguồn, 2 đủ bằng chứng và nguồn. Dùng giải thích ngữ nghĩa, không chỉ exact match với gold.
5. Với câu thiếu evidence, đọc cả answer để xác nhận từ chối rõ và không suy đoán; đối chiếu `absence_reason` và phạm vi corpus.
6. Nếu sửa nhãn, ghi người xác nhận/lý do, chạy `python -m src.lab summarize`. Không chọn lại cấu hình theo test.

Lệnh xem gói bằng chứng compact:

```powershell
python -m src.lab inspect --split dev --configs dense tfidf hybrid hybrid_wide
python -m src.lab inspect --split test --configs tfidf hybrid_wide
```

Thay tên cấu hình ở lệnh test bằng cấu hình thực trong `configs/selected.json`.
