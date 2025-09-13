import { WebSocketServer } from 'ws'

const wss = new WebSocketServer({ port: 3000 })
console.log('Gateway WS listening on ws://localhost:3000')

wss.on('connection', (ws) => {
  ws.on('message', (msg) => {
    try {
      const data = JSON.parse(msg.toString())
      if (data.type === 'chat') {
        console.log('[CHAT]', data.text)
        ws.send(JSON.stringify({ ok: true, echo: data.text }))
      } else {
        ws.send(JSON.stringify({ ok: false, error: 'unknown type' }))
      }
    } catch (e) {
      ws.send(JSON.stringify({ ok: false, error: 'bad json' }))
    }
  })
})
