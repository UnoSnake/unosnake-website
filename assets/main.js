/* ============================================================
   UnoSnake — Interactions (vanilla, ~2KB)
   ============================================================ */
(function () {
  'use strict';

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var MOBILE_BP = 860; // aligné sur assets/style.css

  /* ---- Header scroll state ---- */
  var header = document.querySelector('.site-header');
  if (header) {
    var onScroll = function () {
      if (window.scrollY > 12) header.classList.add('scrolled');
      else header.classList.remove('scrolled');
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---- Mobile menu (accessible : aria-expanded, focus, Escape) ---- */
  var burger = document.querySelector('.burger');
  var mobileNav = document.querySelector('.nav-mobile');
  if (burger && mobileNav) {
    var isOpen = function () { return burger.getAttribute('aria-expanded') === 'true'; };

    var setOpen = function (open, moveFocus) {
      burger.setAttribute('aria-expanded', String(open));
      burger.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
      mobileNav.classList.toggle('open', open);
      document.body.style.overflow = open ? 'hidden' : '';
      if (!moveFocus) return;
      if (open) {
        var first = mobileNav.querySelector('a');
        if (first) first.focus();
      } else {
        burger.focus();
      }
    };

    burger.addEventListener('click', function () { setOpen(!isOpen(), true); });

    mobileNav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { setOpen(false, false); });
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen()) setOpen(false, true);
    });

    // Fermeture automatique si la fenêtre repasse en desktop (rotation, redimensionnement)
    window.addEventListener('resize', function () {
      if (isOpen() && window.innerWidth > MOBILE_BP) setOpen(false, false);
    }, { passive: true });
  }

  /* ---- Reveal on scroll ---- */
  var reveals = document.querySelectorAll('.reveal');
  if (reveals.length) {
    if (reduce || !('IntersectionObserver' in window)) {
      reveals.forEach(function (el) { el.classList.add('in'); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('in');
            io.unobserve(entry.target);
          }
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
      reveals.forEach(function (el) { io.observe(el); });
    }
  }

  /* ---- Current year in footer ---- */
  var yr = document.querySelector('[data-year]');
  if (yr) yr.textContent = new Date().getFullYear();
})();
