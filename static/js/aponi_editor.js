// aponi_editor.js
export class Editor {
  constructor(cfg){
    this.cfg = cfg;
    this.tabsEl = document.getElementById('tabs');
    this.codeEl = document.getElementById('code');
    this.openTabs = new Map(); // path -> {content, unsaved}
    this.active = null;
    this.autosaveTimer = null;
    this.onSave = null; // callback(path, content)
    this._wire();
  }

  _wire(){
    // when user edits code area -> mark unsaved and debounce autosave
    this.codeEl.addEventListener('input', () => {
      if(!this.active) return;
      const state = this.openTabs.get(this.active);
      const newContent = this.codeEl.textContent;
      if(state.content !== newContent){
        state.content = newContent;
        state.unsaved = true;
        this._renderTabs();
        if(this.autosaveTimer) clearTimeout(this.autosaveTimer);
        this.autosaveTimer = setTimeout(()=> this.saveActive(), 1200);
      }
    });
  }

  openTab(path, content){
    if(!this.openTabs.has(path)){
      this.openTabs.set(path, {content: content||'', unsaved:false});
    } else {
      const st = this.openTabs.get(path);
      st.content = content||st.content;
    }
    this.activateTab(path);
    this._renderTabs();
  }

  activateTab(path){
    this.active = path;
    const st = this.openTabs.get(path);
    this.codeEl.textContent = st ? st.content : '';
    this._renderTabs();
  }

  _renderTabs(){
    this.tabsEl.innerHTML = '';
    for(const [path, st] of this.openTabs.entries()){
      const t = document.createElement('div');
      t.className = 'tab' + (this.active === path ? ' active':'' ) + (st.unsaved ? ' unsaved':'');
      t.textContent = path.split('/').pop();
      t.onclick = ()=> this.activateTab(path);
      const close = document.createElement('span');
      close.className = 'close';
      close.textContent = '✕';
      close.onclick = (e)=>{ e.stopPropagation(); this.closeTab(path); };
      t.appendChild(close);
      this.tabsEl.appendChild(t);
    }
  }

  closeTab(path){
    this.openTabs.delete(path);
    if(this.active === path) this.active = this.openTabs.size ? Array.from(this.openTabs.keys())[0] : null;
    if(this.active) this.activateTab(this.active);
    else this.codeEl.textContent = '';
    this._renderTabs();
  }

  async saveActive(){
    if(!this.active) return;
    const st = this.openTabs.get(this.active);
    if(!st || !st.unsaved) return;
    if(this.onSave) await this.onSave(this.active, st.content);
    st.unsaved = false;
    this._renderTabs();
  }
}