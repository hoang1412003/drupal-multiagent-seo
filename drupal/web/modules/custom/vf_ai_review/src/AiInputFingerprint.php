<?php

namespace Drupal\vf_ai_review;

/**
 * Fingerprint v2 của SÁU input mà hệ chấm điểm thực sự đọc.
 *
 * Phải khớp từng byte với multiagent/src/review_platform/fingerprint.py.
 * Hợp đồng giữa hai ngôn ngữ nằm ở drupal/scripts/input_fingerprint_v2_fixture.json;
 * cả hai bên đều có test đọc đúng file đó, nên lệch là đỏ ngay chứ không âm thầm.
 *
 * Vì sao có v2 bên cạnh contentHash() v1: v1 chỉ băm bốn field, bỏ sót
 * `url_alias` và `image_alt` dù SEO Agent có chấm hai thứ đó. Editor sửa alt
 * ảnh xong thì báo cáo cũ KHÔNG bị đánh dấu là cũ (nợ N2). v1 vẫn phải giữ
 * nguyên để job legacy chạy được trong cửa sổ rollback.
 *
 * CỐ Ý KHÔNG phụ thuộc Drupal, giống AiReportRenderer: vào là mảng/chuỗi, ra
 * là chuỗi. Nhờ vậy test bằng PHP thuần, không cần bootstrap Drupal. Phần
 * đọc node nằm ở vf_ai_review_input_fields() trong file .module.
 */
class AiInputFingerprint {

  /**
   * Phiên bản nằm TRONG phần được băm, nên v1 và v2 không bao giờ trùng hash.
   */
  public const VERSION = 2;

  /**
   * Đúng thứ tự này. Đổi thứ tự là đổi hash dù nội dung y nguyên.
   */
  private const FIELDS = [
    'title',
    'body',
    'summary',
    'url_alias',
    'meta_description',
    'image_alt',
  ];

  /**
   * Chuỗi byte được băm. Tách riêng để test đọc được chính xác cái gì vào.
   */
  public static function canonicalBytes(array $fields): string {
    $ordered = [];
    foreach (self::FIELDS as $khoa) {
      $ordered[$khoa] = (string) ($fields[$khoa] ?? '');
    }
    // JSON_UNESCAPED_UNICODE + JSON_UNESCAPED_SLASHES để khớp json.dumps của
    // Python với ensure_ascii=False; PHP mặc định escape cả hai thứ đó.
    $json = json_encode(
      $ordered,
      JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR
    );
    return 'v' . self::VERSION . "\n" . $json;
  }

  /**
   * Fingerprint v2 của sáu field.
   */
  public static function hash(array $fields): string {
    return hash('sha256', self::canonicalBytes($fields));
  }

  /**
   * Liệt kê alt của ảnh đại diện và MỌI ảnh trong body.
   *
   * Phải khớp từng ký tự với _extract_image_alt() bên Python, kể cả nhãn
   * tiếng Việt và thứ tự: ảnh đại diện trước, rồi ảnh trong bài đánh số từ 1.
   *
   * $featuredAlt = NULL nghĩa là bài KHÔNG có ảnh đại diện (không có dòng
   * nào), khác hẳn chuỗi rỗng nghĩa là CÓ ảnh nhưng THIẾU alt (có dòng, phần
   * sau dấu hai chấm để trống).
   */
  public static function imageAltLines(?string $featuredAlt, string $bodyHtml): string {
    $dong = [];
    if ($featuredAlt !== NULL) {
      $dong[] = 'Ảnh đại diện: ' . $featuredAlt;
    }

    preg_match_all('/<img[^>]*>/i', $bodyHtml, $the_img);
    foreach ($the_img[0] as $i => $the) {
      $dong[] = 'Ảnh ' . ($i + 1) . ' trong bài: ' . self::altCuaTheImg($the);
    }

    return implode("\n", $dong);
  }

  /**
   * Giá trị alt của một thẻ <img>. Không có hoặc rỗng -> chuỗi rỗng.
   *
   * (?<![\w-]) chứ KHÔNG phải \b: \b khớp ngay giữa dấu gạch và chữ nên
   * data-alt="x" bị đọc nhầm thành alt. Sai theo hướng nguy hiểm - ảnh THIẾU
   * alt thật nhưng có data-alt sẽ bị coi là có alt, tức bỏ sót lỗi B6.
   */
  private static function altCuaTheImg(string $the): string {
    $khop = [];
    $co = preg_match(
      '/(?<![\w-])alt\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>"\']+))/i',
      $the,
      $khop
    );
    if (!$co) {
      return '';
    }
    // Chuỗi rỗng rơi xuống nhóm sau, y hệt phép `or` nối chuỗi bên Python.
    foreach ([2, 3, 4] as $nhom) {
      if (isset($khop[$nhom]) && $khop[$nhom] !== '') {
        return trim($khop[$nhom]);
      }
    }
    return '';
  }

}
