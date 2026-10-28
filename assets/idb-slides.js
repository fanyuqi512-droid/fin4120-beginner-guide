/**
 * IndexedDB storage for locally imported Fin4120 lecture PDFs.
 * PDFs never leave the browser; nothing is uploaded.
 */
(function (global) {
  "use strict";

  var DB_NAME = "fin4120_slides_v1";
  var DB_VERSION = 1;
  var STORE = "pdfs";

  /** Expected modules and fuzzy match keywords (lowercase). */
  var CATALOG = [
    {
      id: "m1",
      title: "Fundamentals of Bonds",
      keywords: ["fundamentals of bonds", "fundamentals"],
      expectedPages: 28,
    },
    {
      id: "m2",
      title: "Pricing of Bonds",
      keywords: ["pricing of bonds", "pricing"],
      expectedPages: 32,
    },
    {
      id: "m3",
      title: "Yield of Bonds",
      keywords: ["yield of bonds"],
      expectedPages: 32,
    },
    {
      id: "m4",
      title: "Treasury Securities",
      keywords: ["treasury securities", "part i: treasury", "part i treasury"],
      expectedPages: 29,
    },
    {
      id: "m5",
      title: "Corporate Debt",
      keywords: ["corporate debt", "part ii: corporate", "part ii corporate"],
      expectedPages: 43,
    },
    {
      id: "m6",
      title: "International Bond",
      keywords: ["international bond", "part iii: international", "part iii international"],
      expectedPages: 24,
    },
    {
      id: "m7",
      title: "Yield Curve & Yield Curve Management",
      keywords: [
        "yield curve & yield curve management",
        "yield curve management",
        "yield curve &",
      ],
      expectedPages: 58,
      // bare "yield curve" alone is too broad (also appears on m8 title)
    },
    {
      id: "m8",
      title: "Deriving The Zero-Coupon Yield Curve",
      keywords: [
        "zero-coupon yield curve",
        "zero coupon yield curve",
        "treasury zero-coupon",
        "treasury zero coupon",
        "deriving the zero",
        "zero coupon",
        "zero-coupon",
        "zerocurve",
        "zero curve",
      ],
      expectedPages: 66,
    },
  ];

  function openDb() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: "id" });
        }
      };
      req.onsuccess = function () {
        resolve(req.result);
      };
      req.onerror = function () {
        reject(req.error);
      };
    });
  }

  function withStore(mode, fn) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, mode);
        var store = tx.objectStore(STORE);
        var result;
        try {
          result = fn(store);
        } catch (e) {
          reject(e);
          return;
        }
        tx.oncomplete = function () {
          resolve(result);
        };
        tx.onerror = function () {
          reject(tx.error);
        };
        if (result && typeof result.onsuccess !== "undefined") {
          result.onsuccess = function () {
            /* resolved on tx complete with result.result via closure */
          };
          var req = result;
          tx.oncomplete = function () {
            resolve(req.result);
          };
        }
      });
    });
  }

  function putPdf(record) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, "readwrite");
        tx.objectStore(STORE).put(record);
        tx.oncomplete = function () {
          resolve(record.id);
        };
        tx.onerror = function () {
          reject(tx.error);
        };
      });
    });
  }

  function getPdf(id) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, "readonly");
        var req = tx.objectStore(STORE).get(id);
        req.onsuccess = function () {
          resolve(req.result || null);
        };
        req.onerror = function () {
          reject(req.error);
        };
      });
    });
  }

  function getAllMeta() {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, "readonly");
        var req = tx.objectStore(STORE).getAll();
        req.onsuccess = function () {
          var rows = req.result || [];
          resolve(
            rows.map(function (r) {
              return {
                id: r.id,
                title: r.title,
                fileName: r.fileName,
                pageCount: r.pageCount,
                importedAt: r.importedAt,
                hasData: !!(r.data && r.data.byteLength),
              };
            })
          );
        };
        req.onerror = function () {
          reject(req.error);
        };
      });
    });
  }

  function deletePdf(id) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, "readwrite");
        tx.objectStore(STORE).delete(id);
        tx.oncomplete = function () {
          resolve();
        };
        tx.onerror = function () {
          reject(tx.error);
        };
      });
    });
  }

  function clearAll() {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, "readwrite");
        tx.objectStore(STORE).clear();
        tx.oncomplete = function () {
          resolve();
        };
        tx.onerror = function () {
          reject(tx.error);
        };
      });
    });
  }

  /**
   * Score filename (+ optional first-page text) against a catalog entry.
   * Higher is better; 0 = no match.
   */
  function normalizeKey(s) {
    return (s || "")
      .toLowerCase()
      .replace(/[\u2010-\u2015\u2212\-]+/g, " ") // hyphens/dashes → space
      .replace(/[_\.]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function scoreMatch(entry, fileName, firstPageText, pageCount) {
    var name = normalizeKey(fileName);
    var text = normalizeKey(firstPageText);
    var blob = name + " " + text;
    var score = 0;
    var kws = entry.keywords;
    for (var i = 0; i < kws.length; i++) {
      var kw = normalizeKey(kws[i]);
      if (!kw) continue;
      if (name.indexOf(kw) !== -1) score += 100 - i * 5;
      if (text.indexOf(kw) !== -1) score += 80 - i * 5;
    }
    // module id in filename e.g. m1, Fin4120_m1, m8.pdf
    if (new RegExp("\\b" + entry.id + "\\b", "i").test(fileName || "")) score += 50;
    // Chinese shortcuts
    if (entry.id === "m8" && /零息/.test(fileName || "")) score += 90;
    if (entry.id === "m7" && /收益[率]?曲线管理|收益率曲线(?!.*零息)/.test(fileName || "")) score += 60;

    // Zero-curve decks must not be swallowed by m7
    var looksZero =
      /zero\s*coupon|zerocurve|zero\s*curve|deriving\s+the\s+zero|treasury\s+zero|零息/.test(
        blob
      );
    if (looksZero) {
      if (entry.id === "m8") score += 120;
      if (entry.id === "m7") score -= 100;
    }

    // Page-count hint (m8=66, m7=58 are distinctive)
    if (pageCount && entry.expectedPages) {
      var d = Math.abs(pageCount - entry.expectedPages);
      if (d === 0) score += 55;
      else if (d <= 2) score += 25;
      else if (d >= 8) score -= 15;
    }
    return score;
  }

  function matchModule(fileName, firstPageText, pageCount) {
    var best = null;
    var bestScore = 0;
    var second = 0;
    for (var i = 0; i < CATALOG.length; i++) {
      var s = scoreMatch(CATALOG[i], fileName, firstPageText, pageCount);
      if (s > bestScore) {
        second = bestScore;
        bestScore = s;
        best = CATALOG[i];
      } else if (s > second) {
        second = s;
      }
    }
    if (bestScore < 40) return null;
    return { entry: best, score: bestScore, margin: bestScore - second };
  }

  function catalogById(id) {
    for (var i = 0; i < CATALOG.length; i++) {
      if (CATALOG[i].id === id) return CATALOG[i];
    }
    return null;
  }

  global.Fin4120Slides = {
    CATALOG: CATALOG,
    putPdf: putPdf,
    getPdf: getPdf,
    getAllMeta: getAllMeta,
    deletePdf: deletePdf,
    clearAll: clearAll,
    matchModule: matchModule,
    catalogById: catalogById,
  };
})(typeof window !== "undefined" ? window : globalThis);
