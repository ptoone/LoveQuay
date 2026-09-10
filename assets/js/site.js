/* LoveQuay — small progressive enhancements. Nothing here is load-bearing. */
(function () {
  "use strict";

  document.documentElement.classList.remove("no-js");

  /* --- Nav turns solid once you leave the hero ------------------------- */
  var nav = document.querySelector(".lq-nav");
  if (nav) {
    var solidAt = nav.classList.contains("lq-nav--static") ? 8 : 60;
    var tick = function () {
      nav.classList.toggle("is-solid", window.scrollY > solidAt);
    };
    tick();
    window.addEventListener("scroll", tick, { passive: true });
  }

  /* --- Reveal on scroll -------------------------------------------------
     A plain rAF-throttled position check rather than IntersectionObserver.
     IO can coalesce callbacks during a fast or programmatic scroll and skip an
     element entirely, which would leave that content stuck at opacity 0 — far
     worse than losing the animation. This sweep cannot miss: anything at or
     above the trigger line is revealed, whatever route the reader took there. */
  var targets = [].slice.call(document.querySelectorAll(".reveal"));
  if (targets.length) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      targets.forEach(function (el) { el.classList.add("is-in"); });
    } else {
      var queued = false;
      var sweep = function () {
        queued = false;
        var line = window.innerHeight * 0.9;
        targets = targets.filter(function (el) {
          if (el.getBoundingClientRect().top >= line) return true;
          el.classList.add("is-in");
          return false;
        });
        if (!targets.length) {
          window.removeEventListener("scroll", request);
          window.removeEventListener("resize", request);
        }
      };
      var request = function () {
        if (queued) return;
        queued = true;
        window.requestAnimationFrame(sweep);
      };
      sweep();
      window.addEventListener("scroll", request, { passive: true });
      window.addEventListener("resize", request);
      window.addEventListener("load", request);
    }
  }

  /* --- Gallery lightbox ------------------------------------------------ */
  var box = document.querySelector(".lightbox");
  if (box) {
    var items = Array.prototype.slice.call(document.querySelectorAll(".gallery .photo"));
    var img = box.querySelector("img");
    var cap = box.querySelector(".lightbox__cap");
    var i = 0;
    var lastFocus = null;

    function show(n) {
      i = (n + items.length) % items.length;
      var source = items[i].querySelector("img");
      img.src = source.currentSrc || source.src;
      img.alt = source.alt;
      cap.textContent = items[i].dataset.caption || source.alt;
    }
    function open(n) {
      lastFocus = document.activeElement;
      show(n);
      box.classList.add("is-open");
      document.body.style.overflow = "hidden";
      box.querySelector(".lightbox__close").focus();
    }
    function close() {
      box.classList.remove("is-open");
      document.body.style.overflow = "";
      if (lastFocus) lastFocus.focus();
    }

    items.forEach(function (el, n) {
      el.addEventListener("click", function () { open(n); });
    });
    box.querySelector(".lightbox__close").addEventListener("click", close);
    box.querySelector(".lightbox__prev").addEventListener("click", function () { show(i - 1); });
    box.querySelector(".lightbox__next").addEventListener("click", function () { show(i + 1); });
    box.addEventListener("click", function (e) { if (e.target === box) close(); });
    document.addEventListener("keydown", function (e) {
      if (!box.classList.contains("is-open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") show(i - 1);
      if (e.key === "ArrowRight") show(i + 1);
    });
  }

  /* --- Close the mobile menu after tapping a link ---------------------- */
  var menu = document.getElementById("lqMenu");
  if (menu) {
    menu.querySelectorAll(".nav-link").forEach(function (link) {
      link.addEventListener("click", function () {
        if (menu.classList.contains("show") && window.bootstrap) {
          window.bootstrap.Collapse.getOrCreateInstance(menu).hide();
        }
      });
    });
  }
})();
