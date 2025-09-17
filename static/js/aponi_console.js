// aponi_console.js
export class ConsoleUI {
  constructor(cfg){
    this.cfg = cfg;
    this.el = document.getElementById('console');
    this.input = document.getElementById('console-in');
    this._wire();
  }

  _wire(){
    this.input.addEventListener('keydown', (e)=>{
      if(e.key === 'Enter'){
        const cmd = this.input.value.trim();
        if(cmd) this.send(cmd);
        this.input.value = '';
      }
    });
  }

  log(msg){
    const ts = new Date().toISOString().replace('T',' ').split('.')[0];
    this.el.textContent += `\n[${ts}] ${msg}`;
    this.el.scrollTop = this.el.scrollHeight;
  }

  async send(cmd){
    this.log('$ ' + cmd);
    try {
      const res = await fetch(this.cfg.API_PATH + '/run', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ path: '.', args: [cmd] })
      });
      const j = await res.json();
      this.log('run: ' + (j.ok ? 'submitted' : JSON.stringify(j)));
    } catch(e){
      this.log('cmd error: ' + e);
    }
  }
}