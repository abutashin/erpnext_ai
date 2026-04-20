(() => {
  // ../erpnext_ai/erpnext_ai/public/js/ai_chat_widget.bundle.js
  (function() {
    function patchTimeoutPopup() {
      var _a, _b;
      if (window.__erpnext_ai_timeout_patch_done)
        return;
      window.__erpnext_ai_timeout_patch_done = true;
      if ((_a = frappe == null ? void 0 : frappe.request) == null ? void 0 : _a.call) {
        const original = frappe.request.call.bind(frappe.request);
        frappe.request.call = function(opts) {
          opts = opts || {};
          if (opts.timeout === void 0)
            opts.timeout = 0;
          return original(opts);
        };
      }
      if ((_b = frappe == null ? void 0 : frappe.request) == null ? void 0 : _b._server_request_failed) {
        const originalFail = frappe.request._server_request_failed.bind(frappe.request);
        frappe.request._server_request_failed = function(xhr, ...rest) {
          const isTimeout = (xhr == null ? void 0 : xhr.statusText) === "timeout" || (xhr == null ? void 0 : xhr.status) === 504;
          if (isTimeout)
            return;
          return originalFail(xhr, ...rest);
        };
      }
    }
    function init() {
      if (document.getElementById("erpnext-ai-chat-btn"))
        return;
      const btn = document.createElement("div");
      btn.id = "erpnext-ai-chat-btn";
      btn.innerHTML = "AI";
      document.body.appendChild(btn);
      const panel = document.createElement("div");
      panel.id = "erpnext-ai-chat-panel";
      panel.innerHTML = `
      <div class="ai-header">
        <div>ERPNext AI</div>
        <button class="ai-close">\u2715</button>
      </div>
      <div class="ai-body" id="ai-body"></div>
      <div class="ai-footer">
        <input id="ai-input" type="text" placeholder="Ask something\u2026" />
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
        if (!msg)
          return;
        input.value = "";
        addMsg("me", msg);
        addMsg("bot", "Thinking\u2026");
        frappe.call({
          method: "erpnext_ai.api.chat",
          type: "POST",
          timeout: 0,
          args: { message: msg },
          callback: (r) => {
            var _a;
            const last = body.querySelector(".ai-msg.bot:last-child");
            if (last)
              last.remove();
            addMsg("bot", ((_a = r == null ? void 0 : r.message) == null ? void 0 : _a.reply) || JSON.stringify((r == null ? void 0 : r.message) || r, null, 2));
          },
          error: (e) => {
            const last = body.querySelector(".ai-msg.bot:last-child");
            if (last)
              last.remove();
            addMsg("bot", "Error: " + ((e == null ? void 0 : e.message) || "Request failed"));
          }
        });
      };
      btn.onclick = () => panel.classList.toggle("open");
      panel.querySelector(".ai-close").onclick = () => panel.classList.remove("open");
      panel.querySelector("#ai-send").onclick = send;
      input.addEventListener("keydown", (ev) => ev.key === "Enter" ? send() : null);
    }
    function boot() {
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
})();
//# sourceMappingURL=ai_chat_widget.bundle.FZRJWTE6.js.map
