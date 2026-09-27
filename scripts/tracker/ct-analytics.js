/**
 * Coochbehar Travels Analytics Tracker
 * Install on enduser site with:
 *   <script src="https://yourdomain.com/static/ct-analytics.js"
 *           data-api="https://yourdomain.com"
 *           data-socket="https://yourdomain.com/socket.io"
 *           async defer></script>
 *
 * Optional attributes:
 *   data-customer-id  — UUID of logged-in customer (if known at page load)
 *   data-visitor-id   — Persisted visitor UUID from a previous session
 */
(function (window, document) {
  "use strict";

  // ── Config ─────────────────────────────────────────────────────────
  const script = document.currentScript || (function () {
    const scripts = document.getElementsByTagName("script");
    return scripts[scripts.length - 1];
  })();

  const API_BASE   = (script.getAttribute("data-api")    || "").replace(/\/$/, "");
  const SOCKET_URL = (script.getAttribute("data-socket") || API_BASE + "/socket.io");
  const NS         = "ct_analytics";
  const HEARTBEAT_INTERVAL = 30_000; // 30 s
  const EVENT_BUFFER_FLUSH = 5_000;  // 5 s

  // ── Storage helpers ────────────────────────────────────────────────
  function store(key, value) {
    try { localStorage.setItem(NS + "." + key, value ? JSON.stringify(value) : ""); }
    catch (_) {}
  }
  function load(key) {
    try { const v = localStorage.getItem(NS + "." + key); return v ? JSON.parse(v) : null; }
    catch (_) { return null; }
  }

  // ── UTM params ─────────────────────────────────────────────────────
  function parseUtm() {
    const sp = new URLSearchParams(window.location.search);
    const utm = {
      utm_source:   sp.get("utm_source")   || null,
      utm_medium:   sp.get("utm_medium")   || null,
      utm_campaign: sp.get("utm_campaign") || null,
      utm_term:     sp.get("utm_term")     || null,
      utm_content:  sp.get("utm_content")  || null,
    };
    // Persist UTM in session storage so it survives navigation within tab
    if (utm.utm_source || utm.utm_medium || utm.utm_campaign) {
      sessionStorage.setItem(NS + ".utm", JSON.stringify(utm));
    }
    const stored = sessionStorage.getItem(NS + ".utm");
    return stored ? Object.assign(utm, JSON.parse(stored)) : utm;
  }

  // ── Fingerprint (lightweight, no libs) ────────────────────────────
  function generateFingerprint() {
    const parts = [
      navigator.userAgent,
      navigator.language,
      screen.colorDepth,
      screen.width + "x" + screen.height,
      new Date().getTimezoneOffset(),
      navigator.hardwareConcurrency || "",
      navigator.deviceMemory || "",
      !!window.chrome,
      !!window.safari,
    ].join("|");
    // Simple djb2 hash
    let hash = 5381;
    for (let i = 0; i < parts.length; i++) {
      hash = ((hash << 5) + hash) ^ parts.charCodeAt(i);
    }
    return "fp_" + Math.abs(hash).toString(16).padStart(8, "0");
  }

  // ── Device detection ───────────────────────────────────────────────
  function getDevice() {
    const ua = navigator.userAgent;
    if (/tablet|ipad|playbook|silk/i.test(ua)) return "tablet";
    if (/mobile|iphone|ipod|android|blackberry|opera mini|windows phone/i.test(ua)) return "mobile";
    return "desktop";
  }
  function getBrowser() {
    const ua = navigator.userAgent;
    if (/edg/i.test(ua))     return "Edge";
    if (/chrome/i.test(ua))  return "Chrome";
    if (/safari/i.test(ua))  return "Safari";
    if (/firefox/i.test(ua)) return "Firefox";
    if (/msie|trident/i.test(ua)) return "IE";
    return "Other";
  }
  function getOS() {
    const ua = navigator.userAgent;
    if (/windows/i.test(ua))  return "Windows";
    if (/mac os/i.test(ua))   return "macOS";
    if (/android/i.test(ua))  return "Android";
    if (/ios|iphone|ipad/i.test(ua)) return "iOS";
    if (/linux/i.test(ua))    return "Linux";
    return "Other";
  }

  // ── State ──────────────────────────────────────────────────────────
  let visitorId    = load("visitor_id");
  let sessionId    = load("session_id");
  let customerId   = script.getAttribute("data-customer-id") || load("customer_id");
  const fingerprint = generateFingerprint();
  const utm        = parseUtm();
  const referrer   = document.referrer || null;
  let socket       = null;
  let heartbeatTimer = null;
  let eventBuffer  = [];
  let flushTimer   = null;
  let sessionStartTime = Date.now();

  // ── API calls ──────────────────────────────────────────────────────
  async function apiPost(path, body) {
    try {
      const res = await fetch(API_BASE + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        credentials: "include",
      });
      return res.ok ? res.json() : null;
    } catch (_) { return null; }
  }

  // ── Identify visitor ───────────────────────────────────────────────
  async function identifyVisitor() {
    const body = {
      fingerprint,
      device:   getDevice(),
      browser:  getBrowser(),
      os:       getOS(),
      customer_id: customerId || undefined,
    };
    const data = await apiPost("/api/v1/visitors/identify", body);
    if (data && data.data && data.data.visitor) {
      visitorId = data.data.visitor.id;
      store("visitor_id", visitorId);
      if (data.data.visitor.customer_id) {
        customerId = data.data.visitor.customer_id;
        store("customer_id", customerId);
      }
    }
    return visitorId;
  }

  // ── Start session ──────────────────────────────────────────────────
  async function startSession() {
    if (!visitorId) return;
    const body = {
      visitor_id:   visitorId,
      landing_page: window.location.href,
      referrer:     referrer,
      ...utm,
    };
    const data = await apiPost("/api/v1/visitors/sessions/start", body);
    if (data && data.data) {
      sessionId = data.data.id;
      store("session_id", sessionId);
      sessionStartTime = Date.now();
    }
  }

  // ── Heartbeat ──────────────────────────────────────────────────────
  async function sendHeartbeat() {
    if (!sessionId) return;
    await apiPost("/api/v1/visitors/sessions/" + sessionId + "/heartbeat", {
      current_page: window.location.href,
      page_views_delta: 0,
    });
  }

  // ── End session ────────────────────────────────────────────────────
  async function endSession() {
    if (!sessionId) return;
    await apiPost("/api/v1/visitors/sessions/" + sessionId + "/end", {
      exit_page: window.location.href,
    });
    sessionId = null;
    store("session_id", null);
  }

  // ── Track event ────────────────────────────────────────────────────
  function trackEvent(eventName, metadata) {
    if (!visitorId || !sessionId) return;
    eventBuffer.push({
      visitor_id:     visitorId,
      session_id:     sessionId,
      event_name:     eventName,
      page:           window.location.href,
      event_metadata: metadata || null,
    });
    if (!flushTimer) {
      flushTimer = setTimeout(flushEvents, EVENT_BUFFER_FLUSH);
    }
  }

  async function flushEvents() {
    flushTimer = null;
    if (!eventBuffer.length) return;
    const toSend = eventBuffer.splice(0);
    if (toSend.length === 1) {
      await apiPost("/api/v1/visitors/events", toSend[0]);
    } else {
      await apiPost("/api/v1/visitors/events/batch", { events: toSend });
    }
  }

  // ── Socket.IO connection ───────────────────────────────────────────
  function connectSocket() {
    if (typeof io === "undefined") return;
    socket = io(SOCKET_URL, {
      transports:       ["websocket", "polling"],
      reconnection:     true,
      reconnectionDelay: 2000,
      reconnectionAttempts: 10,
      auth: {
        visitor_id:   visitorId,
        session_id:   sessionId,
        customer_id:  customerId || undefined,
        referrer:     referrer,
        current_url:  window.location.href,
        page:         window.location.pathname,
        device:       getDevice(),
        browser:      getBrowser(),
        os:           getOS(),
        utm_source:   utm.utm_source,
        utm_medium:   utm.utm_medium,
        utm_campaign: utm.utm_campaign,
        utm_term:     utm.utm_term,
        utm_content:  utm.utm_content,
      },
    });

    socket.on("connect", function () {
      // After socket connects, send visitor_identify to sync DB record
      socket.emit("visitor_identify", {
        visitor_id:   visitorId,
        session_id:   sessionId,
        customer_id:  customerId || undefined,
        page:         window.location.pathname,
        current_url:  window.location.href,
        device:       getDevice(),
        browser:      getBrowser(),
        os:           getOS(),
        utm_source:   utm.utm_source,
        utm_medium:   utm.utm_medium,
        utm_campaign: utm.utm_campaign,
        utm_term:     utm.utm_term,
        utm_content:  utm.utm_content,
        referrer:     referrer,
      });
    });

    socket.on("disconnect", function () {
      // socket handles reconnect automatically
    });
  }

  // ── Page view tracking ─────────────────────────────────────────────
  function trackPageView(url) {
    const path = url || window.location.href;
    trackEvent("page_view", { url: path, title: document.title });

    // Also emit via socket for real-time admin view
    if (socket && socket.connected) {
      socket.emit("page_view", {
        visitor_id: visitorId,
        session_id: sessionId,
        path:       path,
        page:       window.location.pathname,
      });
    }
  }

  // ── SPA navigation support (History API) ──────────────────────────
  let _lastUrl = window.location.href;
  function onUrlChange() {
    const current = window.location.href;
    if (current !== _lastUrl) {
      _lastUrl = current;
      trackPageView(current);
      if (socket && socket.connected) {
        socket.emit("page_navigation", {
          visitor_id:    visitorId,
          session_id:    sessionId,
          path:          current,
          previous_page: _lastUrl,
        });
      }
    }
  }

  const _pushState = history.pushState;
  history.pushState = function () {
    _pushState.apply(this, arguments);
    setTimeout(onUrlChange, 0);
  };
  window.addEventListener("popstate", onUrlChange);

  // ── Click tracking ─────────────────────────────────────────────────
  document.addEventListener("click", function (e) {
    const el = e.target.closest("a, button, [data-track]");
    if (!el) return;
    const label = el.getAttribute("data-track") || el.getAttribute("aria-label") || el.innerText || el.tagName;
    const eventName = el.tagName === "A" ? "link_click" : "button_click";
    trackEvent(eventName, { selector: label.trim().slice(0, 100), href: el.href || undefined });
    if (socket && socket.connected) {
      socket.emit("click", {
        visitor_id: visitorId,
        session_id: sessionId,
        selector:   label.trim().slice(0, 100),
        current_url: window.location.href,
      });
    }
  }, true);

  // ── Scroll depth tracking ──────────────────────────────────────────
  let _scrollDepthFired = {};
  window.addEventListener("scroll", function () {
    const percent = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
    [25, 50, 75, 90].forEach(function (depth) {
      if (percent >= depth && !_scrollDepthFired[depth]) {
        _scrollDepthFired[depth] = true;
        trackEvent("scroll_depth_" + depth, { depth: depth, page: window.location.href });
      }
    });
  }, { passive: true });

  // ── Visibility / page leave ────────────────────────────────────────
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") {
      flushEvents();
    }
  });

  window.addEventListener("beforeunload", function () {
    flushEvents();
    // Use sendBeacon for reliable delivery on page close
    if (sessionId && navigator.sendBeacon) {
      navigator.sendBeacon(
        API_BASE + "/api/v1/visitors/sessions/" + sessionId + "/end",
        JSON.stringify({ exit_page: window.location.href })
      );
    }
  });

  // ── Public API exposed on window.CTAnalytics ───────────────────────
  window.CTAnalytics = {
    /**
     * Call after customer logs in to link visitor to their account.
     * @param {string} cid - Customer UUID
     */
    identify: function (cid) {
      customerId = cid;
      store("customer_id", cid);
      if (socket && socket.connected) {
        socket.emit("visitor_identify", {
          visitor_id:  visitorId,
          session_id:  sessionId,
          customer_id: cid,
          page:        window.location.pathname,
          current_url: window.location.href,
        });
      }
    },

    /**
     * Track a custom event.
     * @param {string} name - Event name, e.g. "enquiry_submit"
     * @param {object} [metadata] - Optional extra data
     */
    track: function (name, metadata) {
      trackEvent(name, metadata);
    },

    /**
     * Get current visitor/session IDs (for debugging).
     */
    getState: function () {
      return { visitorId, sessionId, customerId, fingerprint };
    },
  };

  // ── Initialise ─────────────────────────────────────────────────────
  async function init() {
    await identifyVisitor();
    await startSession();
    trackPageView();

    // Load Socket.IO client if not already present
    if (typeof io === "undefined" && SOCKET_URL) {
      const s = document.createElement("script");
      s.src = API_BASE + "/socket.io/socket.io.js";
      s.onload = connectSocket;
      document.head.appendChild(s);
    } else {
      connectSocket();
    }

    // Heartbeat
    heartbeatTimer = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})(window, document);
