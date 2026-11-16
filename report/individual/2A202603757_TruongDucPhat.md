# Báo cáo Day 7 — Trương Đức Phát — 2A202603757

## Phạm vi và dữ liệu

Hoàn thành pipeline phần cơ bản: agent thật, ba phương pháp retrieval, benchmark dev/test, hai cấu hình thử cải thiện, trace và đánh giá. Không thực hiện bonus 100 trang đa phương thức.

- Nguồn: OpenStax/Rice University, *Foundations of Information Systems*. Attribution và CC BY-NC-SA 4.0 giữ trong metadata và `data/provenance.json` theo bản PDF Day 6.
- Corpus: **47 trang hợp lệ, 463 chunk**, chương 2 và 3. Không đại diện toàn bộ 497 trang. Citation dùng trang PDF vật lý; trang in = trang PDF - 10.
- PostgreSQL/pgvector Day 6, exact cosine, score = 1 - distance; strategy `20261114T132647004212Z_B`. Không ghi lại index.
- Embedding `text-embedding-3-small`, 1536 chiều. Dùng lại vector tài liệu; chỉ embed query mới, cache theo model/dimensions/query.
- Agent `gpt-4.1-mini`; response model thực ghi trong từng model event. Cấu hình model, prompt và tool chung khi so sánh.
- Benchmark 24 câu: dev 15 có đáp án + 2 thiếu evidence; test 5 có đáp án + 2 thiếu evidence. Dev tái sử dụng Day 6; test mới soạn trước thí nghiệm, thay bộ test Day 6 đã dùng.
- Câu hỏi tiếng Anh phù hợp textbook. Gold gồm nguồn/trang/evidence nguyên văn, alternatives là OR. Không có câu multi-hop trong benchmark cơ bản này.
- Gold/expected answer/answerable chỉ nằm ở evaluator, không truyền vào controller hoặc tool.

**Nguồn nhãn:** Nhãn ban đầu do Codex hỗ trợ đối chiếu câu trả lời và các chunk citation. Trạng thái xác nhận của người làm bài được lấy từ `human_verified` trong từng file review; không suy ra xác nhận cho các cấu hình khác. Tập test được giữ riêng khỏi chọn cấu hình, nhưng không phải benchmark mù do người soạn độc lập.

| Split / cấu hình | Người làm bài đã xác nhận | AI đã soát lại với PDF gốc |
|---|---:|---:|
| dev / dense | 0/17 | 17/17 |
| dev / tfidf | 0/17 | 17/17 |
| dev / hybrid | 0/17 | 17/17 |
| dev / hybrid_wide | 17/17 | 0/17 |
| test / tfidf | 0/7 | 7/7 |
| test / hybrid_wide | 0/7 | 7/7 |

Lần soát nguồn bổ sung đã kiểm tra 79 mục trong 7 file (gồm 14 mục ở lượt test đầu), giữ nguyên 17 mục dev/hybrid_wide do người làm bài xác nhận. Mọi citation được kiểm tra ID trong context và text khớp PDF; nội dung được chấm riêng theo đúng phạm vi/điều kiện. `ai_reviewed: true` không tương đương `human_verified: true`. Mỗi mục AI review lưu hash trace/PDF và lý do cho từng citation.

## Kiến trúc và cấu hình

Model chọn `search(query)` hoặc `finish(status, answer, citations)`. Backend search cố định theo cấu hình. Tối đa 3 lượt search; model có thể viết lại query. Lỗi provider/DB ghi error riêng. Trả lời không có citation hợp lệ hoặc hết lượt tìm dẫn đến abstention.

TF-IDF dùng starter; dense truy vấn pgvector thật; hybrid lấy top-20 từng nhánh và RRF `Σ 1/(60+rank)`, không cộng score thô. Tất cả không filter và dùng cùng snapshot corpus. Context ưu tiên kết quả mới rồi evidence cũ, dedup theo ID, giữ block nguyên vẹn gồm nguồn/trang; budget tính ký tự, gồm header.

| Cấu hình | Phương pháp | Top-k | Budget ký tự | Giả thuyết |
|---|---|---:|---:|---|
| tfidf (baseline) | TF-IDF | 3 | 6000 | Baseline lexical từ starter, nối agent thật |
| dense | Dense Day 6 | 3 | 6000 | Semantic retrieval cải thiện paraphrase |
| hybrid | Dense + TF-IDF RRF | 3 | 6000 | Cải thiện 1: kết hợp lexical/semantic tăng coverage |
| hybrid_wide | RRF | 5 | 10000 | Cải thiện 2: nhiều context hơn giữ đủ điều kiện |

Thí nghiệm wide đổi cả top-k và budget nên không xác định tác động riêng mỗi tham số. Agent/search vẫn có giới hạn như nhau. Các mức trên là lựa chọn thực nghiệm, không phải giới hạn của đề.

## Kết quả retrieval và context

Ranking query gốc được đo riêng với ranking của query agent viết lại. Hit@1/3 có cùng cutoff cho mọi cấu hình; Context Evidence Rate đo context cuối sau mọi lượt. Mẫu số chỉ gồm câu có đáp án. Match tự động đòi đúng source/page và evidence nguyên văn trong chunk; có review ngữ nghĩa riêng.

| Split / cấu hình | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Tổng giây agent | Prompt / completion token |
|---|---|---|---|---:|---|
| dev / dense | 14/15 (93.3%) | 15/15 (100.0%) | 15/15 (100.0%) | 1322.73 | 17328 / 2145 |
| dev / tfidf | 11/15 (73.3%) | 13/15 (86.7%) | 14/15 (93.3%) | 39.66 | 18578 / 2056 |
| dev / hybrid | 12/15 (80.0%) | 13/15 (86.7%) | 14/15 (93.3%) | 42.76 | 18113 / 2266 |
| dev / hybrid_wide | 12/15 (80.0%) | 13/15 (86.7%) | 15/15 (100.0%) | 40.16 | 20772 / 2148 |
| test / tfidf | 4/5 (80.0%) | 5/5 (100.0%) | 3/5 (60.0%) | 31.53 | 6045 / 617 |
| test / hybrid_wide | 4/5 (80.0%) | 4/5 (80.0%) | 5/5 (100.0%) | 15.91 | 8219 / 818 |

## Kết quả agent và citation

| Split / cấu hình | Tool use | Answer 0 / 1 / 2 | Mean /2 | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---:|---|---|---|---|
| dev / dense | 17/17 (100.0%) | 0 / 1 / 14 | 1.933 | 18/19 (94.7%) | 15/15 (100.0%) | 2/2 (100.0%) | 0/15 (0.0%) |
| dev / tfidf | 17/17 (100.0%) | 1 / 0 / 14 | 1.867 | 16/16 (100.0%) | 14/14 (100.0%) | 2/2 (100.0%) | 1/15 (6.7%) |
| dev / hybrid | 17/17 (100.0%) | 0 / 1 / 14 | 1.933 | 18/21 (85.7%) | 15/15 (100.0%) | 2/2 (100.0%) | 0/15 (0.0%) |
| dev / hybrid_wide | 17/17 (100.0%) | 0 / 0 / 15 | 2.000 | 19/19 (100.0%) | 15/15 (100.0%) | 2/2 (100.0%) | 0/15 (0.0%) |
| test / tfidf | 5/5 (100.0%) | 0 / 1 / 2 | 1.667 | 3/4 (75.0%) | 3/3 (100.0%) | 2/2 (100.0%) | 0/3 (0.0%) |
| test / hybrid_wide | 7/7 (100.0%) | 0 / 0 / 5 | 2.000 | 6/6 (100.0%) | 5/5 (100.0%) | 2/2 (100.0%) | 0/5 (0.0%) |

## Phân tích lỗi dev và trước/sau

1. **Lỗi xuất citation:** lượt đầu model trả danh sách citation có ID đúng nhưng answer chưa có inline marker; kiểm tra quá cứng làm từ chối nhầm. Đã giữ `results/initial-dev/`, sửa render marker và chạy lại dev thật. Tiếp đó phát hiện model trả cả header `ID | nguồn | page`; adapter cuối chỉ lấy ID khớp chính xác context. Bản trước chuẩn hóa tại `results/pre-normalization/`. Dev cuối replay bước render từ finish thật đã lưu, không tạo câu trả lời mới, không thay search/context/token/timing. Test chạy end-to-end với adapter cuối.

2. **q01 — TF-IDF tìm nhầm “characteristics”:** query gốc lấy domain characteristics và four-V headings, agent tìm lại vẫn không có triad; context grade 0, answer grade 0 và từ chối nhầm. Dense tìm đủ quality evidence; hybrid top-3 còn thiếu đoạn trực tiếp; hybrid_wide lấy được p105, context và answer grade 2. Kết quả cho thấy cần đo context cuối bên cạnh ranking gốc.

3. **q09 — thêm ngữ cảnh sai mô hình:** dense trả đúng định nghĩa e-commerce nhưng bổ sung chiến lược marketplace từ p69. Chấm answer 1, citation thứ ba false thay vì coi có ID là đúng. Hybrid_wide dùng p68 và ví dụ Amazon p67, answer 2. Chunk độc lập có đại từ “this model” vẫn có thể mất ngữ cảnh dù retrieval liên quan.

4. **Hybrid không luôn tốt hơn:** q01 giải thích completeness lẫn loại bỏ duplicate; q05 dẫn thừa chapter outline. Với q04, lần soát nguồn bổ sung tìm thấy context trang 52 hỗ trợ phần secure/easily retrievable, nên sửa answer grade 1→2; citation duy nhất trang 53 vẫn false do không dẫn nguồn cho phần bổ sung. Đây là sửa nhãn sau kiểm tra đầy đủ context, không sửa agent/prompt/retrieval. Giữ nguyên snapshot lựa chọn ban đầu trong configs/selected.json; cấu hình chọn vẫn là hybrid_wide.

## Chọn cấu hình và đánh giá test

Tiêu chí trước test: grounded-answer mean → abstention đúng → context evidence rate → token thấp hơn. Chọn **hybrid_wide** trên dev. Cấu hình khóa tại `2026-11-16T03:54:20Z` (UTC), kèm hash source/corpus/benchmark/prompt-tools trong `configs/selected.json`. Không đổi prompt/retrieval từ kết quả test.

Test chạy cả TF-IDF baseline và cấu hình chọn trên cùng 7 câu. Cấu hình chọn có grounded-answer mean **2.000/2**, citation hợp lệ **6/6 (100.0%)**, abstention **2/2 (100.0%)**. Đây là benchmark nhỏ theo nhãn AI hỗ trợ, không suy rộng thành độ chính xác thực tế toàn miền.

Lượt test đầu có 3 APIConnectionError ở baseline, không xóa hoặc đổi thành abstention. Toàn bộ 14 trace/nhãn/summary lượt đầu giữ ở `results/test-attempt1/`. Đã chạy lại toàn bộ cặp baseline/cấu hình chọn với source/prompt/model/config giữ nguyên; bảng chính là lượt hai tại `results/test/`. Lượt hai baseline còn 2 APIConnectionError trước model/tool event; cấu hình chọn không có lỗi. Dừng lặp, giữ cả hai lượt thay vì thử đến khi đẹp. Đây là phép lặp lại kiểm tra kết nối, không phải chọn lại cấu hình.

Mean chất lượng trong bảng dùng quy tắc starter: lỗi provider được đếm riêng và loại khỏi mẫu số chất lượng. Vì baseline có lỗi, không diễn giải mean có điều kiện này như điểm trên toàn bộ 5 câu. Nhãn context/answer của câu lỗi vẫn ghi 0 trong operational view; không gọi lỗi là từ chối.

| Cấu hình test | Context grade 0 / 1 / 2 (5 câu có đáp án) | Lỗi hệ thống | Phân bố số lượt search |
|---|---|---:|---|
| tfidf | 2 / 0 / 3 | 2 | {0: 2, 1: 3, 2: 2} |
| hybrid_wide | 0 / 0 / 5 | 0 | {1: 7} |

| Test / cấu hình | Grounded mean gồm lỗi=0, mẫu số 5 câu có đáp án |
|---|---:|
| tfidf | 1.000/2 |
| hybrid_wide | 2.000/2 |

| Lượt test đầu / cấu hình | Lỗi hệ thống / tổng | Mean thành công /2 | Citation hợp lệ | Thời gian giây |
|---|---|---:|---|---:|
| tfidf | 3/7 | 2.000 | 3/3 (100.0%) | 29.36 |
| hybrid_wide | 0/7 | 1.800 | 5/6 (83.3%) | 21.87 |

## Ví dụ và trace

### test-new-01

Câu hỏi: Which database type integrates multiple sources and is optimized for analysis and reporting rather than transactions?

Trả lời (answered): A data warehouse is the database type that integrates multiple sources and is optimized for analysis and reporting rather than transactions. It stores data in a combined manner and is designed to perform complex queries and data analysis quickly and efficiently. [3fb6dbe532b6668b61a316ab0ad6616074c3e5a7eb034e0e30733fdd8e84a611]

Trace: `results/test/hybrid_wide/traces.json`; nhãn và trang evidence trong `reviews.json`.

### test-absent-3

Câu hỏi: What was the exact measured database outage duration at OpenStax on 15 November 2026?

Trả lời (abstain): The indexed OpenStax textbook corpus does not contain information about the exact measured database outage duration at OpenStax on 15 November 2026.

Trace: `results/test/hybrid_wide/traces.json`; nhãn và trang evidence trong `reviews.json`.

## Thời gian, chi phí và giới hạn

- Mỗi trace ghi thời gian agent, ranking query gốc riêng, số model/search call và token prompt/completion. Bảng thời gian không gồm lượt ranking query gốc; xem `ranking_ms` để cộng nếu cần tổng đánh giá.
- Embedding cache dùng chung, chạy lạnh/nóng khác nhau; không kết luận tốc độ phương pháp chỉ từ tổng giây này. Retry ẩn của SDK và usage của response lỗi có thể chưa được ghi đầy đủ.
- Chi phí USD là null/chưa xác minh, không phải 0 USD. Không có đơn giá provider đã xác nhận nên không bịa số tiền; token là đơn vị tài nguyên đã đo. Kết quả baseline TF-IDF vẫn có chi phí gọi agent model.
- Chỉ số exact evidence có thể bỏ sót nguồn tương đương chưa gán gold. Citation render kiểm tra ID không chứng minh nội dung. Các nhãn chưa có `human_verified: true` cần người làm bài tiếp tục kiểm tra với PDF.
- Câu thiếu evidence thuộc phạm vi corpus chọn, không chứng minh cả sách không chứa thông tin. Bốn câu thiếu evidence chưa bao phủ nhiều kiểu từ chối khó.
- Không xử lý bảng/ảnh/biểu đồ và không tuyên bố bonus; không có UI, tool truy cập web hoặc nguồn ngoài corpus.

## Tái lập và bài nộp

Hướng dẫn môi trường/lệnh trong [README_SOLUTION.md](../../README_SOLUTION.md); thiết kế và audit trong `docs/IMPLEMENTATION.md` và `docs/REVIEW_GUIDE.md`. `data/provenance.json` giữ nguồn, license, số trang và hash. `results/comparison.csv` là bảng tổng hợp, từng thư mục có config/trace/reviews/summary.

Đã chạy 20 kiểm thử offline thành công (starter + hành vi mới: fusion, schema/gold, budget, chuẩn hóa ID, provider error). Unit tests dùng mock chỉ kiểm tra code; số benchmark ở trên đến từ model/DB thật.

Nộp link repo cá nhân theo SUBMISSION.md và bảo đảm người chấm có quyền xem. Giữ `.env`, token và cache embedding ngoài Git. Trạng thái AI review và xác nhận của người làm bài được công bố ở đầu báo cáo.

## Phụ lục nhãn test

| Cấu hình | Query ID | Status | Context | Answer | Citation support | Lý do |
|---|---|---|---:|---:|---|---|
| tfidf | test-new-01 | error | 0 | 0 | [] | Trace ghi APIConnectionError trước model/tool event thành công; không có context/answer. Chấm operational 0; giữ lỗi riêng và loại khỏi mẫu số chất lượng theo starter, không đổi thành abstention. |
| tfidf | test-new-02 | error | 0 | 0 | [] | Trace ghi APIConnectionError trước model/tool event thành công; không có context/answer. Chấm operational 0; giữ lỗi riêng và loại khỏi mẫu số chất lượng theo starter, không đổi thành abstention. |
| tfidf | test-new-03 | answered | 2 | 2 | [True] | PDF trang 99 xác nhận referential constraint, quan hệ foreign/primary key và ngăn orphaned records. |
| tfidf | test-new-04 | answered | 2 | 1 | [False] | PDF trang 100 xác nhận giá trị atomic/indivisible, single/simple và ví dụ mỗi số điện thoại có một hàng riêng. Answer thêm "or column" không được ví dụ chứng minh: giữ answer 1, context 2 và citation false. |
| tfidf | test-new-05 | answered | 2 | 2 | [True, True] | PDF trang 100 và 109 xác nhận physical design chọn data types, indexing và storage, triển khai trên DBMS. |
| tfidf | test-absent-3 | abstain | — | — | [] | Đã đối chiếu phạm vi toàn bộ 47 trang được index và các đoạn có password/outage: không có giá hosting/thời lượng sự cố OpenStax 2026, credential thực hay ID triển khai được hỏi. Answer từ chối rõ, không đưa giá trị suy đoán. Chỉ kết luận trong corpus đã index. |
| tfidf | test-absent-4 | abstain | — | — | [] | Đã đối chiếu phạm vi toàn bộ 47 trang được index và các đoạn có password/outage: không có giá hosting/thời lượng sự cố OpenStax 2026, credential thực hay ID triển khai được hỏi. Answer từ chối rõ, không đưa giá trị suy đoán. Chỉ kết luận trong corpus đã index. |
| hybrid_wide | test-new-01 | answered | 2 | 2 | [True] | PDF trang 95 xác nhận data warehouse tích hợp nhiều nguồn, tối ưu analysis/reporting thay vì transaction processing. |
| hybrid_wide | test-new-02 | answered | 2 | 2 | [True] | PDF trang 96 xác nhận bitmap index dùng 0/1 cho cột ít giá trị phân biệt; các ví dụ trong answer khớp. |
| hybrid_wide | test-new-03 | answered | 2 | 2 | [True] | PDF trang 99 xác nhận referential constraint, quan hệ foreign/primary key và ngăn orphaned records. |
| hybrid_wide | test-new-04 | answered | 2 | 2 | [True] | PDF trang 100 xác nhận giá trị atomic/indivisible, single/simple và ví dụ mỗi số điện thoại có một hàng riêng. |
| hybrid_wide | test-new-05 | answered | 2 | 2 | [True, True] | PDF trang 100 và 109 xác nhận physical design chọn data types, indexing và storage, triển khai trên DBMS. |
| hybrid_wide | test-absent-3 | abstain | — | — | [] | Đã đối chiếu phạm vi toàn bộ 47 trang được index và các đoạn có password/outage: không có giá hosting/thời lượng sự cố OpenStax 2026, credential thực hay ID triển khai được hỏi. Answer từ chối rõ, không đưa giá trị suy đoán. Chỉ kết luận trong corpus đã index. |
| hybrid_wide | test-absent-4 | abstain | — | — | [] | Đã đối chiếu phạm vi toàn bộ 47 trang được index và các đoạn có password/outage: không có giá hosting/thời lượng sự cố OpenStax 2026, credential thực hay ID triển khai được hỏi. Answer từ chối rõ, không đưa giá trị suy đoán. Chỉ kết luận trong corpus đã index. |
