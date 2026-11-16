"""Generate the report from measured runs and separately reviewed labels.

python -m src.report -- no network or model calls.
"""
import csv
import io
import hashlib
from collections import Counter
from .lab import ROOT, CONFIGS, load, save, summarize, digest


def ratio(value):
    n, total = value['n'], value['N']
    return f'{n}/{total} ({100*n/total:.1f}%)' if total else '0/0 (không áp dụng)'


def generate():
    selected = load(ROOT/'configs/selected.json')
    if hashlib.sha256((ROOT/'src/lab.py').read_bytes()).hexdigest() != selected['source_sha256']:
        raise ValueError('Frozen agent source changed after test')
    questions = load(ROOT/'data/questions.json')
    rows = []
    for split, names in [('dev', list(CONFIGS)), ('test', ['tfidf', selected['name']])]:
        for name in names:
            path = ROOT/'results'/split/name
            traces = load(path/'traces.json')
            expected_ids = {q['id'] for q in questions if q['split']==split}
            if {t['query_id'] for t in traces} != expected_ids:
                raise ValueError(f'Incomplete evaluation: {split}/{name}')
            summarize(path, [q for q in questions if q['split']==split], traces)
            summary = load(path/'summary.json')
            reviews = load(path/'reviews.json')
            if {r['query_id'] for r in reviews} != expected_ids:
                raise ValueError(f'Incomplete reviews: {split}/{name}')
            traces_by_id = {t['query_id']: t for t in traces}
            for review in reviews:
                if review.get('reviewed_trace_sha256') and review['reviewed_trace_sha256'] != digest(traces_by_id[review['query_id']]):
                    raise ValueError(f"Reviewed trace changed: {split}/{name}/{review['query_id']}")
            rows.append((split, name, summary, traces, reviews))
    chosen = next(row for row in rows if row[0]=='test' and row[1]==selected['name'])
    baseline = next(row for row in rows if row[0]=='test' and row[1]=='tfidf')
    verification_rows = [
        f"| {split} / {name} | {sum(r.get('human_verified') is True for r in reviews)}/{len(reviews)} | {sum(r.get('ai_reviewed') is True for r in reviews)}/{len(reviews)} |"
        for split, name, _, _, reviews in rows
    ]
    for name in ['tfidf', selected['name']]:
        path = ROOT/'results/test-attempt1'/name
        summarize(path, [q for q in questions if q['split']=='test'], load(path/'traces.json'))
    lines = [
        '# Báo cáo Day 7 — Trương Đức Phát — 2A202603757', '',
        '## Phạm vi và dữ liệu', '',
        'Hoàn thành pipeline phần cơ bản: agent thật, ba phương pháp retrieval, benchmark dev/test, hai cấu hình thử cải thiện, trace và đánh giá. Không thực hiện bonus 100 trang đa phương thức.', '',
        '- Nguồn: OpenStax/Rice University, *Foundations of Information Systems*. Attribution và CC BY-NC-SA 4.0 giữ trong metadata và `data/provenance.json` theo bản PDF Day 6.',
        '- Corpus: **47 trang hợp lệ, 463 chunk**, chương 2 và 3. Không đại diện toàn bộ 497 trang. Citation dùng trang PDF vật lý; trang in = trang PDF - 10.',
        '- PostgreSQL/pgvector Day 6, exact cosine, score = 1 - distance; strategy `20261114T132647004212Z_B`. Không ghi lại index.',
        '- Embedding `text-embedding-3-small`, 1536 chiều. Dùng lại vector tài liệu; chỉ embed query mới, cache theo model/dimensions/query.',
        '- Agent `gpt-4.1-mini`; response model thực ghi trong từng model event. Cấu hình model, prompt và tool chung khi so sánh.',
        '- Benchmark 24 câu: dev 15 có đáp án + 2 thiếu evidence; test 5 có đáp án + 2 thiếu evidence. Dev tái sử dụng Day 6; test mới soạn trước thí nghiệm, thay bộ test Day 6 đã dùng.',
        '- Câu hỏi tiếng Anh phù hợp textbook. Gold gồm nguồn/trang/evidence nguyên văn, alternatives là OR. Không có câu multi-hop trong benchmark cơ bản này.',
        '- Gold/expected answer/answerable chỉ nằm ở evaluator, không truyền vào controller hoặc tool.', '',
        '**Nguồn nhãn:** Nhãn ban đầu do Codex hỗ trợ đối chiếu câu trả lời và các chunk citation. Trạng thái xác nhận của người làm bài được lấy từ `human_verified` trong từng file review; không suy ra xác nhận cho các cấu hình khác. Tập test được giữ riêng khỏi chọn cấu hình, nhưng không phải benchmark mù do người soạn độc lập.', '',
        '| Split / cấu hình | Người làm bài đã xác nhận | AI đã soát lại với PDF gốc |',
        '|---|---:|---:|',
        *verification_rows, '',
        'Lần soát nguồn bổ sung đã kiểm tra 79 mục trong 7 file (gồm 14 mục ở lượt test đầu), giữ nguyên 17 mục dev/hybrid_wide do người làm bài xác nhận. Mọi citation được kiểm tra ID trong context và text khớp PDF; nội dung được chấm riêng theo đúng phạm vi/điều kiện. `ai_reviewed: true` không tương đương `human_verified: true`. Mỗi mục AI review lưu hash trace/PDF và lý do cho từng citation.', '',
        '## Kiến trúc và cấu hình', '',
        'Model chọn `search(query)` hoặc `finish(status, answer, citations)`. Backend search cố định theo cấu hình. Tối đa 3 lượt search; model có thể viết lại query. Lỗi provider/DB ghi error riêng. Trả lời không có citation hợp lệ hoặc hết lượt tìm dẫn đến abstention.', '',
        'TF-IDF dùng starter; dense truy vấn pgvector thật; hybrid lấy top-20 từng nhánh và RRF `Σ 1/(60+rank)`, không cộng score thô. Tất cả không filter và dùng cùng snapshot corpus. Context ưu tiên kết quả mới rồi evidence cũ, dedup theo ID, giữ block nguyên vẹn gồm nguồn/trang; budget tính ký tự, gồm header.', '',
        '| Cấu hình | Phương pháp | Top-k | Budget ký tự | Giả thuyết |',
        '|---|---|---:|---:|---|',
        '| tfidf (baseline) | TF-IDF | 3 | 6000 | Baseline lexical từ starter, nối agent thật |',
        '| dense | Dense Day 6 | 3 | 6000 | Semantic retrieval cải thiện paraphrase |',
        '| hybrid | Dense + TF-IDF RRF | 3 | 6000 | Cải thiện 1: kết hợp lexical/semantic tăng coverage |',
        '| hybrid_wide | RRF | 5 | 10000 | Cải thiện 2: nhiều context hơn giữ đủ điều kiện |', '',
        'Thí nghiệm wide đổi cả top-k và budget nên không xác định tác động riêng mỗi tham số. Agent/search vẫn có giới hạn như nhau. Các mức trên là lựa chọn thực nghiệm, không phải giới hạn của đề.', '',
        '## Kết quả retrieval và context', '',
        'Ranking query gốc được đo riêng với ranking của query agent viết lại. Hit@1/3 có cùng cutoff cho mọi cấu hình; Context Evidence Rate đo context cuối sau mọi lượt. Mẫu số chỉ gồm câu có đáp án. Match tự động đòi đúng source/page và evidence nguyên văn trong chunk; có review ngữ nghĩa riêng.', '',
        '| Split / cấu hình | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Tổng giây agent | Prompt / completion token |',
        '|---|---|---|---|---:|---|',
    ]
    csv_rows = []
    for split, name, summary, traces, reviews in rows:
        retrieval = summary['retrieval']
        lines.append(f"| {split} / {name} | {ratio(retrieval['hit_at_1'])} | {ratio(retrieval['hit_at_3'])} | {ratio(retrieval['context_evidence_rate'])} | {summary['total_seconds']:.2f} | {summary['prompt_tokens']} / {summary['completion_tokens']} |")
        csv_rows.append(dict(split=split, config=name, hit1=ratio(retrieval['hit_at_1']),
            hit3=ratio(retrieval['hit_at_3']), context=ratio(retrieval['context_evidence_rate']),
            answer_mean=summary['agent']['grounded_answer']['mean'],
            prompt_tokens=summary['prompt_tokens'], completion_tokens=summary['completion_tokens'],
            seconds=summary['total_seconds'], errors=summary['errors']))
    lines += ['', '## Kết quả agent và citation', '',
        '| Split / cấu hình | Tool use | Answer 0 / 1 / 2 | Mean /2 | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |',
        '|---|---|---|---:|---|---|---|---|']
    for split, name, s, traces, reviews in rows:
        a = s['agent']; g = a['grounded_answer']
        lines.append(f"| {split} / {name} | {ratio(a['tool_use'])} | {g['0']} / {g['1']} / {g['2']} | {g['mean']:.3f} | {ratio(a['citation_validity'])} | {ratio(a['answer_citation_coverage'])} | {ratio(a['abstention'])} | {ratio(a['false_abstention'])} |")
    lines += ['', '## Phân tích lỗi dev và trước/sau', '',
        '1. **Lỗi xuất citation:** lượt đầu model trả danh sách citation có ID đúng nhưng answer chưa có inline marker; kiểm tra quá cứng làm từ chối nhầm. Đã giữ `results/initial-dev/`, sửa render marker và chạy lại dev thật. Tiếp đó phát hiện model trả cả header `ID | nguồn | page`; adapter cuối chỉ lấy ID khớp chính xác context. Bản trước chuẩn hóa tại `results/pre-normalization/`. Dev cuối replay bước render từ finish thật đã lưu, không tạo câu trả lời mới, không thay search/context/token/timing. Test chạy end-to-end với adapter cuối.', '',
        '2. **q01 — TF-IDF tìm nhầm “characteristics”:** query gốc lấy domain characteristics và four-V headings, agent tìm lại vẫn không có triad; context grade 0, answer grade 0 và từ chối nhầm. Dense tìm đủ quality evidence; hybrid top-3 còn thiếu đoạn trực tiếp; hybrid_wide lấy được p105, context và answer grade 2. Kết quả cho thấy cần đo context cuối bên cạnh ranking gốc.', '',
        '3. **q09 — thêm ngữ cảnh sai mô hình:** dense trả đúng định nghĩa e-commerce nhưng bổ sung chiến lược marketplace từ p69. Chấm answer 1, citation thứ ba false thay vì coi có ID là đúng. Hybrid_wide dùng p68 và ví dụ Amazon p67, answer 2. Chunk độc lập có đại từ “this model” vẫn có thể mất ngữ cảnh dù retrieval liên quan.', '',
        '4. **Hybrid không luôn tốt hơn:** q01 giải thích completeness lẫn loại bỏ duplicate; q05 dẫn thừa chapter outline. Với q04, lần soát nguồn bổ sung tìm thấy context trang 52 hỗ trợ phần secure/easily retrievable, nên sửa answer grade 1→2; citation duy nhất trang 53 vẫn false do không dẫn nguồn cho phần bổ sung. Đây là sửa nhãn sau kiểm tra đầy đủ context, không sửa agent/prompt/retrieval. Giữ nguyên snapshot lựa chọn ban đầu trong configs/selected.json; cấu hình chọn vẫn là hybrid_wide.', '',
        '## Chọn cấu hình và đánh giá test', '',
        f"Tiêu chí trước test: grounded-answer mean → abstention đúng → context evidence rate → token thấp hơn. Chọn **{selected['name']}** trên dev. Cấu hình khóa tại `{selected['frozen_at_utc']}` (UTC), kèm hash source/corpus/benchmark/prompt-tools trong `configs/selected.json`. Không đổi prompt/retrieval từ kết quả test.", '',
        f"Test chạy cả TF-IDF baseline và cấu hình chọn trên cùng 7 câu. Cấu hình chọn có grounded-answer mean **{chosen[2]['agent']['grounded_answer']['mean']:.3f}/2**, citation hợp lệ **{ratio(chosen[2]['agent']['citation_validity'])}**, abstention **{ratio(chosen[2]['agent']['abstention'])}**. Đây là benchmark nhỏ theo nhãn AI hỗ trợ, không suy rộng thành độ chính xác thực tế toàn miền.", '',
        'Lượt test đầu có 3 APIConnectionError ở baseline, không xóa hoặc đổi thành abstention. Toàn bộ 14 trace/nhãn/summary lượt đầu giữ ở `results/test-attempt1/`. Đã chạy lại toàn bộ cặp baseline/cấu hình chọn với source/prompt/model/config giữ nguyên; bảng chính là lượt hai tại `results/test/`. Lượt hai baseline còn 2 APIConnectionError trước model/tool event; cấu hình chọn không có lỗi. Dừng lặp, giữ cả hai lượt thay vì thử đến khi đẹp. Đây là phép lặp lại kiểm tra kết nối, không phải chọn lại cấu hình.', '',
        'Mean chất lượng trong bảng dùng quy tắc starter: lỗi provider được đếm riêng và loại khỏi mẫu số chất lượng. Vì baseline có lỗi, không diễn giải mean có điều kiện này như điểm trên toàn bộ 5 câu. Nhãn context/answer của câu lỗi vẫn ghi 0 trong operational view; không gọi lỗi là từ chối.', '',
        '| Cấu hình test | Context grade 0 / 1 / 2 (5 câu có đáp án) | Lỗi hệ thống | Phân bố số lượt search |',
        '|---|---|---:|---|']
    for split, name, s, traces, reviews in rows:
        if split != 'test':
            continue
        counts = Counter(r['context_grade'] for r in reviews if 'context_grade' in r)
        lines.append(f"| {name} | {counts[0]} / {counts[1]} / {counts[2]} | {s['errors']} | {dict(Counter(s['search_counts']))} |")
    lines += ['', '| Test / cấu hình | Grounded mean gồm lỗi=0, mẫu số 5 câu có đáp án |', '|---|---:|']
    for split, name, s, traces, reviews in rows:
        if split == 'test':
            grades = [r['answer_grade'] for r in reviews if 'answer_grade' in r]
            lines.append(f"| {name} | {sum(grades)/len(grades):.3f}/2 |")
    lines += ['', '| Lượt test đầu / cấu hình | Lỗi hệ thống / tổng | Mean thành công /2 | Citation hợp lệ | Thời gian giây |', '|---|---|---:|---|---:|']
    for name in ['tfidf', selected['name']]:
        first = load(ROOT/'results/test-attempt1'/name/'summary.json')
        lines.append(f"| {name} | {first['errors']}/{first['cases']} | {first['agent']['grounded_answer']['mean']:.3f} | {ratio(first['agent']['citation_validity'])} | {first['total_seconds']:.2f} |")
    lines += ['', '## Ví dụ và trace', '']
    for query_id in ['test-new-01', 'test-absent-3']:
        t = next(t for t in chosen[3] if t['query_id']==query_id)
        lines += [f"### {query_id}", '', f"Câu hỏi: {t['question']}", '',
                  f"Trả lời ({t['status']}): {t['answer']}", '',
                  f"Trace: `results/test/{selected['name']}/traces.json`; nhãn và trang evidence trong `reviews.json`.", '']
    lines += ['## Thời gian, chi phí và giới hạn', '',
        '- Mỗi trace ghi thời gian agent, ranking query gốc riêng, số model/search call và token prompt/completion. Bảng thời gian không gồm lượt ranking query gốc; xem `ranking_ms` để cộng nếu cần tổng đánh giá.',
        '- Embedding cache dùng chung, chạy lạnh/nóng khác nhau; không kết luận tốc độ phương pháp chỉ từ tổng giây này. Retry ẩn của SDK và usage của response lỗi có thể chưa được ghi đầy đủ.',
        '- Chi phí USD là null/chưa xác minh, không phải 0 USD. Không có đơn giá provider đã xác nhận nên không bịa số tiền; token là đơn vị tài nguyên đã đo. Kết quả baseline TF-IDF vẫn có chi phí gọi agent model.',
        '- Chỉ số exact evidence có thể bỏ sót nguồn tương đương chưa gán gold. Citation render kiểm tra ID không chứng minh nội dung. Các nhãn chưa có `human_verified: true` cần người làm bài tiếp tục kiểm tra với PDF.',
        '- Câu thiếu evidence thuộc phạm vi corpus chọn, không chứng minh cả sách không chứa thông tin. Bốn câu thiếu evidence chưa bao phủ nhiều kiểu từ chối khó.',
        '- Không xử lý bảng/ảnh/biểu đồ và không tuyên bố bonus; không có UI, tool truy cập web hoặc nguồn ngoài corpus.', '',
        '## Tái lập và bài nộp', '',
        'Hướng dẫn môi trường/lệnh trong [README_SOLUTION.md](../../README_SOLUTION.md); thiết kế và audit trong `docs/IMPLEMENTATION.md` và `docs/REVIEW_GUIDE.md`. `data/provenance.json` giữ nguồn, license, số trang và hash. `results/comparison.csv` là bảng tổng hợp, từng thư mục có config/trace/reviews/summary.', '',
        'Đã chạy 20 kiểm thử offline thành công (starter + hành vi mới: fusion, schema/gold, budget, chuẩn hóa ID, provider error). Unit tests dùng mock chỉ kiểm tra code; số benchmark ở trên đến từ model/DB thật.', '',
        'Nộp link repo cá nhân theo SUBMISSION.md và bảo đảm người chấm có quyền xem. Giữ `.env`, token và cache embedding ngoài Git. Trạng thái AI review và xác nhận của người làm bài được công bố ở đầu báo cáo.', '',
        '## Phụ lục nhãn test', '',
        '| Cấu hình | Query ID | Status | Context | Answer | Citation support | Lý do |',
        '|---|---|---|---:|---:|---|---|']
    for split, name, s, traces, reviews in rows:
        if split != 'test': continue
        by_id = {t['query_id']: t for t in traces}
        for r in reviews:
            t = by_id[r['query_id']]
            lines.append(f"| {name} | {r['query_id']} | {t['status']} | {r.get('context_grade','—')} | {r.get('answer_grade','—')} | {r['citation_support']} | {r['reason'].replace('|','/')} |")
    path = ROOT/'report/individual/2A202603757_TruongDucPhat.md'
    path.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(csv_rows[0]))
    writer.writeheader(); writer.writerows(csv_rows)
    (ROOT/'results/comparison.csv').write_text(buffer.getvalue(), encoding='utf-8', newline='')
    print(str(path))


if __name__ == '__main__':
    generate()
