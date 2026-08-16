<?php

namespace Drupal\vf_ai_review;

/**
 * Dựng HTML báo cáo AI từ dữ liệu trong field_ai_report_json.
 *
 * CỐ Ý KHÔNG phụ thuộc gì của Drupal: vào là mảng, ra là chuỗi HTML đã
 * escape. Nhờ vậy test được bằng script PHP thuần (drupal/scripts/
 * test_ai_report_renderer.php), giữ đúng phong cách 19 bộ test Python của
 * dự án thay vì phải cài PHPUnit.
 *
 * Escape bằng htmlspecialchars() thay vì Html::escape() của Drupal - hai
 * hàm tương đương (Html::escape bên trong chính là htmlspecialchars với
 * cùng cờ), nhưng cái sau kéo theo phụ thuộc Drupal.
 */
class AiReportRenderer {

  /**
   * Phiên bản định dạng JSON mà lớp này biết đọc.
   */
  public const VERSION = 1;

  /**
   * Field tham gia tính content_hash, ĐÚNG THỨ TỰ NÀY.
   *
   * Phải khớp _HASH_FIELDS trong multiagent/src/text_utils.py. Lệch là băng
   * cảnh báo "nội dung đã thay đổi" hiện sai vĩnh viễn - có test hợp đồng
   * dùng chung file drupal/scripts/content_hash_fixture.json để bắt.
   */
  private const HASH_FIELDS = ['title', 'body', 'summary', 'meta_description'];

  private const DECISION_LABELS = [
    'publish' => '✅ Có thể xuất bản',
    'needs_revision' => '⚠ Cần sửa',
    'rejected' => '⛔ Bị từ chối',
  ];

  private const FIELD_LABELS = [
    'title' => 'Tiêu đề',
    'meta_description' => 'Meta description',
    'url_alias' => 'Đường dẫn',
    'summary' => 'Tóm tắt',
    'body' => 'Nội dung',
    'image_alt' => 'Alt text ảnh',
  ];

  /**
   * Băm nội dung để so xem bài có bị sửa sau khi chấm không.
   */
  public static function contentHash(array $fields): string {
    $phan = [];
    foreach (self::HASH_FIELDS as $khoa) {
      $phan[] = (string) ($fields[$khoa] ?? '');
    }
    return hash('sha256', implode("\n", $phan));
  }

  /**
   * Giải mã JSON. Hỏng hoặc rỗng -> NULL, KHÔNG ném exception.
   */
  public function decode(?string $json): ?array {
    if ($json === NULL || trim($json) === '') {
      return NULL;
    }
    $data = json_decode($json, TRUE);
    return is_array($data) ? $data : NULL;
  }

  /**
   * Escape mọi chuỗi động trước khi ghép vào HTML.
   *
   * BẮT BUỘC dùng cho mọi giá trị lấy từ báo cáo: chúng chứa trích dẫn
   * nguyên văn từ bài viết và văn bản do LLM sinh. Render thô là lỗ hổng
   * XSS - người viết chèn thẻ vào bài, LLM trích lại, thẻ chạy trong trang
   * admin của người duyệt (docs/prompt-injection.md mục 5, biện pháp M4).
   */
  private function esc($gia_tri): string {
    return htmlspecialchars((string) ($gia_tri ?? ''), ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
  }

  /**
   * Khối tổng quan cho cột advanced.
   */
  public function overviewHtml(?array $report, bool $stale, bool $loiJson = FALSE): string {
    // Bốn trạng thái ở spec mục 6.1 phải phân biệt được. "Chưa chấm" (field
    // trống) khác hẳn "JSON hỏng" (có dữ liệu nhưng đọc không được) - gộp
    // chung sẽ khiến lỗi dữ liệu bị hiểu nhầm thành tình trạng bình thường.
    if ($loiJson) {
      return '<div class="vf-ai-review vf-ai-warn">'
        . 'Không đọc được báo cáo — xem trường AI Suggestions.'
        . '</div>';
    }
    if ($report === NULL) {
      return '<div class="vf-ai-review vf-ai-empty">'
        . 'Chưa được đánh giá. Chuyển bài sang trạng thái cần duyệt để hệ thống chấm.'
        . '</div>';
    }

    $out = '<div class="vf-ai-review">';

    if (($report['version'] ?? self::VERSION) !== self::VERSION) {
      $out .= '<div class="vf-ai-warn">Báo cáo sinh bởi phiên bản khác, hiển thị có thể thiếu.</div>';
    }

    if (!empty($report['veto_reason'])) {
      $out .= '<div class="vf-ai-veto"><strong>⛔ BỊ TỪ CHỐI</strong><br>'
        . $this->esc($report['veto_reason']) . '</div>';
    }

    if ($stale) {
      $out .= '<div class="vf-ai-stale">⏱ Nội dung đã thay đổi sau lần chấm. '
        . 'Kết quả bên dưới có thể không còn đúng.</div>';
    }

    if (!empty($report['note'])) {
      $out .= '<div class="vf-ai-warn">' . $this->esc($report['note']) . '</div>';
    }

    $quyet_dinh = $report['decision'] ?? NULL;
    $nhan = self::DECISION_LABELS[$quyet_dinh] ?? $this->esc($quyet_dinh);
    $out .= '<dl class="vf-ai-meta">';
    $out .= '<dt>Đề xuất</dt><dd>' . $nhan . '</dd>';

    // === NULL chứ KHÔNG dùng empty(): empty(0) trả TRUE nên điểm 0 sẽ bị
    // hiển thị nhầm thành "chưa đánh giá được".
    $diem = $report['final_score'] ?? NULL;
    $out .= '<dt>Điểm</dt><dd>'
      . ($diem === NULL ? '<em>chưa đánh giá được</em>' : $this->esc($diem) . ' / 100')
      . '</dd>';

    if (!empty($report['scored_at'])) {
      $out .= '<dt>Chấm lúc</dt><dd>' . $this->esc($this->dinhDangGio($report['scored_at'])) . '</dd>';
    }
    $out .= '</dl>';

    $fields = $report['fields'] ?? [];
    $tong = 0;
    foreach ($fields as $ds) {
      $tong += is_array($ds) ? count($ds) : 0;
    }
    if ($tong > 0) {
      $out .= '<p class="vf-ai-count">' . $tong . ' vấn đề trên ' . count($fields) . ' trường:</p><ul>';
      foreach ($fields as $khoa => $ds) {
        $ten = self::FIELD_LABELS[$khoa] ?? $this->esc($khoa);
        $out .= '<li>' . $ten . ' (' . count($ds) . ')</li>';
      }
      $out .= '</ul>';
    }
    else {
      $out .= '<p class="vf-ai-count">Không phát hiện vấn đề nào.</p>';
    }

    return $out . '</div>';
  }

  /**
   * Chú thích hiển thị ngay dưới widget của một field.
   *
   * Trả chuỗi rỗng nếu field đó không có vấn đề gì.
   */
  public function fieldNotesHtml(?array $report, string $fieldKey): string {
    $ds = $report['fields'][$fieldKey] ?? NULL;
    if (!is_array($ds) || $ds === []) {
      return '';
    }

    $out = '<div class="vf-ai-notes">';
    foreach ($ds as $muc) {
      if (!is_array($muc)) {
        continue;
      }
      $sev = $muc['severity'] ?? NULL;
      $lop = 'vf-ai-sev-' . ($sev !== NULL ? $this->esc($sev) : 'none');
      $bieu_tuong = ($sev === 'critical') ? '⛔' : '⚠';

      $out .= '<div class="vf-ai-note ' . $lop . '">';
      $out .= $bieu_tuong . ' <strong>' . $this->esc($muc['agent'] ?? '') . '</strong>';
      if (!empty($muc['label'])) {
        $out .= ' — ' . $this->esc($muc['label']);
      }
      if (!empty($muc['message'])) {
        $out .= '<div class="vf-ai-msg">' . $this->esc($muc['message']) . '</div>';
      }
      if (!empty($muc['excerpt'])) {
        $out .= '<blockquote>' . $this->esc($muc['excerpt']) . '</blockquote>';
      }
      $out .= '</div>';
    }
    return $out . '</div>';
  }

  /**
   * ISO 8601 -> "03/08/2026 09:45". Không parse được thì trả nguyên bản.
   */
  private function dinhDangGio(string $iso): string {
    $ts = strtotime($iso);
    return $ts === FALSE ? $iso : date('d/m/Y H:i', $ts);
  }

  // === THIẾT KẾ LẠI 2026-08-16 (editor-ui-design.md mục 10) ===============

  /**
   * Trạng thái của băng sticky.
   *
   * Bảy trạng thái của bản handoff, CỘNG `loi_json` vốn đã có từ spec mục
   * 6.1: "chưa chấm" (field trống) khác hẳn "có dữ liệu nhưng đọc không
   * được". Gộp chung sẽ khiến lỗi dữ liệu bị hiểu nhầm là bình thường.
   *
   * `dang_cham` KHÔNG suy ở đây - nó đến từ vòng poll của vf_ai_trigger.
   *
   * Thứ tự ưu tiên có chủ đích: `stale` THẮNG `veto`. Nội dung đã đổi sau
   * khi chấm nghĩa là kết quả cũ nói về một bản khác; hiện băng "BỊ TỪ CHỐI"
   * cho bản đang soạn là nói sai. Phải nói "kết quả của bản cũ, chấm lại đi".
   */
  public function trangThai(?array $report, bool $stale, bool $loiJson): string {
    if ($loiJson) {
      return 'loi_json';
    }
    if ($report === NULL) {
      return 'chua_cham';
    }
    if ($stale) {
      return 'stale';
    }
    if (!empty($report['veto_reason'])) {
      return 'veto';
    }
    if (!empty($report['missing_agents'])) {
      return 'thieu';
    }
    return $this->demLoi($report) === 0 ? 'dat' : 'co_loi';
  }

  /**
   * severity trong báo cáo -> mức hiển thị.
   *
   * `block` CHỈ đến từ `critical`. Đây là ràng buộc, không phải quy ước:
   * `critical` đúng bằng thứ kích hoạt quyền phủ quyết ở
   * `graph.aggregator_node`. Ánh xạ NULL -> `block` sẽ làm dòng "Còn N lỗi
   * chặn xuất bản" nói dối, vì hệ thống thật KHÔNG chặn vì những lỗi đó.
   *
   * NULL là trường hợp thường gặp chứ không phải ngoại lệ: ba agent ngoài
   * Compliance cố ý không định nghĩa severity (`graph._issue_to_json`).
   */
  public static function mucHienThi(?string $severity): string {
    return match ($severity) {
      'critical' => 'block',
      'low' => 'tip',
      default => 'fix',
    };
  }

  /**
   * Đếm số vấn đề CHẶN XUẤT BẢN trên toàn báo cáo.
   */
  public function demChan(?array $report): int {
    return $this->demTheo($report, fn($m) => ($m['severity'] ?? NULL) === 'critical');
  }

  /**
   * Đếm tổng số vấn đề trên toàn báo cáo.
   */
  public function demLoi(?array $report): int {
    return $this->demTheo($report, fn($m) => TRUE);
  }

  /**
   * Duyệt mọi mục của mọi field, đếm những mục thoả điều kiện.
   */
  private function demTheo(?array $report, callable $hop_le): int {
    $tong = 0;
    foreach (($report['fields'] ?? []) as $ds) {
      if (!is_array($ds)) {
        continue;
      }
      foreach ($ds as $muc) {
        if (is_array($muc) && $hop_le($muc)) {
          $tong++;
        }
      }
    }
    return $tong;
  }

}
