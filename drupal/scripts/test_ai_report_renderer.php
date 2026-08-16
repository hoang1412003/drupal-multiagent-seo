<?php

/**
 * Test lop AiReportRenderer - PHP thuan, khong can Drupal bootstrap.
 *
 * Chay (tu drupal/): ddev exec php scripts/test_ai_report_renderer.php
 */

require_once __DIR__ . '/../web/modules/custom/vf_ai_review/src/AiReportRenderer.php';

use Drupal\vf_ai_review\AiReportRenderer;

$failed = FALSE;

function kiem(string $ten, bool $dieu_kien, string $chi_tiet = ''): void {
  global $failed;
  if ($dieu_kien) {
    echo "[PASS] $ten\n";
  }
  else {
    $failed = TRUE;
    echo "[FAIL] $ten" . ($chi_tiet ? " - $chi_tiet" : '') . "\n";
  }
}

/**
 * So gia tri THUC voi gia tri MONG, in ca hai khi lech.
 *
 * kiem() chi bao dat/truot; voi ham tra ve gia tri thi biet no tra ve CAI GI
 * moi chan doan duoc, khong phai doc lai code de doan.
 */
function check(string $ten, $thuc, $mong): void {
  kiem($ten, $thuc === $mong,
    'mong ' . var_export($mong, TRUE) . ', thuc ' . var_export($thuc, TRUE));
}

$r = new AiReportRenderer();

$bao_cao = [
  'version' => 1,
  'scored_at' => '2026-08-03T09:45:17+00:00',
  'content_hash' => 'abc',
  'decision' => 'needs_revision',
  'final_score' => 76.5,
  'note' => NULL,
  'veto_reason' => NULL,
  'missing_agents' => [],
  'fields' => [
    'title' => [
      ['agent' => 'SEO', 'label' => 'Độ dài tiêu đề',
       'message' => 'Rút xuống 50-60 ký tự', 'excerpt' => NULL, 'severity' => NULL],
    ],
    'body' => [
      ['agent' => 'Compliance', 'label' => 'Claim thiếu điều kiện đo',
       'message' => NULL, 'excerpt' => 'chạy được 420km', 'severity' => 'medium'],
    ],
  ],
];

// --- HOP DONG 2 NGON NGU -----------------------------------------------
$fx = json_decode(file_get_contents(__DIR__ . '/content_hash_fixture.json'), TRUE);
kiem(
  'hash khop fixture (hop dong voi phia Python)',
  AiReportRenderer::contentHash($fx['fields']) === $fx['expected_sha256'],
  AiReportRenderer::contentHash($fx['fields'])
);

kiem('field thieu = chuoi rong',
  AiReportRenderer::contentHash(['title' => 'A'])
  === AiReportRenderer::contentHash(['title' => 'A', 'body' => '', 'summary' => '', 'meta_description' => '']));

// --- decode -------------------------------------------------------------
kiem('decode JSON hop le', is_array($r->decode('{"version":1}')));
kiem('decode JSON hong -> NULL', $r->decode('{khong phai json') === NULL);
kiem('decode chuoi rong -> NULL', $r->decode('') === NULL);
kiem('decode NULL -> NULL', $r->decode(NULL) === NULL);

// --- overview -----------------------------------------------------------
$html = $r->overviewHtml($bao_cao, FALSE);
kiem('overview co de xuat', str_contains($html, 'Cần sửa'));
kiem('overview co diem', str_contains($html, '76.5'));
kiem('overview dem van de theo field', str_contains($html, 'Tiêu đề') && str_contains($html, 'Nội dung'));

$html_chua_cham = $r->overviewHtml(NULL, FALSE);
kiem('chua cham -> bao chua duoc danh gia', str_contains($html_chua_cham, 'Chưa được đánh giá'));

// Bon trang thai cua spec muc 6.1 phai PHAN BIET duoc. "Chua cham" (field
// trong) khac han "JSON hong" (co du lieu nhung doc khong duoc) - gop chung
// se khien loi du lieu bi hieu nham thanh binh thuong.
$html_hong = $r->overviewHtml(NULL, FALSE, TRUE);
kiem('JSON hong -> bao khong doc duoc', str_contains($html_hong, 'Không đọc được báo cáo'));
kiem('JSON hong KHAC chua cham', !str_contains($html_hong, 'Chưa được đánh giá'), $html_hong);

// --- CAP DOI CHUNG null vs 0 --------------------------------------------
$null_score = $bao_cao;
$null_score['final_score'] = NULL;
$h1 = $r->overviewHtml($null_score, FALSE);
kiem('final_score NULL -> "chua danh gia duoc"', str_contains($h1, 'chưa đánh giá được'));
kiem('final_score NULL -> KHONG in "0"', !str_contains($h1, '>0 /'), $h1);

$zero_score = $bao_cao;
$zero_score['final_score'] = 0;
$h2 = $r->overviewHtml($zero_score, FALSE);
kiem('final_score 0 -> in "0 / 100"', str_contains($h2, '0 / 100'), $h2);

// --- veto + stale -------------------------------------------------------
$veto = $bao_cao;
$veto['decision'] = 'rejected';
$veto['veto_reason'] = 'Bị từ chối do vi phạm Compliance';
kiem('veto_reason hien ra', str_contains($r->overviewHtml($veto, FALSE), 'vi phạm Compliance'));

kiem('stale -> hien bang canh bao', str_contains($r->overviewHtml($bao_cao, TRUE), 'đã thay đổi'));
kiem('khong stale -> khong hien canh bao', !str_contains($r->overviewHtml($bao_cao, FALSE), 'đã thay đổi'));

// --- fieldNotes ---------------------------------------------------------
$note_title = $r->fieldNotesHtml($bao_cao, 'title');
kiem('chu thich title co ten agent', str_contains($note_title, 'SEO'));
kiem('chu thich title co goi y', str_contains($note_title, 'Rút xuống 50-60'));

$note_body = $r->fieldNotesHtml($bao_cao, 'body');
kiem('chu thich body co excerpt', str_contains($note_body, 'chạy được 420km'));
kiem('chu thich body co class severity', str_contains($note_body, 'vf-ai-sev-medium'));

kiem('field khong co loi -> chuoi rong', $r->fieldNotesHtml($bao_cao, 'summary') === '');
kiem('bao cao NULL -> chuoi rong', $r->fieldNotesHtml(NULL, 'title') === '');

// --- XSS (QUAN TRONG NHAT) ----------------------------------------------
$xss = $bao_cao;
$xss['fields']['title'][0]['message'] = '<script>alert(1)</script>';
$xss['fields']['title'][0]['excerpt'] = '"><img src=x onerror=alert(1)>';
$h = $r->fieldNotesHtml($xss, 'title');
kiem('XSS: khong con the <script>', !str_contains($h, '<script>'), $h);
kiem('XSS: khong con the <img', !str_contains($h, '<img'), $h);
kiem('XSS: noi dung van hien duoi dang chu', str_contains($h, '&lt;script&gt;'), $h);

$xss2 = $bao_cao;
$xss2['veto_reason'] = '<script>alert(2)</script>';
kiem('XSS: veto_reason cung duoc escape',
  !str_contains($r->overviewHtml($xss2, FALSE), '<script>'));

// --- doc phong thu ------------------------------------------------------
kiem('thieu khoa fields -> khong loi',
  is_string($r->overviewHtml(['decision' => 'publish'], FALSE)));
kiem('fields co field la -> bo qua',
  $r->fieldNotesHtml(['fields' => ['khong_ton_tai' => [[]]]], 'title') === '');
kiem('version khac 1 -> co canh bao',
  str_contains($r->overviewHtml(['version' => 2, 'decision' => 'publish'], FALSE), 'phiên bản khác'));

// === THIET KE LAI 2026-08-16 (editor-ui-design.md muc 10) ================

// --- trangThai(): suy trang thai bang sticky -----------------------------
// Bay trang thai cua ban handoff, CONG state "JSON hong" von da co tu spec
// muc 6.1 va dang bi test o tren khoa lai. Ban handoff khong biet toi state
// do; gop no vao "chua cham" se lam loi du lieu bi hieu nham la binh thuong.
//
// `dang_cham` KHONG suy o PHP: no den tu vong poll cua vf_ai_trigger.

$co_loi_bt = [
  'decision' => 'needs_revision',
  'fields' => ['title' => [['agent' => 'SEO', 'severity' => NULL]]],
];

kiem('chua cham', $r->trangThai(NULL, FALSE, FALSE) === 'chua_cham');
kiem('JSON hong KHAC chua cham', $r->trangThai(NULL, FALSE, TRUE) === 'loi_json');
kiem('co loi', $r->trangThai($co_loi_bt, FALSE, FALSE) === 'co_loi');
kiem('dat khi khong field nao co loi',
  $r->trangThai(['decision' => 'publish', 'fields' => []], FALSE, FALSE) === 'dat');
kiem('thieu agent',
  $r->trangThai(['fields' => [], 'missing_agents' => ['seo']], FALSE, FALSE) === 'thieu');
kiem('veto', $r->trangThai(
  ['fields' => [], 'veto_reason' => 'vi pham'], FALSE, FALSE) === 'veto');

// stale THANG veto: noi dung da doi sau khi cham, nen ket qua cu noi ve mot
// ban khac. Hien bang "BI TU CHOI" cho noi dung da sua roi la noi sai ve
// ban dang soan - phai noi "ket qua cua ban cu, cham lai di".
kiem('stale thang veto',
  $r->trangThai(['fields' => [], 'veto_reason' => 'vi pham'], TRUE, FALSE) === 'stale');
kiem('JSON hong thang tat ca', $r->trangThai($co_loi_bt, TRUE, TRUE) === 'loi_json');

// --- mucHienThi(): severity 4 muc -> 3 muc -------------------------------
// `block` CHI duoc den tu `critical`. Do la rang buoc, khong phai quy uoc:
// critical dung bang thu kich hoat quyen phu quyet o graph.aggregator_node.
// Anh xa null -> block se lam dong "Con N loi chan xuat ban" noi doi, vi he
// thong that KHONG chan vi nhung loi do.
check('critical -> block', AiReportRenderer::mucHienThi('critical'), 'block');
check('medium -> fix', AiReportRenderer::mucHienThi('medium'), 'fix');
check('low -> tip', AiReportRenderer::mucHienThi('low'), 'tip');
check('NULL -> fix (3 agent ngoai Compliance)',
  AiReportRenderer::mucHienThi(NULL), 'fix');
check('gia tri la -> fix, khong vo', AiReportRenderer::mucHienThi('xyz'), 'fix');

// --- demChan(): dem so loi CHAN XUAT BAN ---------------------------------
$hon_hop = ['fields' => [
  'title' => [
    ['agent' => 'Compliance', 'severity' => 'critical'],
    ['agent' => 'SEO', 'severity' => NULL],
  ],
  'body' => [
    ['agent' => 'Compliance', 'severity' => 'medium'],
    ['agent' => 'Compliance', 'severity' => 'critical'],
    ['agent' => 'Brand Voice', 'severity' => NULL],
  ],
]];
check('demChan dem dung so critical tren moi field',
  $r->demChan($hon_hop), 2);
check('demChan tren bao cao khong loi', $r->demChan(['fields' => []]), 0);
check('demChan tren bao cao NULL', $r->demChan(NULL), 0);

// --- demLoi(): tong so van de -------------------------------------------
check('demLoi dem het moi field', $r->demLoi($hon_hop), 5);
check('demLoi tren NULL', $r->demLoi(NULL), 0);

exit($failed ? 1 : 0);
