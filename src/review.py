"""Materialize explicit decisions after separate Codex evidence inspection.

These labels are AI-assisted, not claimed to be human annotations. This is not
an automatic grading algorithm; decisions and exceptional citation indices below
were assigned after reading the actual answer and evidence packets.
"""
from .lab import ROOT, load, save

DEV_GRADES = {
    'dense': [2,2,2,2,2,2,2,2,1,2,2,2,2,2,2],
    'tfidf': [0,2,2,2,2,2,2,2,2,2,2,2,2,2,2],
    'hybrid': [1,2,2,2,2,2,2,2,2,2,2,2,2,2,2],
    'hybrid_wide': [2]*15,
}
TOPICS = [
    'Quality triad: accurate, complete, consistent; check scope of definition.',
    'Federated analytics analyzes distributed data without central relocation.',
    'Durability preserves completed transactions after a crash.',
    'Retention includes requirements-based periods, archiving, purging and policies.',
    'Technical DAMA-DMBOK versus business MIKE2.0; maturity detail checked.',
    'Veracity means reliability, accuracy and trustworthiness.',
    'Infrastructure covers storage, processing, analysis and governance.',
    'Nonprogrammed decisions are unique, complex and lack predefined guidelines.',
    'E-commerce means buying/selling online; additional strategies need correct model scope.',
    'Mobile databases save storage/power and fit limited device resources.',
    'Check constraints restrict column values, including positive age and status.',
    'Least privilege gives only necessary permissions.',
    'Parameterized queries treat input as data rather than executable code.',
    'Document storage JSON/BSON/XML and nested structures are supported.',
    'SQLite is explicitly named for local mobile storage.',
]
EXCEPTIONS = {
    ('tfidf', 'q01'): (0, [], 'Lexical searches return domain characteristics and four-V headings, without the requested quality triad. Answerable question wrongly abstained.'),
    ('dense', 'q09'): (2, [2], 'Core e-commerce definition correct, but added search/filtering and buyer-seller strategy comes from marketplace context on p69. Third citation has wrong model scope; partial grounding.'),
    ('hybrid', 'q01'): (1, [1], 'Retrieved veracity/cleanliness/ACID rather than direct quality definition. Completeness is conflated with duplicate removal; cleanliness does not support that attribution.'),
    ('hybrid', 'q04'): (2, [0], 'Full context p52 supports security/retrievability, so answer grade 2. Sole citation p53 omits that support: citation remains false.'),
    ('hybrid', 'q05'): (2, [2], 'Answer facts supported by two p55 chunks. Extra p51 chapter outline citation does not support the framework differences.'),
    ('hybrid_wide', 'q01'): (2, [], 'p105 supports accurate/consistent/complete/timely and checking activities. Timely is additional supported information allowed by alternative gold.'),
    ('hybrid_wide', 'q09'): (2, [], 'p68 supports definition, examples and platform strategy; p67 supports Amazon fulfillment example. No p69 marketplace strategy is asserted.'),
}


def write_dev_reviews():
    questions = {q['id']: q for q in load(ROOT/'data/questions.json')}
    for name, grades in DEV_GRADES.items():
        path = ROOT/'results/dev'/name
        if (path/'reviews.json').exists() and any(
                r.get('human_verified') is True or r.get('ai_reviewed') is True
                for r in load(path/'reviews.json')):
            print(f'Preserved completed reviews: dev/{name}')
            continue
        reviews = []
        for t in load(path/'traces.json'):
            q = questions[t['query_id']]
            rows = {c['id']: c for e in t['events'] if e['event']=='search' for c in e['results']}
            r = dict(query_id=q['id'], citation_support=[True]*len(t['citations']),
                     reviewer='Codex separate answer/evidence inspection', human_verified=False,
                     evidence_pages=sorted({c['page'] for cid, c in rows.items() if cid in t['context_ids']}))
            if q['answerable']:
                index = int(q['id'][1:])-1
                r.update(answer_grade=grades[index], context_grade=2, reason=TOPICS[index])
                if (name, q['id']) in EXCEPTIONS:
                    grade, unsupported, reason = EXCEPTIONS[(name, q['id'])]
                    r.update(context_grade=grade, reason=reason)
                    for i in unsupported:
                        r['citation_support'][i] = False
            else:
                r.update(abstention_correct=True, reason='Explicit indexed-corpus insufficiency, no guessed value. Corpus scope and absence checks support abstention.')
            reviews.append(r)
        save(path/'reviews.json', reviews)
    print('Dev review generation complete; human-verified files preserved.')


def write_test_reviews():
    """Explicit decisions for both unchanged test attempts after evidence inspection."""
    reasons = {
        'test-new-01': 'p95 explicitly defines warehouse, source integration and analysis/reporting rather than transactions.',
        'test-new-02': 'p96 states bitmap uses zeros/ones and low-cardinality columns; examples match.',
        'test-new-03': 'p99 defines referential constraint, foreign/primary-key matching and orphan prevention.',
        'test-new-04': 'p100 supports atomic indivisible values, single simple values and the separate-row phone example.',
        'test-new-05': 'p109 and p100 both support physical design, DBMS implementation, types, indexes and storage.',
    }
    questions = {q['id']: q for q in load(ROOT/'data/questions.json')}
    for folder in ['test-attempt1', 'test']:
        for name in ['tfidf', 'hybrid_wide']:
            path = ROOT/'results'/folder/name
            if (path/'reviews.json').exists() and any(
                    r.get('human_verified') is True or r.get('ai_reviewed') is True
                    for r in load(path/'reviews.json')):
                print(f'Preserved completed reviews: {folder}/{name}')
                continue
            reviews = []
            for t in load(path/'traces.json'):
                q = questions[t['query_id']]
                rows = {c['id']: c for e in t['events'] if e['event']=='search' for c in e['results']}
                r = dict(query_id=q['id'], citation_support=[True]*len(t['citations']),
                         reviewer='Codex separate answer/evidence inspection', human_verified=False,
                         evidence_pages=sorted({c['page'] for cid, c in rows.items() if cid in t['context_ids']}))
                if q['answerable']:
                    r.update(answer_grade=2, context_grade=2, reason=reasons[q['id']])
                    if t['status'] == 'error':
                        r.update(answer_grade=0, context_grade=0,
                            reason='APIConnectionError before any successful model/tool event; no answer/context. Included as failure in operational view; excluded and counted separately by starter quality aggregation.')
                    elif ((folder == 'test-attempt1' and name == 'hybrid_wide') or
                          (folder == 'test' and name == 'tfidf')) and q['id']=='test-new-04':
                        r.update(answer_grade=1, citation_support=[False],
                            reason='Core 1NF definition correct, but added "own row or column" is not established by the cited phone-number example, which explicitly says its own row. Partial grounding; no test-driven fix.')
                else:
                    r.update(abstention_correct=True,
                        reason='Explicit indexed-corpus insufficiency, no guessed outage value or deployment identifier; verified corpus scope and recorded absence checks.')
                reviews.append(r)
            save(path/'reviews.json', reviews)
    print('Test review generation complete; human-verified files preserved.')


if __name__ == '__main__':
    write_test_reviews()
