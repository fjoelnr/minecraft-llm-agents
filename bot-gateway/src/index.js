import { WebSocketServer } from 'ws';
const wss = new WebSocketServer({ port: 3000 });
console.log('Gateway WS on ws://localhost:3000');
wss.on('connection', (ws) => {
  ws.on('message', (msg) => {
    try { const d = JSON.parse(msg.toString()); ws.send(JSON.stringify({ok:true, echo:d})); }
    catch { ws.send(JSON.stringify({ok:false, error:'bad json'})); }
  });
});