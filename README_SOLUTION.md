# Bài làm Day 7 — Trương Đức Phát — 2A202603757

Code chính: [`src/lab.py`](src/lab.py). Ba phương pháp: TF-IDF, dense pgvector Day 6 và Hybrid RRF. Agent dùng model thật, tool calling, tìm nhiều lượt, citation và abstention. Corpus gồm 463 chunk / 47 trang của chương 2–3; embedding `text-embedding-3-small`, 1536 chiều.

## Chạy bài làm

Từ thư mục gốc Day 7, dùng Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền credential trong `.env`. Nếu repo Day 6 nằm cạnh Day 7, chương trình tự đọc `starter/.env` Day 6 cho các giá trị còn thiếu. Có thể dùng Python môi trường Day 6 đã có đủ dependencies thay cho `.venv` mới.

Với môi trường Day 7 vừa tạo:

```powershell
docker compose -p day6_student_starter -f ../K5-L3B-Day06-TruongDucPhat-2A202603757-DataIngestion/starter/docker-compose.yml up -d
.\.venv\Scripts\python.exe -m src.lab check
.\.venv\Scripts\python.exe -m src.lab ask "What is a database?" --config hybrid_wide
```

Với môi trường Day 6 đang có trên máy:

Database hiện có là container `day6_student_starter-postgres-1`, cổng `55433`. Nếu container đã chạy thì dùng trực tiếp. Nếu đang dừng, chạy `docker start day6_student_starter-postgres-1`. Khi dùng Compose, giữ `-p day6_student_starter` như lệnh trên để kết nối đúng project/volume Day 6; bỏ `-p` có thể tạo thêm `starter-postgres-1` và gây lỗi cổng đã bị chiếm.

```powershell
& ..\K5-L3B-Day06-TruongDucPhat-2A202603757-DataIngestion\starter\.venv\Scripts\python.exe -m src.lab check
& ..\K5-L3B-Day06-TruongDucPhat-2A202603757-DataIngestion\starter\.venv\Scripts\python.exe -m src.lab ask "What is a database?" --config hybrid_wide
```

## Tái lập thí nghiệm

Các lệnh sau gọi model thật, có thể phát sinh phí. Dùng Python trong môi trường đã cài dependencies:

```powershell
# Chỉ prepare khi cần tái tạo data; yêu cầu strategy B còn trong DB.
.\.venv\Scripts\python.exe -m src.lab prepare
.\.venv\Scripts\python.exe -m src.lab run --split dev --configs dense tfidf hybrid hybrid_wide
# Đối chiếu và hoàn thành reviews.json trước hai bước tiếp theo.
.\.venv\Scripts\python.exe -m src.lab summarize
.\.venv\Scripts\python.exe -m src.lab freeze
# Chạy baseline cùng cấu hình đã chốt từ dev.
.\.venv\Scripts\python.exe -m src.lab run --split test --configs tfidf hybrid_wide
.\.venv\Scripts\python.exe -m src.lab summarize
```

Sau khi đối chiếu và cập nhật nhãn, tạo lại báo cáo offline:

```powershell
.\.venv\Scripts\python.exe -m src.report
```

Không chạy lại `freeze` để chọn theo test. Hai lượt test thực tế, gồm lỗi API, đều được giữ và phân tích trong báo cáo. Lệnh test dùng `hybrid_wide`, cấu hình thực đã chốt từ dev. Kết quả hiện có được giữ và lệnh run sẽ tiếp tục câu chưa chạy; không tự gọi lại các câu đã có trace. Test kiểm tra hash cấu hình để tránh thay đổi pipeline sau khi chốt.

## Tài liệu và kết quả

- [Thiết kế và giới hạn](docs/IMPLEMENTATION.md).
- [Cách kiểm tra nhãn](docs/REVIEW_GUIDE.md).
- [Báo cáo cá nhân](report/individual/2A202603757_TruongDucPhat.md).
- [Bảng so sánh](results/comparison.csv).
- Cấu hình ở `configs/`, benchmark ở `data/`, trace và nhãn ở `results/`.

Nhãn review là AI hỗ trợ đối chiếu nguồn, cần sinh viên xác nhận trước khi nộp. Không thực hiện bonus multimodal.
