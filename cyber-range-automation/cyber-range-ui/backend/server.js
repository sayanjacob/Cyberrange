const express = require('express');
const { exec, spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const WebSocket = require('ws');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const logPath = path.join(__dirname, 'logs', 'http.log'); // This reads logs/http.log relative to your project root

app.use(express.static(path.join(__dirname, '..', 'frontend')));

// Start scenario
app.get('/start', (req, res) => {
  exec('cd ../attacker && vagrant up && cd ../victim && vagrant up', (err, stdout) => {
    res.send(stdout || err.message);
  });
});

// Stop scenario
app.get('/stop', (req, res) => {
  exec('cd ../attacker && vagrant halt && cd ../victim && vagrant halt', (err, stdout) => {
    res.send(stdout || err.message);
  });
});

// WebSocket: stream log lines in real time
wss.on('connection', (ws) => {
  const tail = spawn('tail', ['-f', logPath]);

  tail.stdout.on('data', (data) => {
    ws.send(data.toString());
  });

  tail.stderr.on('data', (err) => {
    ws.send(`ERROR: ${err}`);
  });

  ws.on('close', () => {
    tail.kill();
  });
});

server.listen(3000, () => {
  console.log('Cyber Range UI + WS at port 3000');
});
