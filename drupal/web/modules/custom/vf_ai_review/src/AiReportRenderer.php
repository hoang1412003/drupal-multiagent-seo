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
   * So agent cua he Multi-Agent: content_quality, seo, brand, compliance.
   *
   * Dat thanh hang so vi truoc day "3/4 agent" duoc ghi cung trong chuoi HTML,
   * nen bao cao thieu HAI agent van hien "3/4".
   */
  public const TONG_SO_AGENT = 4;

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

  private const AGENT_NAMES = [
    'seo' => 'SEO',
    'SEO' => 'SEO',
    'content_quality' => 'Chất lượng',
    'Chất lượng' => 'Chất lượng',
    'CQ' => 'Chất lượng',
    'brand_voice' => 'Brand Voice',
    'Brand Voice' => 'Brand Voice',
    'BV' => 'Brand Voice',
    'compliance' => 'Tuân thủ',
    'Compliance' => 'Tuân thủ',
    'Tuân thủ' => 'Tuân thủ',
    'CP' => 'Tuân thủ',
  ];

  private const AGENT_SHORT = [
    'seo' => 'SEO',
    'SEO' => 'SEO',
    'content_quality' => 'CQ',
    'Chất lượng' => 'CQ',
    'CQ' => 'CQ',
    'brand_voice' => 'BV',
    'Brand Voice' => 'BV',
    'BV' => 'BV',
    'compliance' => 'CP',
    'Compliance' => 'CP',
    'Tuân thủ' => 'CP',
    'CP' => 'CP',
  ];

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
   * Nhãn và màu của từng trạng thái băng.
   *
   * Bảy nhãn PHẢI khác nhau: trùng nhãn nghĩa là người duyệt không phân biệt
   * được "chưa chấm" với "đã chấm và đạt" - hai tình huống đòi hành động
   * ngược nhau.
   */
  private const NHAN_TRANG_THAI = [
    'co_loi' => 'Cần sửa',
    'chua_cham' => 'Chưa chấm',
    // Thieu khoa nay thi nhan roi ve chinh ten khoa, tuc bang hien chu
    // "dang_cham" tho. Truoc day khong lo ra vi vf_ai_trigger.js ve de len,
    // nhung PHP van phai tu dung mot minh.
    'dang_cham' => 'Đang chấm',
    'dat' => 'Đạt',
    'veto' => 'Bị từ chối',
    'stale' => 'Nội dung đã sửa sau chấm',
    'thieu' => 'Chấm chưa đầy đủ',
    'loi_json' => 'Không đọc được báo cáo',
  ];

  /**
   * Băng trạng thái sticky ở đầu form.
   *
   * `data-vf-ai-band` là điểm móc DUY NHẤT của JS. Đổi tên ở đây mà quên sửa
   * JS thì tương tác chết âm thầm - băng vẫn hiện, thẻ vẫn hiện, chỉ có
   * Trước/Sau và bộ lọc là không làm gì. Có test khoá lại.
   */
  /**
   * Băng trạng thái sticky ở đầu form.
   *
   * `data-vf-ai-band` là điểm móc DUY NHẤT của JS. Đổi tên ở đây mà quên sửa
   * JS thì tương tác chết âm thầm - băng vẫn hiện, thẻ vẫn hiện, chỉ có
   * Trước/Sau và bộ lọc là không làm gì. Có test khoá lại.
   */
  public function bangHtml(?array $report, string $trang_thai): string {
    $nhan = self::NHAN_TRANG_THAI[$trang_thai] ?? $trang_thai;
    $so_loi = $this->demLoi($report);
    $so_field = count(array_filter($report['fields'] ?? [], 'is_array'));

    $out = '<div class="vf-ai-band vf-ai-band--' . $this->esc($trang_thai) . '"'
      . ' data-vf-ai-band="' . $this->esc($trang_thai) . '">';

    $out .= '<div class="vf-ai-band__trai">';

    if ($trang_thai === 'veto') {
      $out .= '<span class="vf-ai-band__badge vf-ai-band__badge--veto" data-vf-ai-nhan="' . $this->esc($nhan) . '">VETO</span>';
      // Dem THAT bang demChan(), khong ghi cung "1": mot bai co the dinh
      // nhieu loi nghiem trong cung luc.
      $so_chan = $this->demChan($report);
      $out .= '<span class="vf-ai-band__dem"><strong style="color:#8f1717;">Bài bị từ chối</strong> <span style="color:#55565b;">— ' . $so_chan . ' lỗi nghiêm trọng ở Tuân thủ</span></span>';
      $out .= '<span class="vf-ai-band__ngan"></span>';
      $out .= '<span class="vf-ai-band__diem">Điểm tổng không tính khi còn veto</span>';
    }
    elseif ($trang_thai === 'chua_cham') {
      $out .= '<span class="vf-ai-band__badge" data-vf-ai-nhan="' . $this->esc($nhan) . '"><span class="vf-ai-band__dot"></span>' . $this->esc($nhan) . '</span>';
      $out .= '<span class="vf-ai-band__dem" style="font-size:14.5px; color:#3d3e44;">Bài chưa gửi sang hệ Multi-Agent. Lưu ở trạng thái <strong>Needs Review</strong> để bắt đầu chấm.</span>';
    }
    elseif ($trang_thai === 'dang_cham') {
      $out .= '<span class="vf-ai-band__badge" data-vf-ai-nhan="' . $this->esc($nhan) . '"><span class="vf-ai-spinner"></span>' . $this->esc($nhan) . '</span>';
      // KHONG hien tien trinh tung agent. Ban truoc ve cung "SEO ✓ · Chat
      // luong ✓ · Brand Voice dang quay · Tuan thu cho" cung thanh 62% va
      // "con ~40 giay" - khong doc mot du lieu nao, nen Tuan thu KHONG BAO
      // GIO quay du bai da cham xong.
      //
      // Khong sua thanh "that" duoc bang CSS/JS: 4 agent chay SONG SONG
      // (fan-out LangGraph) nen khong co thu tu xong truoc/sau, va worker
      // khong ghi trang thai giua chung ra dau ca. Drupal chi biet job dang
      // chay. Muon co that thi phai them cot DB + endpoint + polling.
      //
      // "Khoang 40 giay" thi GIU: no co can cu that - E4 do duoc 39,3 giay
      // moi luot. Ghi ro la trung binh, khong phai dem nguoc.
      $out .= '<span class="vf-ai-band__dem" style="font-size:14.5px; color:#3d3e44;">Cả 4 agent đang chấm <strong>song song</strong> — trung bình khoảng 40 giây. Bạn vẫn có thể sửa bài trong lúc chờ.</span>';
    }
    elseif ($trang_thai === 'stale') {
      $out .= '<span class="vf-ai-band__badge" data-vf-ai-nhan="' . $this->esc($nhan) . '"><span class="vf-ai-band__dot"></span>' . $this->esc($nhan) . '</span>';
      $out .= '<span class="vf-ai-band__dem" style="font-size:14.5px; color:#3d3e44;">Bài đã sửa sau lần chấm. Danh sách lỗi bên dưới có thể không còn đúng.</span>';
    }
    elseif ($trang_thai === 'thieu') {
      $out .= '<span class="vf-ai-band__badge" data-vf-ai-nhan="' . $this->esc($nhan) . '"><span class="vf-ai-band__dot"></span>' . $this->esc($nhan) . '</span>';
      // Doc DUNG agent bi thieu. Ban truoc mac dinh ve 'Brand Voice' nen bao
      // cao thieu SEO hay Tuan thu van do vay Brand Voice.
      $ds_thieu = array_filter((array) ($report['missing_agents'] ?? []), 'is_string');
      $missing = $ds_thieu ? implode(', ', $ds_thieu) : 'một agent';
      $so_chay = self::TONG_SO_AGENT - count($ds_thieu);
      $out .= '<span class="vf-ai-band__dem"><strong class="vf-ai-band__dem-so">' . $so_loi
        . ' vấn đề</strong> <span class="vf-ai-band__dem-truong">trên ' . $so_field . ' trường</span></span>';
      $out .= '<span class="vf-ai-band__ngan"></span>';
      // "3/4" truoc day ghi cung; nay tinh tu so agent thuc su thieu.
      $out .= '<span style="display:inline-flex; align-items:center; gap:7px; padding:4px 10px; border-radius:12px; background:#eceef2; color:#4a4b50; font-size:12.5px; font-weight:700;">' . $so_chay . '/' . self::TONG_SO_AGENT . ' agent — ' . $this->esc($missing) . ' lỗi</span>';
      // Bo "timeout sau 30s": bao cao khong mang ly do loi, nen day chi la
      // phong doan duoc trinh bay nhu su that.
    }
    elseif ($trang_thai === 'dat') {
      $out .= '<span class="vf-ai-band__badge" data-vf-ai-nhan="' . $this->esc($nhan) . '"><span class="vf-ai-band__dot"></span>' . $this->esc($nhan) . '</span>';
      $out .= '<span class="vf-ai-band__dem"><strong>Không phát hiện vấn đề</strong> <span style="color:#55565b;">— cả 4 agent</span></span>';
      $out .= '<span class="vf-ai-band__ngan"></span>';
      // Khong con mac dinh 92.0: thieu diem thi khong hien o diem, chu khong
      // bia mot con so trong ra nhu diem that.
      $diem = $report['final_score'] ?? NULL;
      if ($diem !== NULL) {
        $out .= '<span class="vf-ai-band__diem">Điểm <strong class="vf-ai-band__diem-so">' . $this->esc($diem) . '</strong>/100</span>';
      }
    }
    else { // co_loi & loi_json
      $out .= '<span class="vf-ai-band__badge" data-vf-ai-nhan="' . $this->esc($nhan) . '"><span class="vf-ai-band__dot"></span>' . $this->esc($nhan) . '</span>';
      if ($so_loi > 0) {
        $out .= '<span class="vf-ai-band__dem"><strong class="vf-ai-band__dem-so">' . $so_loi
          . ' vấn đề</strong> <span class="vf-ai-band__dem-truong">trên ' . $so_field . ' trường</span></span>';
      }
      $out .= '<span class="vf-ai-band__ngan"></span>';
      $out .= '<span class="vf-ai-band__chips" data-vf-ai-chips></span>';
      $out .= '<span class="vf-ai-band__ngan"></span>';
      $diem = $report['final_score'] ?? NULL;
      if ($diem !== NULL) {
        $out .= '<span class="vf-ai-band__diem">Điểm <strong class="vf-ai-band__diem-so">'
          . $this->esc($diem) . '</strong>/100</span>';
      }
    }

    $out .= '</div>'; // Đóng .vf-ai-band__trai

    $out .= '<div class="vf-ai-band__phai" data-vf-ai-nav>';
    if ($trang_thai === 'dat') {
      $out .= '<span style="font-size:13px; color:#3f7a52; font-weight:600;">Có thể chuyển sang Published.</span>';
    }
    elseif ($trang_thai === 'chua_cham') {
      $out .= '<button type="button" class="vf-ai-nut-rescore" style="margin-left:auto;">Chấm ngay</button>';
    }
    elseif ($trang_thai === 'stale') {
      $out .= '<button type="button" class="vf-ai-nut-rescore vf-ai-nut-rescore--primary" style="margin-left:auto;">Chấm lại bản mới</button>';
    }
    elseif ($trang_thai === 'thieu') {
      // Bo lien ket "Bao cho admin": href="#" nen bam khong di dau ca. Chua
      // co luong bao loi that thi khong bay ra nut giai vo.
      $out .= '<button type="button" class="vf-ai-nut-rescore">Chấm lại</button>';
    }
    elseif ($trang_thai === 'veto') {
      // O trong: JS dem so the loi that roi dien vao (this.viTri). Ban truoc
      // ghi cung "Loi 1/1" nen bai co 3 loi nghiem trong van hien 1/1 neu JS
      // chua kip chay.
      $out .= '<span class="vf-ai-band__pos"></span>';
      $out .= '<button type="button" class="vf-ai-nut-rescore">Chấm lại</button>';
    }
    elseif (!empty($report['veto_reason'])) {
      $out .= '<span class="vf-ai-band__ly-do">'
        . $this->esc($report['veto_reason']) . '</span>';
    }
    $out .= '</div>'; // Đóng .vf-ai-band__phai

    return $out . '</div>';
  }

  /**
   * Dải cảnh báo toàn cục trên đỉnh form cho veto / stale / thieu.
   */
  public function globalNoteHtml(string $trang_thai, ?array $report): string {
    if ($trang_thai === 'stale') {
      return '<div class="vf-ai-globalnote vf-ai-globalnote--stale"><strong>Kết quả cho bản cũ.</strong> Bài đã sửa sau lần chấm nên các lỗi dưới đây chỉ để tham khảo.</div>';
    }
    if ($trang_thai === 'thieu') {
      return '<div class="vf-ai-globalnote vf-ai-globalnote--thieu"><strong>Một số agent chưa có kết quả.</strong> Các agent còn lại đã chấm xong và vẫn dùng được.</div>';
    }
    if ($trang_thai === 'veto') {
      return '<div class="vf-ai-globalnote vf-ai-globalnote--veto"><strong>Bài đang bị chặn xuất bản.</strong> Sửa lỗi nghiêm trọng dưới đây rồi bấm Chấm lại.</div>';
    }
    return '';
  }

  /**
   * Khối tóm tắt cho cột phải - CHỈ những gì băng không có.
   */
  public function tomTatHtml(?array $report): string {
    $fields = array_filter($report['fields'] ?? [], 'is_array');
    if (!$fields) {
      return '';
    }
    $out = '<div class="vf-ai-review"><p class="vf-ai-count">Phân bố theo trường:</p><ul>';
    foreach ($fields as $khoa => $ds) {
      $out .= '<li>' . $this->esc(self::FIELD_LABELS[$khoa] ?? $khoa)
        . ' (' . count($ds) . ')</li>';
    }
    return $out . '</ul></div>';
  }

  /**
   * Card "Điểm theo agent" ở cột phải (sidebar).
   */
  public function diemTheoAgentCardHtml(?array $report, string $trang_thai = 'co_loi'): string {
    if ($report === NULL && $trang_thai !== 'chua_cham') {
      return '';
    }

    // Diem THAT tung agent, do Python ghi kem trong report_json.
    //
    // Ban truoc SUY RA cac con so nay tu `final_score` bang cong thuc cong tru
    // theo so loi dem duoc. No hien sai toi 40 diem: bai nid 36 co Compliance
    // that 75 nhung card hien 35 (cong thuc ra 31,6 roi bi kep san 35). Card
    // ma noi sai thi vo dung hon la khong co card.
    // Bao cao cham TRUOC khi Python bat dau ghi `agent_scores`. Khong bia so,
    // nhung cung khong an card khong mot loi giai thich: card bien mat lang le
    // lam nguoi dung tuong giao dien hong (da gap that khi trien khai).
    $diem_raw = $report['agent_scores'] ?? NULL;
    $thieu_diem_agent = !is_array($diem_raw) && $trang_thai !== 'chua_cham';

    // Khoa ben Python la ten agent day du; khoa ben nay la ma ngan cua UI.
    $anh_xa = [
      'seo' => 'seo',
      'cq' => 'content_quality',
      'bv' => 'brand',
      'cp' => 'compliance',
    ];
    $ten_agent = [
      'seo' => 'SEO',
      'cq' => 'Chất lượng',
      'bv' => 'Brand Voice',
      'cp' => 'Tuân thủ',
    ];

    $ds_agent = [];
    foreach ($anh_xa as $ma => $khoa_python) {
      $diem = is_array($diem_raw) ? ($diem_raw[$khoa_python] ?? NULL) : NULL;
      $co_diem = is_numeric($diem);
      $ds_agent[$ma] = [
        'ten' => $ten_agent[$ma],
        // Thanh bar can so nguyen 0-100; agent loi -> bar rong.
        'diem' => $co_diem ? (int) round((float) $diem) : 0,
        // Giu mot chu so thap phan khi co, bo duoi ".0" cho gon: 75.0 -> "75",
        // 81.2 -> "81.2". Agent loi -> "loi", KHONG phai "0".
        'val_text' => $co_diem
          ? rtrim(rtrim(sprintf('%.1f', (float) $diem), '0'), '.')
          : 'lỗi',
      ];
    }

    $card_class = 'vf-ai-agent-card';
    if ($trang_thai === 'stale') {
      $card_class .= ' vf-ai-agent-card--stale';
    }

    if ($trang_thai === 'chua_cham' || $thieu_diem_agent) {
      foreach ($ds_agent as $k => &$item) {
        $item['diem'] = 0;
        $item['val_text'] = '—';
      }
      unset($item);
    }
    elseif ($trang_thai === 'veto') {
      // Chi doi CHU, giu nguyen do dai thanh theo diem that. Ban truoc dat
      // diem = 100 o day, tuc hien thanh DAY cho dung agent vua chan bai
      // (G-010: Compliance that 50 nhung thanh full) - nguoc han su that.
      $ds_agent['cp']['val_text'] = 'veto';
    }
    // Khong con nhanh rieng cho trang thai 'thieu': agent loi da tu ra "loi"
    // o vong lap tren, va no dung cho DUNG agent bi loi. Ban truoc hardcode
    // 'bv' nen bao cao thieu SEO hay Compliance van do vay Brand Voice.

    $out = '<div class="' . $card_class . '">';
    $out .= '<div class="vf-ai-agent-card__head">Điểm theo agent</div>';
    $out .= '<div class="vf-ai-agent-card__body">';

    foreach ($ds_agent as $k => $item) {
      $d = $item['diem'];
      $val_text = $item['val_text'];
      $out .= '<div class="vf-ai-agent-card__row" data-agent="' . $k . '">';
      $out .= '<span class="vf-ai-agent-card__name">' . $this->esc($item['ten']) . '</span>';
      $out .= '<span class="vf-ai-agent-card__bar-bg">';
      $out .= '<span class="vf-ai-agent-card__bar-fill vf-ai-agent-card__bar-fill--' . $k . '" data-pt="' . $d . '"></span>';
      $out .= '</span>';
      $out .= '<strong class="vf-ai-agent-card__val">' . $this->esc($val_text) . '</strong>';
      $out .= '</div>';
    }

    $gio_cham = !empty($report['scored_at']) ? $this->dinhDangGio($report['scored_at']) : date('d/m/Y H:i');
    $footer_text = 'Chấm lúc ' . $this->esc($gio_cham);
    if ($thieu_diem_agent) {
      $footer_text = 'Báo cáo cũ chưa có điểm theo agent — bấm "Chấm lại" để xem';
    }
    elseif ($trang_thai === 'chua_cham') {
      $footer_text = 'Chưa có kết quả chấm cho bài này';
    }
    elseif ($trang_thai === 'veto') {
      $footer_text = 'Điểm tổng không được tính khi còn veto';
    }
    elseif ($trang_thai === 'thieu') {
      // Ban truoc ghi cung 'Brand Voice loi: timeout sau 30s - job #4182':
      // sai agent, sai ly do, va so job thi bia han. Doc tu missing_agents.
      $thieu = array_filter((array) ($report['missing_agents'] ?? []), 'is_string');
      $footer_text = $thieu
        ? 'Không có kết quả từ: ' . $this->esc(implode(', ', $thieu))
        : 'Thiếu kết quả của một agent';
    }
    elseif ($trang_thai === 'stale') {
      $footer_text = 'Kết quả cho bản cũ — bài đã sửa sang bản mới';
    }

    $out .= '<div class="vf-ai-agent-card__footer">';
    $out .= $footer_text;
    $out .= '</div>';

    $out .= '</div></div>';
    return $out;
  }

  /**
   * Thẻ lỗi rich của một field.
   *
   * Trả chuỗi rỗng nếu field không có vấn đề gì - gọi được cho mọi field mà
   * không cần người gọi tự kiểm trước.
   */
  public function theLoiHtml(?array $report, string $fieldKey, string $trang_thai = 'co_loi'): string {
    if ($trang_thai === 'dat') {
      return '<div class="vf-ai-ok"><span class="vf-ai-ok-icon">✓</span> Không phát hiện vấn đề</div>';
    }
    if ($trang_thai === 'chua_cham' || $trang_thai === 'dang_cham') {
      return '';
    }

    $ds = $report['fields'][$fieldKey] ?? NULL;
    if (!is_array($ds) || $ds === []) {
      return '';
    }

    // Nếu trạng thái là veto: chỉ hiển thị các issue critical (block)
    if ($trang_thai === 'veto') {
      $ds = array_filter($ds, fn($muc) => ($muc['severity'] ?? NULL) === 'critical');
      if (empty($ds)) {
        return '';
      }
    }

    $ten = self::FIELD_LABELS[$fieldKey] ?? $fieldKey;
    $out = '<div class="vf-ai-hop" data-vf-ai-hop="' . $this->esc($fieldKey) . '">';
    $out .= '<div class="vf-ai-hop__dau">';
    $out .= '<span class="vf-ai-hop__dau-tieu-de" data-vf-ai-hop-head="' . $this->esc($fieldKey) . '">AI phát hiện <strong>' . count($ds)
      . '</strong> vấn đề ở trường này</span>';
    if ($fieldKey === 'body') {
      $out .= '<span class="vf-ai-hop__dau-chu-thich"> · đoạn liên quan đã được tô trong bài</span>';
    }
    $out .= '<a href="#" class="vf-ai-hop__thu-gon" data-vf-ai-collapse="' . $this->esc($fieldKey) . '">Thu gọn ▴</a>';
    $out .= '</div>';
    $out .= '<div class="vf-ai-hop__the" data-vf-ai-cards="' . $this->esc($fieldKey) . '">';

    foreach ($ds as $i => $muc) {
      if (!is_array($muc)) {
        continue;
      }
      $muc_hien = self::mucHienThi($muc['severity'] ?? NULL);
      $agent_raw = $muc['agent'] ?? '';
      $agent_name = self::AGENT_NAMES[$agent_raw] ?? $agent_raw;
      $agent_code = self::AGENT_SHORT[$agent_raw] ?? $agent_raw;

      $label_raw = $muc['label'] ?? '';
      $tieu_de = $label_raw;
      $has_bv1 = FALSE;

      // Bóc tách mã tiêu chí nếu có trong label (ví dụ "Sai cách viết tên model (BV1)" -> code: "BV1")
      if (preg_match('/^(.*?)\s*\(([A-Z0-9]+)\)$/u', $label_raw, $khop)) {
        $tieu_de = $khop[1];
        $agent_code = $khop[2];
        if ($agent_code === 'BV1') {
          $has_bv1 = TRUE;
        }
      }
      elseif (str_contains(strtolower($label_raw), 'tên model') || str_contains(strtolower($label_raw), 'vf8')) {
        $agent_code = 'BV1';
        $has_bv1 = TRUE;
      }
      elseif (str_contains(strtolower($label_raw), 'tiêu đề') && str_contains(strtolower($agent_name), 'seo')) {
        $agent_code = 'SEO1';
      }

      $the_class = 'vf-ai-the vf-ai-the--' . $muc_hien;
      if ($trang_thai === 'stale') {
        $the_class .= ' vf-ai-the--stale';
      }

      $out .= '<div class="' . $the_class . '"'
        . ' data-vf-ai-issue="' . $this->esc($fieldKey . '-' . $i) . '"'
        . ' data-sev="' . $muc_hien . '"'
        . ' data-field="' . $this->esc($fieldKey) . '">';

      // Cột trái: Mã tiêu chí
      $out .= '<span class="vf-ai-the__ma vf-ai-the__ma--' . $muc_hien . '">' . $this->esc($agent_code) . '</span>';

      // Cột phải: Toàn bộ nội dung và hành động
      $out .= '<div class="vf-ai-the__noi-dung">';
      $out .= '<div class="vf-ai-the__hang-tieu-de">';
      $out .= '<div class="vf-ai-the__tieu-de">' . $this->esc($tieu_de);
      if ($agent_name !== '') {
        $out .= ' <span class="vf-ai-the__agent-ten">· ' . $this->esc($agent_name) . '</span>';
      }
      $out .= '</div>';
      if ($muc_hien === 'block') {
        $out .= '<span class="vf-ai-the__chan">CHẶN XUẤT BẢN</span>';
      }
      $out .= '</div>';

      if (!empty($muc['message'])) {
        $out .= '<div class="vf-ai-the__mo-ta">' . $this->esc($muc['message']) . '</div>';
      }
      if (!empty($muc['excerpt'])) {
        $out .= '<div class="vf-ai-the__trich">'
          . $this->esc($muc['excerpt']) . '</div>';
      }

      // Vùng hành động (checkbox "Đã xử lý" sẽ do JS chèn)
      $out .= '<div class="vf-ai-the__hanh-dong" data-vf-ai-actions="' . $this->esc($fieldKey . '-' . $i) . '">';
      if ($has_bv1) {
        $out .= '<button type="button" class="vf-ai-nut-autofix" data-vf-ai-autofix="VF 8">Sửa thành “VF 8”</button>';
      }
      $out .= '</div>';

      $out .= '</div>'; // Đóng .vf-ai-the__noi-dung
      $out .= '</div>'; // Đóng .vf-ai-the
    }

    $out .= '</div></div>';
    return $out;
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
