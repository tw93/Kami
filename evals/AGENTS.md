# Evals Guide

`evals/<case>/` holds end-to-end cases for `claude plugin eval`: a realistic request
with invented data (`prompt.md`), and graders for skill trigger, PDF (or HTML)
creation, and unfilled placeholders, plus fact fidelity in the HTML. Fact fidelity is
a `regex` grader wherever the facts are literal (one-pager-en, resume-cn, long-doc-cn,
equity-report-cn, letter-ko): LLM judges split on derived figures and reported false
FAILs on outputs whose facts were all present. What a judge was asked beyond the facts
is a `not_contains` regex too where it can be: invented contact details and non-Korean
copy in letter-ko, outside companies and consensus in equity-report-cn. A `focus` on a
long HTML file drew unanimous FAIL votes on outputs a standalone sonnet judge passed
with every figure rechecked, matching the harness docs' advice to keep
`llm` graders for short outputs. Invented numbers in long-doc-cn are `score.py`'s
`invented` gate: every number with a unit must be supplied, or for % and 倍 a ratio or
percent change of two supplied ones; it catches invented seconds, 万, 元 and 台 but
not an invented percentage, since ratios of a dozen inputs reach most integers.
slides-en keeps the one LLM fidelity judge, which has passed every run on its deck.
`evals/score.py` then applies Kami's own gates to each kept run workspace (page
contract, atomic facts in the PDF text, fonts, density, residue, style, resume
balance, generated chart count), which the harness cannot run itself; it is
read-only unless given `--write`, which saves `gate-scores.json`. One suite run is 10
cases, 20 document builds at `--runs 2`, at roughly $1-3 each.

- landing-page-en names Kami in its prompt because the description only claims a
  Kami landing page; an unnamed landing-page request fired the skill in 3 of
  4 runs, so the case measured trigger noise instead of the template.
- `--case` takes one glob, and a second `--case` replaces the first:
  `--case long-doc-cn --case equity-report-cn` ran only equity-report-cn.
- A file grader takes an exact path; globs such as `*.html` fail with "path does not
  exist". Every prompt pins its output file names for that reason.
- Kept workspaces live under `/private/tmp/e-*/sealed/home/cwd` with mode 000;
  `score.py` opens them itself. Results stay in the ignored `evals/results/`.
- Mathematics is not covered: the sandbox cannot install the MathJax runtime.
- LLM fidelity rubrics carry the case's full brief, because a judge that sees only a
  partial fact list fails supplied facts as invented. On artifacts over about 15k
  characters the harness judge is unreliable: before treating its FAIL as real,
  re-judge the stored `evidence` HTML with the same rubric (`claude -p --model sonnet`)
  and read the stated reason.
- resume-cn deliberately supplies thin notes (three employers, eight bullets). The
  expected behavior is two honest pages with `[DATA NEEDED]` gaps and a reported
  balance shortfall (`references/resume-writing.md` «Thin source»). `--deliver` and
  `score.py` both read that through `checks.resume_thin_source` and treat it as a
  reported gap rather than a balance failure.
