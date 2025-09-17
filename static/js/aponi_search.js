// aponi_search.js
export class QuickSearch {
  constructor(cfg){
    this.cfg = cfg;
    this.input = document.getElementById('global-search');
    this.btn = document.getElementById('search-btn');
    this.onSelect = null;
    this._wire();
  }

  _wire(){
    this.btn.onclick = ()=> this.query(this.input.value);
    this.input.addEventListener('keydown', (e)=>{
      if(e.key === 'Enter') this.query(this.input.value);
      if(e.key === 'k' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); this.input.focus(); }
    });
  }

  async query(q){
    const term = String(q || '').trim();
    if(!term) return;
    // simple strategy: request root explorer and find matches recursively but shallow
    try {
      const r = await fetch(this.cfg.API_PATH + `/explorer?path=&children=true`);
      const j = await r.json();
      if (j.items){
        const matches = [];
        const stack = [...j.items];
        while(stack.length && matches.length < 30){
          const it = stack.shift();
          if(it.name && it.name.toLowerCase().includes(term.toLowerCase())) matches.push(it);
          if(it.is_dir) {
            // fetch children lazily but only one level deep to limit CPU
            const rr = await fetch(this.cfg.API_PATH + `/explorer?path=${encodeURIComponent(it.path)}&children=false`);
            const cj = await rr.json();
            if(cj.items) stack.push(...cj.items);
          }
        }
        if(matches.length){
          // open the first match by default
          const pick = matches[0];
          if(this.onSelect) this.onSelect(pick.path);
        } else {
          alert('No matches found (shallow search). Try a different term.');
        }
      }
    } catch(e){
      console.warn('quick search failed', e);
    }
  }
}