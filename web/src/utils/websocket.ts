import { ref, reactive } from 'vue'
import { defaultWsUrl } from './api'

interface SocketState {
  isConnected: boolean
  isStreaming: boolean
  statusText: string
}

class WebSocketService {
  private socket: WebSocket | null = null
  private heartbeatTimer: number | null = null
  private sessionId: string = ''
  private messageCallback: ((data: any) => void) | null = null
  
  public state = reactive<SocketState>({
    isConnected: false,
    isStreaming: false,
    statusText: 'offline'
  })
  
  public wsUrl = ref(defaultWsUrl)
  
  setSessionId(sessionId: string) {
    this.sessionId = sessionId
  }
  
  setMessageCallback(callback: (data: any) => void) {
    this.messageCallback = callback
  }
  
  connect() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }
    
    this.state.statusText = 'connecting'
    this.socket = new WebSocket(this.wsUrl.value)
    
    this.socket.onopen = () => {
      this.state.isConnected = true
      this.state.statusText = 'connected'
      this.startHeartbeat()
    }
    
    this.socket.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (this.messageCallback) {
        this.messageCallback(payload)
      }
    }
    
    this.socket.onerror = () => {
      this.state.statusText = 'error'
    }
    
    this.socket.onclose = () => {
      this.state.isConnected = false
      this.state.isStreaming = false
      this.state.statusText = 'offline'
      this.stopHeartbeat()
      this.socket = null
    }
  }
  
  disconnect() {
    if (!this.socket) return
    this.stopHeartbeat()
    this.socket.close()
    this.socket = null
  }
  
  send(data: any) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return false
    }
    
    this.socket.send(JSON.stringify({
      ...data,
      session_id: this.sessionId
    }))
    return true
  }
  
  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return
      this.socket.send(JSON.stringify({ type: 'heartbeat', session_id: this.sessionId }))
    }, 30000)
  }
  
  private stopHeartbeat() {
    if (this.heartbeatTimer !== null) {
      window.clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}

// 导出单例实例
export const wsService = new WebSocketService()
