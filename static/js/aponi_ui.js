// static/js/aponi_ui.js
// Aponi UI Module – toast queue, modals (Promise), context menus, tiny helpers
// Usage:
// import { AponiUI } from './aponi_ui.js';
// AponiUI.toast("hello", "success");
// await AponiUI.modal("Title", "<p>content</p>", [{label:"OK", class:"btn"}]);

export class AponiUI {
  // ---------- Toasts ----------
  // simple queue so toasts don't stack wildly
  static _toastQueue = [];
  static _toastActive = false;

  static toast(message, type = "info", timeout = 3000) {
    AponiUI._toastQueue.push({ message, type, timeout });
    if (!AponiUI._toastActive) AponiUI._drainQueue();
  }

  static async _drainQueue() {
    AponiUI._toastActive = true;
    while (AponiUI._toastQueue.length) {
      const { message, type, timeout } = AponiUI._toastQueue.shift();
      await AponiUI._showToast(message, type, timeout);
    }
    AponiUI._toastActive = false;
  }

  static _showToast(message, type, timeout) {
    return new Promise(resolve => {
      const t = document.createElement("div");
      t.className = `aponi-toast ${type}`;
      t.textContent = message;
      document.body.appendChild(t);

      // auto remove
      const remove = () => {
        t.classList.add("fade-out");
        t.addEventListener("transitionend", () => {
          if (t.parentNode) t.parentNode.removeChild(t);
          resolve();
        }, { once: true });
      };

      // allow click to dismiss early
      t.addEventListener("click", () => remove());
      setTimeout(remove, timeout);
    });
  }

  // ---------- Modal (Promise-based) ----------
  // actions: [{ label, class, onClick }]
  static modal(title = "", contentHtml = "", actions = []) {
    return new Promise(resolve => {
      const overlay = document.createElement("div");
      overlay.className = "aponi-modal-overlay";

      const modal = document.createElement("div");
      modal.className = "aponi-modal";

      modal.innerHTML = `
        <div class="aponi-modal-header">
          <span class="aponi-modal-title">${title}</span>
          <button class="aponi-modal-close" aria-label="Close">×</button>
        </div>
        <div class="aponi-modal-content">${contentHtml}</div>
        <div class="aponi-modal-actions"></div>
      `;

      const actionsContainer = modal.querySelector(".aponi-modal-actions");
      actions.forEach(a => {
        const btn = document.createElement("button");
        btn.textContent = a.label;
        if (a.class) btn.className = a.class;
        btn.onclick = () => {
          if (a.onClick) a.onClick();
          cleanup();
          resolve(a.value ?? a.label);
        };
        actionsContainer.appendChild(btn);
      });

      const closeBtn = modal.querySelector(".aponi-modal-close");
      closeBtn.onclick = () => { cleanup(); resolve(null); };

      overlay.appendChild(modal);
      document.body.appendChild(overlay);

      const onEsc = (ev) => { if (ev.key === "Escape") { cleanup(); resolve(null); } };

      function cleanup() {
        document.removeEventListener("keydown", onEsc);
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      }
      document.addEventListener("keydown", onEsc);
    });
  }

  // ---------- Context Menu ----------
  // items: [{label, onClick}]
  // returns the created menu element so caller can close it manually if desired
  static contextMenu(x, y, items = []) {
    // close any existing
    AponiUI._closeContextMenu();

    const menu = document.createElement("div");
    menu.className = "aponi-context-menu";
    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;

    items.forEach(item => {
      const el = document.createElement("div");
      el.className = "context-item";
      el.textContent = item.label;
      el.onclick = (ev) => {
        ev.stopPropagation();
        try { item.onClick && item.onClick(); } catch(e){ console.warn(e); }
        menu.remove();
      };
      menu.appendChild(el);
    });

    document.body.appendChild(menu);
    // close on next click
    setTimeout(() => document.addEventListener("click", AponiUI._closeContextMenu, { once: true }), 0);
    // ESC closes
    function onKey(e) { if (e.key === "Escape") AponiUI._closeContextMenu(); }
    document.addEventListener("keydown", onKey, { once: true });

    // store ref
    AponiUI._activeContextMenu = menu;
    return menu;
  }

  static _closeContextMenu() {
    if (AponiUI._activeContextMenu && AponiUI._activeContextMenu.parentNode) {
      AponiUI._activeContextMenu.parentNode.removeChild(AponiUI._activeContextMenu);
      AponiUI._activeContextMenu = null;
    }
  }

  // ---------- Small helpers ----------
  // safe filename sanitizer
  static sanitizeFilename(name) {
    return String(name || "").replace(/[<>:"/\\|?*\u0000-\u001F]/g, "_").trim();
  }

  // nice confirm wrapper (async)
  static confirm(message, title = "Confirm") {
    return AponiUI.modal(title, `<p>${message}</p>`, [
      { label: "Cancel", class: "", value: false },
      { label: "OK", class: "btn", value: true }
    ]);
  }
}