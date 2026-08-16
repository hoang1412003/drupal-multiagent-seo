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

  // Khoảng cách chừa ra khi cuộn tới lỗi: băng sticky + toolbar + chỗ thở.
  var CHUA_CHO_BANG = 160;

  /**
   * Đồng bộ chiều cao thanh admin toolbar vào biến CSS của băng.
   *
   * Không có bước này thì băng dính ở top:0 nhưng nằm SAU LƯNG toolbar và
   * coi như biến mất khi cuộn - đúng lúc người dùng cần nó nhất.
   *
   * Drupal 10 mới tự đặt --drupal-displace-offset-top; bản cũ hơn thì không,
   * nên vẫn phải tự đặt từ Drupal.displace. Cả hai đường đều bọc phòng thủ:
   * không có displace thì rơi về 0 và băng vẫn dùng được, chỉ hơi khuất.
   */
  function dongBoOffset(doc) {
    var tren = 0;
    try {
      if (Drupal.displace && typeof Drupal.displace.offsets === 'object') {
        tren = Drupal.displace.offsets.top || 0;
      }
    }
    catch (e) { /* không có toolbar: giữ 0 */ }
    doc.documentElement.style.setProperty(
      '--drupal-displace-offset-top', tren + 'px'
    );
    return tren;
  }

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
    // Trừ cả toolbar lẫn băng, nếu không lỗi được cuộn tới lại nằm ngay
    // dưới hai thanh đó và người dùng không thấy gì.
    var chua = CHUA_CHO_BANG + dongBoOffset(this.doc);
    var y = the.getBoundingClientRect().top + win.pageYOffset - chua;
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

  /**
   * Ô nhập THẬT của một field trong báo cáo.
   *
   * Nhắm bằng thuộc tính `name` do Drupal sinh (`title[0][value]`,
   * `field_meta_description[0][value]`...), lấy từ map PHP truyền sang.
   *
   * KHÔNG dùng closest() để đoán tổ tiên: hộp lỗi được chèn qua '#suffix'
   * nên nó không nằm trong wrapper của field, closest() leo lên tận
   * container chứa MỌI field và viền lan sang những field không có lỗi -
   * tức UI nói sai sự thật. Đã thấy trên ảnh chụp thật 2026-08-16.
   */
  Bang.prototype.oNhap = function (field) {
    var ten = (this.cfg.fieldMap || {})[field];
    if (!ten) { return []; }

    // PHẢI nhắm đúng `[0][value]` trước.
    //
    // Field Body có BA phần tử cùng tiền tố: body[0][summary],
    // body[0][value], body[0][format] - và `summary` đứng TRƯỚC trong DOM
    // (đã kiểm trên form thật). Nên `[name^="body["]` trả về textarea
    // summary, thứ nằm trong vùng "Edit summary" đang thu gọn và KHÔNG phải
    // nguồn của CKEditor. Đó là lý do khung Body không bao giờ được tô viền
    // dù Title thì được (ảnh chụp 2026-08-16).
    //
    // Dự phòng `[name^=...]` cho field không có `[0][value]`, ví dụ
    // url_alias là `path[0][alias]`.
    var o = this.doc.querySelector('[name="' + ten + '[0][value]"]')
      || this.doc.querySelector('[name^="' + ten + '["]');
    if (!o) { return []; }
    // CKEditor giấu textarea gốc và vẽ khung riêng - phải tô đúng khung đó,
    // tô textarea ẩn thì không ai nhìn thấy gì.
    //
    // Khung này có thể CHƯA TỒN TẠI lúc behaviors chạy: CKEditor 5 khởi tạo
    // bất đồng bộ sau khi trang tải. Đó là lý do lần đầu Body không có viền
    // dù Title thì có (thấy trên ảnh chụp 2026-08-16). `theoDoiCkeditor()`
    // gọi lại hàm này khi khung xuất hiện.
    // `core/modules/ckeditor5/js/ckeditor5.js:637` cho biết khung CKEditor
    // chính là `sourceElement.nextElementSibling`. Dùng đúng quan hệ đó thay
    // vì querySelector trong parentNode: chắc chắn hơn và không thể trúng
    // khung của một editor khác trên cùng form.
    var ke = o.nextElementSibling;
    var khung = (ke && ke.classList && ke.classList.contains('ck-editor'))
      ? ke
      : (o.parentNode ? o.parentNode.querySelector('.ck.ck-editor') : null);
    return khung ? [o, khung] : [o];
  };

  /**
   * Tô lại viền khi CKEditor dựng xong khung của nó.
   *
   * Một lần duy nhất rồi ngắt: không cần theo dõi mãi, và để observer sống
   * suốt vòng đời trang là rò rỉ không có lý do.
   */
  Bang.prototype.theoDoiCkeditor = function () {
    var self = this;
    var win = this.doc.defaultView;
    if (!win.MutationObserver) { return; }
    if (this.doc.querySelector('.ck.ck-editor')) { return; }

    var quan_sat = new win.MutationObserver(function () {
      if (self.doc.querySelector('.ck.ck-editor')) {
        quan_sat.disconnect();
        self.vienField();
      }
    });
    quan_sat.observe(this.doc.body, { childList: true, subtree: true });
    // Lưới an toàn: CKEditor không bao giờ dựng (lỗi JS của nó, hoặc field
    // dùng text format khác) thì cũng phải ngắt observer.
    win.setTimeout(function () { quan_sat.disconnect(); }, 10000);
  };

  /** Viền ô nhập theo mức nghiêm trọng CAO NHẤT còn hiển thị của field đó. */
  Bang.prototype.vienField = function () {
    var self = this;

    // Gom theo field trước: `summary` và `body` cùng trỏ về một ô nhập, nên
    // phải lấy mức cao nhất của CẢ HAI rồi mới tô, không tô đè lần lượt.
    var mucCua = {};
    this.doc.querySelectorAll('[data-vf-ai-hop]').forEach(function (hop) {
      var field = hop.getAttribute('data-vf-ai-hop');
      var con = Array.prototype.filter.call(
        hop.querySelectorAll('[data-vf-ai-issue]'),
        function (t) { return t.style.display !== 'none'; }
      );
      var muc = con.some(function (t) { return t.getAttribute('data-sev') === 'block'; })
        ? 'block'
        : (con.length ? 'fix' : '');
      var ten = (self.cfg.fieldMap || {})[field];
      if (!ten) { return; }
      if (muc === 'block' || !mucCua[ten]) { mucCua[ten] = muc; }
    });

    Object.keys(self.cfg.fieldMap || {}).forEach(function (field) {
      var ten = self.cfg.fieldMap[field];
      self.oNhap(field).forEach(function (o) {
        o.classList.remove('vf-ai-o--block', 'vf-ai-o--fix');
        if (mucCua[ten]) { o.classList.add('vf-ai-o--' + mucCua[ten]); }
      });
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

        b.theoDoiCkeditor();
        dongBoOffset(b.doc);
        // Toolbar đổi chiều cao khi thu/mở hoặc khi đổi kích thước cửa sổ.
        // Không nghe sự kiện này thì băng lệch chỗ ngay lần đầu người dùng
        // thu thanh toolbar lại.
        b.doc.defaultView.addEventListener(
          'drupalViewportOffsetChange', function () { dongBoOffset(b.doc); }
        );
      });
    }
  };
})(Drupal, drupalSettings, once);
