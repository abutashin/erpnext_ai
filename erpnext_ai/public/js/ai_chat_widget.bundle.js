// ERPNext AI Chat Widget (Desk-global)
(function () {
  function patchTimeoutPopup() {
    // run once
    if (window.__erpnext_ai_timeout_patch_done) return;
    window.__erpnext_ai_timeout_patch_done = true;

    // A) prevent client-side timeout (jQuery: timeout=0 means "no timeout")
    if (frappe?.request?.call) {
      const original = frappe.request.call.bind(frappe.request);
      frappe.request.call = function (opts) {
        opts = opts || {};
        if (opts.timeout === undefined) opts.timeout = 0;
        return original(opts);
      };
    }

    // B) suppress ONLY the "Request Timed Out" popup
    if (frappe?.request?._server_request_failed) {
      const originalFail = frappe.request._server_request_failed.bind(frappe.request);

      frappe.request._server_request_failed = function (xhr, ...rest) {
        const isTimeout =
          xhr?.statusText === "timeout" ||   // client timeout
          xhr?.status === 504;              // gateway timeout (nginx)

        if (isTimeout) return; // <- kills the popup entirely
        return originalFail(xhr, ...rest);
      };
    }
  }

  function init() {
    // Don't add twice
    if (document.getElementById("erpnext-ai-chat-btn")) return;

    // Floating button
    const btn = document.createElement("div");
    btn.id = "erpnext-ai-chat-btn";
    btn.innerHTML = "AI";
    document.body.appendChild(btn);

    // Panel
    const panel = document.createElement("div");
    panel.id = "erpnext-ai-chat-panel";
    panel.innerHTML = `
      <div class="ai-header">
        <div>ERPNext AI</div>
        <button class="ai-close">✕</button>
      </div>
      <div class="ai-body" id="ai-body"></div>
      <div class="ai-footer">
        <input id="ai-input" type="text" placeholder="Ask something…" />
        <button id="ai-send">Send</button>
      </div>
    `;
    document.body.appendChild(panel);

    const body = panel.querySelector("#ai-body");
    const input = panel.querySelector("#ai-input");

    const addMsg = (who, text) => {
      const row = document.createElement("div");
      row.className = `ai-msg ${who}`;
      row.textContent = text;
      body.appendChild(row);
      body.scrollTop = body.scrollHeight;
    };

    const send = () => {
      const msg = (input.value || "").trim();
      if (!msg) return;

      input.value = "";
      addMsg("me", msg);
      addMsg("bot", "Thinking…");

      // frappe.call is the supported Desk AJAX API
      frappe.call({
        method: "erpnext_ai.api.chat",
        type: "POST",
        timeout: 0, // no timeout
        args: { message: msg },
        callback: (r) => {
          const last = body.querySelector(".ai-msg.bot:last-child");
          if (last) last.remove();
          addMsg("bot", r?.message?.reply || JSON.stringify(r?.message || r, null, 2));
        },
        error: (e) => {
          const last = body.querySelector(".ai-msg.bot:last-child");
          if (last) last.remove();
          addMsg("bot", "Error: " + (e?.message || "Request failed"));
        },
      });
    };

    btn.onclick = () => panel.classList.toggle("open");
    panel.querySelector(".ai-close").onclick = () => panel.classList.remove("open");
    panel.querySelector("#ai-send").onclick = send;
    input.addEventListener("keydown", (ev) => (ev.key === "Enter" ? send() : null));
  }

  function boot() {
    // Desk loads scripts async; wait until frappe.call exists
    if (window.frappe && typeof frappe.call === "function") {
      patchTimeoutPopup();
      init();
      return;
    }
    setTimeout(boot, 600);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
