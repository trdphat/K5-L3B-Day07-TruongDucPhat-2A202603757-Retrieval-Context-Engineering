# Triển khai Day 7

## Phạm vi

Phần cơ bản 85 điểm; không tuyên bố hoàn thành bonus multimodal. Corpus là 47 trang được chọn của chương 2/3 trong OpenStax *Foundations of Information Systems*, không phải toàn bộ 497 trang. Giữ attribution và CC BY-NC-SA 4.0 theo manifest Day 6. Trang trong citation là trang PDF vật lý, 1-based; trang in của corpus này = trang PDF - 10.

## Kiến trúc

`src/lab.py` chứa adapter pgvector chỉ đọc, ba retriever, controller gọi model thật, vòng lặp agent và evaluator. Không cần framework agent hay UI. Dùng trực tiếp bảng `ingestion_chunks`, strategy `20261114T132647004212Z_B`, 463 chunk. Model query `text-embedding-3-small`, 1536 chiều, cosine exact; không embed lại tài liệu, không gọi upsert.

TF-IDF dùng `starter/baseline.py`. Dense tìm trên PostgreSQL Day 6. Hybrid lấy top-20 mỗi nhánh và hợp nhất `sum(1/(60+rank))`, tie-break bằng chunk ID. Không cộng hai score khác thang. Cả ba dùng cùng corpus, không filter. Số candidate nội bộ khác số chunk trả tool, ghi trong config.

Model agent chọn tool `search` hoặc `finish`. Backend search được cố định theo từng cấu hình để so sánh công bằng. Agent có thể viết lại query, tối đa 3 lượt search; không lặp query nguyên văn. `finish` trả `answered` hoặc `abstain`. Lỗi API/DB/schema ghi `error`, không giả kết quả hoặc đổi thành abstention.

Mỗi lượt, kết quả mới được ưu tiên, tiếp theo bằng chứng cũ, dedup theo ID. Chỉ các block nguyên vẹn vừa budget ký tự mới được đưa vào context; có header ID/nguồn/trang. Không nén bằng LLM, không tự cắt mất điều kiện. Việc ưu tiên kết quả mới có thể loại evidence cũ, được ghi là giới hạn. Toàn bộ lịch sử tool lưu trên disk; model nhận context tích lũy cuối để tránh nhân budget.

Danh sách citation cấu trúc do model chọn được kiểm tra có trong context và render thành `[chunk-id]` nếu thiếu trong answer. Đây là bước định dạng, không phải kiểm chứng ngữ nghĩa. Review riêng chấm từng citation. Nội dung tool là dữ liệu không đáng tin, không phải chỉ dẫn.

## Benchmark và đánh giá

15 câu dev có đáp án từ Day 6, thêm 2 câu dev thiếu evidence. Tạo 5 câu test có đáp án mới (warehouse, bitmap, referential constraint, 1NF, physical design) và 2 câu thiếu evidence mới. Không sử dụng lại 5 câu test Day 6. Test mới được tạo trước thử nghiệm Day 7, không dùng chọn cấu hình; được xem ở bước soạn nhãn nên đây là held-out theo quy trình cấu hình, không phải blind benchmark với một người soạn độc lập.

Các câu hỏi được giữ bằng tiếng Anh để phù hợp textbook và benchmark Day 6. Agent trả lời theo ngôn ngữ câu hỏi. Câu thiếu evidence được kiểm tra trên toàn corpus đã index bằng tìm từ khóa và đối chiếu phạm vi; không kết luận toàn bộ cuốn sách không có thông tin.

Gold chỉ được đọc ở preparation và evaluation. `run_agent` chỉ nhận chuỗi câu hỏi, retriever và config. Retrieval metric query gốc được tính riêng; agent có thể search lại, nên context evidence rate có thể cao hơn original Hit@3. Gold alternatives là OR; mỗi evidence phải nằm trong một chunk đúng nguồn/trang. Không tuyên bố metric multi-hop.

Hit@1/3 và context evidence rate dùng mẫu số câu có đáp án. Context metric dùng nguyên văn evidence + provenance; có thể thấp hơn đánh giá ngữ nghĩa nếu một đoạn tương đương không nằm trong gold. Review lưu thêm context grade 0/1/2, grounded answer 0/1/2, từng citation support và abstention. Script tổng hợp dùng `starter/agent_metrics.py`.

Review trong bài này do Codex đối chiếu riêng câu trả lời và nội dung các chunk nguồn; là **AI hỗ trợ kiểm tra**, không phải nhãn con người đã xác nhận. Sinh viên cần đọc lại nhãn và nguồn trước khi nộp. Không dùng một phép kiểm tra ID để tự gán tất cả citation đúng.

## Thí nghiệm

Baseline: TF-IDF + agent thật. So sánh thêm dense và hybrid RRF. Hai giả thuyết cải thiện: hybrid tăng coverage so với lexical; hybrid_wide tăng top-k 3→5 và budget 6000→10000 ký tự để khôi phục điều kiện. Thí nghiệm thứ hai đổi hai tham số cùng lúc nên không quy kết tác động riêng từng tham số. Giữ model/prompt/max search chung.

Tiêu chí chọn đã lưu trong `configs/selection_policy.json`: grounded-answer mean, abstention, context evidence rate, rồi token thấp hơn. Chốt tại `configs/selected.json`, kèm hash corpus, benchmark, prompt/tools và source. Test từ chối chạy khi hash thay đổi.

Kết quả dev đầu trước sửa lỗi citation nằm trong `results/initial-dev/`; không trộn với kết quả hiện hành. Sau sửa inline citation đã chạy lại dev thật. Tiếp đó phát hiện model đôi khi trả toàn header `ID | nguồn | page` thay vì ID; chuẩn hóa phần ID chỉ khi khớp chính xác context, không fuzzy match. Bản dev trước chuẩn hóa ở `results/pre-normalization/`. Dev cuối replay riêng bước render xác định từ finish thật đã lưu, không gọi lại model, không thay đổi câu trả lời thô, search, context, token hoặc timing. Trace ghi rõ replay. Test chạy end-to-end với adapter cuối sau khi chốt; không đổi prompt/retrieval theo test.

Lượt test đầu có 3 APIConnectionError ở baseline, được giữ tại `results/test-attempt1/`. Chạy lại toàn bộ cặp 7 câu baseline và 7 câu cấu hình chọn, giữ nguyên source/prompt/model/config; kết quả lượt hai ở `results/test/`, baseline còn 2 lỗi kết nối. Dừng lặp và báo cáo cả hai lượt. Không retry chọn lọc để xóa lỗi, không điều chỉnh từ test. Ngoài mean theo starter (loại lỗi provider), báo cáo thêm mean gồm lỗi=0 trên đủ 5 câu có đáp án.

## Tài nguyên và lỗi

Embedding query cache tại `.cache/embeddings/`, key gồm model/dimensions/query. Cache không lưu credential, không đưa vào Git. Chạy đầu lạnh có thể chậm và tốn embedding token hơn; so sánh thời gian các lần có cache là quan sát có giới hạn, không phải microbenchmark tốc độ retriever.

Trace lưu token prompt/completion theo từng response và embedding token thực gọi. Chi phí USD để null vì không có đơn giá provider được xác minh; không coi null là 0. TF-IDF không gọi dịch vụ embedding nhưng agent của mọi phương pháp vẫn gọi model. Retry do SDK có thể gây usage ngoài response thành công không được ghi. Không biết hóa đơn thực tế từ các trace này.

Output được ghi sau từng câu; chạy lại cùng lệnh tiếp tục các câu còn thiếu. Muốn chạy mới, dùng bản sao riêng của results hoặc đổi thư mục sau khi lưu phiên bản cũ; không ghi đè kết quả test để chỉnh bài. Provider errors giữ nguyên trong trace. Với phần cơ bản, lỗi được báo riêng khỏi chất lượng theo starter; bonus có quy tắc khác và không thực hiện ở đây.

## Tái tạo dữ liệu

`python -m src.lab prepare` xuất đúng snapshot strategy B từ DB, chuẩn hóa schema, kiểm tra gold và lưu hash. Không cần chạy prepare lại khi chỉ muốn hỏi hoặc chạy benchmark. Nếu mất volume Day 6, tái tạo theo pipeline Day 6 rồi xác nhận model, strategy và hash trước khi báo kết quả so sánh.
