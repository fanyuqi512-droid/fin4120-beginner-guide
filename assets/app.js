(function () {
  var KEY = "fin4120_beginner_progress_v1";

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || "{}"); }
    catch (e) { return {}; }
  }
  function save(data) {
    localStorage.setItem(KEY, JSON.stringify(data));
  }

  window.Fin4120 = {
    modules: ["m0","m1","m2","m3","m4","m5","m6","m7","m8"],
    titles: {
      m0: "导论：什么是固定收益",
      m1: "债券是什么",
      m2: "债券怎么定价",
      m3: "收益率怎么算",
      m4: "国债与准国债",
      m5: "公司债",
      m6: "国际债券",
      m7: "收益率曲线",
      m8: "零息曲线怎么来"
    },
    isDone: function (id) { return !!load()[id]; },
    setDone: function (id, val) {
      var d = load();
      if (val) d[id] = true; else delete d[id];
      save(d);
      this.refreshUI();
    },
    countDone: function () {
      var d = load(), n = 0;
      this.modules.forEach(function (m) { if (d[m]) n++; });
      return n;
    },
    refreshUI: function () {
      var total = this.modules.length;
      var done = this.countDone();
      var pct = Math.round((done / total) * 100);
      document.querySelectorAll("[data-progress-bar]").forEach(function (el) {
        el.style.width = pct + "%";
      });
      document.querySelectorAll("[data-progress-text]").forEach(function (el) {
        el.textContent = done + " / " + total + " 模块已完成（" + pct + "%）";
      });
      document.querySelectorAll("[data-mod-card]").forEach(function (el) {
        var id = el.getAttribute("data-mod-card");
        el.classList.toggle("done", !!load()[id]);
      });
      document.querySelectorAll("[data-done-mark]").forEach(function (el) {
        var id = el.getAttribute("data-done-mark");
        el.textContent = load()[id] ? "✓ 已完成" : "";
      });
      var box = document.querySelector("[data-module-check]");
      if (box) {
        var id = box.getAttribute("data-module-check");
        box.checked = !!load()[id];
      }
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".q button[data-reveal]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var q = btn.closest(".q");
        q.classList.toggle("open");
        btn.textContent = q.classList.contains("open") ? "收起答案" : "显示答案";
      });
    });

    var box = document.querySelector("[data-module-check]");
    if (box) {
      box.addEventListener("change", function () {
        Fin4120.setDone(box.getAttribute("data-module-check"), box.checked);
      });
    }

    Fin4120.refreshUI();
  });
})();
