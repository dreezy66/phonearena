// aponi_explorer.js
export class Explorer {
  constructor(cfg){
    this.cfg = cfg;
    this.api = cfg.API_PATH;
    this.el = document.getElementById('explorer');
    this.baseEl = document.getElementById('breadcrumbs') || null;
    this.currentPath = ".";
    this.onOpenFile = null; // callback(path, content)
  }

  async init(){
    await this.ping();
    await this.refresh();
  }

  async ping(){
    try {
      const r = await fetch(this.api.replace(/\/api$/,'') + '/api/ping');
      const j = await r.json();
      if(this.baseEl) this.baseEl.textContent = j.base || "/";
    } catch(e) {
      console.warn('ping failed', e);
    }
  }

  async refresh(path="."){
    this.currentPath = path || ".";
    this.el.innerHTML = 'Loading…';
    try {
      const r = await fetch(this.api + `/explorer?path=${encodeURIComponent(path)}&children=true`);
      const j = await r.json();
      if (j.error) { this.el.textContent = j.error; return; }
      this.renderList(j.items || []);
    } catch(e){
      this.el.textContent = 'Explorer error';
      console.error(e);
    }
  }

  renderList(items){
    this.el.innerHTML = '';
    if (this.currentPath !== "."){
      const parent = document.createElement('div');
      parent.className = 'tree-item folder';
      parent.innerHTML = `<div class="file-name">.. (parent)</div>`;
      parent.onclick = ()=> {
        const parts = this.currentPath.split('/').filter(Boolean);
        parts.pop();
        this.refresh(parts.length ? parts.join('/') : ".");
      };
      this.el.appendChild(parent);
    }

    items.forEach(it => {
      const row = document.createElement('div');
      row.className = 'tree-item ' + (it.is_dir ? 'folder' : 'file');
      row.dataset.path = it.path;
      row.innerHTML = `<div style="width:20px;flex:0 0 20px">${it.is_dir ? "📁":"📄"}</div><div class="file-name" title="${it.name}">${it.name}</div>`;
      row.onclick = async () => {
        if(it.is_dir) return this.refresh(it.path);
        await this.fetchAndOpenFile(it.path);
      };
      this.el.appendChild(row);
    });
  }

  async fetchAndOpenFile(path){
    try {
      const r = await fetch(this.api + `/file?path=${encodeURIComponent(path)}`);
      const j = await r.json();
      if(j.error) return console.warn('open file error', j);
      if(this.onOpenFile) this.onOpenFile(path, j.content || '');
    } catch(e){ console.error(e); }
  }

  async ensurePathAndOpen(path){
    // ensure current view contains path's parent
    const parent = path.split('/').slice(0,-1).join('/') || ".";
    if(parent !== this.currentPath) await this.refresh(parent);
  }

  refreshCurrent(){ this.refresh(this.currentPath); }
}