<?php

namespace Drupal\vf_ai_review\Theme;

use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\Core\Theme\ThemeNegotiatorInterface;

/**
 * Sets administration theme for user profile pages.
 */
class UserAdminThemeNegotiator implements ThemeNegotiatorInterface {

  /**
   * {@inheritdoc}
   */
  public function applies(RouteMatchInterface $route_match) {
    $route_name = $route_match->getRouteName();
    return in_array($route_name, ['entity.user.canonical', 'user.page']);
  }

  /**
   * {@inheritdoc}
   */
  public function determineActiveTheme(RouteMatchInterface $route_match) {
    return 'claro';
  }

}
