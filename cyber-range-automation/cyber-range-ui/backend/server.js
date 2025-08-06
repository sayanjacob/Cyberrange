const express = require('express');
const { exec } = require('child_process');
const app = express();
const port = 3000;

app.use(express.static('frontend'));

app.get('/start', (req, res) => {
  exec('cd ../attacker && vagrant up && cd ../victim && vagrant up', (err, stdout) => {
    res.send(stdout || err.message);
  });
});

app.get('/stop', (req, res) => {
  exec('cd ../attacker && vagrant halt && cd ../victim && vagrant halt', (err, stdout) => {
    res.send(stdout || err.message);
  });
});

app.get('/log', (req, res) => {
  exec('cat ../attacker/http.log', (err, stdout) => {
    res.send(stdout || err.message);
  });
});

app.listen(port, () => {
  console.log(`Cyber Range UI running at http://localhost:${port}`);
});
