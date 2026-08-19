/**
 * Blog Filter and Search functionality for VinFast Theme.
 */
(function (Drupal, once) {
  'use strict';

  Drupal.behaviors.vinfastBlogFilter = {
    attach: function (context) {
      var filterContainer = document.querySelector('[data-vf-filter-bar]');
      var cards = document.querySelectorAll('[data-vf-blog-card]');
      var searchInput = document.querySelector('[data-vf-search-input]');
      var emptyState = document.getElementById('vf-empty-results');

      if (!filterContainer && !searchInput) return;

      var currentCategory = 'all';
      var currentQuery = '';

      function filterArticles() {
        var visibleCount = 0;

        cards.forEach(function (card) {
          var category = (card.getAttribute('data-category') || '').toLowerCase();
          var tags = (card.getAttribute('data-tags') || '').toLowerCase();
          var title = (card.querySelector('[data-vf-card-title]') ? card.querySelector('[data-vf-card-title]').textContent : '').toLowerCase();
          var summary = (card.querySelector('[data-vf-card-summary]') ? card.querySelector('[data-vf-card-summary]').textContent : '').toLowerCase();

          var matchesCategory = (currentCategory === 'all' || category === currentCategory || tags.includes(currentCategory));
          var matchesQuery = !currentQuery || title.includes(currentQuery) || summary.includes(currentQuery);


          if (matchesCategory && matchesQuery) {
            card.classList.remove('hidden');
            visibleCount++;
          } else {
            card.classList.add('hidden');
          }
        });

        if (emptyState) {
          if (visibleCount === 0) {
            emptyState.classList.remove('hidden');
          } else {
            emptyState.classList.add('hidden');
          }
        }
      }

      // Category chip click
      once('vf-filter-chips', '[data-vf-filter-chip]', context).forEach(function (chip) {
        chip.addEventListener('click', function () {
          var selectedCat = (chip.getAttribute('data-category') || 'all').toLowerCase();
          currentCategory = selectedCat;

          // Update active state styles
          document.querySelectorAll('[data-vf-filter-chip]').forEach(function (btn) {
            btn.classList.remove('bg-primary', 'text-on-primary');
            btn.classList.add('bg-surface-container', 'text-on-surface-variant', 'hover:bg-surface-variant');
          });

          chip.classList.remove('bg-surface-container', 'text-on-surface-variant', 'hover:bg-surface-variant');
          chip.classList.add('bg-primary', 'text-on-primary');

          filterArticles();
        });
      });

      // Search input typing
      if (searchInput) {
        once('vf-search-input', searchInput, context).forEach(function (input) {
          input.addEventListener('input', function (e) {
            currentQuery = e.target.value.trim().toLowerCase();
            filterArticles();
          });
        });
      }

      // Load More button simulation
      var loadMoreBtn = document.querySelector('[data-vf-load-more]');
      if (loadMoreBtn) {
        once('vf-load-more', loadMoreBtn, context).forEach(function (btn) {
          btn.addEventListener('click', function () {
            btn.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span> Đang tải...';
            setTimeout(function () {
              btn.innerHTML = 'Đã hiển thị tất cả bài viết';
              btn.classList.add('opacity-60', 'cursor-not-allowed');
              btn.disabled = true;
            }, 800);
          });
        });
      }
    }
  };
})(Drupal, once);
