/**
 * PDF.js dual-pane viewer: left = lecture PDF page, right = synced 解析.
 * Requires: pdf.js (global pdfjsLib), Fin4120Slides (idb-slides.js).
 */
(function (global) {
  "use strict";

  var PDFJS_CDN = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.4.168/build";
  var notesCache = {};
  var state = {
    moduleId: null,
    pdfDoc: null,
    pageNum: 1,
    pageCount: 0,
    scale: 1.15,
    rendering: false,
    pendingPage: null,
    mode: "pdf", // pdf | text
    notes: null,
  };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }
  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function ensurePdfJs() {
    if (global.pdfjsLib) {
      pdfjsLib.GlobalWorkerOptions.workerSrc =
        PDFJS_CDN + "/pdf.worker.min.mjs";
      return Promise.resolve(pdfjsLib);
    }
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.type = "module";
      // Fallback: load classic build via script tag of UMD if available
      s.src = PDFJS_CDN + "/pdf.min.mjs";
      // pdf.js v4 is ESM-only on jsdelivr; use legacy build instead
      s.onerror = function () {
        reject(new Error("pdf.js module load failed"));
      };
      // Prefer UMD legacy
      reject(new Error("use ensurePdfJsUmd"));
    });
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      if (document.querySelector('script[src="' + src + '"]')) {
        resolve();
        return;
      }
      var s = document.createElement("script");
      s.src = src;
      s.onload = function () {
        resolve();
      };
      s.onerror = function () {
        reject(new Error("Failed to load " + src));
      };
      document.head.appendChild(s);
    });
  }

  function ensurePdfJsUmd() {
    if (global.pdfjsLib) {
      global.pdfjsLib.GlobalWorkerOptions.workerSrc =
        "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js";
      return Promise.resolve(global.pdfjsLib);
    }
    return loadScript(
      "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js"
    ).then(function () {
      global.pdfjsLib.GlobalWorkerOptions.workerSrc =
        "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js";
      return global.pdfjsLib;
    });
  }

  function notesUrl(moduleId) {
    var base = document.body.getAttribute("data-assets-base") || "../assets";
    return base + "/notes/" + moduleId + ".json";
  }

  function loadNotes(moduleId) {
    if (notesCache[moduleId]) return Promise.resolve(notesCache[moduleId]);
    return fetch(notesUrl(moduleId))
      .then(function (r) {
        if (!r.ok) throw new Error("notes " + r.status);
        return r.json();
      })
      .then(function (j) {
        notesCache[moduleId] = j;
        return j;
      });
  }

  function pageByNum(notes, pageNum) {
    if (!notes || !notes.pages) return null;
    for (var i = 0; i < notes.pages.length; i++) {
      if (notes.pages[i].page === pageNum) return notes.pages[i];
    }
    return null;
  }

  function nearestRich(notes, pageNum) {
    if (!notes || !notes.pages) return null;
    var best = null;
    var bestDist = 1e9;
    for (var i = 0; i < notes.pages.length; i++) {
      var p = notes.pages[i];
      if (p.thin) continue;
      var d = Math.abs(p.page - pageNum);
      if (d < bestDist) {
        bestDist = d;
        best = p;
      }
    }
    return best;
  }

  function findNote(notes, pageNum) {
    var exact = pageByNum(notes, pageNum);
    var nearest = nearestRich(notes, pageNum);
    return { exact: exact, nearest: nearest };
  }

  function renderNote(pageNum) {
    var host = $("#page-note");
    if (!host) return;
    var found = findNote(state.notes, pageNum);
    if (!found || (!found.exact && !found.nearest)) {
      host.innerHTML =
        '<p class="muted">本页暂无解析。可切换「文字摘录」对照，或稍后再看。</p>';
      return;
    }
    var e = found.exact;
    var useNearest = e && e.thin && found.nearest && found.nearest.page !== e.page;
    if (e && !useNearest) {
      host.innerHTML =
        '<div class="note-page-label">第 ' +
        pageNum +
        " 页 · " +
        escapeHtml(e.title || "") +
        "</div>" +
        (e.explainHtml || "<p>暂无解析。</p>");
    } else if (useNearest || (!e && found.nearest)) {
      var n = found.nearest;
      var banner =
        '<div class="note-fallback-banner">本页以图/表为主，对照课件；以下为最近相关页（第 ' +
        n.page +
        " 页）解析。</div>";
      host.innerHTML =
        banner +
        '<div class="note-page-label">近邻 · ' +
        escapeHtml(n.title || "") +
        "</div>" +
        (n.explainHtml || "");
    } else {
      host.innerHTML =
        '<p class="muted">本页暂无解析。</p>';
    }
    if (global.renderMathInElement) {
      try {
        global.renderMathInElement(host, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "$", right: "$", display: false },
          ],
          throwOnError: false,
        });
      } catch (err) {}
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function updateChrome() {
    var label = $("#pdf-page-label");
    if (label) {
      label.textContent =
        (state.pageCount ? state.pageNum + " / " + state.pageCount : "—");
    }
    var prev = $("#pdf-prev");
    var next = $("#pdf-next");
    if (prev) prev.disabled = state.pageNum <= 1;
    if (next) next.disabled = state.pageNum >= state.pageCount;
    var zoomLabel = $("#pdf-zoom-label");
    if (zoomLabel) zoomLabel.textContent = Math.round(state.scale * 100) + "%";
  }

  function renderPage(num) {
    if (!state.pdfDoc) return Promise.resolve();
    if (state.rendering) {
      state.pendingPage = num;
      return Promise.resolve();
    }
    state.rendering = true;
    state.pageNum = num;
    updateChrome();
    renderNote(num);

    return state.pdfDoc
      .getPage(num)
      .then(function (page) {
        var canvas = $("#pdf-canvas");
        if (!canvas) return;
        var ctx = canvas.getContext("2d");
        var dpr = window.devicePixelRatio || 1;
        var viewport = page.getViewport({ scale: state.scale });
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        canvas.style.width = Math.floor(viewport.width) + "px";
        canvas.style.height = Math.floor(viewport.height) + "px";
        var transform = dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null;
        var renderContext = {
          canvasContext: ctx,
          viewport: viewport,
          transform: transform,
        };
        return page.render(renderContext).promise;
      })
      .then(function () {
        state.rendering = false;
        if (state.pendingPage !== null && state.pendingPage !== state.pageNum) {
          var p = state.pendingPage;
          state.pendingPage = null;
          return renderPage(p);
        }
        state.pendingPage = null;
      })
      .catch(function (err) {
        state.rendering = false;
        console.error(err);
      });
  }

  function showCta(show) {
    var cta = $("#pdf-cta");
    var wrap = $("#pdf-canvas-wrap");
    if (cta) cta.hidden = !show;
    if (wrap) wrap.hidden = !!show;
  }

  function showTextFallback(show) {
    var tf = $("#text-fallback");
    var wrap = $("#pdf-canvas-wrap");
    var cta = $("#pdf-cta");
    if (tf) tf.hidden = !show;
    if (show) {
      if (wrap) wrap.hidden = true;
      if (cta) cta.hidden = true;
      renderTextFallback(state.pageNum);
    } else {
      if (tf) tf.hidden = true;
    }
  }

  function renderTextFallback(pageNum) {
    var tf = $("#text-fallback");
    if (!tf || !state.notes) return;
    var found = findNote(state.notes, pageNum);
    var page = (found && (found.exact || found.nearest)) || null;
    if (!page) {
      tf.innerHTML = '<pre class="lecture-text">（无文字摘录）</pre>';
      return;
    }
    tf.innerHTML =
      '<div class="note-page-label">文字摘录 · 第 ' +
      page.page +
      " 页 · " +
      escapeHtml(page.title || "") +
      "</div>" +
      '<pre class="lecture-text">' +
      escapeHtml(page.excerpt || "") +
      "</pre>";
  }

  function openArrayBuffer(buf) {
    return ensurePdfJsUmd().then(function (pdfjsLib) {
      return pdfjsLib.getDocument({ data: buf }).promise;
    });
  }

  function loadModulePdf(moduleId) {
    state.moduleId = moduleId;
    showCta(false);
    return Fin4120Slides.getPdf(moduleId).then(function (rec) {
      if (!rec || !rec.data) {
        showCta(true);
        state.pdfDoc = null;
        state.pageCount = (state.notes && state.notes.pageCount) || 0;
        state.pageNum = 1;
        updateChrome();
        renderNote(1);
        return null;
      }
      var data = rec.data;
      if (data instanceof Blob) {
        return data.arrayBuffer().then(function (ab) {
          return openArrayBuffer(cloneBuf(ab));
        });
      }
      return openArrayBuffer(cloneBuf(data));
    }).then(function (pdf) {
      if (!pdf) return;
      state.pdfDoc = pdf;
      state.pageCount = pdf.numPages;
      state.pageNum = 1;
      showCta(false);
      showTextFallback(false);
      var modeBtn = $("#mode-toggle");
      if (modeBtn) {
        state.mode = "pdf";
        modeBtn.textContent = "文字摘录";
      }
      return renderPage(1);
    });
  }

  function readFileAsArrayBuffer(file) {
    return file.arrayBuffer();
  }

  function cloneBuf(buf) {
    return buf.slice(0);
  }

  function peekFirstPageText(arrayBuffer) {
    return ensurePdfJsUmd()
      .then(function (pdfjsLib) {
        return pdfjsLib.getDocument({ data: cloneBuf(arrayBuffer) }).promise;
      })
      .then(function (pdf) {
        return pdf.getPage(1).then(function (page) {
          return page.getTextContent().then(function (tc) {
            return tc.items
              .map(function (it) {
                return it.str;
              })
              .join(" ");
          });
        });
      })
      .catch(function () {
        return "";
      });
  }

  function importFiles(fileList) {
    var files = Array.prototype.slice.call(fileList || []);
    if (!files.length) return Promise.resolve([]);
    var results = [];
    var chain = Promise.resolve();
    files.forEach(function (file) {
      chain = chain.then(function () {
        return readFileAsArrayBuffer(file).then(function (buf) {
          return peekFirstPageText(buf).then(function (text) {
            var match = Fin4120Slides.matchModule(file.name, text);
            if (!match) {
              results.push({
                fileName: file.name,
                ok: false,
                reason: "无法识别对应模块（请检查文件名或是否为 Fin4120 讲义）",
              });
              return;
            }
            var id = match.entry.id;
            var storeBuf = cloneBuf(buf);
            return openArrayBuffer(cloneBuf(buf)).then(function (pdf) {
              var pageCount = pdf.numPages;
              return Fin4120Slides.putPdf({
                id: id,
                title: match.entry.title,
                fileName: file.name,
                pageCount: pageCount,
                data: storeBuf,
                importedAt: new Date().toISOString(),
              }).then(function () {
                results.push({
                  fileName: file.name,
                  ok: true,
                  id: id,
                  title: match.entry.title,
                  pageCount: pageCount,
                });
              });
            });
          });
        });
      });
    });
    return chain.then(function () {
      return results;
    });
  }

  function refreshImportStatus(host) {
    var el = host || $("#import-status");
    if (!el) return Promise.resolve();
    return Fin4120Slides.getAllMeta().then(function (metas) {
      var byId = {};
      metas.forEach(function (m) {
        byId[m.id] = m;
      });
      var html = '<ul class="import-status-list">';
      Fin4120Slides.CATALOG.forEach(function (c) {
        var m = byId[c.id];
        if (m) {
          html +=
            '<li class="ok"><strong>' +
            c.id +
            "</strong> " +
            escapeHtml(c.title) +
            ' <span class="muted">✓ 已导入（' +
            m.pageCount +
            " 页 · " +
            escapeHtml(m.fileName) +
            "）</span></li>";
        } else {
          html +=
            '<li class="miss"><strong>' +
            c.id +
            "</strong> " +
            escapeHtml(c.title) +
            ' <span class="muted">未导入</span></li>';
        }
      });
      html += "</ul>";
      var n = metas.length;
      html =
        '<p class="muted">已导入 <strong>' +
        n +
        "</strong> / 8 份讲义 PDF（仅存本机 IndexedDB，不会上传）。</p>" +
        html;
      el.innerHTML = html;
    });
  }

  function wireImporter(root) {
    root = root || document;
    $all("[data-import-pdfs]", root).forEach(function (btn) {
      var input = document.createElement("input");
      input.type = "file";
      input.accept = "application/pdf,.pdf";
      input.multiple = true;
      input.hidden = true;
      btn.parentNode.appendChild(input);
      btn.addEventListener("click", function () {
        input.click();
      });
      input.addEventListener("change", function () {
        var status = $("#import-live");
        if (status) status.textContent = "正在导入…";
        importFiles(input.files).then(function (results) {
          var ok = results.filter(function (r) {
            return r.ok;
          }).length;
          var fail = results.length - ok;
          if (status) {
            status.textContent =
              "完成：成功 " + ok + (fail ? "，未识别 " + fail : "") + "。";
          }
          refreshImportStatus();
          if (state.moduleId) {
            loadModulePdf(state.moduleId);
          }
          input.value = "";
        });
      });
    });
    $all("[data-clear-pdfs]", root).forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (!confirm("清除本机已导入的全部讲义 PDF？")) return;
        Fin4120Slides.clearAll().then(function () {
          refreshImportStatus();
          if (state.moduleId) loadModulePdf(state.moduleId);
        });
      });
    });
  }

  function wireViewer() {
    var prev = $("#pdf-prev");
    var next = $("#pdf-next");
    var zoomIn = $("#pdf-zoom-in");
    var zoomOut = $("#pdf-zoom-out");
    var modeBtn = $("#mode-toggle");

    if (prev)
      prev.addEventListener("click", function () {
        if (state.pageNum > 1) {
          if (state.mode === "text") {
            state.pageNum--;
            updateChrome();
            renderNote(state.pageNum);
            renderTextFallback(state.pageNum);
          } else renderPage(state.pageNum - 1);
        }
      });
    if (next)
      next.addEventListener("click", function () {
        var max =
          state.mode === "text"
            ? (state.notes && state.notes.pageCount) || state.pageCount
            : state.pageCount;
        if (state.pageNum < max) {
          if (state.mode === "text") {
            state.pageNum++;
            updateChrome();
            renderNote(state.pageNum);
            renderTextFallback(state.pageNum);
          } else renderPage(state.pageNum + 1);
        }
      });
    if (zoomIn)
      zoomIn.addEventListener("click", function () {
        state.scale = Math.min(2.5, state.scale + 0.15);
        updateChrome();
        if (state.mode === "pdf") renderPage(state.pageNum);
      });
    if (zoomOut)
      zoomOut.addEventListener("click", function () {
        state.scale = Math.max(0.5, state.scale - 0.15);
        updateChrome();
        if (state.mode === "pdf") renderPage(state.pageNum);
      });
    if (modeBtn)
      modeBtn.addEventListener("click", function () {
        if (state.mode === "pdf") {
          state.mode = "text";
          modeBtn.textContent = "课件 PDF";
          if (!state.pageCount && state.notes)
            state.pageCount = state.notes.pageCount;
          showTextFallback(true);
          updateChrome();
          renderNote(state.pageNum);
        } else {
          state.mode = "pdf";
          modeBtn.textContent = "文字摘录";
          showTextFallback(false);
          if (state.pdfDoc) {
            showCta(false);
            renderPage(state.pageNum);
          } else {
            showCta(true);
            renderNote(state.pageNum);
          }
        }
      });

    document.addEventListener("keydown", function (ev) {
      if (ev.target && /input|textarea|select/i.test(ev.target.tagName)) return;
      if (ev.key === "ArrowLeft") {
        if (prev) prev.click();
      } else if (ev.key === "ArrowRight") {
        if (next) next.click();
      }
    });
  }

  function initModulePage() {
    var mid = document.body.getAttribute("data-module");
    if (!mid || mid === "m0") {
      wireImporter();
      refreshImportStatus();
      return;
    }
    wireImporter();
    wireViewer();
    loadNotes(mid)
      .then(function (notes) {
        state.notes = notes;
        state.pageCount = notes.pageCount || 0;
        return loadModulePdf(mid);
      })
      .catch(function (err) {
        console.error(err);
        var host = $("#page-note");
        if (host)
          host.innerHTML =
            '<p class="muted">解析数据加载失败。仍可导入 PDF 查看课件。</p>';
        return loadModulePdf(mid);
      });
    refreshImportStatus();
  }

  function initIndexPage() {
    wireImporter();
    refreshImportStatus();
  }

  global.Fin4120PdfViewer = {
    initModulePage: initModulePage,
    initIndexPage: initIndexPage,
    importFiles: importFiles,
    refreshImportStatus: refreshImportStatus,
    loadModulePdf: loadModulePdf,
  };

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.hasAttribute("data-module")) {
      initModulePage();
    } else if ($("#import-status") || $("[data-import-pdfs]")) {
      initIndexPage();
    }
  });
})(typeof window !== "undefined" ? window : globalThis);
