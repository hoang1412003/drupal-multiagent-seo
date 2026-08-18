# Publish Policy v2 Core — Offline Verification Checkpoint

Thoi diem: 2026-08-18T09:58 (Asia/Saigon, UTC+7)
Nhanh: `ai/v14-relabel`
Core HEAD parent (truoc commit evidence nay): `c60b5e45bafec2890d7ae5dbbbe402ae5073741a`
Data HEAD (pinned, khong doi): `8635a45c9aee1369f6f7b17b0918a580db7390da`

Day la evidence cua Task 9 trong
[`2026-08-17-publish-blocking-decision-policy.md`](../superpowers/plans/2026-08-17-publish-blocking-decision-policy.md).
Muc dich: chung nhan core/runner/guard cua policy v2 san sang duoc mo rong
sang bon dataset (Evaluation Plan), **khong phai** ket qua do luong va
**khong phai** measured result.

## Pham vi

Xac nhan offline-readiness cho code Tasks 1-8 (decision engine, B15 fix,
A5/A6/A7/CP7-v2 checks, evaluator v2 base, release guard, doc reconcile).
Khong chay bat ky paid API call nao; khong tao raw output moi; khong freeze
release manifest (freeze thuoc Task 3 cua Evaluation Plan).

## Step 1 — Focused suite fresh

Lenh (tu `multiagent/`, dung venv repo chinh vi worktree khong co `.venv`
rieng — da doi chieu `requirements.txt` giong het repo chinh):

```powershell
$env:VF_ALLOW_PAID_EVAL = '0'
$env:HF_HUB_OFFLINE = '1'
$py = "D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe"
& $py scripts\test_decision_policy.py
& $py scripts\test_policy_routing.py
& $py scripts\test_cq_rubric.py
& $py scripts\test_compliance_rubric.py
& $py scripts\test_eval_policy_v2.py
& $py scripts\test_eval_policy_v2_metrics.py
& $py scripts\test_policy_release.py
```

Ket qua (tat ca exit code 0, khong skip):

| Script | Exit |
|---|---|
| test_decision_policy.py | 0 |
| test_policy_routing.py | 0 |
| test_cq_rubric.py | 0 |
| test_compliance_rubric.py | 0 |
| test_eval_policy_v2.py | 0 |
| test_eval_policy_v2_metrics.py | 0 |
| test_policy_release.py | 0 |

`test_policy_release.py` in ra mot dong `usage: ... error: unrecognized
arguments: --force` — day la stderr cua chinh CLI duoc goi nhu subprocess de
kiem tra no tu choi co `--force`; test tuong ung ngay sau do bao `[PASS] CLI
khong co --force`. Khong phai loi that.

Khong co provider call nao phat sinh (`VF_ALLOW_PAID_EVAL=0` xuyen suot).

## Step 2 — Full offline bang lenh canonical

```powershell
& $py scripts\run_test_group.py all-offline
```

Ket qua tu output that:

```
tong: 82   hong: 0   co [SKIP]: 0
```

Nhom `pure`: 53 file, 0 hong, 0 skip. Nhom `postgres`: 29 file, 0 hong, 0
skip. **Khong chep so 72 lich su** — manifest hien tai phu dung 82 file.

## Step 3 — Verify protected/immutable paths

```powershell
git diff --exit-code 8635a45 -- docs/goldset/raw docs/goldset/labels.csv `
  docs/functional-tests/clean docs/functional-tests/gold-corrected `
  docs/functional-tests/criterion-coverage multiagent/config/scoring.yaml
```

Exit code: `0` — khong co diff so voi Data HEAD.

```powershell
& $py scripts\functional_dataset_v2.py validate-inventory
```

Output: `valid inventory: 20 corrected, 11 coverage` — dung 20 corrected
(10 C + 10 GC da corrected) + 11 coverage nhu ky vong.

```powershell
git diff --check
git status --short
```

Ca hai deu rong truoc khi tao file evidence nay.

## Policy/prompt/safety hashes tai Core HEAD parent

Tinh truc tiep bang ham noi bo cua `eval_policy_v2.py`
(`_sha256_file`/`_bundle_hash`/`_model_name`), doc-only, khong tao client,
khong goi provider:

```json
{
  "policy_hash": "a61173dac56efeaf2d730851121ef72554e038885bb52fe67252cf50ce617703",
  "scoring_hash": "d9eeec581888a112fa20faaea545199e698a067209229eac9de0f0193adb90a3",
  "safety_rules_hash": "d592eb10e6539d86b365ad19fb7698292552d80ce89d81a20adc062f058f0e27",
  "fact_kb_hash": "d15e61c8b290b4788e16ae121c3e66d80c034587ff8ee817544cbdb2a88a4f68",
  "brand_kb_hash": "6f89233c3ed371a62a64d5ae65a4cb3345e086c1bd957de0085dd0c01dbf82a5",
  "guideline_hash": "48c5e136e0089189c11057f258b6c3ee9b119263bb3ddd7520abc7168c436f7a",
  "rubric_hash": "8b4e472d4853fd570efcd3c7fa569e08e7c95cdfecf4d191bb6f04aba4979768",
  "prompt_version": "e95362b99fed169c70b22f414e68303c92f0395563a9d10a2475db0ffe2d2b0d",
  "model": "claude-haiku-4-5-20251001",
  "policy_version": "cam-nang-vn-v2",
  "guideline_version": "v1.4",
  "rubric_version": "v1"
}
```

Day chi la snapshot fingerprint tai Core HEAD parent de tra cuu. `freeze`
(Task 3 Evaluation Plan) se tinh lai va khoa chinh thuc vao
`publish-policy-v2-manifest.json`; con so o day khong thay the buoc do va se
doi neu bat ky file lien quan bi sua truoc freeze.

## Usage / chi phi

`VF_ALLOW_PAID_EVAL=0` xuyen suot toan bo checkpoint. Khong co Anthropic API
call nao phat sinh. Chi phi: **$0**.

## Gioi han — doc truoc khi dung ket qua nay

```text
offline-ready != measured
preflight chua phai result
policy v2 chua active
independent label reliability = not_demonstrated
```

`publish-policy-v2-manifest.json` van con `release_source_commit=null` va
nam paid gate deu `pending`. `scoring.yaml.meta.calibrated` khong doi.
Checkpoint nay chi xac nhan core/runner/guard san sang de Evaluation Plan
tieu thu — khong phai bang chung chat luong hay ket qua do.

## Ket luan

Core offline-ready tai `c60b5e45bafec2890d7ae5dbbbe402ae5073741a`. Buoc tiep
theo duy nhat: thuc thi
[`2026-08-17-corrected-publish-criterion-coverage-evaluation.md`](../superpowers/plans/2026-08-17-corrected-publish-criterion-coverage-evaluation.md)
tu Task 1, van dung tai tung USER GATE tra phi.
