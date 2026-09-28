/* 目录状态只作用于 nav；不折叠正文、不改写数据、不使用持久化存储。 */
(function () {
  "use strict";
  function setup() {
    var nav = document.querySelector('.section-nav[data-toc-mode="tree"]');
    var payload = document.getElementById("report-toc-data");
    if (!nav || !payload) return;
    var index = JSON.parse(payload.textContent);
    var byId = Object.create(null), links = Object.create(null), toggles = Object.create(null);
    var positions = [], activeBody = null, pending = false;
    index.nodes.forEach(function (node) {
      byId[node.id] = node;
      var element = document.getElementById(node.id);
      if (element) positions.push({ node: node, element: element, top: 0 });
    });
    nav.querySelectorAll("[data-toc-link]").forEach(function (link) {
      links[link.dataset.tocLink] = link;
    });
    nav.querySelectorAll("[data-toc-toggle]").forEach(function (button) {
      toggles[button.dataset.tocToggle] = button;
      button.addEventListener("click", function () {
        setOpen(button.dataset.tocToggle, button.getAttribute("aria-expanded") !== "true");
      });
    });
    function setOpen(id, open) {
      var button = toggles[id];
      if (!button) return;
      var branch = document.getElementById(button.getAttribute("aria-controls"));
      if (!open && branch.contains(document.activeElement)) button.focus();
      branch.hidden = !open;
      button.setAttribute("aria-expanded", String(open));
    }
    nav.querySelectorAll("[data-toc-all]").forEach(function (button) {
      button.addEventListener("click", function () {
        Object.keys(toggles).forEach(function (id) { setOpen(id, button.dataset.tocAll === "expand"); });
      });
    });
    function highlight(node) {
      activeBody = node.id;
      Object.keys(links).forEach(function (id) {
        var active = id === node.active_id;
        links[id].classList.toggle("active", active);
        links[id].classList.toggle("toc-active-ancestor", node.ancestors.indexOf(id) !== -1);
        if (active) links[id].setAttribute("aria-current", "location");
        else links[id].removeAttribute("aria-current");
      });
    }
    function measure() {
      positions.forEach(function (p) { p.top = p.element.getBoundingClientRect().top + window.pageYOffset; });
      positions.sort(function (a, b) { return a.top - b.top || a.node.body_order - b.node.body_order; });
    }
    function update() {
      pending = false;
      var best = positions[0];
      var line = window.pageYOffset + Math.min(100, window.innerHeight * 0.15);
      positions.forEach(function (p) { if (p.top <= line) best = p; });
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
    if (window.ResizeObserver) new ResizeObserver(refresh).observe(document.querySelector(".report-main"));
    fromHash();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
  else setup();
})();
