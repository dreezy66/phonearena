// aponi_main.js
export const CONFIG = {
  API_BASE: window.APONI_API_BASE || "http://127.0.0.1:8765",
  API_PATH: (window.APONI_API_BASE || "http://127.0.0.1:8765") + "/api"
};

import { Explorer } from './aponi_explorer.js';
import { Editor } from './aponi_editor.js';
import { ConsoleUI } from './aponi_console.js';
import { QuickSearch } from './aponi_search.js';
import { AponiKPI } from './aponi_kpi.js';
import { AponiUI } from './aponi_ui.js';
import { AponiKPI } from './aponi_kpi.js';
import { AponiUI } from './aponi_ui.js';

document.addEventListener('DOMContentLoaded', async () => {
  const kpi = new AponiKPI('aponi-kpi'); // ensure an element with that ID exists or it will create one
  kpi.init();

  AponiUI.toast("Welcome to Aponi Dashboard 🚀");

  // ...init explorer/editor/console...
});
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize KPI tracker
  const kpi = new AponiKPI("aponi-kpi");
  kpi.init();

  // Welcome toast
  AponiUI.toast("Welcome to Aponi Dashboard 🚀");

  // Initialize core modules
  const explorer = new Explorer(CONFIG);
  const editor = new Editor(CONFIG);
  const consoleUI = new ConsoleUI(CONFIG);
  const quick = new QuickSearch(CONFIG);

  // File open -> editor tab
  explorer.onOpenFile = (path, content) => {
    editor.openTab(path, content);
  };

  // Editor save -> backend write
  editor.onSave = async (path, content) => {
    try {
      const res = await fetch(CONFIG.API_PATH + '/file', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ path, content, overwrite: true })
      });
      const j = await res.json();
      consoleUI.log(`💾 Saved ${path}: ${j.ok ? 'ok' : JSON.stringify(j)}`);
      explorer.refreshCurrent();
    } catch (e) {
      consoleUI.log('❌ Save error: ' + e);
    }
  };

  // Quick search select -> open file
  quick.onSelect = (path) => {
    explorer.ensurePathAndOpen(path)
      .then(() => explorer.fetchAndOpenFile(path));
  };

  // Expose for legacy/global hooks
  window.aponi = { explorer, editor, consoleUI, quick, kpi };

  // Initial load
  await explorer.init();
  consoleUI.log('✅ Aponi ready');
});