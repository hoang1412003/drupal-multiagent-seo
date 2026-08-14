<?php

namespace Drupal\vf_ai_trigger\Service;

/**
 * Payload result callback sai hợp đồng.
 *
 * Tách riêng khỏi lỗi hệ thống để controller trả 400 (client sửa được) thay
 * vì 500 (server hỏng) - hai thứ đó cần hai phản ứng vận hành khác nhau.
 */
class AiResultRequestException extends \RuntimeException {}
