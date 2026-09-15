// Pofu landing page behaviour. No dependencies.
// - Every [data-store] link points to the App Store campaign URL (pt + ct from ?ct=).
// - iPhone/iPad only: sticky "Open in App Store" bar and a visible, cancellable countdown.
//   Home pages: starts with ?go=1 or after 6 s without any interaction.
//   Ad page (<html data-redirect="auto">): starts right away. ?go=0 always disables it.
//   Never on desktop or Android, and only once per browser session.
// - Page settings live on <html>: data-default-ct, data-page, data-redirect, data-countdown.
// - Videos load lazily and only play while visible.
(function () {
  "use strict";

  var APP_ID = "6778044605";
  var PROVIDER_TOKEN = "128375664";   // App Store Connect > Campaigns link pt= value
  var META_PIXEL_ID = "";             // Meta Events Manager > Pixel ID (empty = no third-party script)
  var IDLE_MS = 6000;
  var OPENED_KEY = "pofu_store_opened";

  var root = document.documentElement;
  var COUNTDOWN_S = parseInt(root.getAttribute("data-countdown"), 10) || 5;
  var AUTO_REDIRECT = root.getAttribute("data-redirect") === "auto";
  var PAGE_NAME = root.getAttribute("data-page") || "pofu_home";

  var params = new URLSearchParams(location.search);
  var campaign = params.get("ct") || root.getAttribute("data-default-ct") || "site_home";
  var storeUrl = "https://apps.apple.com/app/apple-store/id" + APP_ID +
    "?pt=" + PROVIDER_TOKEN + "&ct=" + encodeURIComponent(campaign) + "&mt=8";
  var isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Exposed for debugging/QA only.
  window.pofuLanding = { storeUrl: storeUrl, isIOS: isIOS, campaign: campaign };

  function remember(key) {
    try { sessionStorage.setItem(key, "1"); } catch (e) { /* private mode */ }
  }
  function recalled(key) {
    try { return sessionStorage.getItem(key) === "1"; } catch (e) { return false; }
  }

  /* ---------- Meta Pixel (only when an ID is configured) ---------- */
  if (META_PIXEL_ID) {
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = "2.0"; n.queue = [];
      t = b.createElement(e); t.async = !0; t.src = v;
      s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    }(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
    window.fbq("init", META_PIXEL_ID);
    window.fbq("track", "PageView");
    window.fbq("track", "ViewContent", { content_name: PAGE_NAME, campaign: campaign });
  }

  function trackStoreClick() {
    remember(OPENED_KEY);
    if (META_PIXEL_ID && window.fbq) window.fbq("trackCustom", "AppStoreClick", { ct: campaign });
  }

  /* ---------- Store links ---------- */
  Array.prototype.forEach.call(document.querySelectorAll("a[data-store]"), function (link) {
    link.href = storeUrl;
    link.addEventListener("click", trackStoreClick);
  });

  /* ---------- iOS: sticky bar + countdown ---------- */
  if (isIOS) {
    document.documentElement.classList.add("is-ios");
    Array.prototype.forEach.call(document.querySelectorAll("[data-ios-only]"), function (el) {
      el.hidden = false;
    });
    setupAutoRedirect();
  }

  function setupAutoRedirect() {
    var panel = document.querySelector(".redirect");
    if (!panel || recalled(OPENED_KEY) || params.get("go") === "0") return;

    var countEl = panel.querySelector("[data-count]");
    var idleTimer = null;
    var tick = null;
    var done = false;
    var startY = window.scrollY;
    var events = ["touchstart", "pointerdown", "keydown", "wheel", "scroll"];

    function stopAll() {
      done = true;
      clearTimeout(idleTimer);
      clearInterval(tick);
      panel.hidden = true;
      panel.classList.remove("is-running");
      events.forEach(function (name) { window.removeEventListener(name, onInteract, true); });
      document.removeEventListener("visibilitychange", onHidden);
    }

    function onInteract(e) {
      if (done) return;
      if (e.target && e.target.nodeType === 1 && panel.contains(e.target)) return;
      if (e.type === "scroll" && Math.abs(window.scrollY - startY) < 24) return;
      stopAll();
    }

    function onHidden() {
      if (document.hidden) stopAll();
    }

    function startCountdown() {
      if (done) return;
      var left = COUNTDOWN_S;
      countEl.textContent = String(left);
      panel.hidden = false;
      panel.style.setProperty("--countdown", COUNTDOWN_S + "s");
      void panel.offsetWidth; // restart the drain animation
      panel.classList.add("is-running");
      tick = setInterval(function () {
        left -= 1;
        if (left > 0) {
          countEl.textContent = String(left);
          return;
        }
        stopAll();
        trackStoreClick();
        location.href = storeUrl;
      }, 1000);
    }

    panel.querySelector(".redirect__cancel").addEventListener("click", stopAll);
    panel.querySelector(".redirect__go").addEventListener("click", stopAll);
    events.forEach(function (name) {
      window.addEventListener(name, onInteract, { capture: true, passive: true });
    });
    document.addEventListener("visibilitychange", onHidden);
    // Returning from the App Store via back/forward cache must not restart anything.
    window.addEventListener("pageshow", function (e) { if (e.persisted) stopAll(); });

    if (AUTO_REDIRECT || params.get("go") === "1") startCountdown();
    else idleTimer = setTimeout(startCountdown, IDLE_MS);
  }

  /* ---------- Scroll reveal ---------- */
  var revealEls = document.querySelectorAll(".rv");
  if ("IntersectionObserver" in window && !reduceMotion) {
    var revealIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          revealIO.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    Array.prototype.forEach.call(revealEls, function (el) { revealIO.observe(el); });
  } else {
    Array.prototype.forEach.call(revealEls, function (el) { el.classList.add("in"); });
  }

  /* ---------- Videos ---------- */
  var saveData = !!(navigator.connection && navigator.connection.saveData);

  function setupVideo(box) {
    var video = box.querySelector("video[data-src]");
    var toggle = box.querySelector(".vid-toggle");
    if (!video) return null;
    var state = { video: video, loaded: false, visible: false, userPaused: reduceMotion };

    function load() {
      if (state.loaded) return;
      state.loaded = true;
      video.src = video.getAttribute("data-src");
      video.load();
    }
    function sync() {
      if (toggle) toggle.setAttribute("aria-pressed", String(video.paused));
    }
    function play() {
      load();
      var p = video.play();
      if (p && p.catch) p.catch(function () { sync(); });
    }
    state.update = function () {
      if (state.visible && !state.userPaused) play();
      else if (!video.paused) video.pause();
    };
    state.load = load;

    video.addEventListener("playing", function () { video.classList.add("is-playing"); sync(); });
    video.addEventListener("pause", sync);

    // Reduced motion hides the hero clip entirely, so its toggle stays hidden too.
    if (toggle && !(reduceMotion && video.hasAttribute("data-hero"))) {
      toggle.hidden = false;
      sync();
      toggle.addEventListener("click", function () {
        if (video.paused) {
          state.userPaused = false;
          play();
        } else {
          state.userPaused = true;
          video.pause();
        }
        sync();
      });
    }
    return state;
  }

  var boxes = Array.prototype.map.call(document.querySelectorAll("[data-video-box]"), setupVideo)
    .filter(Boolean);

  if (!("IntersectionObserver" in window)) return;

  var loadIO = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var s = entry.target._pofuVideo;
      if (!s.video.hasAttribute("data-hero") && !reduceMotion && !saveData) s.load();
      loadIO.unobserve(entry.target);
    });
  }, { rootMargin: "400px 0px" });

  var playIO = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      var s = entry.target._pofuVideo;
      s.visible = entry.isIntersecting;
      if (s.video.hasAttribute("data-hero") && !s.heroReady) return;
      if (saveData && !s.loaded) return;
      s.update();
    });
  }, { threshold: 0.25 });

  boxes.forEach(function (s) {
    var box = s.video.closest("[data-video-box]");
    box._pofuVideo = s;
    if (!s.video.hasAttribute("data-hero")) loadIO.observe(box);
    playIO.observe(box);
  });

  // Hero clip waits until the page (and its poster, the LCP image) has finished loading.
  var hero = boxes.filter(function (s) { return s.video.hasAttribute("data-hero"); })[0];
  if (hero && !reduceMotion && !saveData) {
    var startHero = function () {
      hero.heroReady = true;
      hero.update();
    };
    var whenIdle = function () {
      if ("requestIdleCallback" in window) window.requestIdleCallback(startHero, { timeout: 1500 });
      else setTimeout(startHero, 300);
    };
    if (document.readyState === "complete") whenIdle();
    else window.addEventListener("load", whenIdle);
  }
})();
