<?php

/**
 * @file
 * Test result callback compare-and-set trên node và revision THẬT.
 *
 * Phần quyết định (validate/decide) có thể test bằng PHP thuần, nhưng thứ
 * đáng lo nhất ở đây lại là hành vi entity thật: revision có tăng đúng một
 * lần không, có field nào ngoài bốn field AI bị đổi không, moderation state
 * có bị chạm không. Nên test này chạy có bootstrap Drupal.
 *
 * Node tạm được XOÁ trong finally, kể cả khi test đỏ.
 *
 * Chạy (từ drupal/):
 *   ddev drush php:script scripts/test_ai_result_callback.php
 */

use Drupal\node\Entity\Node;
use Drupal\vf_ai_trigger\Service\AiResultRequestException;
use Drupal\vf_ai_trigger\Service\AiResultWriter;

$that_bai = FALSE;

function kiem(string $ten, bool $dieu_kien, string $chi_tiet = ''): void {
  global $that_bai;
  if ($dieu_kien) {
    echo "[PASS] $ten\n";
  }
  else {
    $that_bai = TRUE;
    echo "[FAIL] $ten" . ($chi_tiet ? " - $chi_tiet" : '') . "\n";
  }
}

function uuid4_gia(string $duoi): string {
  return '99999999-8888-4777-8666-' . str_pad($duoi, 12, '0', STR_PAD_LEFT);
}

/** @var \Drupal\vf_ai_trigger\Service\AiResultWriter $writer */
$writer = \Drupal::service('vf_ai_trigger.result_writer');
$storage = \Drupal::entityTypeManager()->getStorage('node');

$node = Node::create([
  'type' => 'article',
  'title' => 'TAM - test result callback',
  'body' => ['value' => '<p>Noi dung tam de test callback.</p>', 'summary' => 'Tom tat'],
  'moderation_state' => 'needs_review',
  'langcode' => 'vi',
]);
$node->save();
$nid = (int) $node->id();

try {
  $storage->resetCache([$nid]);
  $rev_1 = (string) $storage->getLatestRevisionId($nid);
  $latest = $storage->loadRevision($rev_1);
  $hash_1 = AiResultWriter::fingerprintCua($latest, 2);

  $run_a = uuid4_gia('1');

  // ---------------------------------------------------- 1. duong thanh cong
  $bao_cao = [
    'version' => 1,
    'content_hash' => $hash_1,
    'content_hash_version' => 2,
    'platform_run_id' => $run_a,
    'fields' => [],
  ];
  $yeu_cau = [
    'run_id' => $run_a,
    'external_content_id' => $node->uuid(),
    'expected_revision_id' => $rev_1,
    'content_hash' => $hash_1,
    'content_hash_version' => 2,
    'status' => 'needs_revision',
    'score' => 76.5,
    'suggestions' => 'Them meta description',
    'report_json' => $bao_cao,
  ];

  $tieu_de_truoc = $latest->label();
  $body_truoc = $latest->get('body')->value;
  $state_truoc = $latest->get('moderation_state')->value;

  $ket_qua = $writer->apply($yeu_cau);
  kiem('revision dung + hash dung -> applied', $ket_qua['outcome'] === 'applied',
    json_encode($ket_qua));

  $storage->resetCache([$nid]);
  $rev_2 = (string) $storage->getLatestRevisionId($nid);
  $sau = $storage->loadRevision($rev_2);
  kiem('applied tao dung mot revision moi', $rev_2 !== $rev_1);
  kiem('applied_revision_id khop revision vua tao',
    $ket_qua['applied_revision_id'] === $rev_2,
    "{$ket_qua['applied_revision_id']} vs $rev_2");

  kiem('bon field AI da duoc ghi',
    $sau->get('field_ai_status')->value === 'needs_revision'
    && (float) $sau->get('field_ai_score')->value === 76.5
    && $sau->get('field_ai_suggestions')->value === 'Them meta description');
  kiem('tieu de KHONG bi doi', $sau->label() === $tieu_de_truoc);
  kiem('body KHONG bi doi', $sau->get('body')->value === $body_truoc);
  kiem('moderation state KHONG bi doi - he thong khong tu xuat ban',
    $sau->get('moderation_state')->value === $state_truoc,
    $sau->get('moderation_state')->value . ' vs ' . $state_truoc);

  // -------------------------------------- 2. gui lai cung run_id (mat response)
  $lai = $writer->apply($yeu_cau);
  kiem('gui lai cung run_id -> already_applied',
    $lai['outcome'] === 'already_applied', json_encode($lai));
  $storage->resetCache([$nid]);
  kiem('already_applied KHONG tao them revision',
    (string) $storage->getLatestRevisionId($nid) === $rev_2);

  // ------------------------------------------------- 3. stale write bi tu choi
  $moi = $storage->loadRevision($storage->getLatestRevisionId($nid));
  $moi->setTitle('TAM - editor vua sua tieu de');
  $moi->setNewRevision(TRUE);
  $moi->save();
  $storage->resetCache([$nid]);
  $rev_3 = (string) $storage->getLatestRevisionId($nid);
  $truoc_khi_stale = $storage->loadRevision($rev_3);
  $ai_truoc = [
    $truoc_khi_stale->get('field_ai_status')->value,
    $truoc_khi_stale->get('field_ai_score')->value,
    $truoc_khi_stale->get('field_ai_suggestions')->value,
    $truoc_khi_stale->get('field_ai_report_json')->value,
  ];

  $run_b = uuid4_gia('2');
  $stale = $writer->apply([
    'run_id' => $run_b,
    'external_content_id' => $node->uuid(),
    // Job cu chi biet revision 1, trong khi bay gio da co revision 3.
    'expected_revision_id' => $rev_1,
    'content_hash' => $hash_1,
    'content_hash_version' => 2,
    'status' => 'rejected',
    'score' => 10.0,
    'suggestions' => 'KET QUA CU KHONG DUOC GHI DE',
    'report_json' => ['version' => 1, 'platform_run_id' => $run_b],
  ]);
  kiem('revision cu -> content_superseded', $stale['outcome'] === 'content_superseded',
    json_encode($stale));
  $storage->resetCache([$nid]);
  kiem('content_superseded KHONG tao revision',
    (string) $storage->getLatestRevisionId($nid) === $rev_3);
  $sau_stale = $storage->loadRevision($rev_3);
  kiem('bon field AI giu nguyen sau khi tu choi stale write', [
    $sau_stale->get('field_ai_status')->value,
    $sau_stale->get('field_ai_score')->value,
    $sau_stale->get('field_ai_suggestions')->value,
    $sau_stale->get('field_ai_report_json')->value,
  ] === $ai_truoc);

  // -------------------------- 4. hash lech du revision dung cung bi tu choi
  $hash_lech = $writer->apply([
    'run_id' => uuid4_gia('3'),
    'external_content_id' => $node->uuid(),
    'expected_revision_id' => $rev_3,
    'content_hash' => str_repeat('a', 64),
    'content_hash_version' => 2,
    'status' => 'rejected',
    'score' => 10.0,
    'suggestions' => 'x',
    'report_json' => ['version' => 1],
  ]);
  kiem('revision dung nhung hash lech -> content_superseded',
    $hash_lech['outcome'] === 'content_superseded', json_encode($hash_lech));

  // ----------------------------------------------- 5. payload sai hop dong
  $hop_le = [
    'run_id' => uuid4_gia('4'),
    'external_content_id' => $node->uuid(),
    'expected_revision_id' => $rev_3,
    'content_hash' => str_repeat('b', 64),
    'content_hash_version' => 2,
    'status' => 'needs_revision',
    'score' => 50.0,
    'suggestions' => 'x',
    'report_json' => ['version' => 1],
  ];

  $sai = [
    'them moderation_state' => ['moderation_state' => 'published'],
    'them title' => ['title' => 'ghi de tieu de'],
    'them body' => ['body' => 'ghi de noi dung'],
    'them field thu nam' => ['field_ai_note' => 'x'],
    'run_id khong phai UUID' => ['run_id' => 'khong-phai-uuid'],
    'revision khong phai so' => ['expected_revision_id' => 'abc'],
    'revision bang 0' => ['expected_revision_id' => '0'],
    'hash chu hoa' => ['content_hash' => strtoupper(str_repeat('b', 64))],
    'hash sai do dai' => ['content_hash' => 'abc'],
    'hash version 3' => ['content_hash_version' => 3],
    'status la' => ['status' => 'da_xuat_ban'],
    'score ngoai 0-100' => ['score' => 500],
    'suggestions qua lon' => ['suggestions' => str_repeat('x', 65537)],
    'report_json qua lon' => ['report_json' => ['x' => str_repeat('y', 400000)]],
  ];
  foreach ($sai as $ten => $thay_doi) {
    $bi_tu_choi = FALSE;
    try {
      $writer->apply(array_merge($hop_le, $thay_doi));
    }
    catch (AiResultRequestException $e) {
      $bi_tu_choi = TRUE;
    }
    kiem("payload sai bi tu choi: $ten", $bi_tu_choi);
  }

  $storage->resetCache([$nid]);
  kiem('khong payload sai nao tao duoc revision',
    (string) $storage->getLatestRevisionId($nid) === $rev_3);

  // ------------------------------------------------ 6. thu tu quyet dinh
  // Idempotency phai duoc kiem TRUOC conflict: sau khi ghi xong revision da
  // tang, nen neu kiem conflict truoc thi mot lan gui lai se bi hieu nham
  // thanh "noi dung da doi".
  kiem('already_applied duoc uu tien hon content_superseded',
    AiResultWriter::decide(
      ['run_id' => $run_a, 'expected_revision_id' => '1', 'content_hash' => 'x'],
      ['revision_id' => '99', 'fingerprint' => 'khac', 'platform_run_id' => $run_a]
    ) === 'already_applied');
}
finally {
  $node = Node::load($nid);
  if ($node !== NULL) {
    $node->delete();
  }
  echo "Da xoa node tam $nid\n";
}

echo $that_bai ? "CO TEST DO\n" : "OK\n";
if ($that_bai) {
  exit(1);
}
