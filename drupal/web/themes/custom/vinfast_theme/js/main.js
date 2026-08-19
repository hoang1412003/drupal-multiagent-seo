/**
 * Main JavaScript for VinFast Theme.
 */
(function (Drupal, once) {
  'use strict';

  Drupal.behaviors.vinfastThemeMain = {
    attach: function (context) {
      // Mobile Navigation Toggle
      once('vf-mobile-menu', '[data-vf-mobile-menu-btn]', context).forEach(function (btn) {
        var menu = document.querySelector('[data-vf-mobile-menu]');
        if (!menu) return;

        btn.addEventListener('click', function () {
          menu.classList.toggle('hidden');
        });
      });

      // Share Button Action
      once('vf-share-btn', '[data-vf-share-btn]', context).forEach(function (btn) {
        btn.addEventListener('click', function () {
          var title = document.title;
          var url = window.location.href;

          if (navigator.share) {
            navigator.share({
              title: title,
              url: url
            }).catch(function (err) {
              console.log('Share dismissed:', err);
            });
          } else {
            // Fallback: Copy to clipboard
            navigator.clipboard.writeText(url).then(function () {
              showToast('Đã sao chép liên kết vào bộ nhớ tạm!');
            }).catch(function () {
              showToast('Không thể sao chép liên kết.');
            });
          }
        });
      });

      // Bookmark Button Action
      once('vf-bookmark-btn', '[data-vf-bookmark-btn]', context).forEach(function (btn) {
        btn.addEventListener('click', function () {
          var icon = btn.querySelector('.material-symbols-outlined');
          var isBookmarked = btn.getAttribute('data-bookmarked') === 'true';

          if (isBookmarked) {
            btn.setAttribute('data-bookmarked', 'false');
            btn.classList.remove('bg-primary', 'text-white');
            if (icon) icon.style.fontVariationSettings = "'FILL' 0";
            showToast('Đã gỡ bài viết khỏi danh sách lưu.');
          } else {
            btn.setAttribute('data-bookmarked', 'true');
            btn.classList.add('bg-primary', 'text-white');
            if (icon) icon.style.fontVariationSettings = "'FILL' 1";
            showToast('Đã lưu bài viết thành công!');
          }
        });
      });

      // Password Visibility Toggle
      once('vf-toggle-password', '[data-vf-toggle-password]', context).forEach(function (btn) {
        btn.addEventListener('click', function () {
          var passwordInput = document.querySelector('[data-vf-password-input]') || (btn.closest('.relative') ? btn.closest('.relative').querySelector('input') : null);
          var icon = btn.querySelector('.material-symbols-outlined');
          if (!passwordInput) return;

          if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            if (icon) icon.textContent = 'visibility';
          } else {
            passwordInput.type = 'password';
            if (icon) icon.textContent = 'visibility_off';
          }
        });
      });

      // Newsletter Form Action
      once('vf-newsletter-form', '[data-vf-newsletter-form]', context).forEach(function (form) {
        form.addEventListener('submit', function (e) {
          e.preventDefault();
          var emailInput = form.querySelector('input[type="email"]');
          var email = emailInput ? emailInput.value.trim() : '';

          if (email) {
            showToast('Cảm ơn bạn đã đăng ký nhận bản tin VinFast!');
            form.reset();
          } else {
            showToast('Vui lòng nhập địa chỉ email hợp lệ.');
          }
        });
      });

      // Toast notification helper
      function showToast(message) {
        var existingToast = document.getElementById('vf-toast-notice');
        if (existingToast) {
          existingToast.remove();
        }

        var toast = document.createElement('div');
        toast.id = 'vf-toast-notice';
        toast.className = 'fixed bottom-6 right-6 z-50 bg-primary text-on-primary px-6 py-3 rounded-full shadow-xl flex items-center space-x-2 text-sm font-medium transition-all duration-300 transform translate-y-0 opacity-100';
        toast.innerHTML = '<span class="material-symbols-outlined text-base">check_circle</span><span>' + message + '</span>';

        document.body.appendChild(toast);

        setTimeout(function () {
          toast.style.opacity = '0';
          toast.style.transform = 'translateY(10px)';
          setTimeout(function () {
            toast.remove();
          }, 300);
        }, 3500);
      }
    }
  };
})(Drupal, once);
