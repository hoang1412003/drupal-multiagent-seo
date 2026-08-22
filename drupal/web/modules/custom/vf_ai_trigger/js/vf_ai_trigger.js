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

        function veDangChamTrenBand() {
          var band = document.querySelector('[data-vf-ai-band]');
          if (!band) return;
          band.className = 'vf-ai-band vf-ai-band--dang_cham';
          band.setAttribute('data-vf-ai-band', 'dang_cham');

          var trai = band.querySelector('.vf-ai-band__trai');
          if (trai) {
            // KHÔNG vẽ tiến trình từng agent. Bản trước ghi cứng "SEO ✓ ·
            // Chất lượng ✓ · Brand Voice đang quay · Tuân thủ chờ" cùng thanh
            // 62% — không đọc dữ liệu nào, nên Tuân thủ không bao giờ quay dù
            // bài đã chấm xong.
            //
            // Không làm "thật" được: 4 agent chạy SONG SONG (fan-out
            // LangGraph) nên không có thứ tự xong trước/sau, và worker không
            // ghi trạng thái giữa chừng ra đâu cả — poll chỉ biết job đang
            // queued/running/done.
            //
            // "Khoảng 40 giây" thì giữ: có căn cứ thật (E4 đo 39,3 giây mỗi
            // lượt). Ghi rõ là trung bình, không phải đếm ngược.
            //
            // ĐOẠN NÀY PHẢI KHỚP VỚI AiReportRenderer::bangHtml() nhánh
            // 'dang_cham' — cùng một băng, hai module cùng vẽ.
            trai.innerHTML = '<span class="vf-ai-band__badge"><span class="vf-ai-spinner"></span>Đang chấm</span>'
              + '<span class="vf-ai-band__dem" style="font-size:14.5px; color:#3d3e44;">'
              + 'Cả 4 agent đang chấm <strong>song song</strong> — trung bình khoảng 40 giây. '
              + 'Bạn vẫn có thể sửa bài trong lúc chờ.</span>';
          }
          var phai = band.querySelector('[data-vf-ai-nav]');
          if (phai) {
            phai.innerHTML = '';
          }
          document.querySelectorAll('[data-vf-ai-hop]').forEach(function (h) {
            h.style.display = 'none';
          });
          var luu = document.querySelector('.vf-ai-chan-luu');
          if (luu) {
            luu.innerHTML = '<span style="color:#55565b">Đang chờ kết quả chấm…</span>';
            luu.className = 'vf-ai-chan-luu';
          }
        }

        function ve(trangThai) {
          if (trangThai === 'queued') {
            el.textContent = '⏳ Đã xếp hàng, đang chờ tới lượt…';
            veDangChamTrenBand();
          }
          else if (trangThai === 'running') {
            el.textContent = '⏳ Đang chấm…';
            veDangChamTrenBand();
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
              if (d.status === 'failed') {
                // Trạng thái cuối, không hỏi tiếp. ve() đã hiện thông báo.
                return;
              }
              // 'none' KHÔNG phải trạng thái cuối — nghĩa là job chưa được
              // xếp hàng (ví dụ Save vừa chạy, hook chưa kịp gọi service),
              // vẫn phải hỏi tiếp cho tới khi thấy queued/running/done.
              if (lan < TOI_DA_LAN) {
                window.setTimeout(hoi, CHU_KY_MS);
              }
              else {
                // Chạm trần TOI_DA_LAN mà chưa xong: dừng hỏi nhưng phải nói
                // rõ đã dừng, không được để nguyên chữ "Đang chấm…" mãi mãi
                // khiến người dùng tưởng hệ thống vẫn đang chạy.
                el.textContent = '⚠ Đã ngừng theo dõi sau ' + TOI_DA_LAN + ' lần hỏi. Tải lại trang để kiểm tra kết quả mới nhất.';
              }
            })
            .catch(function () {
              // Một request rớt giữa lúc chấm (mất mạng thoáng qua, service
              // restart) không được coi là trạng thái cuối — nếu không thì ô
              // trạng thái đứng yên ở thông báo này mãi mãi dù job chấm xong
              // ngay sau đó. Hỏi tiếp giống nhánh 'khong_ro' phía trên.
              ve('khong_ro');
              if (lan < TOI_DA_LAN) {
                window.setTimeout(hoi, CHU_KY_MS);
              }
              else {
                el.textContent = '⚠ Đã ngừng theo dõi sau ' + TOI_DA_LAN + ' lần hỏi. Tải lại trang để kiểm tra kết quả mới nhất.';
              }
            });
        }

        hoi();
      });

      // Nút "Chấm lại": ép chấm lại thủ công, tốn tiền API thật nên chỉ hiện
      // với người có quyền 'dieu khien ai' (xem vf_ai_trigger.module).
      var nut = once('vf-ai-cham-lai', '[data-vf-ai-rescore-url]', context);
      nut.forEach(function (btn) {
        btn.addEventListener('click', function () {
          btn.disabled = true;
          btn.textContent = 'Đang gửi…';
          fetch(btn.getAttribute('data-vf-ai-rescore-url'), {
            method: 'POST',
            credentials: 'same-origin'
          })
            .then(function (r) {
              if (r.status === 202) {
                window.location.reload();
              }
              else {
                // Bật lại nút: lỗi có thể tạm thời (mất mạng, service vừa
                // khởi động lại) - không bật lại thì người dùng phải tải lại
                // cả trang mới bấm được lần nữa, mà không biết vì sao.
                btn.disabled = false;
                btn.textContent = 'Gửi thất bại, bấm để thử lại';
              }
            })
            .catch(function () {
              btn.disabled = false;
              btn.textContent = 'Gửi thất bại, bấm để thử lại';
            });
        });
      });
    }
  };
})(Drupal, once);
