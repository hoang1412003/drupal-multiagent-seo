/**
 * @file
 * Poll trạng thái chấm điểm và tự nạp lại trang khi xong.
 *
 * Không có nó thì editor bấm Save xong sẽ thấy "Chưa được đánh giá" suốt một
 * phút, tưởng hệ thống hỏng rồi bấm Save lại — mỗi lần bấm là tiền API thật.
 */
(function (Drupal, once) {
  'use strict';

  var CHU_KY_MS = 3000;
  var TOI_DA_LAN = 40; // ~2 phút rồi thôi, không poll mãi

  Drupal.behaviors.vfAiTrigger = {
    attach: function (context, settings) {
      var els = once('vf-ai-trang-thai', '[data-vf-ai-status-url]', context);
      els.forEach(function (el) {
        var url = el.getAttribute('data-vf-ai-status-url');
        var lan = 0;
        // CHỈ được tải lại trang khi đã tận mắt thấy job đang "queued" hoặc
        // "running" rồi mới thấy nó "done". Vì sao: bài ĐÃ CHẤM XONG TỪ TRƯỚC
        // cũng trả "done" ngay ở lần poll đầu tiên. Thiếu cờ này thì mở form
        // sửa một bài cũ là trang tự tải lại → behavior chạy lại → lại thấy
        // "done" ngay → tải lại nữa… vòng lặp vô hạn, và mọi bài đã có kết
        // quả sẽ không mở ra sửa được.
        var da_thay_dang_chay = false;

        function ve(trangThai) {
          if (trangThai === 'queued') {
            el.textContent = '⏳ Đã xếp hàng, đang chờ tới lượt…';
          }
          else if (trangThai === 'running') {
            el.textContent = '⏳ Đang chấm…';
          }
          else if (trangThai === 'failed') {
            el.textContent = '⛔ Chấm thất bại. Xem log của worker.';
          }
          else if (trangThai === 'khong_ro') {
            el.textContent = '⚠ Không liên lạc được với dịch vụ chấm điểm.';
          }
        }

        function hoi() {
          lan += 1;
          fetch(url, { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (d) {
              if (d.status === 'queued' || d.status === 'running') {
                da_thay_dang_chay = true;
              }
              if (d.status === 'done') {
                if (da_thay_dang_chay) {
                  // Nạp lại để khối báo cáo hiện dữ liệu mới. Chỉ làm việc
                  // này khi chính lượt poll này đã chứng kiến job chạy —
                  // xem giải thích ở khai báo cờ phía trên.
                  window.location.reload();
                }
                return;
              }
              ve(d.status);
              if (d.status !== 'none' && d.status !== 'failed' && lan < TOI_DA_LAN) {
                window.setTimeout(hoi, CHU_KY_MS);
              }
            })
            .catch(function () {
              el.textContent = '⚠ Không liên lạc được với dịch vụ chấm điểm.';
            });
        }

        hoi();
      });
    }
  };
})(Drupal, once);
