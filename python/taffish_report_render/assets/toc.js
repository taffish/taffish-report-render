/* 目录状态只作用于 nav；不折叠正文、不改写数据、不使用持久化存储。 */
(function () {
  "use strict";
  function setup() {
    var nav = document.querySelector('.section-nav[data-toc-mode="tree"]');
    var payload = document.getElementById("report-toc-data");
    var main = document.querySelector(".report-main");
    if (!nav || !payload || !main) return;
    var index = JSON.parse(payload.textContent);
    var follow = index.interaction === "follow";
    var byId = Object.create(null), links = Object.create(null), toggles = Object.create(null), branches = Object.create(null);
    var positions = [], activeBody = null, pending = false;
    index.nodes.forEach(function (node) {
      byId[node.id] = node;
      var element = document.getElementById(node.id);
      if (element) positions.push({ node: node, element: element, top: 0 });
    });
    nav.querySelectorAll("[data-toc-link]").forEach(function (link) {
      links[link.dataset.tocLink] = link;
    });
    nav.querySelectorAll("[data-toc-branch]").forEach(function (branch) {
      branches[branch.dataset.tocBranch] = branch;
    });
    nav.querySelectorAll("[data-toc-toggle]").forEach(function (button) {
      toggles[button.dataset.tocToggle] = button;
      button.addEventListener("click", function () {
        setOpen(button.dataset.tocToggle, button.getAttribute("aria-expanded") !== "true");
      });
    });
    function setOpen(id, open, automatic) {
      var button = toggles[id];
      var branch = branches[id];
      if (!branch) return;
      if (!open && branch.contains(document.activeElement)) {
        // 阅读跟随不抢焦点，也不把正在键盘访问的链接隐藏；focusout 后再同步。
        if (automatic) return;
        if (button) button.focus();
      }
      branch.hidden = !open;
      (button || links[id]).setAttribute("aria-expanded", String(open));
    }
    nav.querySelectorAll("[data-toc-all]").forEach(function (button) {
      button.addEventListener("click", function () {
        Object.keys(toggles).forEach(function (id) { setOpen(id, button.dataset.tocAll === "expand"); });
      });
    });
    function highlight(node) {
      activeBody = node.id;
      if (follow) {
        var bodyTop = main.getBoundingClientRect().top;
        var activeNode = byId[node.active_id];
        var path = activeNode.ancestors.concat([activeNode.id]);
        Object.keys(branches).forEach(function (id) { setOpen(id, path.indexOf(id) !== -1, true); });
      }
      Object.keys(links).forEach(function (id) {
        var active = id === node.active_id;
        links[id].classList.toggle("active", active);
        links[id].classList.toggle("toc-active-ancestor", node.ancestors.indexOf(id) !== -1);
        if (active) links[id].setAttribute("aria-current", "location");
        else links[id].removeAttribute("aria-current");
      });
      // 开合和高亮加粗引起的换行都不能推走正在阅读的正文。布局读取先结算原生 scroll
      // anchoring，仅补偿剩余位移；不按章节跳转、不平滑滚动或循环纠偏。正文尚未进入
      // 视口上沿（仍在阅读目录）时不干预；桌面侧栏不移动正文，位移为零。
      if (follow && bodyTop < 0) {
        var bodyShift = main.getBoundingClientRect().top - bodyTop;
        if (Math.abs(bodyShift) > 0.5) window.scrollBy({ top: bodyShift, behavior: "instant" });
      }
      // 只滚动桌面 sticky 侧栏；scrollIntoView 会连带移动正文，窄屏则不适用。
      var sidebar = nav.closest(".report-sidebar"), link = links[node.active_id];
      if (follow && sidebar && link && !nav.contains(document.activeElement) &&
          window.getComputedStyle(sidebar).position === "sticky") {
        var bounds = sidebar.getBoundingClientRect(), item = link.getBoundingClientRect();
        if (item.bottom > bounds.bottom - 8) sidebar.scrollTop += item.bottom - bounds.bottom + 8;
        else if (item.top < bounds.top + 8) sidebar.scrollTop += item.top - bounds.top - 8;
      }
    }
    function measure() {
      // 窄屏目录在正文上方，开合会移动正文但不改变正文尺寸。只缓存正文内的相对坐标，
      // 不依赖 ResizeObserver 捕获位置变化，也不递归重测/反复开合。
      var origin = main.getBoundingClientRect().top;
      positions.forEach(function (p) { p.top = p.element.getBoundingClientRect().top - origin; });
      positions.sort(function (a, b) { return a.top - b.top || a.node.body_order - b.node.body_order; });
    }
    function update() {
      pending = false;
      var best = positions[0];
      var line = (follow ? Math.min(180, window.innerHeight * 0.28) : Math.min(100, window.innerHeight * 0.15)) - main.getBoundingClientRect().top;
      positions.forEach(function (p) { if (p.top <= line) best = p; });
      if (window.pageYOffset >= document.documentElement.scrollHeight - window.innerHeight - 4) best = positions[positions.length - 1];
      if (best) highlight(best.node);
    }
    function refresh() { measure(); update(); }
    function navigate(id, scroll) {
      var node = byId[id], element = document.getElementById(id);
      if (!node || !element) return;
      node.ancestors.forEach(function (ancestor) { setOpen(ancestor, true); });
      if (scroll) element.scrollIntoView({ block: "start", behavior: "instant" });
      measure();
      highlight(node);
    }
    function hashId() {
      if (window.location.hash.indexOf("#taffish-subreport=") === 0) return null;
      try { return decodeURIComponent(window.location.hash.slice(1)); }
      catch (_) { return null; }
    }
    function fromHash() {
      var id = hashId();
      if (id && byId[id]) navigate(id, true);
      else refresh();
    }
    nav.addEventListener("click", function (event) {
      var link = event.target.closest("[data-toc-link]");
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      // 保留浏览器原生 hash/history；重复点击相同 hash 也能重新展开祖先。
      navigate(link.dataset.tocLink, true);
    });
    nav.addEventListener("focusout", function () {
      if (follow) window.requestAnimationFrame(update);
    });
    window.addEventListener("hashchange", fromHash);
    window.addEventListener("popstate", function () { window.requestAnimationFrame(fromHash); });
    window.addEventListener("scroll", function () {
      if (!pending) { pending = true; window.requestAnimationFrame(update); }
    }, { passive: true });
    window.addEventListener("resize", refresh);
    window.addEventListener("load", fromHash);
    window.addEventListener("taffish-language-changed", function () {
      var id = activeBody || hashId();
      window.requestAnimationFrame(function () { if (id) navigate(id, true); else refresh(); });
    });
    // 表格展开、字体/图片加载及 viewer 布局变化都可能改变正文位置。
    if (window.ResizeObserver) new ResizeObserver(refresh).observe(main);
    fromHash();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
  else setup();
})();
