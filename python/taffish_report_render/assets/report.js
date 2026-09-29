(function () {
  var root = document.documentElement;
  var key = "taffish-flow-report-lang";

  function supportedLanguages() {
    var buttons = document.querySelectorAll("[data-lang-toggle]");
    var langs = [];
    for (var i = 0; i < buttons.length; i++) {
      langs.push(buttons[i].getAttribute("data-lang-toggle"));
    }
    return langs.length ? langs : [root.getAttribute("data-lang") || "en"];
  }

  function isSupportedLanguage(lang) {
    var langs = supportedLanguages();
    for (var i = 0; i < langs.length; i++) {
      if (langs[i] === lang) return true;
    }
    return false;
  }

  function defaultLanguage() {
    return root.getAttribute("data-lang") || root.getAttribute("lang") || "en";
  }

  function applyLanguage(lang) {
    if (!isSupportedLanguage(lang)) lang = defaultLanguage();
    root.setAttribute("data-lang", lang);
    root.setAttribute("lang", lang === "zh" ? "zh-CN" : lang);
    try {
      localStorage.setItem(key, lang);
    } catch (e) {
      /* ignore storage failures in file:// or strict browsers */
    }
    var buttons = document.querySelectorAll("[data-lang-toggle]");
    for (var i = 0; i < buttons.length; i++) {
      var active = buttons[i].getAttribute("data-lang-toggle") === lang;
      buttons[i].setAttribute("aria-pressed", active ? "true" : "false");
    }
    window.dispatchEvent(new CustomEvent("taffish-language-changed"));
  }

  function setupLanguageSwitch() {
    var saved = defaultLanguage();
    try {
      saved = localStorage.getItem(key) || saved;
    } catch (e) {
      saved = defaultLanguage();
    }
    applyLanguage(saved);
    var buttons = document.querySelectorAll("[data-lang-toggle]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener("click", function () {
        applyLanguage(this.getAttribute("data-lang-toggle"));
      });
    }
  }

  function setupScrollSpy() {
    if (document.querySelector('.section-nav[data-toc-mode="tree"]')) return;
    var links = document.querySelectorAll(".section-nav a[href^='#']");
    var sections = [];
    var linkById = {};
    for (var i = 0; i < links.length; i++) {
      var id = links[i].getAttribute("href").slice(1);
      var section = document.getElementById(id);
      if (section) {
        sections.push({ id: id, element: section, top: 0 });
        linkById[id] = links[i];
      }
    }
    if (!sections.length) return;


    function measure() {
      for (var i = 0; i < sections.length; i++) {
        sections[i].top =
          sections[i].element.getBoundingClientRect().top +
          window.pageYOffset;
      }
      sections.sort(function (a, b) {
        return a.top - b.top;
      });
    }

    function activate(id) {
      for (var j = 0; j < links.length; j++) {
        links[j].classList.remove("active");
        links[j].removeAttribute("aria-current");
      }
      var activeLink = linkById[id];
      if (!activeLink) return;
      activeLink.classList.add("active");
      activeLink.setAttribute("aria-current", "location");

      var activeGroup = activeLink.closest
        ? activeLink.closest(".nav-group")
        : null;
      var groups = document.querySelectorAll(".nav-group");
      for (var g = 0; g < groups.length; g++) {
        if (activeGroup && groups[g] === activeGroup) {
          groups[g].setAttribute("open", "");
        } else if (!groups[g].contains(document.activeElement)) {
          groups[g].removeAttribute("open");
        }
      }
    }

    function chooseActive() {
      var maxScroll = Math.max(
        0,
        document.documentElement.scrollHeight - window.innerHeight
      );
      if (window.pageYOffset >= maxScroll - 4) {
        activate(sections[sections.length - 1].id);
        return;
      }
      var line = window.pageYOffset + Math.min(180, window.innerHeight * 0.28);
      var best = sections[0].id;
      for (var i = 0; i < sections.length; i++) {
        if (sections[i].top <= line) {
          best = sections[i].id;
        } else {
          break;
        }
      }
      activate(best);
    }

    var ticking = false;
    function requestUpdate() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        ticking = false;
        chooseActive();
      });
    }

    function refresh() {
      measure();
      requestUpdate();
    }

    measure();
    chooseActive();
    window.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", refresh);
    window.addEventListener("load", refresh);
    window.addEventListener("taffish-language-changed", refresh);
    document.querySelector(".section-nav").addEventListener("focusout", requestUpdate);
  }

  function setupEmbeddedSubreports() {
    var script = document.getElementById("embedded-subreports-data");
    if (!script) return false;

    var entries = [];
    try {
      entries = JSON.parse(script.textContent || "[]");
    } catch (e) {
      entries = [];
    }
    if (!entries.length) return false;

    var byId = {};
    for (var i = 0; i < entries.length; i++) {
      byId[entries[i].id] = entries[i];
    }

    function subreportIdFromHash() {
      var prefix = "#taffish-subreport=";
      var hash = window.location.hash || "";
      if (hash.indexOf(prefix) !== 0) return "";
      try {
        return decodeURIComponent(hash.slice(prefix.length));
      } catch (e) {
        return hash.slice(prefix.length);
      }
    }

    function renderSubreportFromHash() {
      var id = subreportIdFromHash();
      if (!id) return false;
      var entry = byId[id];
      if (!entry) return false;
      try {
        document.open();
        document.write(entry.html || "");
        document.close();
        return true;
      } catch (e) {
        return false;
      }
    }

    function escapeHtmlText(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function writeLoadingPage(targetWindow, entry) {
      if (!targetWindow || !targetWindow.document) return false;
      var lang = currentLang();
      var title =
        lang === "zh" ? "正在打开内嵌报告" : "Opening embedded report";
      var message =
        lang === "zh"
          ? "TAFFISH 正在从当前单文件报告中载入已打包的原生 HTML 页面。"
          : "TAFFISH is loading the bundled native HTML page from this standalone report.";
      try {
        targetWindow.document.open();
        targetWindow.document.write(
          '<!doctype html><html lang="' +
            (lang === "zh" ? "zh-CN" : lang) +
            '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
            "<title>" +
            title +
            "</title>" +
            "<style>html,body{margin:0;min-height:100%;font-family:Inter,Arial,sans-serif;background:#f6fbfa;color:#10242b}.loading-wrap{min-height:100vh;display:grid;place-items:center;padding:32px}.loading-card{max-width:560px;border:1px solid #d6e7e4;border-radius:18px;background:#fff;padding:28px 32px;box-shadow:0 18px 50px rgba(6,61,59,.12)}.loading-kicker{margin:0 0 12px;color:#09877d;font-size:12px;font-weight:800;letter-spacing:.16em;text-transform:uppercase}.loading-title{margin:0 0 12px;font-size:26px;line-height:1.2}.loading-message{margin:0;color:#60757c;font-size:16px;line-height:1.65}.loading-id{margin-top:18px;color:#85969b;font-size:12px;word-break:break-all}</style>" +
            "<" +
            '/head><body><main class="loading-wrap" data-subreport-loading><section class="loading-card"><p class="loading-kicker">TAFFISH</p><h1 class="loading-title">' +
            title +
            '</h1><p class="loading-message">' +
            message +
            '</p><p class="loading-id">' +
            escapeHtmlText(entry.id) +
            "</p></section></main><" +
            "/body><" +
            "/html>"
        );
        targetWindow.document.close();
        return true;
      } catch (e) {
        return false;
      }
    }

    function writeSubreportWindow(targetWindow, entry) {
      if (!targetWindow || targetWindow.closed || !entry) return false;
      try {
        targetWindow.document.open();
        targetWindow.document.write(entry.html || "");
        targetWindow.document.close();
        try {
          targetWindow.focus();
        } catch (e) {
          /* ignore focus restrictions */
        }
        return true;
      } catch (e) {
        return false;
      }
    }

    function openEmbeddedSubreportWindow(entry) {
      var targetWindow = null;
      try {
        targetWindow = window.open("about:blank", "_blank");
      } catch (e) {
        targetWindow = null;
      }
      if (!targetWindow) return false;
      try {
        targetWindow.opener = null;
      } catch (e) {
        /* ignore browsers that do not allow changing opener */
      }
      writeLoadingPage(targetWindow, entry);
      window.setTimeout(function () {
        writeSubreportWindow(targetWindow, entry);
      }, 0);
      return true;
    }

    if (renderSubreportFromHash()) return true;

    var browsers = document.querySelectorAll("[data-subreport-browser]");
    if (!browsers.length) return false;

    for (var b = 0; b < browsers.length; b++) {
      var links = browsers[b].querySelectorAll("[data-open-subreport]");
      for (var j = 0; j < links.length; j++) {
        var id = links[j].getAttribute("data-open-subreport");
        var entry = byId[id];
        if (!entry) {
          links[j].setAttribute("aria-disabled", "true");
          links[j].classList.add("disabled");
          links[j].setAttribute(
            "title",
            "This browser cannot create a local page from the embedded HTML payload."
          );
        } else {
          links[j].setAttribute(
            "href",
            "#taffish-subreport=" + encodeURIComponent(id)
          );
          links[j].setAttribute("target", "_blank");
          links[j].setAttribute("rel", "noopener");
          links[j].addEventListener("click", function (event) {
            if (
              event.defaultPrevented ||
              event.button !== 0 ||
              event.metaKey ||
              event.ctrlKey ||
              event.shiftKey ||
              event.altKey
            ) {
              return;
            }
            var linkId = this.getAttribute("data-open-subreport");
            var linkEntry = byId[linkId];
            if (!linkEntry) return;
            if (openEmbeddedSubreportWindow(linkEntry)) {
              event.preventDefault();
            }
          });
        }
      }
    }
    return false;
  }

  function currentLang() {
    return root.getAttribute("data-lang") || defaultLanguage();
  }

  function localizedFromElement(el) {
    if (!el) return "";
    var node = el.querySelector('[data-i18n-lang="' + currentLang() + '"]');
    if (!node) node = el.querySelector('[data-i18n-lang="en"]');
    if (!node) node = el.querySelector("[data-i18n-lang]");
    return node ? node.textContent.trim() : el.textContent.trim();
  }

  function setTextPair(el, en, zh) {
    if (!el) return;
    el.textContent = currentLang() === "zh" ? zh : en;
  }

  function syncModalScrollLock() {
    if (!document.body) return;
    var openModal = document.querySelector(".report-modal:not([hidden])");
    document.body.classList.toggle("report-modal-open", !!openModal);
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.setAttribute("hidden", "");
    modal.setAttribute("aria-hidden", "true");
    syncModalScrollLock();
  }

  function openModal(modal) {
    if (!modal) return;
    modal.removeAttribute("hidden");
    modal.setAttribute("aria-hidden", "false");
    syncModalScrollLock();
  }

  function setupImageLightbox() {
    var modal = document.querySelector("[data-image-modal]");
    if (!modal) return;
    var panel = modal.querySelector(".image-modal-panel");
    var canvas = modal.querySelector(".image-modal-canvas");
    var img = modal.querySelector("[data-image-modal-img]");
    var title = modal.querySelector("#image-modal-title");
    var resetButton = modal.querySelector("[data-image-fit-reset]");
    var zoomInButton = modal.querySelector("[data-image-zoom-in]");
    var zoomOutButton = modal.querySelector("[data-image-zoom-out]");
    var zoomStatus = modal.querySelector("[data-image-zoom-status]");
    var zoom = 1;
    var fitWidth = 0;

    function setZoomStatus(text) {
      if (!zoomStatus) return;
      zoomStatus.textContent = text;
    }

    function canvasAvailableSize() {
      if (!canvas) return { width: window.innerWidth, height: window.innerHeight };
      var styles = window.getComputedStyle(canvas);
      var padX = parseFloat(styles.paddingLeft || "0") + parseFloat(styles.paddingRight || "0");
      var padY = parseFloat(styles.paddingTop || "0") + parseFloat(styles.paddingBottom || "0");
      return {
        width: Math.max(1, canvas.clientWidth - padX),
        height: Math.max(1, canvas.clientHeight - padY)
      };
    }

    function naturalSize() {
      return {
        width: Math.max(1, img.naturalWidth || img.width || 1),
        height: Math.max(1, img.naturalHeight || img.height || 1)
      };
    }

    function setFitMode() {
      zoom = 1;
      if (panel) panel.classList.remove("is-zoomed");
      if (img) {
        var natural = naturalSize();
        var available = canvasAvailableSize();
        var scale = Math.min(1, available.width / natural.width, available.height / natural.height);
        fitWidth = Math.max(1, Math.floor(natural.width * scale));
        img.style.width = fitWidth + "px";
        img.style.height = "auto";
        img.style.maxWidth = "none";
        img.style.maxHeight = "none";
      }
      if (canvas) {
        canvas.scrollTop = 0;
        canvas.scrollLeft = 0;
      }
      setTextPair(zoomStatus, "Fit", "适配");
      if (zoomOutButton) zoomOutButton.disabled = true;
    }

    function applyZoom(nextZoom) {
      zoom = Math.max(1, Math.min(8, nextZoom));
      if (zoom <= 1.01) {
        setFitMode();
        return;
      }
      if (panel) panel.classList.add("is-zoomed");
      img.style.maxWidth = "none";
      img.style.maxHeight = "none";
      if (!fitWidth) setFitMode();
      img.style.width = Math.round(fitWidth * zoom) + "px";
      img.style.height = "auto";
      setZoomStatus(Math.round(zoom * 100) + "%");
      if (zoomOutButton) zoomOutButton.disabled = false;
    }

    function openFromTrigger(trigger) {
      var id = trigger.getAttribute("data-open-image");
      var card = document.getElementById(id);
      if (!card) return;
      var cardImg = card.querySelector("img");
      if (!cardImg) return;
      img.onload = function () {
        img.onload = null;
        setFitMode();
      };
      img.style.width = "";
      img.style.height = "";
      img.style.maxWidth = "";
      img.style.maxHeight = "";
      img.setAttribute("src", cardImg.getAttribute("src") || "");
      img.setAttribute("alt", cardImg.getAttribute("alt") || "");
      title.textContent = localizedFromElement(card.querySelector("figcaption strong"));
      openModal(modal);
      if (img.complete && img.naturalWidth) {
        img.onload = null;
        window.requestAnimationFrame(setFitMode);
      }
      if (resetButton) resetButton.focus();
    }

    var triggers = document.querySelectorAll("[data-open-image]");
    for (var i = 0; i < triggers.length; i++) {
      triggers[i].addEventListener("click", function () {
        openFromTrigger(this);
      });
    }
    if (resetButton) {
      resetButton.addEventListener("click", setFitMode);
    }
    if (zoomInButton) {
      zoomInButton.addEventListener("click", function () {
        applyZoom(zoom * 1.25);
      });
    }
    if (zoomOutButton) {
      zoomOutButton.addEventListener("click", function () {
        applyZoom(zoom / 1.25);
      });
    }
    window.addEventListener("resize", function () {
      if (!modal || modal.hasAttribute("hidden") || zoom > 1.01) return;
      setFitMode();
    });
    modal.addEventListener("wheel", function (event) {
      if (modal.hasAttribute("hidden")) return;
      var scroller = event.target.closest ? event.target.closest(".image-modal-canvas") : null;
      if (!scroller) {
        event.preventDefault();
        return;
      }
      var scrollableY = scroller.scrollHeight > scroller.clientHeight + 1;
      var scrollableX = scroller.scrollWidth > scroller.clientWidth + 1;
      if (!scrollableY && !scrollableX) {
        event.preventDefault();
      }
    }, { passive: false });
  }

  function setupModalClose() {
    var closers = document.querySelectorAll("[data-modal-close]");
    for (var i = 0; i < closers.length; i++) {
      closers[i].addEventListener("click", function () {
        closeModal(this.closest(".report-modal"));
      });
    }
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      var open = document.querySelector(".report-modal:not([hidden])");
      closeModal(open);
    });
  }

  function setupCopyButtons() {
    var buttons = document.querySelectorAll("[data-copy-code]");
    function fallbackCopy(text) {
      var textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand("copy");
      } catch (e) {
        /* ignore legacy copy failures */
      }
      document.body.removeChild(textarea);
    }
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener("click", function () {
        var target = document.getElementById(this.getAttribute("data-copy-target"));
        if (!target) return;
        var button = this;
        var original = button.innerHTML;
        var text = target.textContent || "";
        var done = function () {
          button.textContent = currentLang() === "zh" ? "已复制" : "Copied";
          window.setTimeout(function () {
            button.innerHTML = original;
          }, 1200);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () {
            fallbackCopy(text);
            done();
          });
        } else {
          fallbackCopy(text);
          done();
        }
      });
    }
  }

  function copyPlainText(text, done) {
    function fallbackCopy(value) {
      var textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand("copy");
      } catch (e) {
        /* ignore legacy copy failures */
      }
      document.body.removeChild(textarea);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {
        fallbackCopy(text);
        if (done) done();
      });
    } else {
      fallbackCopy(text);
      if (done) done();
    }
  }

  function tableButtonLabel(button, action) {
    var lang = currentLang();
    return (
      button.getAttribute("data-label-" + action + "-" + lang) ||
      button.getAttribute("data-label-" + action + "-en") ||
      button.getAttribute("data-label-" + action + "-zh") ||
      button.textContent ||
      ""
    );
  }

  function setTableToggleLabel(button, expanded) {
    if (!button) return;
    button.textContent = tableButtonLabel(button, expanded ? "hide" : "show");
  }

  function cellSortValue(cell) {
    var raw = (cell && (cell.getAttribute("data-cell-value") || cell.textContent) || "").trim();
    var numeric = raw.replace(/,/g, "");
    if (/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(numeric)) {
      return { number: Number(numeric), text: raw.toLowerCase() };
    }
    return { number: null, text: raw.toLowerCase() };
  }

  function sortTableByColumn(table, columnIndex, direction) {
    var tbody = table.querySelector("tbody");
    if (!tbody) return;
    var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr[data-table-row]"));
    rows.sort(function (a, b) {
      var av = cellSortValue(a.children[columnIndex]);
      var bv = cellSortValue(b.children[columnIndex]);
      var result = 0;
      if (av.number !== null && bv.number !== null) {
        result = av.number - bv.number;
      } else {
        result = av.text.localeCompare(bv.text, undefined, { numeric: true, sensitivity: "base" });
      }
      return direction === "desc" ? -result : result;
    });
    for (var i = 0; i < rows.length; i++) {
      tbody.appendChild(rows[i]);
    }
  }

  function updateTableRowCount(panel) {
    if (!panel) return;
    var counter = panel.querySelector("[data-table-row-count]");
    if (!counter) return;
    var rows = panel.querySelectorAll("tbody tr[data-table-row]");
    var visible = 0;
    for (var i = 0; i < rows.length; i++) {
      if (!rows[i].classList.contains("is-filtered")) visible += 1;
    }
    var total = counter.getAttribute("data-total-rows") || String(rows.length);
    counter.textContent = currentLang() === "zh"
      ? "显示 " + visible + " / " + total + " 行"
      : "Showing " + visible + " / " + total + " rows";
  }

  function setupInteractiveTables() {
    var cards = document.querySelectorAll(".table-preview-card");
    for (var c = 0; c < cards.length; c++) {
      (function (card) {
        var toggle = card.querySelector("[data-table-toggle]");
        var tableScope = card.querySelector("[data-table-scope]");
        var toolbar = card.querySelector("[data-table-toolbar]");
        var usage = card.querySelector("[data-table-usage]");
        var tableWrap = card.querySelector(".table-wrap");
        var scrollControls = card.querySelector("[data-table-scroll-controls]");
        var scrollLeftButton = card.querySelector("[data-table-scroll-left]");
        var scrollRightButton = card.querySelector("[data-table-scroll-right]");
        function updateScrollControls() {
          if (!tableWrap || !scrollControls) return;
          var canScroll = tableWrap.scrollWidth > tableWrap.clientWidth + 2;
          if (canScroll) scrollControls.removeAttribute("hidden");
          else scrollControls.setAttribute("hidden", "");
          if (scrollLeftButton) scrollLeftButton.disabled = !canScroll || tableWrap.scrollLeft <= 1;
          if (scrollRightButton) {
            scrollRightButton.disabled =
              !canScroll || tableWrap.scrollLeft + tableWrap.clientWidth >= tableWrap.scrollWidth - 1;
          }
        }
        function scrollTable(delta) {
          if (!tableWrap) return;
          tableWrap.scrollLeft += delta;
          updateScrollControls();
        }
        function setExpanded(expanded) {
          card.classList.toggle("is-table-expanded", expanded);
          if (toolbar) {
            if (expanded) toolbar.removeAttribute("hidden");
            else toolbar.setAttribute("hidden", "");
          }
          if (usage) {
            if (expanded) usage.removeAttribute("hidden");
            else usage.setAttribute("hidden", "");
          }
          if (toggle) {
            toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
            setTableToggleLabel(toggle, expanded);
          }
          updateTableRowCount(tableScope);
          updateScrollControls();
        }
        if (toggle && tableScope) {
          setTableToggleLabel(toggle, toggle.getAttribute("aria-expanded") === "true");
          toggle.addEventListener("click", function () {
            var expanded = toggle.getAttribute("aria-expanded") !== "true";
            setExpanded(expanded);
          });
          setExpanded(toggle.getAttribute("aria-expanded") === "true" || card.classList.contains("is-table-expanded"));
        }
        if (tableWrap && scrollControls) {
          updateScrollControls();
          tableWrap.addEventListener("scroll", updateScrollControls);
          window.addEventListener("resize", updateScrollControls);
          if (scrollLeftButton) {
            scrollLeftButton.addEventListener("click", function () {
              scrollTable(-Math.max(160, Math.floor(tableWrap.clientWidth * 0.8)));
            });
          }
          if (scrollRightButton) {
            scrollRightButton.addEventListener("click", function () {
              scrollTable(Math.max(160, Math.floor(tableWrap.clientWidth * 0.8)));
            });
          }
        }

        var search = card.querySelector("[data-table-search]");
        if (search && tableScope) {
          search.addEventListener("input", function () {
            var query = search.value.trim().toLowerCase();
            var rows = tableScope.querySelectorAll("tbody tr[data-table-row]");
            for (var r = 0; r < rows.length; r++) {
              var haystack = rows[r].textContent.toLowerCase();
              rows[r].classList.toggle("is-filtered", !!query && haystack.indexOf(query) === -1);
            }
            updateTableRowCount(tableScope);
          });
          updateTableRowCount(tableScope);
        }
      })(cards[c]);
    }

    var sortButtons = document.querySelectorAll(".table-sort-button[data-table-sort]");
    for (var s = 0; s < sortButtons.length; s++) {
      sortButtons[s].addEventListener("click", function () {
        var button = this;
        var table = button.closest("table");
        if (!table) return;
        var direction = button.getAttribute("data-sort-dir") === "asc" ? "desc" : "asc";
        var allButtons = table.querySelectorAll(".table-sort-button");
        for (var i = 0; i < allButtons.length; i++) {
          allButtons[i].removeAttribute("data-sort-dir");
        }
        button.setAttribute("data-sort-dir", direction);
        sortTableByColumn(table, Number(button.getAttribute("data-table-sort") || 0), direction);
      });
    }

    var cells = document.querySelectorAll(".table-preview-card td[data-cell-value]");
    for (var t = 0; t < cells.length; t++) {
      cells[t].addEventListener("click", function () {
        this.classList.toggle("cell-expanded");
      });
      cells[t].addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        this.classList.toggle("cell-expanded");
      });
      cells[t].addEventListener("dblclick", function () {
        var cell = this;
        copyPlainText(cell.getAttribute("data-cell-value") || cell.textContent || "", function () {
          cell.classList.add("cell-copied");
          window.setTimeout(function () {
            cell.classList.remove("cell-copied");
          }, 900);
        });
      });
    }

    window.addEventListener("taffish-language-changed", function () {
      var toggles = document.querySelectorAll("[data-table-toggle]");
      for (var i = 0; i < toggles.length; i++) {
        setTableToggleLabel(toggles[i], toggles[i].getAttribute("aria-expanded") === "true");
      }
      var panels = document.querySelectorAll("[data-table-scope]");
      for (var p = 0; p < panels.length; p++) {
        updateTableRowCount(panels[p]);
      }
    });
  }

  function setupInteractivePlots() {
    var cards = document.querySelectorAll("[data-interactive-plot]");
    if (!cards.length) return;

    function readPayload(card) {
      var script = card.querySelector("[data-interactive-plot-payload]");
      if (!script) return null;
      try {
        return JSON.parse(script.textContent || "{}");
      } catch (e) {
        return null;
      }
    }

    function finiteNumber(value) {
      var number = Number(value);
      return isFinite(number) ? number : null;
    }

    function negLog10(value) {
      var number = finiteNumber(value);
      if (number === null || number <= 0) return null;
      return -Math.log(number) / Math.LN10;
    }

    function langPair(en, zh) {
      return currentLang() === "zh" ? zh : en;
    }

    function echartsAvailable() {
      return !!(window.echarts && window.echarts.init);
    }

    function setStats(card, items) {
      var stats = card.querySelector("[data-interactive-plot-stats]");
      if (!stats) return;
      stats.innerHTML = "";
      for (var i = 0; i < items.length; i++) {
        var wrap = document.createElement("div");
        var dt = document.createElement("dt");
        var dd = document.createElement("dd");
        dt.textContent = items[i][0];
        dd.textContent = String(items[i][1]);
        wrap.appendChild(dt);
        wrap.appendChild(dd);
        stats.appendChild(wrap);
      }
    }

    function setLegend(card, items) {
      var legend = card.querySelector("[data-interactive-plot-legend]");
      if (!legend) return;
      legend.innerHTML = "";
      for (var i = 0; i < items.length; i++) {
        var item = document.createElement("span");
        item.className = "interactive-plot-legend-item";
        var swatch = document.createElement("span");
        swatch.className = "interactive-plot-legend-swatch";
        swatch.style.backgroundColor = items[i].color;
        var text = document.createElement("span");
        text.textContent = items[i].label + " (" + items[i].count + ")";
        item.appendChild(swatch);
        item.appendChild(text);
        legend.appendChild(item);
      }
    }

    function inputNumber(card, selector, fallback) {
      var input = card.querySelector(selector);
      if (!input) return fallback;
      var value = finiteNumber(input.value);
      return value === null ? fallback : value;
    }

    function inputColor(card, selector, fallback) {
      var input = card.querySelector(selector);
      if (!input) return fallback;
      var value = String(input.value || "").trim();
      return /^#[0-9a-f]{6}$/i.test(value) ? value : fallback;
    }

    function inputChecked(card, selector, fallback) {
      var input = card.querySelector(selector);
      if (!input) return fallback;
      return !!input.checked;
    }

    function setRangeOutput(input) {
      if (!input) return;
      var target = input.getAttribute("data-output-target");
      if (!target) return;
      var output = document.getElementById(target);
      if (output) output.textContent = String(input.value);
    }

    function classify(row, padjCutoff, log2fcCutoff) {
      var padj = finiteNumber(row.padj);
      var lfc = finiteNumber(row.log2fc);
      if (padj === null || lfc === null || padj > padjCutoff || Math.abs(lfc) < log2fcCutoff) {
        return "ns";
      }
      return lfc > 0 ? "up" : "down";
    }

    function chartFor(card, stage) {
      if (!stage) return null;
      if (!echartsAvailable()) {
        stage.textContent = langPair("ECharts runtime unavailable.", "ECharts runtime 不可用。");
        return null;
      }
      if (card._taffishEchart && card._taffishEchart.getDom && card._taffishEchart.getDom() === stage) {
        return card._taffishEchart;
      }
      stage.textContent = "";
      card._taffishEchart = window.echarts.init(stage, null, { renderer: "canvas" });
      return card._taffishEchart;
    }

    function domain(values, pad) {
      var min = null;
      var max = null;
      for (var i = 0; i < values.length; i++) {
        var value = finiteNumber(values[i]);
        if (value === null) continue;
        min = min === null ? value : Math.min(min, value);
        max = max === null ? value : Math.max(max, value);
      }
      if (min === null || max === null) return {};
      if (min === max) {
        min -= 1;
        max += 1;
      }
      var span = Math.max(max - min, 1e-9);
      return { min: min - span * (pad || 0.06), max: max + span * (pad || 0.06) };
    }

    function formatP(value) {
      var number = finiteNumber(value);
      if (number === null) return "NA";
      if (number === 0) return "0";
      return number < 0.001 ? number.toExponential(3) : number.toFixed(4);
    }

    function shortLabel(value, maxChars) {
      var label = String(value || "term");
      var limit = Math.max(12, Number(maxChars || 42));
      if (label.length <= limit) return label;
      var left = Math.max(8, Math.floor(limit * 0.56));
      var right = Math.max(6, limit - left - 3);
      return label.slice(0, left) + "..." + label.slice(label.length - right);
    }

    function renderVolcanoLike(card, payload, isMA) {
      var stage = card.querySelector("[data-interactive-plot-stage]");
      if (!stage) return;
      var chart = chartFor(card, stage);
      if (!chart) return;
      var defaults = payload.defaults || {};
      var padjCutoff = inputNumber(card, "[data-plot-padj]", defaults.padj || 0.05);
      var log2fcCutoff = inputNumber(card, "[data-plot-log2fc]", defaults.log2fc || 1);
      var pointSize = inputNumber(card, "[data-plot-point-size]", defaults.pointSize || 7);
      var opacity = inputNumber(card, "[data-plot-opacity]", defaults.opacity || 0.78);
      var colorUp = inputColor(card, "[data-plot-color-up]", defaults.colorUp || "#d95f02");
      var colorDown = inputColor(card, "[data-plot-color-down]", defaults.colorDown || "#2b8cbe");
      var colorNs = inputColor(card, "[data-plot-color-ns]", defaults.colorNs || "#9aa8ad");
      var fixedRange = inputChecked(card, "[data-plot-fixed-range]", defaults.fixedRange !== false);
      var showThresholdLines = inputChecked(card, "[data-plot-threshold-lines]", defaults.showThresholdLines !== false);
      var buckets = {
        down: { data: [], name: langPair("Down", "下调"), color: colorDown },
        ns: { data: [], name: langPair("Not significant", "不显著"), color: colorNs },
        up: { data: [], name: langPair("Up", "上调"), color: colorUp }
      };
      var valid = 0;
      var up = 0;
      var down = 0;
      var allX = [];
      var allY = [];
      for (var i = 0; i < (payload.rows || []).length; i++) {
        var row = payload.rows[i];
        var lfc = finiteNumber(row.log2fc);
        var yValue = isMA ? lfc : negLog10(row.padj || row.pvalue);
        var xValue = isMA ? Math.log((finiteNumber(row.baseMean) || 0) + 1) / Math.LN10 : lfc;
        if (lfc === null || yValue === null || xValue === null) continue;
        valid += 1;
        allX.push(xValue);
        allY.push(yValue);
        var group = classify(row, padjCutoff, log2fcCutoff);
        if (group === "up") up += 1;
        if (group === "down") down += 1;
        var bucket = buckets[group];
        bucket.data.push({
          id: "row-" + i,
          name: row.label || "feature",
          value: [xValue, yValue, row.label || "", lfc, row.padj, row.pvalue, row.baseMean]
        });
      }
      var markerSize = Math.max(3, Math.min(18, pointSize));
      var series = ["down", "ns", "up"].map(function (name) {
        var bucket = buckets[name];
        return {
          id: "volcano-" + name,
          name: bucket.name,
          type: "scatter",
          animation: false,
          animationDuration: 0,
          animationDurationUpdate: 0,
          symbolSize: name === "ns" ? Math.max(2, markerSize * 0.74) : markerSize,
          data: bucket.data,
          itemStyle: {
            color: bucket.color,
            opacity: name === "ns" ? Math.min(opacity, 0.42) : opacity,
            borderColor: "#ffffff",
            borderWidth: 0.5
          },
          large: false,
          progressive: 0,
          universalTransition: false
        };
      });
      if (showThresholdLines && series.length) {
        var markLineData = isMA
          ? [{ yAxis: -log2fcCutoff }, { yAxis: log2fcCutoff }]
          : [{ xAxis: -log2fcCutoff }, { xAxis: log2fcCutoff }, { yAxis: negLog10(padjCutoff) }];
        series[0].markLine = {
          silent: true,
          symbol: "none",
          lineStyle: { color: "#8eaaa5", type: "dashed", width: 1 },
          data: markLineData.filter(function (item) {
            return item.xAxis !== null && item.yAxis !== null;
          })
        };
      }
      var xDomain = fixedRange ? domain(allX, 0.08) : {};
      var yDomain = fixedRange ? domain(allY, 0.10) : {};
      chart.setOption({
        backgroundColor: "transparent",
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
        stateAnimation: { duration: 0 },
        grid: { left: 62, right: 28, top: 24, bottom: 56, containLabel: true },
        tooltip: {
          trigger: "item",
          confine: true,
          formatter: function (params) {
            var value = params.value || [];
            return [
              "<strong>" + (value[2] || "feature") + "</strong>",
              (isMA ? "log10(baseMean + 1)" : "log2FC") + ": " + Number(value[0]).toFixed(3),
              (isMA ? "log2FC" : "-log10(padj)") + ": " + Number(value[1]).toFixed(3),
              "log2FC: " + Number(value[3]).toFixed(3),
              "padj: " + formatP(value[4]),
              "pvalue: " + formatP(value[5])
            ].join("<br>");
          }
        },
        toolbox: {
          right: 6,
          top: 0,
          itemSize: 14,
          feature: {
            dataZoom: { yAxisIndex: "none" },
            restore: {},
            saveAsImage: { backgroundColor: "#ffffff" }
          }
        },
        xAxis: {
          type: "value",
          name: isMA ? "log10(baseMean + 1)" : "log2 fold change",
          nameLocation: "middle",
          nameGap: 36,
          splitLine: { lineStyle: { color: "#dbe9e6" } },
          axisLine: { lineStyle: { color: "#9db8b4" } },
          min: xDomain.min,
          max: xDomain.max
        },
        yAxis: {
          type: "value",
          name: isMA ? "log2 fold change" : "-log10(adjusted p-value)",
          nameLocation: "middle",
          nameGap: 46,
          splitLine: { lineStyle: { color: "#dbe9e6" } },
          axisLine: { lineStyle: { color: "#9db8b4" } },
          min: yDomain.min,
          max: yDomain.max
        },
        dataZoom: [{ type: "inside", xAxisIndex: 0 }, { type: "inside", yAxisIndex: 0 }],
        series: series
      }, true);
      setLegend(card, [
        { label: buckets.up.name, color: colorUp, count: up },
        { label: buckets.down.name, color: colorDown, count: down },
        { label: buckets.ns.name, color: colorNs, count: buckets.ns.data.length }
      ]);
      setStats(card, [
        [langPair("Embedded rows", "内嵌行数"), payload.embeddedRows || 0],
        [langPair("Plotted rows", "绘制行数"), valid],
        [langPair("Up", "上调"), up],
        [langPair("Down", "下调"), down],
        [langPair("Cutoffs", "阈值"), "padj≤" + padjCutoff + ", |log2FC|≥" + log2fcCutoff]
      ]);
    }

    function renderOraDotplot(card, payload) {
      var stage = card.querySelector("[data-interactive-plot-stage]");
      if (!stage) return;
      var chart = chartFor(card, stage);
      if (!chart) return;
      var defaults = payload.defaults || {};
      var padjCutoff = inputNumber(card, "[data-plot-padj]", defaults.padj || 0.05);
      var topN = Math.max(3, Math.floor(inputNumber(card, "[data-plot-topn]", defaults.topN || 20)));
      var pointSize = inputNumber(card, "[data-plot-point-size]", defaults.pointSize || 10);
      var opacity = inputNumber(card, "[data-plot-opacity]", defaults.opacity || 0.86);
      var colorLow = inputColor(card, "[data-plot-color-low]", defaults.colorLow || "#f7e64b");
      var colorHigh = inputColor(card, "[data-plot-color-high]", defaults.colorHigh || "#5b21b6");
      var labelMaxChars = defaults.labelMaxChars || 46;
      var rows = (payload.rows || []).filter(function (row) {
        var padj = finiteNumber(row.padj);
        return padj !== null && padj <= padjCutoff;
      });
      rows.sort(function (a, b) {
        return (finiteNumber(a.padj) || 1) - (finiteNumber(b.padj) || 1);
      });
      rows = rows.slice(0, topN);
      var categories = [];
      var data = [];
      var counts = [];
      var padjs = [];
      for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var score = negLog10(row.padj || row.pvalue);
        if (score === null) continue;
        var count = finiteNumber(row.count) || 1;
        var labelText = row.label || row.id || "term";
        categories.push(labelText);
        counts.push(count);
        padjs.push(finiteNumber(row.padj) || padjCutoff);
        data.push({
          id: row.id || row.label || ("term-" + i),
          name: labelText,
          value: [score, labelText, count, finiteNumber(row.padj) || padjCutoff, row.geneRatio || "NA", row.id || "", labelText]
        });
      }
      var maxCount = counts.length ? Math.max.apply(null, counts) : 1;
      var minPadj = padjs.length ? Math.min.apply(null, padjs) : 0;
      var maxPadj = padjs.length ? Math.max.apply(null, padjs) : padjCutoff;
      var option;
      if (!data.length) {
        option = {
          grid: { left: 20, right: 20, top: 20, bottom: 20 },
          xAxis: { show: false },
          yAxis: { show: false },
          series: [],
          graphic: {
            type: "text",
            left: "center",
            top: "middle",
            style: {
              text: langPair("No terms pass the current cutoff.", "当前阈值下没有可展示条目。"),
              fill: "#64787d",
              fontSize: 16,
              fontWeight: 700
            }
          }
        };
      } else {
        option = {
          backgroundColor: "transparent",
          animation: false,
          animationDuration: 0,
          animationDurationUpdate: 0,
          stateAnimation: { duration: 0 },
          grid: { left: 18, right: 96, top: 24, bottom: 56, containLabel: true },
          tooltip: {
            trigger: "item",
            confine: true,
            formatter: function (params) {
              var value = params.value || [];
              return [
                "<strong>" + (value[6] || "term") + "</strong>",
                "-log10(padj): " + Number(value[0]).toFixed(3),
                "Count: " + value[2],
                "GeneRatio: " + value[4],
                "padj: " + formatP(value[3])
              ].join("<br>");
            }
          },
          toolbox: {
            right: 6,
            top: 0,
            itemSize: 14,
            feature: {
              dataZoom: { yAxisIndex: "none" },
              restore: {},
              saveAsImage: { backgroundColor: "#ffffff" }
            }
          },
          visualMap: {
            min: minPadj,
            max: maxPadj,
            dimension: 3,
            orient: "vertical",
            right: 8,
            top: 46,
            itemWidth: 10,
            itemHeight: 90,
            text: ["padj", ""],
            textStyle: { color: "#64787d", fontSize: 10 },
            inRange: { color: [colorHigh, colorLow] }
          },
          xAxis: {
            type: "value",
            name: "-log10(adjusted p-value)",
            nameLocation: "middle",
            nameGap: 36,
            splitLine: { lineStyle: { color: "#dbe9e6" } },
            axisLine: { lineStyle: { color: "#9db8b4" } }
          },
          yAxis: {
            type: "category",
            inverse: true,
            data: categories,
            axisLabel: {
              width: 260,
              overflow: "truncate",
              formatter: function (value) { return shortLabel(value, labelMaxChars); }
            },
            splitLine: { show: true, lineStyle: { color: "#eef5f3" } },
            axisLine: { lineStyle: { color: "#9db8b4" } }
          },
          dataZoom: [{ type: "inside", xAxisIndex: 0 }],
          series: [{
            name: langPair("ORA terms", "ORA 条目"),
            id: "ora-terms",
            type: "scatter",
            animation: false,
            animationDuration: 0,
            animationDurationUpdate: 0,
            data: data,
            symbolSize: function (value) {
              var count = Number(value[2] || 1);
              var scale = Math.sqrt(count / Math.max(maxCount, 1));
              return Math.max(7, Math.min(42, pointSize + scale * pointSize * 2.5));
            },
            itemStyle: {
              opacity: opacity,
              borderColor: "#ffffff",
              borderWidth: 0.8
            }
          }]
        };
      }
      chart.setOption(option, true);
      setLegend(card, [
        { label: langPair("Terms", "条目"), color: colorHigh, count: data.length },
        { label: langPair("Higher significance", "更显著"), color: colorLow, count: "padj↓" }
      ]);
      setStats(card, [
        [langPair("Embedded rows", "内嵌行数"), payload.embeddedRows || 0],
        [langPair("Shown terms", "展示条目"), data.length],
        [langPair("Top N", "Top N"), topN],
        [langPair("padj cutoff", "padj 阈值"), padjCutoff]
      ]);
    }

    function renderPcaPlot(card, payload) {
      var stage = card.querySelector("[data-interactive-plot-stage]");
      if (!stage) return;
      var chart = chartFor(card, stage);
      if (!chart) return;
      var defaults = payload.defaults || {};
      var pointSize = inputNumber(card, "[data-plot-point-size]", defaults.pointSize || 8);
      var opacity = inputNumber(card, "[data-plot-opacity]", defaults.opacity || 0.82);
      var fixedRange = inputChecked(card, "[data-plot-fixed-range]", defaults.fixedRange !== false);
      var palette = ["#087f74", "#d95f02", "#2b8cbe", "#7b4cc2", "#b7791f", "#4d7c0f", "#be123c", "#334155"];
      var groups = {};
      var order = [];
      var allX = [];
      var allY = [];
      var plotted = 0;
      for (var i = 0; i < (payload.rows || []).length; i++) {
        var row = payload.rows[i];
        var x = finiteNumber(row.x);
        var y = finiteNumber(row.y);
        if (x === null || y === null) continue;
        var group = String(row.group || langPair("Samples", "样本"));
        if (!groups[group]) {
          groups[group] = { data: [], color: palette[order.length % palette.length] };
          order.push(group);
        }
        plotted += 1;
        allX.push(x);
        allY.push(y);
        groups[group].data.push({
          id: "pca-row-" + i,
          name: row.sample || row.label || ("sample-" + i),
          value: [x, y, row.sample || row.label || "", group]
        });
      }
      var markerSize = Math.max(4, Math.min(20, pointSize));
      var series = order.map(function (group) {
        var entry = groups[group];
        return {
          id: "pca-" + group.replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 36),
          name: group,
          type: "scatter",
          animation: false,
          animationDuration: 0,
          animationDurationUpdate: 0,
          symbolSize: markerSize,
          data: entry.data,
          itemStyle: {
            color: entry.color,
            opacity: opacity,
            borderColor: "#ffffff",
            borderWidth: 1
          },
          large: false,
          progressive: 0,
          universalTransition: false
        };
      });
      var xDomain = fixedRange ? domain(allX, 0.10) : {};
      var yDomain = fixedRange ? domain(allY, 0.10) : {};
      var xLabel = defaults.xLabel || "PC1";
      var yLabel = defaults.yLabel || "PC2";
      chart.setOption({
        backgroundColor: "transparent",
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
        stateAnimation: { duration: 0 },
        grid: { left: 62, right: 28, top: 24, bottom: 56, containLabel: true },
        tooltip: {
          trigger: "item",
          confine: true,
          formatter: function (params) {
            var value = params.value || [];
            return [
              "<strong>" + (value[2] || "sample") + "</strong>",
              "group: " + (value[3] || "NA"),
              xLabel + ": " + Number(value[0]).toFixed(3),
              yLabel + ": " + Number(value[1]).toFixed(3)
            ].join("<br>");
          }
        },
        toolbox: {
          right: 6,
          top: 0,
          itemSize: 14,
          feature: {
            dataZoom: { yAxisIndex: "none" },
            restore: {},
            saveAsImage: { backgroundColor: "#ffffff" }
          }
        },
        xAxis: {
          type: "value",
          name: xLabel,
          nameLocation: "middle",
          nameGap: 36,
          splitLine: { lineStyle: { color: "#dbe9e6" } },
          axisLine: { lineStyle: { color: "#9db8b4" } },
          min: xDomain.min,
          max: xDomain.max
        },
        yAxis: {
          type: "value",
          name: yLabel,
          nameLocation: "middle",
          nameGap: 46,
          splitLine: { lineStyle: { color: "#dbe9e6" } },
          axisLine: { lineStyle: { color: "#9db8b4" } },
          min: yDomain.min,
          max: yDomain.max
        },
        dataZoom: [{ type: "inside", xAxisIndex: 0 }, { type: "inside", yAxisIndex: 0 }],
        series: series
      }, true);
      setLegend(card, order.map(function (group) {
        return { label: group, color: groups[group].color, count: groups[group].data.length };
      }));
      setStats(card, [
        [langPair("Embedded rows", "内嵌行数"), payload.embeddedRows || 0],
        [langPair("Plotted samples", "绘制样本数"), plotted],
        [langPair("Groups", "分组数"), order.length],
        [langPair("Axes", "坐标轴"), xLabel + " / " + yLabel]
      ]);
    }

    function resetCardControls(card, payload) {
      var defaults = payload.defaults || {};
      function setValue(selector, value) {
        var input = card.querySelector(selector);
        if (!input || value == null) return;
        if (input.type === "checkbox") input.checked = !!value;
        else input.value = String(value);
        setRangeOutput(input);
      }
      setValue("[data-plot-padj]", defaults.padj);
      setValue("[data-plot-log2fc]", defaults.log2fc);
      setValue("[data-plot-topn]", defaults.topN);
      setValue("[data-plot-point-size]", defaults.pointSize);
      setValue("[data-plot-opacity]", defaults.opacity);
      setValue("[data-plot-color-up]", defaults.colorUp);
      setValue("[data-plot-color-down]", defaults.colorDown);
      setValue("[data-plot-color-ns]", defaults.colorNs);
      setValue("[data-plot-color-low]", defaults.colorLow);
      setValue("[data-plot-color-high]", defaults.colorHigh);
      setValue("[data-plot-fixed-range]", defaults.fixedRange !== false);
      setValue("[data-plot-threshold-lines]", defaults.showThresholdLines !== false);
    }

    function renderCard(card) {
      var payload = readPayload(card);
      if (!payload) return;
      if (payload.kind === "volcano") renderVolcanoLike(card, payload, false);
      else if (payload.kind === "ma") renderVolcanoLike(card, payload, true);
      else if (payload.kind === "ora_dotplot") renderOraDotplot(card, payload);
      else if (payload.kind === "pca") renderPcaPlot(card, payload);
      var ranges = card.querySelectorAll("input[type='range']");
      for (var r = 0; r < ranges.length; r++) setRangeOutput(ranges[r]);
    }

    function debounceRender(card) {
      if (card._taffishInteractivePlotTimer) window.clearTimeout(card._taffishInteractivePlotTimer);
      card._taffishInteractivePlotTimer = window.setTimeout(function () {
        renderCard(card);
      }, 80);
    }

    for (var c = 0; c < cards.length; c++) {
      (function (card) {
        var payload = readPayload(card);
        var inputs = card.querySelectorAll(
          "[data-plot-padj], [data-plot-log2fc], [data-plot-topn], [data-plot-point-size], [data-plot-opacity], " +
          "[data-plot-color-up], [data-plot-color-down], [data-plot-color-ns], [data-plot-color-low], [data-plot-color-high], " +
          "[data-plot-fixed-range], [data-plot-threshold-lines]"
        );
        for (var i = 0; i < inputs.length; i++) {
          inputs[i].addEventListener("input", function () {
            setRangeOutput(this);
            debounceRender(card);
          });
          inputs[i].addEventListener("change", function () {
            setRangeOutput(this);
            renderCard(card);
          });
        }
        var reset = card.querySelector("[data-plot-reset]");
        if (reset) {
          reset.addEventListener("click", function () {
            resetCardControls(card, payload || readPayload(card) || {});
            renderCard(card);
          });
        }
        renderCard(card);
        if (window.ResizeObserver && !card._taffishInteractiveResizeObserver) {
          card._taffishInteractiveResizeObserver = new ResizeObserver(function () {
            if (card._taffishEchart) card._taffishEchart.resize();
          });
          card._taffishInteractiveResizeObserver.observe(card);
        }
      })(cards[c]);
    }

    window.addEventListener("resize", function () {
      for (var i = 0; i < cards.length; i++) {
        if (cards[i]._taffishEchart) cards[i]._taffishEchart.resize();
      }
    });
    window.addEventListener("taffish-language-changed", function () {
      for (var i = 0; i < cards.length; i++) renderCard(cards[i]);
    });
  }

  function setupStructureViewers() {
    var cards = document.querySelectorAll("[data-structure-viewer]");
    if (!cards.length) return;

    function readPayload(card) {
      var script = card.querySelector("[data-structure-payload]");
      if (!script) return null;
      try {
        return JSON.parse(script.textContent || "{}");
      } catch (e) {
        return null;
      }
    }

    function colorToRgb(color) {
      var value = String(color || "#087f74").trim();
      var match = value.match(/^#?([0-9a-f]{6})$/i);
      if (!match) return { r: 8, g: 127, b: 116 };
      var hex = match[1];
      return {
        r: parseInt(hex.slice(0, 2), 16),
        g: parseInt(hex.slice(2, 4), 16),
        b: parseInt(hex.slice(4, 6), 16)
      };
    }

    function rgbString(color, alpha) {
      var rgb = colorToRgb(color);
      if (alpha == null) return "rgb(" + rgb.r + "," + rgb.g + "," + rgb.b + ")";
      return "rgba(" + rgb.r + "," + rgb.g + "," + rgb.b + "," + alpha + ")";
    }

    function collectAtoms(payload) {
      var atoms = [];
      var models = payload.models || [];
      for (var m = 0; m < models.length; m++) {
        var modelAtoms = models[m].atoms || [];
        for (var a = 0; a < modelAtoms.length; a++) {
          atoms.push(modelAtoms[a]);
        }
      }
      return atoms;
    }

    function boundsForAtoms(atoms) {
      if (!atoms.length) return { cx: 0, cy: 0, cz: 0, radius: 1 };
      var minX = atoms[0].x, maxX = atoms[0].x;
      var minY = atoms[0].y, maxY = atoms[0].y;
      var minZ = atoms[0].z, maxZ = atoms[0].z;
      for (var i = 1; i < atoms.length; i++) {
        minX = Math.min(minX, atoms[i].x);
        maxX = Math.max(maxX, atoms[i].x);
        minY = Math.min(minY, atoms[i].y);
        maxY = Math.max(maxY, atoms[i].y);
        minZ = Math.min(minZ, atoms[i].z);
        maxZ = Math.max(maxZ, atoms[i].z);
      }
      var cx = (minX + maxX) / 2;
      var cy = (minY + maxY) / 2;
      var cz = (minZ + maxZ) / 2;
      var radius = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 1) / 2;
      return { cx: cx, cy: cy, cz: cz, radius: radius };
    }

    function colorValue(color) {
      var value = String(color || "").trim();
      var match = value.match(/^#?([0-9a-f]{6})$/i);
      if (!match) return null;
      return parseInt(match[1], 16);
    }

    function nglRepresentationParams(model, payload) {
      var params = {
        quality: "medium",
        opacity: 0.94
      };
      var value = colorValue(model.color);
      if (value == null) {
        params.colorScheme = model.color || "chainindex";
      } else {
        params.colorScheme = "uniform";
        params.colorValue = value;
      }
      if ((model.representation || payload.representation) === "surface") {
        params.opacity = 0.45;
      }
      return params;
    }

    function nglSiteSelection(group) {
      if (group.selection) return String(group.selection);
      var residues = group.residues || [];
      var chain = String(group.chain || "").replace(/[^A-Za-z0-9_-]/g, "");
      var atom = String(group.atom || "CA").replace(/[^A-Za-z0-9_*]/g, "");
      var terms = [];
      for (var i = 0; i < residues.length; i++) {
        var residue = String(residues[i] || "").trim();
        if (!/^[A-Za-z0-9_.:-]+$/.test(residue)) continue;
        var term = residue;
        if (chain) term += ":" + chain;
        if (atom && atom !== "*") term += "." + atom;
        terms.push(term);
      }
      return terms.join(" or ");
    }

    function readStructureControlState(card) {
      var state = {
        modelVisible: {},
        siteVisible: {},
        siteRadius: null,
        siteOpacity: null
      };
      var modelToggles = card.querySelectorAll("[data-structure-model-toggle]");
      for (var i = 0; i < modelToggles.length; i++) {
        state.modelVisible[modelToggles[i].value] = modelToggles[i].checked;
      }
      var siteToggles = card.querySelectorAll("[data-structure-site-toggle]");
      for (var j = 0; j < siteToggles.length; j++) {
        state.siteVisible[siteToggles[j].value] = siteToggles[j].checked;
      }
      var radius = card.querySelector("[data-structure-site-radius]");
      var opacity = card.querySelector("[data-structure-site-opacity]");
      if (radius) state.siteRadius = Number(radius.value);
      if (opacity) state.siteOpacity = Number(opacity.value);
      return state;
    }

    function updateStructureControlOutputs(card) {
      var radius = card.querySelector("[data-structure-site-radius]");
      var radiusOutput = card.querySelector("[data-structure-site-radius-output]");
      var opacity = card.querySelector("[data-structure-site-opacity]");
      var opacityOutput = card.querySelector("[data-structure-site-opacity-output]");
      if (radius && radiusOutput) radiusOutput.textContent = Number(radius.value).toFixed(2);
      if (opacity && opacityOutput) opacityOutput.textContent = Number(opacity.value).toFixed(2);
    }

    function modelIsVisible(model, state) {
      if (!state || !state.modelVisible || !(model.id in state.modelVisible)) return true;
      return !!state.modelVisible[model.id];
    }

    function siteIsVisible(group, state) {
      if (!state || !state.siteVisible || !(group.id in state.siteVisible)) return true;
      return !!state.siteVisible[group.id];
    }

    function addNglSiteRepresentations(component, model, payload, state) {
      var groups = payload.siteGroups || payload.site_groups || [];
      for (var i = 0; i < groups.length; i++) {
        var group = groups[i] || {};
        if (group.model && String(group.model) !== String(model.id)) continue;
        if (!siteIsVisible(group, state)) continue;
        var selection = nglSiteSelection(group);
        if (!selection) continue;
        var color = colorValue(group.color);
        var params = {
          sele: selection,
          quality: "medium",
          opacity: Number(state && state.siteOpacity != null ? state.siteOpacity : (group.opacity || 0.96)),
          radiusScale: Number(state && state.siteRadius != null ? state.siteRadius : (group.radiusScale || group.radius_scale || 1.65))
        };
        if (color == null) {
          params.colorScheme = group.color || "element";
        } else {
          params.colorScheme = "uniform";
          params.colorValue = color;
        }
        component.addRepresentation(group.representation || "spacefill", params);
      }
    }

    function addNglRepresentations(component, model, payload, representation, state) {
      var rep = representation || model.representation || payload.representation || "cartoon";
      component.removeAllRepresentations();
      component.addRepresentation(rep, nglRepresentationParams(model, payload));
      if (payload.showSurface && rep !== "surface") {
        var surfaceParams = nglRepresentationParams(model, payload);
        surfaceParams.opacity = 0.16;
        component.addRepresentation("surface", surfaceParams);
      }
      addNglSiteRepresentations(component, model, payload, state);
      if (component.setVisibility) {
        component.setVisibility(modelIsVisible(model, state));
      }
    }

    function markNglFailure(stageEl, status, message) {
      stageEl.classList.add("is-runtime-failed");
      stageEl.textContent = message;
      if (status) status.textContent = message;
    }

    function resizeNglStage(stage) {
      if (!stage) return;
      if (stage.handleResize) stage.handleResize();
      if (stage.viewer && stage.viewer.requestRender) stage.viewer.requestRender();
    }

    function initBuiltinStructureViewer(card, payload, canvas, status) {
      if (!canvas || !canvas.getContext) return;
      var ctx = canvas.getContext("2d");
      var allAtoms = collectAtoms(payload);
      var bounds = boundsForAtoms(allAtoms);
      var state = { rotX: -0.55, rotY: 0.72, zoom: 1 };
      var dragging = false;
      var lastX = 0;
      var lastY = 0;

      function resizeCanvas() {
        var dpr = window.devicePixelRatio || 1;
        var rect = canvas.getBoundingClientRect();
        var width = Math.max(320, Math.floor(rect.width || canvas.clientWidth || 640));
        var height = Math.max(260, Math.floor(rect.height || canvas.clientHeight || Number(payload.height || 420)));
        var pxWidth = Math.floor(width * dpr);
        var pxHeight = Math.floor(height * dpr);
        if (canvas.width !== pxWidth || canvas.height !== pxHeight) {
          canvas.width = pxWidth;
          canvas.height = pxHeight;
        }
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        return { width: width, height: height };
      }

      function project(atom, size) {
        var x = atom.x - bounds.cx;
        var y = atom.y - bounds.cy;
        var z = atom.z - bounds.cz;
        var cosY = Math.cos(state.rotY);
        var sinY = Math.sin(state.rotY);
        var cosX = Math.cos(state.rotX);
        var sinX = Math.sin(state.rotX);
        var x1 = x * cosY + z * sinY;
        var z1 = -x * sinY + z * cosY;
        var y1 = y * cosX - z1 * sinX;
        var z2 = y * sinX + z1 * cosX;
        var scale = Math.min(size.width, size.height) * 0.39 * state.zoom / bounds.radius;
        return {
          x: size.width / 2 + x1 * scale,
          y: size.height / 2 - y1 * scale,
          z: z2,
          scale: scale
        };
      }

      function drawEmpty(size) {
        ctx.clearRect(0, 0, size.width, size.height);
        ctx.fillStyle = "#63757d";
        ctx.textAlign = "center";
        ctx.font = "700 15px -apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif";
        ctx.fillText(currentLang() === "zh" ? "没有可绘制的 PDB 坐标" : "No drawable PDB coordinates", size.width / 2, size.height / 2);
      }

      function residueKey(model, atom) {
        return String(model && model.id ? model.id : "") + "|" + String(atom.chain || "") + "|" + String(atom.resseq || "");
      }

      function drawSiteGroups(residuePoints, state) {
        var groups = payload.siteGroups || payload.site_groups || [];
        for (var g = 0; g < groups.length; g++) {
          var group = groups[g] || {};
          if (!siteIsVisible(group, state)) continue;
          var residues = group.residues || [];
          var radius = Math.max(3, Math.min(18, Number(state && state.siteRadius != null ? state.siteRadius : (group.radiusScale || group.radius_scale || 1.65)) * 4.2));
          var opacity = Math.max(0.1, Math.min(1, Number(state && state.siteOpacity != null ? state.siteOpacity : (group.opacity || 0.96))));
          ctx.fillStyle = rgbString(group.color || "#b7791f", opacity);
          ctx.strokeStyle = "rgba(255,255,255,0.92)";
          ctx.lineWidth = 1.5;
          for (var r = 0; r < residues.length; r++) {
            var residue = String(residues[r] || "");
            var modelFilter = String(group.model || "");
            var chainFilter = String(group.chain || "");
            var keys = Object.keys(residuePoints);
            for (var k = 0; k < keys.length; k++) {
              var point = residuePoints[keys[k]];
              if (!point || String(point.atom.resseq || "") !== residue) continue;
              if (modelFilter && String(point.model.id || "") !== modelFilter) continue;
              if (chainFilter && String(point.atom.chain || "") !== chainFilter) continue;
              ctx.beginPath();
              ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
              ctx.fill();
              ctx.stroke();
            }
          }
        }
      }

      function draw() {
        var size = resizeCanvas();
        var controlState = readStructureControlState(card);
        updateStructureControlOutputs(card);
        ctx.clearRect(0, 0, size.width, size.height);
        if (!allAtoms.length) {
          drawEmpty(size);
          return;
        }
        ctx.fillStyle = "#fbfdfc";
        ctx.fillRect(0, 0, size.width, size.height);
        ctx.strokeStyle = "rgba(8,127,116,0.08)";
        ctx.lineWidth = 1;
        for (var gx = 0; gx < size.width; gx += 40) {
          ctx.beginPath();
          ctx.moveTo(gx, 0);
          ctx.lineTo(gx, size.height);
          ctx.stroke();
        }
        for (var gy = 0; gy < size.height; gy += 40) {
          ctx.beginPath();
          ctx.moveTo(0, gy);
          ctx.lineTo(size.width, gy);
          ctx.stroke();
        }
        var points = [];
        var residuePoints = {};
        var models = payload.models || [];
        for (var m = 0; m < models.length; m++) {
          if (!modelIsVisible(models[m], controlState)) continue;
          var atoms = models[m].atoms || [];
          var projected = [];
          for (var a = 0; a < atoms.length; a++) {
            var p = project(atoms[a], size);
            p.atom = atoms[a];
            p.color = models[m].color || "#087f74";
            p.model = models[m];
            projected.push(p);
            points.push(p);
            residuePoints[residueKey(models[m], atoms[a])] = p;
          }
          ctx.strokeStyle = rgbString(models[m].color, 0.60);
          ctx.lineWidth = 2;
          ctx.beginPath();
          var started = false;
          for (var k = 0; k < projected.length; k++) {
            if (!started || (k > 0 && projected[k - 1].atom.chain !== projected[k].atom.chain)) {
              ctx.moveTo(projected[k].x, projected[k].y);
              started = true;
            } else {
              ctx.lineTo(projected[k].x, projected[k].y);
            }
          }
          if (started) ctx.stroke();
        }
        points.sort(function (a, b) { return a.z - b.z; });
        for (var i = 0; i < points.length; i++) {
          var radius = Math.max(2.4, Math.min(6, 3.2 + points[i].z / Math.max(bounds.radius, 1) * 0.8));
          ctx.beginPath();
          ctx.fillStyle = rgbString(points[i].color, 0.88);
          ctx.arc(points[i].x, points[i].y, radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = "rgba(255,255,255,0.75)";
          ctx.lineWidth = 1;
          ctx.stroke();
        }
        drawSiteGroups(residuePoints, controlState);
        if (status) {
          var total = points.length;
          status.textContent = currentLang() === "zh" ? "内置结构查看器 · 拖拽旋转 · " + total + " 个显示点" : "Built-in structure viewer · drag to rotate · " + total + " displayed points";
        }
      }

      function setZoom(next) {
        state.zoom = Math.max(0.35, Math.min(8, next));
        draw();
      }

      canvas.addEventListener("pointerdown", function (event) {
        dragging = true;
        lastX = event.clientX;
        lastY = event.clientY;
        canvas.setPointerCapture(event.pointerId);
      });
      canvas.addEventListener("pointermove", function (event) {
        if (!dragging) return;
        var dx = event.clientX - lastX;
        var dy = event.clientY - lastY;
        lastX = event.clientX;
        lastY = event.clientY;
        state.rotY += dx * 0.01;
        state.rotX += dy * 0.01;
        draw();
      });
      canvas.addEventListener("pointerup", function (event) {
        dragging = false;
        try {
          canvas.releasePointerCapture(event.pointerId);
        } catch (e) {
          /* ignore stale pointer capture */
        }
      });
      canvas.addEventListener("wheel", function (event) {
        event.preventDefault();
        setZoom(state.zoom * (event.deltaY > 0 ? 0.9 : 1.1));
      }, { passive: false });

      var reset = card.querySelector("[data-structure-reset]");
      var zoomIn = card.querySelector("[data-structure-zoom-in]");
      var zoomOut = card.querySelector("[data-structure-zoom-out]");
      if (reset) {
        reset.addEventListener("click", function () {
          state.rotX = -0.55;
          state.rotY = 0.72;
          state.zoom = 1;
          draw();
        });
      }
      if (zoomIn) zoomIn.addEventListener("click", function () { setZoom(state.zoom * 1.2); });
      if (zoomOut) zoomOut.addEventListener("click", function () { setZoom(state.zoom / 1.2); });
      var controlInputs = card.querySelectorAll("[data-structure-model-toggle], [data-structure-site-toggle], [data-structure-site-radius], [data-structure-site-opacity]");
      for (var c = 0; c < controlInputs.length; c++) {
        controlInputs[c].addEventListener("input", draw);
        controlInputs[c].addEventListener("change", draw);
      }
      window.addEventListener("resize", draw);
      window.addEventListener("taffish-language-changed", draw);
      draw();
    }

    function fallbackToBuiltinStructureViewer(card, payload, message) {
      var stageEl = card.querySelector("[data-structure-ngl-stage]");
      var status = card.querySelector("[data-structure-status]");
      if (!stageEl) return;
      card.classList.add("is-structure-fallback");
      stageEl.classList.add("is-runtime-fallback");
      stageEl.setAttribute("data-structure-fallback-active", "true");
      stageEl.innerHTML = '<canvas class="structure-canvas structure-canvas-fallback" style="height:' + String(payload.height || 420) + 'px" data-structure-canvas></canvas>';
      if (status) status.textContent = message;
      var select = card.querySelector("[data-structure-representation]");
      if (select) {
        select.innerHTML = '<option value="trace">fallback trace</option>';
        select.value = "trace";
        select.disabled = true;
        select.setAttribute("aria-label", currentLang() === "zh" ? "内置 fallback 只支持 trace 视图" : "Built-in fallback only supports trace view");
      }
      var styleLabel = card.querySelector(".structure-select-label span");
      if (styleLabel) {
        styleLabel.textContent = currentLang() === "zh" ? "Fallback 样式" : "Fallback style";
      }
      var canvas = stageEl.querySelector("[data-structure-canvas]");
      initBuiltinStructureViewer(card, payload, canvas, status);
    }

    function initNglViewer(card, payload) {
      var stageEl = card.querySelector("[data-structure-ngl-stage]");
      var status = card.querySelector("[data-structure-status]");
      if (!stageEl) return;
      if (payload.runtimeShim || !window.NGL || !window.NGL.Stage || !window.Blob || window.NGL.__taffishTestShim) {
        fallbackToBuiltinStructureViewer(card, payload, currentLang() === "zh" ? "NGL runtime 不可用；已切换到内置结构查看器。" : "NGL runtime is unavailable; switched to the built-in structure viewer.");
        return;
      }
      var loadedComponents = [];
      var spinning = false;
      try {
        var stage = new window.NGL.Stage(stageEl, {
          backgroundColor: payload.background || "white"
        });
        updateStructureControlOutputs(card);
        var promises = [];
        var models = payload.models || [];
        for (var m = 0; m < models.length; m++) {
          (function (model, index) {
            var pdbText = model.pdbText || model.pdb_text || "";
            if (!pdbText) return;
            var blob = new Blob([pdbText], { type: "text/plain" });
            var name = (model.label || model.id || ("model-" + (index + 1))) + ".pdb";
            var fileLike = blob;
            if (window.File) {
              try {
                fileLike = new File([pdbText], name, { type: "chemical/x-pdb" });
              } catch (e) {
                fileLike = blob;
              }
            }
            try {
              fileLike.name = name;
            } catch (e) {
              // File.name is read-only in some browsers; NGL also receives the name option below.
            }
            promises.push(stage.loadFile(fileLike, { ext: "pdb", name: name, defaultRepresentation: false }).then(function (component) {
              component.setName(model.label || model.id || name);
              addNglRepresentations(component, model, payload, model.representation || payload.representation || "cartoon", readStructureControlState(card));
              loadedComponents.push({ component: component, model: model });
              return component;
            }));
          })(models[m], m);
        }
        if (!promises.length) {
          fallbackToBuiltinStructureViewer(card, payload, currentLang() === "zh" ? "没有可加载的 NGL PDB 内容；已切换到内置结构查看器。" : "No loadable NGL PDB content; switched to the built-in viewer.");
          return;
        }
        resizeNglStage(stage);
        Promise.all(promises).then(function () {
          resizeNglStage(stage);
          stage.autoView(650);
          window.setTimeout(function () {
            resizeNglStage(stage);
            stage.autoView(350);
          }, 80);
          window.setTimeout(function () {
            resizeNglStage(stage);
          }, 260);
          if (payload.spin) {
            spinning = true;
            if (stage.setSpin) stage.setSpin(true);
          }
          if (status) {
            status.textContent = currentLang() === "zh" ? "NGL 已加载 · 鼠标拖拽旋转，滚轮缩放" : "NGL loaded · drag to rotate, wheel to zoom";
          }
        }).catch(function () {
          fallbackToBuiltinStructureViewer(card, payload, currentLang() === "zh" ? "NGL 加载 PDB 失败；已切换到内置结构查看器。" : "NGL failed to load the PDB payload; switched to the built-in viewer.");
        });
        var reset = card.querySelector("[data-structure-reset]");
        var spin = card.querySelector("[data-structure-spin]");
        var select = card.querySelector("[data-structure-representation]");
        function refreshRepresentations(autoView) {
          var state = readStructureControlState(card);
          updateStructureControlOutputs(card);
          for (var i = 0; i < loadedComponents.length; i++) {
            addNglRepresentations(loadedComponents[i].component, loadedComponents[i].model, payload, select ? select.value : null, state);
          }
          resizeNglStage(stage);
          if (autoView) stage.autoView(350);
        }
        if (reset) {
          reset.addEventListener("click", function () {
            resizeNglStage(stage);
            stage.autoView(650);
          });
        }
        if (spin) {
          spin.addEventListener("click", function () {
            spinning = !spinning;
            if (stage.setSpin) stage.setSpin(spinning);
          });
        }
        if (select) {
          select.addEventListener("change", function () {
            refreshRepresentations(true);
          });
        }
        var controlInputs = card.querySelectorAll("[data-structure-model-toggle], [data-structure-site-toggle], [data-structure-site-radius], [data-structure-site-opacity]");
        for (var c = 0; c < controlInputs.length; c++) {
          controlInputs[c].addEventListener("input", function () {
            refreshRepresentations(false);
          });
          controlInputs[c].addEventListener("change", function () {
            refreshRepresentations(false);
          });
        }
        window.addEventListener("resize", function () {
          resizeNglStage(stage);
        });
        window.addEventListener("taffish-language-changed", function () {
          window.setTimeout(function () {
            resizeNglStage(stage);
          }, 50);
        });
      } catch (e) {
        fallbackToBuiltinStructureViewer(card, payload, currentLang() === "zh" ? "NGL 初始化失败；已切换到内置结构查看器。" : "NGL initialization failed; switched to the built-in viewer.");
      }
    }

    function initViewer(card) {
      var payload = readPayload(card);
      if (!payload) return;
      if (payload.runtime === "ngl") {
        initNglViewer(card, payload);
        return;
      }
      var canvas = card.querySelector("[data-structure-canvas]");
      if (!canvas || !canvas.getContext) return;
      var status = card.querySelector("[data-structure-status]");
      initBuiltinStructureViewer(card, payload, canvas, status);
    }

    for (var i = 0; i < cards.length; i++) {
      initViewer(cards[i]);
    }
  }

  function setupGenomeBrowsers() {
    var cards = document.querySelectorAll("[data-genome-browser]");
    if (!cards.length) return;

    function readPayload(card) {
      var script = card.querySelector("script[data-genome-browser-payload]");
      if (!script) return null;
      try {
        return JSON.parse(script.textContent || "{}");
      } catch (e) {
        return null;
      }
    }

    function renderGenomeBrowserFallback(stage, status, payload, reason) {
      if (stage) stage.classList.remove("is-live");
      var card = stage ? stage.closest("[data-genome-browser]") : null;
      if (card) card.classList.remove("is-live");
      var options = payload.options || {};
      var tracks = options.tracks || [];
      var trackCards = [];
      for (var i = 0; i < tracks.length; i++) {
        var track = tracks[i] || {};
        var url = track.url || track.URL || track.source || "";
        var indexUrl = track.indexURL || track.index_url || "";
        trackCards.push(
          '<article class="genome-browser-fallback-track">' +
          '<strong>' + escapeHtmlText(track.name || ("track-" + (i + 1))) + '</strong>' +
          '<span>' + escapeHtmlText((track.type || "track") + " / " + (track.format || "unknown")) + '</span>' +
          (url ? '<a href="' + escapeHtmlText(url) + '" target="_blank" rel="noopener">' + (currentLang() === "zh" ? "打开轨道" : "Open track") + '</a>' : "") +
          (indexUrl ? '<a href="' + escapeHtmlText(indexUrl) + '" target="_blank" rel="noopener">' + (currentLang() === "zh" ? "打开索引" : "Open index") + '</a>' : "") +
          '</article>'
        );
      }
      var reference = options.reference || {};
      var referenceHtml = "";
      if (reference.fastaURL || reference.indexURL) {
        referenceHtml =
          '<div class="genome-browser-reference">' +
          '<strong>' + (currentLang() === "zh" ? "参考序列" : "Reference") + '</strong>' +
          '<p>' + escapeHtmlText(reference.id || options.genome || "custom") + '</p>' +
          (reference.fastaURL ? '<a href="' + escapeHtmlText(reference.fastaURL) + '" target="_blank" rel="noopener">FASTA</a>' : "") +
          (reference.indexURL ? '<a href="' + escapeHtmlText(reference.indexURL) + '" target="_blank" rel="noopener">FAI</a>' : "") +
          '</div>';
      }
      var configText = JSON.stringify(options, null, 2);
      stage.innerHTML =
        '<div class="genome-browser-fallback-panel">' +
        '<div class="genome-browser-fallback-summary">' +
        '<strong>' + (currentLang() === "zh" ? "IGV 审阅配置" : "IGV review configuration") + '</strong>' +
        '<p>' + escapeHtmlText(reason) + '</p>' +
        '<dl>' +
        '<div><dt>mode</dt><dd>' + escapeHtmlText(payload.viewerMode || "embedded") + '</dd></div>' +
        '<div><dt>data</dt><dd>' + escapeHtmlText(payload.dataMode || "external") + '</dd></div>' +
        '<div><dt>genome</dt><dd>' + escapeHtmlText(options.genome || (reference.id || "custom")) + '</dd></div>' +
        '<div><dt>locus</dt><dd>' + escapeHtmlText(options.locus || "") + '</dd></div>' +
        '</dl>' +
        '</div>' +
        referenceHtml +
        '<div class="genome-browser-fallback-tracks">' +
        (trackCards.length ? trackCards.join("") : '<p>' + (currentLang() === "zh" ? "未声明轨道。" : "No tracks declared.") + '</p>') +
        '</div>' +
        '<details class="genome-browser-config"><summary>' + (currentLang() === "zh" ? "查看内嵌 IGV 配置" : "Show embedded IGV config") + '</summary><pre><code>' + escapeHtmlText(configText) + '</code></pre></details>' +
        '</div>';
      if (status) status.textContent = reason;
    }

    function availableGenomeBrowserModes(payload) {
      var raw = payload.viewerModes || payload.viewer_modes || [payload.viewerMode || payload.viewer_mode || "embedded"];
      if (!Array.isArray(raw)) raw = [raw];
      var modes = [];
      for (var i = 0; i < raw.length; i++) {
        var mode = String(raw[i] || "").toLowerCase();
        if ((mode === "embedded" || mode === "linked") && modes.indexOf(mode) < 0) modes.push(mode);
      }
      if (!modes.length) modes.push("embedded");
      return modes;
    }

    function setGenomeBrowserModeButtons(card, mode) {
      var buttons = card.querySelectorAll("[data-genome-browser-mode]");
      for (var i = 0; i < buttons.length; i++) {
        var active = buttons[i].getAttribute("data-genome-browser-mode") === mode;
        buttons[i].classList.toggle("is-active", active);
        buttons[i].setAttribute("aria-pressed", active ? "true" : "false");
      }
    }

    function effectiveGenomeBrowserPayload(payload, mode) {
      var copy = {};
      for (var key in payload) {
        if (Object.prototype.hasOwnProperty.call(payload, key)) copy[key] = payload[key];
      }
      copy.viewerMode = mode;
      return copy;
    }

    function renderGenomeBrowserMode(card, payload, mode) {
      var stage = card.querySelector("[data-genome-browser-stage]");
      var status = card.querySelector("[data-genome-browser-status]");
      if (!payload || !stage) return;
      stage.classList.remove("is-live");
      card.classList.remove("is-live");
      var currentPayload = effectiveGenomeBrowserPayload(payload, mode);
      stage.style.minHeight = String(currentPayload.height || 520) + "px";
      setGenomeBrowserModeButtons(card, mode);
      if (mode === "linked") {
        renderGenomeBrowserFallback(stage, status, currentPayload, currentLang() === "zh" ? "链接审阅模式：轨道数据和 IGV 配置保存在报告中，可在外部 genome browser 中复用。" : "Linked review mode: track URLs and IGV configuration are preserved for reuse in an external genome browser.");
        return;
      }
      if (!window.igv || typeof window.igv.createBrowser !== "function" || window.igv.__taffishTestShim) {
        renderGenomeBrowserFallback(stage, status, currentPayload, currentLang() === "zh" ? "IGV runtime 不可用或为测试 shim；轨道配置仍完整内嵌在本报告中。" : "IGV runtime is unavailable or is a test shim; track configuration is still embedded in this report.");
        return;
      }
      var options = currentPayload.options || {};
      try {
        var host = document.createElement("div");
        host.className = "genome-browser-live-host";
        host.style.minHeight = String(currentPayload.height || 520) + "px";
        var loading = document.createElement("div");
        loading.className = "genome-browser-live-loading";
        loading.textContent = currentLang() === "zh" ? "正在初始化 IGV 浏览器" : "Initializing IGV browser";
        stage.innerHTML = "";
        card.classList.add("is-live");
        stage.classList.add("is-live");
        stage.appendChild(host);
        stage.appendChild(loading);
        var settled = false;
        var timeout = window.setTimeout(function () {
          if (settled) return;
          settled = true;
          renderGenomeBrowserFallback(stage, status, currentPayload, currentLang() === "zh" ? "IGV 初始化超时；保留可审计配置面板。" : "IGV initialization timed out; keeping the auditable configuration panel.");
        }, 8000);
        var created = window.igv.createBrowser(host, options);
        function markLoaded(messageZh, messageEn) {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          if (loading && loading.parentNode) loading.parentNode.removeChild(loading);
          if (status) status.textContent = currentLang() === "zh" ? messageZh : messageEn;
        }
        if (created && typeof created.then === "function") {
          created.then(function () {
            markLoaded(
              "IGV 已加载。拖拽浏览基因组坐标；大型轨道可能依赖外部 URL 或本地服务。",
              "IGV loaded. Drag to browse genomic coordinates; large tracks may depend on external URLs or local services."
            );
          }).catch(function (err) {
            window.clearTimeout(timeout);
            settled = true;
            renderGenomeBrowserFallback(stage, status, currentPayload, "IGV error: " + (err && err.message ? err.message : String(err)));
          });
        } else {
          window.setTimeout(function () {
            markLoaded("IGV 已加载。", "IGV loaded.");
          }, 0);
        }
      } catch (e) {
        renderGenomeBrowserFallback(stage, status, currentPayload, "IGV error: " + (e && e.message ? e.message : String(e)));
      }
    }

    function initBrowser(card) {
      var payload = readPayload(card);
      if (!payload) return;
      var modes = availableGenomeBrowserModes(payload);
      var requestedMode = String(payload.viewerMode || payload.viewer_mode || modes[0]).toLowerCase();
      var initialMode = modes.indexOf(requestedMode) >= 0 ? requestedMode : modes[0];
      var buttons = card.querySelectorAll("[data-genome-browser-mode]");
      for (var b = 0; b < buttons.length; b++) {
        buttons[b].addEventListener("click", function () {
          var nextMode = this.getAttribute("data-genome-browser-mode") || initialMode;
          renderGenomeBrowserMode(card, payload, nextMode);
        });
      }
      renderGenomeBrowserMode(card, payload, initialMode);
    }

    for (var i = 0; i < cards.length; i++) {
      initBrowser(cards[i]);
    }
  }

  function init() {
    if (setupEmbeddedSubreports()) return;
    setupLanguageSwitch();
    setupScrollSpy();
    setupImageLightbox();
    setupModalClose();
    setupCopyButtons();
    setupInteractiveTables();
    setupInteractivePlots();
    setupStructureViewers();
    setupGenomeBrowsers();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
