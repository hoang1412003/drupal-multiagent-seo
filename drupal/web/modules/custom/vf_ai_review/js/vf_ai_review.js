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
  "use strict";

  var MUC = { block: "Chặn", fix: "Cần sửa", tip: "Gợi ý" };

  // Khoảng cách chừa ra khi cuộn tới lỗi: băng sticky + toolbar + chỗ thở.
  var CHUA_CHO_BANG = 160;

  /**
   * Đồng bộ chiều cao thanh admin toolbar vào biến CSS của băng.
   */
  function dongBoOffset(doc) {
    var tren = 0;
    try {
      if (Drupal.displace && typeof Drupal.displace.offsets === "object") {
        tren = Drupal.displace.offsets.top || 0;
      }
    } catch (e) {
      /* không có toolbar: giữ 0 */
    }
    doc.documentElement.style.setProperty(
      "--drupal-displace-offset-top",
      tren + "px",
    );
    return tren;
  }

  /**
   * GHI_CHU_KHOA: khoá PHẢI gồm content_hash, không chỉ nid.
   */
  function khoaLuu(cfg) {
    return "vf-ai:" + cfg.nid + ":" + (cfg.hash || "chua-cham");
  }

  function docDaXong(cfg) {
    try {
      return JSON.parse(window.localStorage.getItem(khoaLuu(cfg)) || "[]");
    } catch (e) {
      return [];
    }
  }

  function ghiDaXong(cfg, ds) {
    try {
      window.localStorage.setItem(khoaLuu(cfg), JSON.stringify(ds));
    } catch (e) {
      /* hết dung lượng hoặc bị chặn: bỏ qua */
    }
  }

  function Bang(band, cfg) {
    this.band = band;
    this.cfg = cfg;
    this.doc = band.ownerDocument;
    this.the = Array.prototype.slice.call(
      this.doc.querySelectorAll("[data-vf-ai-issue]"),
    );
    this.loc = "tat_ca";
    this.hien = 0;
    this.daXong = docDaXong(cfg);
  }

  Bang.prototype.dungDieuKhien = function () {
    var self = this;
    var st = this.cfg.trangThai;

    // 1. Chip lọc mức - CHỈ hiện ở trạng thái 'co_loi'
    var containerChips = this.band.querySelector("[data-vf-ai-chips]");
    if (containerChips && st === "co_loi" && this.the.length) {
      // Nút 'Tất cả'
      var bAll = this.doc.createElement("button");
      bAll.type = "button";
      bAll.className = "vf-ai-chip";
      bAll.textContent = "Tất cả";
      bAll.setAttribute("aria-pressed", "true");
      bAll.addEventListener("click", function () {
        self.datLoc("tat_ca");
      });
      this.chip_tat_ca = bAll;
      containerChips.appendChild(bAll);

      // Các nút 'Chặn', 'Cần sửa', 'Gợi ý' kèm số đếm
      ["block", "fix", "tip"].forEach(function (m) {
        var b = self.doc.createElement("button");
        b.type = "button";
        b.className = "vf-ai-chip";
        b.innerHTML = MUC[m] + ' <span data-n="' + m + '">0</span>';
        b.setAttribute("aria-pressed", "false");
        b.addEventListener("click", function () {
          self.datLoc(m);
        });
        self["chip_" + m] = b;
        containerChips.appendChild(b);
      });
    }

    // 2. Điều khiển bên phải:
    var containerNav = this.band.querySelector("[data-vf-ai-nav]");
    if (!containerNav) {
      return;
    }

    // Xoá trắng nội dung cũ trong containerNav để JS dựng chuẩn theo trạng thái
    containerNav.innerHTML = "";

    if (st === "chua_cham") {
      var nutChamNgay = this.doc.createElement("button");
      nutChamNgay.type = "button";
      nutChamNgay.className = "vf-ai-nut-rescore";
      nutChamNgay.textContent = "Chấm ngay";
      nutChamNgay.addEventListener("click", function () {
        var triggerRescore = self.doc.querySelector("[data-vf-ai-rescore-url]");
        if (triggerRescore) {
          triggerRescore.click();
        } else {
          var selectState =
            self.doc.querySelector('[name="moderation_state[0][state]"]') ||
            self.doc.querySelector('[name="moderation_state[0][value]"]');
          if (selectState) {
            selectState.value = "needs_review";
          }
          var saveBtn = self.doc.querySelector("#edit-submit");
          if (saveBtn) {
            saveBtn.click();
          }
        }
      });
      containerNav.appendChild(nutChamNgay);
      return;
    }

    if (st === "stale") {
      var nutChamLaiMoi = this.doc.createElement("button");
      nutChamLaiMoi.type = "button";
      nutChamLaiMoi.className = "vf-ai-nut-rescore vf-ai-nut-rescore--primary";
      nutChamLaiMoi.textContent = "Chấm lại bản mới";
      nutChamLaiMoi.addEventListener("click", function () {
        var triggerRescore = self.doc.querySelector("[data-vf-ai-rescore-url]");
        if (triggerRescore) {
          triggerRescore.click();
        } else {
          window.location.reload();
        }
      });
      containerNav.appendChild(nutChamLaiMoi);
      return;
    }

    if (st === "dat") {
      var txtDat = this.doc.createElement("span");
      txtDat.style.fontSize = "13px";
      txtDat.style.color = "#3f7a52";
      txtDat.style.fontWeight = "600";
      txtDat.textContent = "Có thể chuyển sang Published.";
      containerNav.appendChild(txtDat);
      return;
    }

    if (st === "dang_cham") {
      return;
    }

    if (st === "thieu") {
      var nutRescoreThieu = this.doc.createElement("button");
      nutRescoreThieu.type = "button";
      nutRescoreThieu.className = "vf-ai-nut-rescore";
      nutRescoreThieu.textContent = "Chấm lại";
      nutRescoreThieu.addEventListener("click", function () {
        var triggerRescore = self.doc.querySelector("[data-vf-ai-rescore-url]");
        if (triggerRescore) {
          triggerRescore.click();
        } else {
          window.location.reload();
        }
      });
      containerNav.appendChild(nutRescoreThieu);

      var linkAdmin = this.doc.createElement("a");
      linkAdmin.href = "#";
      linkAdmin.className = "vf-ai-link-toggle";
      linkAdmin.textContent = "Báo cho admin";
      containerNav.appendChild(linkAdmin);
      return;
    }

    // Với 'veto' và 'co_loi':
    if (this.the.length) {
      this.viTri = this.doc.createElement("span");
      this.viTri.className = "vf-ai-band__pos";
      containerNav.appendChild(this.viTri);

      if (st === "co_loi") {
        this.nutTruoc = this.nut(containerNav, "↑", "Lỗi trước", -1);
        this.nutSau = this.nut(containerNav, "↓", "Lỗi tiếp theo", 1);
      }
    }

    var nutRescore = this.doc.createElement("button");
    nutRescore.type = "button";
    nutRescore.className = "vf-ai-nut-rescore";
    nutRescore.textContent = "Chấm lại";
    nutRescore.addEventListener("click", function () {
      var triggerRescore = self.doc.querySelector("[data-vf-ai-rescore-url]");
      if (triggerRescore) {
        triggerRescore.click();
      } else {
        window.location.reload();
      }
    });
    containerNav.appendChild(nutRescore);

    if (st === "co_loi") {
      var linkToggle = this.doc.createElement("a");
      linkToggle.href = "#";
      linkToggle.className = "vf-ai-link-toggle";
      linkToggle.textContent = "Ẩn báo cáo";
      linkToggle.addEventListener("click", function (e) {
        e.preventDefault();
        var dangAn = linkToggle.textContent.indexOf("Ẩn") === 0;
        self.doc.querySelectorAll("[data-vf-ai-hop]").forEach(function (h) {
          h.style.display = dangAn ? "none" : "";
        });
        linkToggle.textContent = dangAn ? "Hiện báo cáo" : "Ẩn báo cáo";
      });
      containerNav.appendChild(linkToggle);
    }
  };

  Bang.prototype.nut = function (container, icon, title, buoc) {
    var self = this;
    var b = this.doc.createElement("button");
    b.type = "button";
    b.className = "vf-ai-nut-nav";
    b.textContent = icon;
    b.title = title;
    b.addEventListener("click", function () {
      self.nhay(buoc);
    });
    container.appendChild(b);
    return b;
  };

  /** Checkbox "Đã xử lý" & Link "Không đồng ý" */
  Bang.prototype.ganCheckbox = function () {
    var self = this;
    this.the.forEach(function (the) {
      var id = the.getAttribute("data-vf-ai-issue");
      var actionBox = the.querySelector("[data-vf-ai-actions]") || the;

      var nhan = self.doc.createElement("label");
      nhan.className = "vf-ai-the__xong";
      var o = self.doc.createElement("input");
      o.type = "checkbox";
      o.checked = self.daXong.indexOf(id) !== -1;
      o.addEventListener("change", function () {
        var i = self.daXong.indexOf(id);
        if (o.checked && i === -1) {
          self.daXong.push(id);
        }
        if (!o.checked && i !== -1) {
          self.daXong.splice(i, 1);
        }
        ghiDaXong(self.cfg, self.daXong);
        self.veLai();
      });
      nhan.appendChild(o);
      nhan.appendChild(self.doc.createTextNode(" Đã xử lý"));
      actionBox.appendChild(nhan);

      var linkDisagree = self.doc.createElement("a");
      linkDisagree.href = "#";
      linkDisagree.className = "vf-ai-link-disagree";
      linkDisagree.textContent = "Không đồng ý";
      linkDisagree.addEventListener("click", function (e) {
        e.preventDefault();
      });
      actionBox.appendChild(linkDisagree);

      the.classList.toggle("vf-ai-the--xong", o.checked);
    });
  };

  /** Gắn sự kiện Thu gọn / Mở rộng cho từng hộp field. */
  Bang.prototype.ganThuGon = function () {
    var self = this;
    this.doc.querySelectorAll("[data-vf-ai-collapse]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var field = btn.getAttribute("data-vf-ai-collapse");
        var cards = self.doc.querySelector(
          '[data-vf-ai-cards="' + field + '"]',
        );
        if (!cards) {
          return;
        }
        var an = cards.style.display === "none";
        cards.style.display = an ? "" : "none";
        btn.textContent = an ? "Thu gọn ▴" : "Mở rộng ▾";
      });
    });
  };

  /** Nút Auto-Fix ("Sửa thành 'VF 8'") */
  Bang.prototype.ganAutoFix = function () {
    var self = this;
    this.doc.querySelectorAll("[data-vf-ai-autofix]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var targetVal = btn.getAttribute("data-vf-ai-autofix");
        var titleInput = self.doc.querySelector('[name="title[0][value]"]');
        if (titleInput && targetVal) {
          titleInput.value = titleInput.value.replace(/VF8/g, targetVal);
        }
        var card = btn.closest("[data-vf-ai-issue]");
        if (card) {
          var ex = card.querySelector(".vf-ai-the__trich");
          if (ex) {
            ex.textContent = ex.textContent.replace(/VF8/g, targetVal);
          }
          var chk = card.querySelector('input[type="checkbox"]');
          if (chk && !chk.checked) {
            chk.checked = true;
            chk.dispatchEvent(new Event("change"));
          }
        }
        btn.textContent = "Đã sửa";
        btn.disabled = true;
      });
    });
  };

  Bang.prototype.datLoc = function (m) {
    var self = this;
    this.loc = m;
    ["tat_ca", "block", "fix", "tip"].forEach(function (k) {
      if (self["chip_" + k]) {
        self["chip_" + k].setAttribute("aria-pressed", String(k === m));
      }
    });
    this.hien = 0;
    this.veLai();
  };

  Bang.prototype.dangHien = function () {
    var self = this;
    return this.the.filter(function (t) {
      if (self.daXong.indexOf(t.getAttribute("data-vf-ai-issue")) !== -1) {
        return false;
      }
      return self.loc === "tat_ca" || t.getAttribute("data-sev") === self.loc;
    });
  };

  Bang.prototype.nhay = function (buoc) {
    var ds = this.dangHien();
    if (!ds.length) {
      return;
    }
    this.hien = (this.hien + buoc + ds.length) % ds.length;
    var the = ds[this.hien];

    this.the.forEach(function (t) {
      t.classList.remove("vf-ai-the--dang-chon");
    });
    the.classList.add("vf-ai-the--dang-chon");

    var win = this.doc.defaultView;
    var chua = CHUA_CHO_BANG + dongBoOffset(this.doc);
    var y = the.getBoundingClientRect().top + win.pageYOffset - chua;
    win.scrollTo({ top: y, behavior: "smooth" });

    the.classList.remove("vf-ai-flash");
    void the.offsetWidth;
    the.classList.add("vf-ai-flash");

    this.veLai();
  };

  /**
   * Vẽ lại mọi thứ phụ thuộc tập thẻ đang hiển thị:
   * - Số đếm từng mức trên chip lọc
   * - Tổng số vấn đề trên băng sticky
   * - Tiêu đề hộp của từng field
   * - Viền màu của từng field
   * - Dòng cảnh báo cạnh nút Save
   */
  Bang.prototype.veLai = function () {
    var self = this;
    var ds = this.dangHien();

    this.the.forEach(function (t) {
      var xong = self.daXong.indexOf(t.getAttribute("data-vf-ai-issue")) !== -1;
      var hopLoc =
        self.loc === "tat_ca" || t.getAttribute("data-sev") === self.loc;
      t.style.display = hopLoc ? "" : "none";
      t.classList.toggle("vf-ai-the--xong", xong);
    });

    // 1. Đếm số lỗi chưa xử lý theo từng mức
    var demMuc = { block: 0, fix: 0, tip: 0 };
    var truongConLoi = new Set();
    this.the.forEach(function (t) {
      var id = t.getAttribute("data-vf-ai-issue");
      var sev = t.getAttribute("data-sev");
      var field = t.getAttribute("data-field");
      if (self.daXong.indexOf(id) === -1) {
        if (demMuc[sev] !== undefined) {
          demMuc[sev] += 1;
        }
        if (field) {
          truongConLoi.add(field);
        }
      }
    });

    var tongChuaXuLy = demMuc.block + demMuc.fix + demMuc.tip;

    // Cập nhật số đếm trên các chip
    ["block", "fix", "tip"].forEach(function (m) {
      if (self["chip_" + m]) {
        var elN = self["chip_" + m].querySelector('[data-n="' + m + '"]');
        if (elN) {
          elN.textContent = String(demMuc[m]);
        }
      }
    });

    // Cập nhật số vấn đề trên băng sticky
    var elDemSo = this.band.querySelector(".vf-ai-band__dem-so");
    var elDemTruong = this.band.querySelector(".vf-ai-band__dem-truong");
    if (elDemSo) {
      elDemSo.textContent =
        tongChuaXuLy > 0 ? tongChuaXuLy + " vấn đề" : "Không còn vấn đề";
    }
    if (elDemTruong) {
      elDemTruong.textContent =
        tongChuaXuLy > 0
          ? "trên " + truongConLoi.size + " trường"
          : "tất cả đã xử lý";
    }

    // Badge trạng thái trên băng
    var badge = this.band.querySelector(".vf-ai-band__badge");
    if (badge && this.cfg.trangThai === "co_loi") {
      if (tongChuaXuLy === 0 && this.the.length > 0) {
        badge.style.background = "#e3f3e6";
        badge.style.color = "#265c35";
        badge.innerHTML =
          '<span class="vf-ai-band__dot" style="background:#3f7a52"></span>Đã xử lý hết';
      } else {
        badge.style.background = "";
        badge.style.color = "";
        badge.innerHTML = '<span class="vf-ai-band__dot"></span>Cần sửa';
      }
    }

    // 2. Cập nhật tiêu đề hộp từng field
    this.doc.querySelectorAll("[data-vf-ai-hop]").forEach(function (hop) {
      var field = hop.getAttribute("data-vf-ai-hop");
      var con = hop.querySelectorAll("[data-vf-ai-issue]");
      var conChuaXong = Array.prototype.filter.call(con, function (t) {
        return self.daXong.indexOf(t.getAttribute("data-vf-ai-issue")) === -1;
      });

      var head = hop.querySelector("[data-vf-ai-hop-head]");
      if (head) {
        head.innerHTML =
          conChuaXong.length > 0
            ? "AI phát hiện <strong>" +
              conChuaXong.length +
              "</strong> vấn đề ở trường này"
            : "Đã xử lý hết vấn đề ở trường này";
      }
    });

    // 3. Cập nhật vị trí lỗi
    if (this.viTri) {
      this.viTri.textContent = ds.length
        ? "Lỗi " + Math.min(this.hien + 1, ds.length) + "/" + ds.length
        : "Hết lỗi";
    }
    if (this.nutTruoc && this.nutSau) {
      this.nutTruoc.disabled = this.nutSau.disabled = ds.length === 0;
    }

    this.vienField();
    this.canhBaoLuu(demMuc.block);
  };

  /** Ô nhập THẬT của một field trong báo cáo */
  Bang.prototype.oNhap = function (field) {
    var ten = (this.cfg.fieldMap || {})[field];
    if (!ten) {
      return [];
    }

    if (field === "summary") {
      var sum =
        this.doc.querySelector('[name="' + ten + '[0][summary]"]') ||
        this.doc.querySelector('[name$="[summary]"]') ||
        this.doc.querySelector(".js-text-summary");
      if (sum) {
        return [sum];
      }
    }

    var o =
      this.doc.querySelector('[name="' + ten + '[0][value]"]') ||
      this.doc.querySelector('[name^="' + ten + '["]');
    if (!o) {
      return [];
    }

    var ke = o.nextElementSibling;
    var khung =
      ke && ke.classList && ke.classList.contains("ck-editor")
        ? ke
        : o.parentNode
          ? o.parentNode.querySelector(".ck.ck-editor")
          : null;
    return khung ? [o, khung] : [o];
  };

  Bang.prototype.theoDoiCkeditor = function () {
    var self = this;
    var win = this.doc.defaultView;
    if (!win.MutationObserver) {
      return;
    }
    if (this.doc.querySelector(".ck.ck-editor")) {
      return;
    }

    var quan_sat = new win.MutationObserver(function () {
      if (self.doc.querySelector(".ck.ck-editor")) {
        quan_sat.disconnect();
        self.vienField();
      }
    });
    quan_sat.observe(this.doc.body, { childList: true, subtree: true });
    win.setTimeout(function () {
      quan_sat.disconnect();
    }, 10000);
  };

  /** Viền ô nhập theo mức nghiêm trọng CAO NHẤT còn chưa xử lý của field đó */
  Bang.prototype.vienField = function () {
    var self = this;
    var mucCua = {};

    if (this.cfg.trangThai === "dat") {
      Object.keys(self.cfg.fieldMap || {}).forEach(function (field) {
        self.oNhap(field).forEach(function (o) {
          o.classList.remove("vf-ai-o--block", "vf-ai-o--fix");
          o.classList.add("vf-ai-o--dat");
        });
      });
      return;
    }

    if (
      this.cfg.trangThai === "chua_cham" ||
      this.cfg.trangThai === "dang_cham"
    ) {
      Object.keys(self.cfg.fieldMap || {}).forEach(function (field) {
        self.oNhap(field).forEach(function (o) {
          o.classList.remove("vf-ai-o--block", "vf-ai-o--fix", "vf-ai-o--dat");
        });
      });
      return;
    }

    this.doc.querySelectorAll("[data-vf-ai-hop]").forEach(function (hop) {
      var field = hop.getAttribute("data-vf-ai-hop");
      var con = Array.prototype.filter.call(
        hop.querySelectorAll("[data-vf-ai-issue]"),
        function (t) {
          return self.daXong.indexOf(t.getAttribute("data-vf-ai-issue")) === -1;
        },
      );
      var muc = con.some(function (t) {
        return t.getAttribute("data-sev") === "block";
      })
        ? "block"
        : con.length
          ? "fix"
          : "";
      if (!field) {
        return;
      }
      if (muc === "block" || !mucCua[field]) {
        mucCua[field] = muc;
      }
    });

    Object.keys(self.cfg.fieldMap || {}).forEach(function (field) {
      self.oNhap(field).forEach(function (o) {
        o.classList.remove("vf-ai-o--block", "vf-ai-o--fix", "vf-ai-o--dat");
        if (mucCua[field]) {
          o.classList.add("vf-ai-o--" + mucCua[field]);
        }
      });
    });
  };

  /** Dòng cảnh báo cạnh nút Save */
  Bang.prototype.canhBaoLuu = function (soLoiBlock) {
    var actions = this.doc.querySelector(".form-actions, #edit-actions");
    if (!actions) {
      return;
    }

    var o = this.doc.querySelector(".vf-ai-chan-luu");
    if (!o) {
      o = this.doc.createElement("span");
      o.className = "vf-ai-chan-luu";
      actions.appendChild(o);
    } else if (o.parentNode !== actions || actions.lastElementChild !== o) {
      actions.appendChild(o);
    }

    var st = this.cfg.trangThai;
    if (st === "chua_cham") {
      o.innerHTML =
        '<span style="color:#55565b">Chưa có kết quả chấm cho bài này.</span>';
      o.className = "vf-ai-chan-luu";
      return;
    }
    if (st === "dang_cham") {
      o.innerHTML = '<span style="color:#55565b">Đang chờ kết quả chấm…</span>';
      o.className = "vf-ai-chan-luu";
      return;
    }

    if (soLoiBlock > 0) {
      o.innerHTML =
        "Còn <strong>" +
        soLoiBlock +
        " lỗi chặn xuất bản</strong> — không thể chuyển sang Published." +
        (st === "stale"
          ? ' <span style="color:#8b8c92">(theo bản cũ)</span>'
          : "");
      o.className = "vf-ai-chan-luu";
    } else {
      o.innerHTML = "Không còn lỗi chặn — có thể chuyển sang Published.";
      o.className = "vf-ai-chan-luu vf-ai-chan-luu--ok";
    }
  };

  Drupal.behaviors.vfAiReview = {
    attach: function (context) {
      var cfg = (drupalSettings && drupalSettings.vfAiReview) || null;
      if (!cfg) {
        return;
      }

      // Cập nhật chiều rộng cho các thanh progress bar của Card Điểm theo agent
      var bars = context.querySelectorAll
        ? context.querySelectorAll(".vf-ai-agent-card__bar-fill[data-pt]")
        : [];
      Array.prototype.forEach.call(bars, function (fill) {
        var pt = fill.getAttribute("data-pt");
        if (pt) {
          fill.style.width = pt + "%";
        }
      });

      once("vf-ai-band", "[data-vf-ai-band]", context).forEach(function (band) {
        // Di chuyển băng sticky ra ngoài layout-container và đặt NGAY SAU header.content-header
        // để nó dính sát dưới đáy thanh tab View/Edit và có cùng chiều dài 100% full-width với header
        var doc = band.ownerDocument;
        var header =
          doc.querySelector("header.content-header") ||
          doc.querySelector("header.page-header") ||
          doc.querySelector(".tabs-wrapper");

        if (
          header &&
          header.parentNode &&
          band.previousElementSibling !== header
        ) {
          header.parentNode.insertBefore(band, header.nextSibling);
        } else {
          var form = band.closest("form.node-form");
          var layout = form ? form.querySelector(".layout-node-form") : null;
          if (form && layout && band.nextElementSibling !== layout) {
            form.insertBefore(band, layout);
          } else if (form && form.parentNode && !layout) {
            form.parentNode.insertBefore(band, form);
          }
        }

        var b = new Bang(band, cfg);
        b.dungDieuKhien();
        b.ganCheckbox();
        b.ganThuGon();
        b.ganAutoFix();
        b.veLai();

        b.theoDoiCkeditor();
        dongBoOffset(b.doc);
        b.doc.defaultView.addEventListener(
          "drupalViewportOffsetChange",
          function () {
            dongBoOffset(b.doc);
          },
        );
      });
    },
  };
})(Drupal, drupalSettings, once);
