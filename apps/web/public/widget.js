/*! Tiago AI widget - https://github.com/Tiagokochem/tiago-ai-twin (MIT)
 *
 * <script src="https://<host>/widget.js" data-locale="pt" data-whatsapp="55..." defer></script>
 *
 * data-locale             pt | en | auto (default: browser language)
 * data-whatsapp           WhatsApp number of the bot (digits, with country code)
 * data-fallback-whatsapp  number used when the API is offline (default: data-whatsapp)
 * data-position           right (default) | left
 */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script || window.__tiagoAiWidget) return;
  window.__tiagoAiWidget = true;

  var base = new URL(script.src, location.href).origin;
  var data = script.dataset;
  var nav = (navigator.language || "").toLowerCase();
  var locale = data.locale === "pt" || data.locale === "en" ? data.locale : nav.indexOf("pt") === 0 ? "pt" : "en";
  var digits = function (v) { return (v || "").replace(/\D/g, ""); };
  var whatsapp = digits(data.whatsapp);
  var fallback = digits(data.fallbackWhatsapp) || whatsapp;
  var side = data.position === "left" ? "left" : "right";

  var T = {
    pt: {
      launcher: "Entreviste o Tiago AI",
      title: "Fale com o Tiago",
      subtitle: "Recrutador? O Tiago AI responde agora sobre experiência e projetos, com fontes.",
      chat: "Conversar aqui",
      chatSub: "Chat ou voz, com citações",
      wa: "Conversar pelo WhatsApp",
      waSub: "Texto ou áudio, no seu celular",
      open: "Abrir em tela cheia",
      close: "Fechar",
      prefill: "Olá! Sou recrutador(a) e gostaria de saber mais sobre o Tiago.",
      offline: "Falar com o Tiago no WhatsApp"
    },
    en: {
      launcher: "Interview Tiago AI",
      title: "Talk to Tiago",
      subtitle: "Recruiter? Tiago AI answers about his experience and projects right now, with sources.",
      chat: "Chat here",
      chatSub: "Chat or voice, with citations",
      wa: "Chat on WhatsApp",
      waSub: "Text or audio, on your phone",
      open: "Open full page",
      close: "Close",
      prefill: "Hi! I'm a recruiter and would like to know more about Tiago.",
      offline: "Message Tiago on WhatsApp"
    }
  }[locale];

  var waLink = function (n) { return "https://wa.me/" + n + "?text=" + encodeURIComponent(T.prefill); };
  var ICON_WA = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M17.47 14.38c-.3-.15-1.76-.87-2.03-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.94 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.48-.89-.79-1.49-1.77-1.66-2.07-.17-.3-.02-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.08-.15-.67-1.62-.92-2.22-.24-.58-.49-.5-.67-.51h-.57c-.2 0-.52.07-.8.37-.27.3-1.04 1.02-1.04 2.48s1.07 2.88 1.21 3.08c.15.2 2.1 3.2 5.08 4.49.71.31 1.26.49 1.69.63.71.23 1.36.2 1.87.12.57-.09 1.76-.72 2.01-1.41.25-.7.25-1.29.17-1.41-.07-.13-.27-.2-.57-.35M12.05 21.5h-.01a9.4 9.4 0 0 1-4.79-1.31l-.34-.2-3.56.93.95-3.47-.22-.36a9.4 9.4 0 0 1-1.44-5.01c0-5.2 4.23-9.43 9.44-9.43a9.4 9.4 0 0 1 9.42 9.44c0 5.2-4.23 9.43-9.43 9.43m8.02-17.45A11.27 11.27 0 0 0 12.05.72C5.8.72.7 5.8.7 12.07c0 2 .52 3.95 1.52 5.67L.6 23.7l6.1-1.6a11.3 11.3 0 0 0 5.35 1.36h.01c6.25 0 11.35-5.09 11.35-11.35 0-3.03-1.18-5.88-3.33-8.02"/></svg>';
  var ICON_CHAT = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
  var ICON_X = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  var ICON_EXPAND = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>';

  var css = [
    ":host{all:initial}",
    "*{box-sizing:border-box;font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}",
    ".w{position:fixed;bottom:20px;" + side + ":20px;z-index:2147483000;display:flex;flex-direction:column;align-items:" + (side === "left" ? "flex-start" : "flex-end") + ";gap:12px}",
    ".launch{position:relative;width:60px;height:60px;border:0;border-radius:50%;cursor:pointer;padding:0;background:#05060a;box-shadow:0 10px 30px rgba(124,92,255,.45);transition:transform .2s}",
    ".launch:hover{transform:scale(1.06)}",
    ".launch .orb{position:absolute;inset:0;border-radius:50%;overflow:hidden}",
    ".launch .orb:before{content:'';position:absolute;inset:-25%;background:conic-gradient(from 0deg,#7c5cff,#22d3ee,#a78bfa,#f472b6,#7c5cff);filter:blur(6px);animation:spin 8s linear infinite}",
    ".launch .ico{position:absolute;inset:0;display:grid;place-items:center;color:#fff;filter:drop-shadow(0 1px 2px rgba(0,0,0,.4))}",
    ".launch.off{background:#25d366;box-shadow:0 10px 30px rgba(37,211,102,.4)}",
    ".launch.off .orb{display:none}",
    ".pill{position:absolute;bottom:14px;" + (side === "left" ? "left" : "right") + ":72px;white-space:nowrap;background:#0b0d14;color:#e7e9f2;border:1px solid rgba(255,255,255,.1);font-size:13px;padding:7px 12px;border-radius:999px;opacity:0;transform:translateX(" + (side === "left" ? "-6px" : "6px") + ");transition:.25s;pointer-events:none}",
    ".w:hover .pill,.pill.show{opacity:1;transform:none}",
    ".menu.open+div .pill{opacity:0}",
    ".menu{width:300px;background:rgba(11,13,20,.96);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.1);border-radius:20px;padding:18px;color:#e7e9f2;box-shadow:0 24px 60px rgba(0,0,0,.5);display:none;animation:up .2s ease-out}",
    ".menu.open{display:block}",
    ".menu h3{margin:0;font-size:16px;font-weight:600;color:#fff}",
    ".menu p{margin:6px 0 14px;font-size:13px;line-height:1.45;color:#9aa0b4}",
    ".opt{display:flex;align-items:center;gap:12px;width:100%;text-align:left;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);color:#fff;border-radius:14px;padding:12px;margin-top:8px;cursor:pointer;text-decoration:none;font-size:14px;transition:.15s}",
    ".opt:hover{border-color:rgba(167,139,250,.5);background:rgba(124,92,255,.12)}",
    ".opt .i{display:grid;place-items:center;width:38px;height:38px;border-radius:11px;flex:none}",
    ".opt.chat .i{background:linear-gradient(135deg,#7c5cff,#22d3ee)}",
    ".opt.wa .i{background:#25d366;color:#05060a}",
    ".opt small{display:block;color:#9aa0b4;font-size:12px;margin-top:2px}",
    ".panel{position:fixed;bottom:92px;" + side + ":20px;width:410px;height:min(700px,calc(100vh - 120px));border-radius:22px;overflow:hidden;background:#05060a;border:1px solid rgba(255,255,255,.1);box-shadow:0 30px 80px rgba(0,0,0,.55);display:none;flex-direction:column;z-index:2147483001;animation:up .22s ease-out}",
    ".panel.open{display:flex}",
    ".bar{display:flex;align-items:center;justify-content:space-between;padding:10px 12px 10px 16px;border-bottom:1px solid rgba(255,255,255,.06);color:#e7e9f2;font-size:14px;font-weight:600}",
    ".bar .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#34d399;margin-right:8px;box-shadow:0 0 8px #34d399}",
    ".bar a,.bar button{display:inline-grid;place-items:center;width:32px;height:32px;border:0;border-radius:9px;background:transparent;color:#9aa0b4;cursor:pointer}",
    ".bar a:hover,.bar button:hover{background:rgba(255,255,255,.08);color:#fff}",
    "iframe{flex:1;width:100%;border:0;background:#05060a}",
    "@media (max-width:520px){.panel{inset:0;width:auto;height:auto;border-radius:0;bottom:0}.menu{width:calc(100vw - 40px)}}",
    "@keyframes spin{to{transform:rotate(360deg)}}",
    "@keyframes up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}",
    "@media (prefers-reduced-motion:reduce){.launch .orb:before{animation:none}}"
  ].join("");

  var host = document.createElement("div");
  host.id = "tiago-ai-widget";
  var root = host.attachShadow({ mode: "open" });
  root.innerHTML =
    "<style>" + css + "</style>" +
    '<div class="panel" role="dialog" aria-label="Tiago AI">' +
    '<div class="bar"><span><span class="dot"></span>Tiago AI</span><span>' +
    '<a class="full" target="_blank" rel="noopener" title="' + T.open + '">' + ICON_EXPAND + "</a>" +
    '<button class="x" title="' + T.close + '">' + ICON_X + "</button></span></div></div>" +
    '<div class="w"><div class="menu" role="menu"><h3>' + T.title + "</h3><p>" + T.subtitle + "</p>" +
    '<button class="opt chat" role="menuitem"><span class="i">' + ICON_CHAT + "</span><span>" + T.chat + "<small>" + T.chatSub + "</small></span></button>" +
    (whatsapp
      ? '<a class="opt wa" role="menuitem" target="_blank" rel="noopener" href="' + waLink(whatsapp) + '"><span class="i">' + ICON_WA + "</span><span>" + T.wa + "<small>" + T.waSub + "</small></span></a>"
      : "") +
    "</div>" +
    '<div style="position:relative"><span class="pill">' + T.launcher + "</span>" +
    '<button class="launch" aria-label="' + T.launcher + '" aria-expanded="false"><span class="orb"></span><span class="ico">' + ICON_CHAT + "</span></button></div></div>";

  var $ = function (s) { return root.querySelector(s); };
  var launch = $(".launch"), menu = $(".menu"), panel = $(".panel"), pill = $(".pill");
  var pageUrl = base + "/" + locale + "/interview";
  var embedUrl = base + "/" + locale + "/embed";
  $(".full").href = pageUrl;
  var online = true;
  var iframe = null;

  function setMenu(open) {
    menu.classList.toggle("open", open);
    launch.setAttribute("aria-expanded", String(open));
  }
  function openPanel() {
    setMenu(false);
    if (!iframe) {
      iframe = document.createElement("iframe");
      iframe.src = embedUrl;
      iframe.title = "Tiago AI";
      iframe.allow = "microphone; autoplay; clipboard-write";
      panel.appendChild(iframe);
    }
    panel.classList.add("open");
    launch.querySelector(".ico").innerHTML = ICON_X;
  }
  function closePanel() {
    panel.classList.remove("open");
    launch.querySelector(".ico").innerHTML = ICON_CHAT;
  }

  launch.addEventListener("click", function () {
    if (!online) {
      if (fallback) window.open(waLink(fallback), "_blank", "noopener");
      return;
    }
    if (panel.classList.contains("open")) return closePanel();
    setMenu(!menu.classList.contains("open"));
  });
  $(".chat").addEventListener("click", openPanel);
  $(".x").addEventListener("click", closePanel);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { setMenu(false); closePanel(); }
  });
  document.addEventListener("click", function (e) {
    if (e.composedPath().indexOf(host) === -1) setMenu(false);
  });

  function goOffline() {
    online = false;
    setMenu(false);
    launch.classList.add("off");
    launch.querySelector(".ico").innerHTML = ICON_WA;
    launch.setAttribute("aria-label", T.offline);
    pill.textContent = T.offline;
    if (!fallback) host.remove();
  }

  var ctrl = typeof AbortController === "function" ? new AbortController() : null;
  var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, 4000);
  fetch(base + "/api/health", { signal: ctrl ? ctrl.signal : undefined, cache: "no-store" })
    .then(function (r) { if (!r.ok) throw new Error(String(r.status)); })
    .catch(goOffline)
    .then(function () { clearTimeout(timer); });

  function mount() {
    document.body.appendChild(host);
    setTimeout(function () { pill.classList.add("show"); }, 1500);
    setTimeout(function () { pill.classList.remove("show"); }, 6500);
  }
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
