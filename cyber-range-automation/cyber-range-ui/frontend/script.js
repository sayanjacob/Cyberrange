function startScenario() {
  fetch('/start').then(r => r.text()).then(console.log);
}
function stopScenario() {
  fetch('/stop').then(r => r.text()).then(console.log);
}

// WebSocket connection for live logs
const logOutput = document.getElementById('log-output');
const ws = new WebSocket('ws://' + window.location.host);

ws.onmessage = (event) => {
  logOutput.textContent += event.data;
  logOutput.scrollTop = logOutput.scrollHeight;
};
