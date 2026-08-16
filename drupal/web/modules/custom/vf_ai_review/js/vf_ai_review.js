/**
 * @file
 * Tương tác cho khối báo cáo lỗi AI (docs/editor-ui-design.md mục 10).
 *
 * PROGRESSIVE ENHANCEMENT: file này hỏng hoặc không nạp thì form vẫn dùng
 * bình thường. Băng trạng thái và thẻ lỗi do PHP render nên vẫn đọc được -
 * chỉ mất phần điều khiển. Vì vậy MỌI phần tử điều khiển đều do JS tự chèn,
 * không có sẵn trong HTML.
 *
 * Module vf_ai_review là CHỈ ĐỌC, không được ghi vào node. Nên dấu "đã xử
 * lý" nằm ở localStorage, khoá gồm cả content_hash - xem GHI_CHU_KHOA.
 */
(function (Drupal, drupalSettings, once) {
  'use strict';

  var MUC = { block: 'Chặn xuất bản', fix: 'Cần sửa', tip: 'Gợi ý' };

  // Khoảng cách chừa ra khi cuộn tới lỗi: băng sticky cao ~60px, cộng thở.
  var CHUA_CHO_BANG = 160;

  /**
   * GHI_CHU_KHOA: khoá PHẢI gồm content_hash, không chỉ nid.
   *
   * Bài được chấm lại thì hash đổi -> toàn bộ dấu cũ tự hết hiệu lực. Nếu
   * chỉ khoá theo nid, dấu "đã xử lý" của lỗi CŨ sẽ dính trên báo cáo MỚI
   * và người duyệt tưởng đã xử lý rồi - đúng loại lỗi im lặng mà mục 4.4
   * của tài liệu thiết kế đã phải xử lý một lần với mốc `changed`.
   */
  function khoaLuu(cfg) {
    return 'vf-ai:' + cfg.nid + ':' + (cfg.hash || 'chua-cham');
  }

  function docDaXong(cfg) {
    try {
      return JSON.parse(window.localStorage.getItem(khoaLuu(cfg)) || '[]');
    }
    catch (e) {
      // localStorage bị chặn (chế độ riêng tư, cấu hình trình duyệt) không
      // được làm chết cả khối báo cáo - phần còn lại vẫn dùng được.
      return [];
    }
  }

  function ghiDaXong(cfg, ds) {
    try {
      window.localStorage.setItem(khoaLuu(cfg), JSON.stringify(ds));
    }
    catch (e) {
      /* hết dung lượng hoặc bị chặn: bỏ qua, không chặn thao tác */
    }
  }

  function Bang(band, cfg) {
    this.band = band;
    this.cfg = cfg;
    this.doc = band.ownerDocument;
    this.the = Array.prototype.slice.call(
      this.doc.querySelectorAll('[data-vf-ai-issue]')
    );
    this.loc = 'tat_ca';
    this.hien = 0;
    this.daXong = docDaXong(cfg);
  }

  Bang.prototype.dungDieuKhien = function () {
    var self = this;
    var hop = this.doc.createElement('span');
    hop.className = 'vf-ai-band__dieu-khien';

    // Chip lọc mức - chỉ có ý nghĩa khi thật sự có lỗi để lọc.
    if (this.the.length) {
      ['tat_ca', 'block', 'fix', 'tip'].forEach(function (m) {
        var b = self.doc.createElement('button');
        b.type = 'button';
        b.className = 'vf-ai-chip';
        b.textContent = m === 'tat_ca' ? 'Tất cả' : MUC[m];
        b.setAttribute('aria-pressed', String(m === 'tat_ca'));
        b.addEventListener('click', function () { self.datLoc(m); });
        self['chip_' + m] = b;
        hop.appendChild(b);
      });

      this.viTri = this.doc.createElement('span');
      this.viTri.className = 'vf-ai-band__dem';
      hop.appendChild(this.viTri);

      this.nutTruoc = this.nut(hop, '← Trước', -1);
      this.nutSau = this.nut(hop, 'Sau →', 1);
    }

    var an = this.doc.createElement('button');
    an.type = 'button';
    an.className = 'vf-ai-nut';
    an.textContent = 'Ẩn báo cáo';
    an.addEventListener('click', function () {
      var dangAn = an.textContent.indexOf('Ẩn') === 0;
      self.doc.querySelectorAll('[data-vf-ai-hop]').forEach(function (h) {
        h.style.display = dangAn ? 'none' : '';
      });
      an.textContent = dangAn ? 'Hiện báo cáo' : 'Ẩn báo cáo';
    });
    hop.appendChild(an);

    this.band.appendChild(hop);
  };

  Bang.prototype.nut = function (hop, chu, buoc) {
    var self = this;
    var b = this.doc.createElement('button');
    b.type = 'button';
    b.className = 'vf-ai-nut';
    b.textContent = chu;
    b.addEventListener('click', function () { self.nhay(buoc); });
    hop.appendChild(b);
    return b;
  };

  /** Checkbox "Đã xử lý": PHP không render được (Drupal nuốt <input>). */
  Bang.prototype.ganCheckbox = function () {
    var self = this;
    this.the.forEach(function (the) {
      var id = the.getAttribute('data-vf-ai-issue');
      var nhan = self.doc.createElement('label');
      nhan.className = 'vf-ai-the__xong';
      var o = self.doc.createElement('input');
      o.type = 'checkbox';
      o.checked = self.daXong.indexOf(id) !== -1;
      o.addEventListener('change', function () {
        var i = self.daXong.indexOf(id);
        if (o.checked && i === -1) { self.daXong.push(id); }
        if (!o.checked && i !== -1) { self.daXong.splice(i, 1); }
        ghiDaXong(self.cfg, self.daXong);
        self.veLai();
      });
      nhan.appendChild(o);
      nhan.appendChild(self.doc.createTextNode(' Đã xử lý'));
      the.appendChild(nhan);
      the.classList.toggle('vf-ai-the--xong', o.checked);
    });
  };

  Bang.prototype.datLoc = function (m) {
    var self = this;
    this.loc = m;
    ['tat_ca', 'block', 'fix', 'tip'].forEach(function (k) {
      if (self['chip_' + k]) {
        self['chip_' + k].setAttribute('aria-pressed', String(k === m));
      }
    });
    this.hien = 0;
    this.veLai();
  };

  Bang.prototype.dangHien = function () {
    var self = this;
    return this.the.filter(function (t) {
      if (self.daXong.indexOf(t.getAttribute('data-vf-ai-issue')) !== -1) {
        return false;
      }
      return self.loc === 'tat_ca' || t.getAttribute('data-sev') === self.loc;
    });
  };

  Bang.prototype.nhay = function (buoc) {
    var ds = this.dangHien();
    if (!ds.length) { return; }
    this.hien = (this.hien + buoc + ds.length) % ds.length;
    var the = ds[this.hien];

    this.the.forEach(function (t) { t.classList.remove('vf-ai-the--dang-chon'); });
    the.classList.add('vf-ai-the--dang-chon');

    var win = this.doc.defaultView;
    var y = the.getBoundingClientRect().top + win.pageYOffset - CHUA_CHO_BANG;
    win.scrollTo({ top: y, behavior: 'smooth' });
    this.veLai();
  };

  /**
   * Vẽ lại mọi thứ phụ thuộc tập thẻ đang hiển thị.
   *
   * Dòng "còn N lỗi chặn xuất bản" đếm ĐỘNG theo số thẻ `block` đang hiển
   * thị, không đếm tĩnh: đếm tĩnh sẽ sai ngay khi người dùng đổi bộ lọc hoặc
   * đánh dấu đã xử lý, mà đó là hai thao tác thường xuyên nhất.
   */
  Bang.prototype.veLai = function () {
    var self = this;
    var ds = this.dangHien();

    this.the.forEach(function (t) {
      var xong = self.daXong.indexOf(t.getAttribute('data-vf-ai-issue')) !== -1;
      var hopLoc = self.loc === 'tat_ca' || t.getAttribute('data-sev') === self.loc;
      t.style.display = hopLoc ? '' : 'none';
      t.classList.toggle('vf-ai-the--xong', xong);
    });

    // Hộp của field không còn thẻ nào hiển thị thì ẩn luôn cả hộp.
    this.doc.querySelectorAll('[data-vf-ai-hop]').forEach(function (hop) {
      var con = hop.querySelectorAll('[data-vf-ai-issue]');
      var conHien = Array.prototype.filter.call(con, function (t) {
        return t.style.display !== 'none';
      });
      hop.style.display = conHien.length ? '' : 'none';
    });

    if (this.viTri) {
      this.viTri.textContent = ds.length
        ? 'Lỗi ' + Math.min(this.hien + 1, ds.length) + '/' + ds.length
        : 'Không còn lỗi nào';
    }
    if (this.nutTruoc) {
      this.nutTruoc.disabled = this.nutSau.disabled = ds.length === 0;
    }

    this.vienField();
    this.canhBaoLuu(ds);
  };

  /** Viền field theo mức nghiêm trọng CAO NHẤT còn hiển thị trong field đó. */
  Bang.prototype.vienField = function () {
    var self = this;
    this.doc.querySelectorAll('[data-vf-ai-hop]').forEach(function (hop) {
      var field = hop.getAttribute('data-vf-ai-hop');
      var con = Array.prototype.filter.call(
        hop.querySelectorAll('[data-vf-ai-issue]'),
        function (t) { return t.style.display !== 'none'; }
      );
      var muc = con.some(function (t) { return t.getAttribute('data-sev') === 'block'; })
        ? 'block'
        : (con.length ? 'fix' : '');

      var boc = hop.closest('.js-form-wrapper, .field--type-text-with-summary')
        || hop.parentNode;
      if (!boc || !boc.classList) { return; }
      boc.classList.remove('vf-ai-field--block', 'vf-ai-field--fix');
      if (muc) { boc.classList.add('vf-ai-field--' + muc); }
      self.doc.body.setAttribute('data-vf-ai-field-' + field, muc || 'sach');
    });
  };

  /** Dòng cảnh báo cạnh nút Save. */
  Bang.prototype.canhBaoLuu = function (ds) {
    var chan = ds.filter(function (t) {
      return t.getAttribute('data-sev') === 'block';
    }).length;

    var o = this.doc.querySelector('.vf-ai-chan-luu');
    if (!o) {
      var neo = this.doc.querySelector('.form-actions, #edit-actions');
      if (!neo) { return; }
      o = this.doc.createElement('p');
      o.className = 'vf-ai-chan-luu';
      neo.parentNode.insertBefore(o, neo);
    }
    o.innerHTML = '';
    if (!chan) { o.style.display = 'none'; return; }
    o.style.display = '';
    o.appendChild(this.doc.createTextNode('Còn '));
    var m = this.doc.createElement('strong');
    m.textContent = chan + ' lỗi chặn xuất bản';
    o.appendChild(m);
    o.appendChild(this.doc.createTextNode(' — cân nhắc sửa trước khi chuyển sang Published.'));
  };

  Drupal.behaviors.vfAiReview = {
    attach: function (context) {
      var cfg = (drupalSettings && drupalSettings.vfAiReview) || null;
      if (!cfg) { return; }

      once('vf-ai-band', '[data-vf-ai-band]', context).forEach(function (band) {
        var b = new Bang(band, cfg);
        b.dungDieuKhien();
        b.ganCheckbox();
        b.veLai();
      });
    }
  };
})(Drupal, drupalSettings, once);
