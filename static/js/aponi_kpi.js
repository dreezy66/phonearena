// static/js/aponi_kpi.js
// Aponi KPI Module – lightweight performance & API tracker with a tiny sparkline
// Usage:
// import { AponiKPI } from './aponi_kpi.js';
// const k = new AponiKPI('aponi-kpi'); k.init();
// k.logApiCall(durationMs, success);

export class AponiKPI {
  constructor(containerId = "aponi-kpi") {
    this.containerId = containerId;
    this.container = document.getElementById(containerId) || null;

    // fallback elements (if HTML already provides IDs)
    this.elCalls = document.getElementById("kpi-api-calls") || null;
    this.elErrors = document.getElementById("kpi-errors") || null;
    this.elLatency = document.getElementById("kpi-latency") || null;

    this.maxPoints = 60; // keep 60 samples
    this.latencyPoints = []; // ms
    this.callTimestamps = []; // epoch ms
    this.errorCount = 0;
    this._canvas = null;
    this._ctx = null;

    this._origFetch = window.fetch.bind(window);
    this._patchFetch();
    this._raf = null;
  }

  init() {
    // if there's no container, create a small one in the right-bottom corner
    if (!this.container) {
      this.container = document.createElement("div");
      this.container.id = this.containerId;
      this.container.style.position = "fixed";
      this.container.style.right = "18px";
      this.container.style.bottom = "18px";
      this.container.style.zIndex = 9997;
      this.container.style.width = "220px";
      document.body.appendChild(this.container);
    }
    this._renderBase();
    this._startRenderLoop();
  }

  _renderBase() {
    // prefer existing numeric elements if present to avoid altering layout
    if (!this.container.querySelector(".kpi-panel")) {
      this.container.innerHTML = `
        <div class="kpi-panel">
          <div class="kpi-item">
            <span class="kpi-label">API Calls</span>
            <span id="kpi-api-calls" class="kpi-value">0</span>
          </div>
          <div class="kpi-item">
            <span class="kpi-label">Errors</span>
            <span id="kpi-errors" class="kpi-value">0</span>
          </div>
          <div class="kpi-item">
            <span class="kpi-label">Latency</span>
            <span id="kpi-latency" class="kpi-value">-</span>
            <canvas id="${this.containerId}-spark" width="120" height="28" style="display:block;margin-top:6px"></canvas>
          </div>
        </div>
      `;
    }

    // wire elements (prefer existing DOM ids if present)
    this.elCalls = document.getElementById("kpi-api-calls") || this.elCalls || this.container.querySelector("#kpi-api-calls");
    this.elErrors = document.getElementById("kpi-errors") || this.elErrors || this.container.querySelector("#kpi-errors");
    this.elLatency = document.getElementById("kpi-latency") || this.elLatency || this.container.querySelector("#kpi-latency");

    this._canvas = document.getElementById(`${this.containerId}-spark`);
    if (this._canvas) this._ctx = this._canvas.getContext("2d");
  }

  // patch window.fetch to record latencies
  _patchFetch() {
    const self = this;
    window.fetch = async function (...args) {
      const start = performance.now();
      try {
        const res = await self._origFetch(...args);
        const dur = performance.now() - start;
        try { self.logApiCall(dur, res.ok); } catch (e) { console.warn(e); }
        return res;
      } catch (err) {
        const dur = performance.now() - start;
        try { self.logApiCall(dur, false); } catch (e) { console.warn(e); }
        throw err;
      }
    };
  }

  // Public: manual logging if desired
  logApiCall(durationMs, success = true) {
    // push values
    const t = Date.now();
    this.callTimestamps.push(t);
    this.latencyPoints.push(durationMs);
    if (!success) this.errorCount++;

    // cap arrays
    if (this.callTimestamps.length > this.maxPoints) this.callTimestamps.shift();
    if (this.latencyPoints.length > this.maxPoints) this.latencyPoints.shift();

    // update numeric UI
    this._updateNumbers();
  }

  _updateNumbers() {
    if (this.elCalls) this.elCalls.textContent = String(this.callTimestamps.length);
    if (this.elErrors) this.elErrors.textContent = String(this.errorCount || 0);
    if (this.elLatency) {
      const avg = this.latencyPoints.length ? (this.latencyPoints.reduce((a,b)=>a+b,0)/this.latencyPoints.length).toFixed(1) : "-";
      this.elLatency.textContent = `${avg} ms`;
    }
  }

  // draw tiny sparkline for latency
  _drawSpark() {
    if (!this._ctx || !this._canvas) return;
    const ctx = this._ctx;
    const w = this._canvas.width;
    const h = this._canvas.height;
    ctx.clearRect(0,0,w,h);

    const data = this.latencyPoints;
    if (!data.length) return;

    // normalize
    const max = Math.max(...data) || 1;
    const min = Math.min(...data);
    const range = Math.max(1, max - min);

    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "rgba(90,200,250,0.9)";
    ctx.beginPath();
    for (let i = 0; i < data.length; i++) {
      const x = Math.floor((i / (data.length - 1 || 1)) * (w - 2)) + 1;
      const y = Math.floor(h - 4 - ((data[i] - min) / range) * (h - 8));
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // draw a soft fill
    ctx.lineTo(w-1, h-3);
    ctx.lineTo(1, h-3);
    ctx.closePath();
    const g = ctx.createLinearGradient(0,0,0,h);
    g.addColorStop(0, "rgba(90,200,250,0.12)");
    g.addColorStop(1, "rgba(90,200,250,0.02)");
    ctx.fillStyle = g;
    ctx.fill();
  }

  // animation loop to redraw sparkline when needed
  _startRenderLoop() {
    const loop = () => {
      this._drawSpark();
      this._raf = requestAnimationFrame(loop);
    };
    this._raf = requestAnimationFrame(loop);
  }

  stop() {
    if (this._raf) cancelAnimationFrame(this._raf);
    // restore native fetch if needed (left intentionally patched — restore only if you want)
    // window.fetch = this._origFetch;
  }
}