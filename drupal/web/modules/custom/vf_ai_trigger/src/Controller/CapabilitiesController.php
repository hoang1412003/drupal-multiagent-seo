<?php

namespace Drupal\vf_ai_trigger\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\Core\Session\AccountInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpFoundation\JsonResponse;

/**
 * Báo tài khoản machine đang gọi THỰC SỰ làm được những gì.
 *
 * Vì sao cần: một GET collection JSON:API trả 200 không chứng minh được gì.
 * Tài khoản thiếu "view latest version" vẫn đọc được danh sách bài đã xuất
 * bản, nên "test connection" sẽ báo xanh, rồi worker chết ở đúng nhóm bài
 * needs_review - tức là báo xanh ở chỗ không quan trọng và báo im ở chỗ quan
 * trọng. Ở đây trả thẳng ba năng lực mà production thật sự dùng.
 *
 * Không trả username/role/secret: đây là endpoint chẩn đoán, không phải chỗ
 * để lộ cấu hình tài khoản.
 */
class CapabilitiesController extends ControllerBase {

  public const VERSION = 1;

  public function __construct(
    private readonly AccountInterface $currentUserService,
  ) {}

  public static function create(ContainerInterface $container): static {
    return new static($container->get('current_user'));
  }

  public function capabilities(): JsonResponse {
    $user = $this->currentUserService;
    $response = new JsonResponse([
      'version' => self::VERSION,
      'pending_feed' => $user->hasPermission('access vf ai integration feed'),
      'result_callback' => $user->hasPermission('submit vf ai integration result'),
      // Đọc đúng revision needs_review cần cả hai quyền này; thiếu một trong
      // hai là worker sẽ 403 ở giữa chừng.
      'revision_read' => $user->hasPermission('view latest version')
        && $user->hasPermission('view any unpublished content'),
    ]);
    $response->headers->set('Cache-Control', 'no-store');
    return $response;
  }

}
