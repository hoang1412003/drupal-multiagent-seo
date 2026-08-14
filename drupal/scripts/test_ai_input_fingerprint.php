<?php

/**
 * Test AiInputFingerprint - PHP thuan, khong can Drupal bootstrap.
 *
 * Doc CUNG file fixture voi test Python. Neu hai ngon ngu lech nhau, dung mot
 * trong hai ben se do - khong co truong hop ca hai cung sai theo cung mot
 * kieu ma khong ai biet.
 *
 * Chay (tu drupal/): ddev exec php scripts/test_ai_input_fingerprint.php
 */

require_once __DIR__ . '/../web/modules/custom/vf_ai_review/src/AiInputFingerprint.php';

use Drupal\vf_ai_review\AiInputFingerprint;

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

$fixture = json_decode(
  file_get_contents(__DIR__ . '/input_fingerprint_v2_fixture.json'),
  TRUE,
  512,
  JSON_THROW_ON_ERROR
);

// -------------------------------------------------- hop dong voi Python

$thuc_te = AiInputFingerprint::hash($fixture['fields']);
kiem(
  'PHP ra dung expected_sha256 cua fixture dung chung voi Python',
  $thuc_te === $fixture['expected_sha256'],
  "thuc te=$thuc_te mong doi={$fixture['expected_sha256']}"
);

$canonical = AiInputFingerprint::canonicalBytes($fixture['fields']);
kiem('canonical bytes bat dau bang prefix v2', str_starts_with($canonical, "v2\n"));
kiem(
  'JSON compact khong co khoang trang sau dau phay/hai cham',
  !str_contains($canonical, ', ') && !str_contains($canonical, '": ')
);
kiem(
  'unicode giu nguyen ban, khong escape \\uXXXX',
  str_contains($canonical, 'Hướng dẫn') && !str_contains($canonical, '\\u')
);
kiem(
  'dau gach cheo cua url_alias khong bi escape',
  str_contains($canonical, '"/huong-dan-sac-pin"')
);

// ------------------------------------------------------ thu tu va field

$dao_thu_tu = array_reverse($fixture['fields'], TRUE);
kiem(
  'thu tu key trong mang dau vao khong anh huong hash',
  AiInputFingerprint::hash($dao_thu_tu) === $fixture['expected_sha256']
);

kiem(
  'field thieu duoc coi la chuoi rong',
  AiInputFingerprint::hash([]) === AiInputFingerprint::hash([
    'title' => '', 'body' => '', 'summary' => '',
    'url_alias' => '', 'meta_description' => '', 'image_alt' => '',
  ])
);

$goc_hash = AiInputFingerprint::hash($fixture['fields']);
foreach (array_keys($fixture['fields']) as $ten) {
  $doi = $fixture['fields'];
  $doi[$ten] = $doi[$ten] . 'x';
  kiem(
    "doi field '$ten' lam doi hash",
    AiInputFingerprint::hash($doi) !== $goc_hash
  );
}

// -------------------------------------------------------------- alt anh

kiem(
  'anh dai dien dung truoc anh trong bai, danh so tu 1',
  AiInputFingerprint::imageAltLines(
    'Xe điện đang sạc',
    '<p>a</p><img src="1.jpg" alt="Cổng sạc VF e34">'
  ) === "Ảnh đại diện: Xe điện đang sạc\nẢnh 1 trong bài: Cổng sạc VF e34"
);

kiem(
  'khop dung chuoi image_alt trong fixture',
  AiInputFingerprint::imageAltLines(
    'Xe điện đang sạc',
    '<img src="1.jpg" alt="Cổng sạc VF e34">'
  ) === $fixture['fields']['image_alt']
);

kiem(
  'khong co anh dai dien thi khong co dong nao cho no',
  AiInputFingerprint::imageAltLines(NULL, '<img src="1.jpg" alt="A">')
    === 'Ảnh 1 trong bài: A'
);

kiem(
  'co anh dai dien nhung thieu alt van phai co dong, phan sau de trong',
  AiInputFingerprint::imageAltLines('', '') === 'Ảnh đại diện: '
);

kiem(
  'alt dat trong nhay kep',
  AiInputFingerprint::imageAltLines(NULL, '<img alt="kep">') === 'Ảnh 1 trong bài: kep'
);
kiem(
  'alt dat trong nhay don',
  AiInputFingerprint::imageAltLines(NULL, "<img alt='don'>") === 'Ảnh 1 trong bài: don'
);
kiem(
  'alt khong co dau nhay',
  AiInputFingerprint::imageAltLines(NULL, '<img alt=khongnhay>')
    === 'Ảnh 1 trong bài: khongnhay'
);
kiem(
  'anh thieu alt hoan toan -> phan sau dau hai cham de trong',
  AiInputFingerprint::imageAltLines(NULL, '<img src="1.jpg">') === 'Ảnh 1 trong bài: '
);
kiem(
  'data-alt KHONG duoc doc nham thanh alt',
  AiInputFingerprint::imageAltLines(NULL, '<img src="1.jpg" data-alt="bay">')
    === 'Ảnh 1 trong bài: '
);
kiem(
  'nhieu anh duoc danh so tang dan',
  AiInputFingerprint::imageAltLines(NULL, '<img alt="a"><p>x</p><img alt="b">')
    === "Ảnh 1 trong bài: a\nẢnh 2 trong bài: b"
);
kiem(
  'khong co anh nao -> chuoi rong',
  AiInputFingerprint::imageAltLines(NULL, '<p>khong co anh</p>') === ''
);

echo $failed ? "CO TEST DO\n" : "OK\n";
exit($failed ? 1 : 0);
