/**
 * WebSocket Client para Sincronización en Tiempo Real
 * FASE 6: Frontend WebSocket Integration
 * 
 * Uso:
 * ----
 * const client = new WebSocketClient(usuarioId, sucursalId, 'web');
 * client.on('mesa.cambio_estado', (datos) => {
 *     console.log('Mesa actualizada:', datos);
 *     // Actualizar UI
 * });
 */

class WebSocketClient {
    constructor(usuarioId, sucursalId, dispositivo = 'web') {
        this.usuarioId = usuarioId;
        this.sucursalId = sucursalId;
        this.dispositivo = dispositivo;
        this.token = `${usuarioId}:${sucursalId}:${dispositivo}`;
        
        this.ws = null;
        this.handlers = {};
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        
        this.eventQueue = [];
        this.isReady = false;
        
        console.log(`🚀 Inicializando WebSocket Client: ${this.token}`);
    }
    
    /**
     * Conecta al servidor WebSocket
     */
    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
            const host = window.location.host;
            const url = `${protocol}://${host}/ws/${this.token}`;
            
            console.log(`📡 Conectando a: ${url}`);
            this.ws = new WebSocket(url);
            
            this.ws.onopen = () => this._onOpen();
            this.ws.onmessage = (event) => this._onMessage(event);
            this.ws.onerror = (event) => this._onError(event);
            this.ws.onclose = () => this._onClose();
            
        } catch (error) {
            console.error('❌ Error conectando:', error);
            this._attemptReconnect();
        }
    }
    
    /**
     * Registra un handler para un evento
     */
    on(evento, callback) {
        if (!this.handlers[evento]) {
            this.handlers[evento] = [];
        }
        this.handlers[evento].push(callback);
    }
    
    /**
     * Desregistra un handler
     */
    off(evento, callback) {
        if (this.handlers[evento]) {
            this.handlers[evento] = this.handlers[evento].filter(h => h !== callback);
        }
    }
    
    /**
     * Emite un evento hacia el servidor
     */
    emit(evento, datos = {}) {
        const mensaje = {
            tipo: 'evento',
            evento: evento,
            datos: datos,
            timestamp: new Date().toISOString(),
            remitente_id: this.usuarioId,
            sucursal_id: this.sucursalId
        };
        
        if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(mensaje));
            console.log(`📤 Evento enviado: ${evento}`, datos);
        } else {
            console.warn(`⚠️ WebSocket no conectado. Evento encolado: ${evento}`);
            this.eventQueue.push(mensaje);
        }
    }
    
    /**
     * Desconecta el cliente
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            console.log('🔌 WebSocket desconectado');
        }
    }
    
    /**
     * Callbacks privados
     */
    _onOpen() {
        console.log('✅ WebSocket conectado');
        this.isConnected = true;
        this.isReady = true;
        this.reconnectAttempts = 0;
        
        // Enviar eventos encolados
        while (this.eventQueue.length > 0) {
            const mensaje = this.eventQueue.shift();
            this.ws.send(JSON.stringify(mensaje));
        }
        
        // Emitir evento de conexión
        this._fireHandler('__connected__', { timestamp: new Date() });
    }
    
    _onMessage(event) {
        try {
            const mensaje = JSON.parse(event.data);
            console.log(`📥 Evento recibido: ${mensaje.evento}`, mensaje.datos);
            
            // Disparar handlers del evento
            this._fireHandler(mensaje.evento, mensaje.datos);
            
            // Disparar handler genérico
            this._fireHandler('__any__', mensaje);
            
        } catch (error) {
            console.error('❌ Error parsando mensaje:', error);
        }
    }
    
    _onError(event) {
        console.error('❌ Error WebSocket:', event);
        this.isConnected = false;
    }
    
    _onClose() {
        console.log('⚠️ WebSocket cerrado');
        this.isConnected = false;
        this.isReady = false;
        this._attemptReconnect();
    }
    
    _fireHandler(evento, datos) {
        if (this.handlers[evento]) {
            this.handlers[evento].forEach(callback => {
                try {
                    callback(datos);
                } catch (error) {
                    console.error(`Error en handler de ${evento}:`, error);
                }
            });
        }
    }
    
    _attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`🔄 Reintentando conexión (${this.reconnectAttempts}/${this.maxReconnectAttempts}) en ${this.reconnectDelay}ms`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay);
        } else {
            console.error('❌ Max reconexión alcanzada');
            this._fireHandler('__disconnected__', { reason: 'max_attempts' });
        }
    }
    
    /**
     * Obtiene el estado de la conexión
     */
    getStatus() {
        return {
            conectado: this.isConnected,
            listo: this.isReady,
            token: this.token,
            reintentos: this.reconnectAttempts
        };
    }
}

/**
 * Instancia global del cliente WebSocket
 * Se inicializa automáticamente en templates
 */
let wsClient = null;

/**
 * Inicializa el cliente WebSocket globalmente
 */
function initWebSocketClient(usuarioId, sucursalId, dispositivo = 'web') {
    if (!wsClient) {
        wsClient = new WebSocketClient(usuarioId, sucursalId, dispositivo);
        wsClient.connect();
        
        // Guardar en window para acceso global
        window.wsClient = wsClient;
        
        return wsClient;
    }
    return wsClient;
}

/**
 * Helpers para actualización de UI
 */
const UIUpdates = {
    /**
     * Actualiza una mesa en el plano
     */
    actualizarMesa(mesaId, estado, datos = {}) {
        const mesaElement = document.querySelector(`[data-mesa-id="${mesaId}"]`);
        if (mesaElement) {
            mesaElement.classList.remove('libre', 'ocupada', 'reservada', 'mantenimiento');
            mesaElement.classList.add(estado);
            
            // Actualizar atributo de dato
            mesaElement.setAttribute('data-mesa-estado', estado);
            
            // Actualizar contenido si hay datos
            if (datos.cliente) {
                const clienteEl = mesaElement.querySelector('.mesa-cliente');
                if (clienteEl) {
                    clienteEl.textContent = datos.cliente;
                }
            }
            
            console.log(`🔄 Mesa ${mesaId} actualizada a ${estado}`);
        }
    },
    
    /**
     * Actualiza una comanda en la vista
     */
    actualizarComanda(comandaId, estado, datos = {}) {
        const comandaElement = document.querySelector(`[data-comanda-id="${comandaId}"]`);
        if (comandaElement) {
            comandaElement.classList.remove('pendiente', 'preparando', 'lista', 'entregada');
            comandaElement.classList.add(estado);
            
            // Actualizar badge de estado
            const estadoBadge = comandaElement.querySelector('.comanda-estado');
            if (estadoBadge) {
                estadoBadge.textContent = estado.toUpperCase();
                estadoBadge.className = `comanda-estado estado-${estado}`;
            }
            
            // Actualizar nota si existe
            if (datos.notas) {
                const notasEl = comandaElement.querySelector('.comanda-notas');
                if (notasEl) {
                    notasEl.textContent = datos.notas;
                }
            }
            
            console.log(`🔄 Comanda ${comandaId} actualizada a ${estado}`);
        }
    },
    
    /**
     * Añade notificación flotante
     */
    mostrarNotificacion(titulo, mensaje, tipo = 'info') {
        const notificacion = document.createElement('div');
        notificacion.className = `notificacion notificacion-${tipo}`;
        notificacion.innerHTML = `
            <div class="notificacion-contenido">
                <strong>${titulo}</strong>
                <p>${mensaje}</p>
            </div>
        `;
        
        document.body.appendChild(notificacion);
        
        // Animar entrada
        setTimeout(() => notificacion.classList.add('mostrar'), 10);
        
        // Remover después de 5 segundos
        setTimeout(() => {
            notificacion.classList.remove('mostrar');
            setTimeout(() => notificacion.remove(), 300);
        }, 5000);
    },
    
    /**
     * Actualiza contador de stats
     */
    actualizarStat(statId, valor, animacion = true) {
        const statElement = document.querySelector(`[data-stat="${statId}"]`);
        if (statElement) {
            const valueEl = statElement.querySelector('.stat-value');
            if (valueEl) {
                const oldValue = parseInt(valueEl.textContent);
                valueEl.textContent = valor;
                
                if (animacion && oldValue !== valor) {
                    valueEl.classList.add('actualizar');
                    setTimeout(() => valueEl.classList.remove('actualizar'), 300);
                }
            }
        }
    },
    
    /**
     * Actualiza lista en tiempo real (agrega/modifica)
     */
    actualizarListaItem(listId, itemId, datos) {
        const lista = document.querySelector(`[data-lista="${listId}"]`);
        if (!lista) return;
        
        let item = lista.querySelector(`[data-item-id="${itemId}"]`);
        
        if (!item) {
            // Crear nuevo item
            item = document.createElement('div');
            item.className = 'lista-item';
            item.setAttribute('data-item-id', itemId);
            lista.appendChild(item);
        }
        
        // Actualizar contenido
        item.innerHTML = datos.html || JSON.stringify(datos);
        console.log(`🔄 Lista ${listId} - Item ${itemId} actualizado`);
    },
    
    /**
     * Muestra indicador de "en vivo"
     */
    mostrarIndicadorVivo() {
        let indicator = document.querySelector('.websocket-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'websocket-indicator';
            indicator.innerHTML = '<span class="pulse"></span> EN VIVO';
            document.body.appendChild(indicator);
        }
        indicator.classList.add('conectado');
    },
    
    /**
     * Oculta indicador de "en vivo"
     */
    ocultarIndicadorVivo() {
        const indicator = document.querySelector('.websocket-indicator');
        if (indicator) {
            indicator.classList.remove('conectado');
        }
    }
};

/**
 * CSS para notificaciones y indicadores
 */
function inyectarEstilosWebSocket() {
    const style = document.createElement('style');
    style.textContent = `
        /* Notificaciones */
        .notificacion {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border-radius: 8px;
            padding: 16px 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            opacity: 0;
            transform: translateX(400px);
            transition: all 0.3s ease;
            z-index: 10000;
            max-width: 400px;
        }
        
        .notificacion.mostrar {
            opacity: 1;
            transform: translateX(0);
        }
        
        .notificacion-info {
            border-left: 4px solid #0f3460;
        }
        
        .notificacion-success {
            border-left: 4px solid #10b981;
        }
        
        .notificacion-warning {
            border-left: 4px solid #f59e0b;
        }
        
        .notificacion-error {
            border-left: 4px solid #ef4444;
        }
        
        .notificacion-contenido strong {
            display: block;
            color: #1f2937;
            margin-bottom: 4px;
        }
        
        .notificacion-contenido p {
            margin: 0;
            color: #6b7280;
            font-size: 14px;
        }
        
        /* Indicador WebSocket */
        .websocket-indicator {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 8px 16px;
            background: #f5f5f5;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            color: #999;
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 9999;
        }
        
        .websocket-indicator.conectado {
            background: #d1fae5;
            color: #065f46;
        }
        
        .pulse {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .websocket-indicator.conectado .pulse {
            background: #10b981;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Actualización de stats */
        .stat-value.actualizar {
            animation: bounce 0.3s ease;
        }
        
        @keyframes bounce {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        /* Estados de mesa */
        [data-mesa-id] {
            transition: all 0.3s ease;
        }
        
        [data-mesa-id].libre {
            background-color: #10b981;
        }
        
        [data-mesa-id].ocupada {
            background-color: #ef4444;
        }
        
        [data-mesa-id].reservada {
            background-color: #f59e0b;
        }
        
        [data-mesa-id].mantenimiento {
            background-color: #6b7280;
        }
    `;
    
    document.head.appendChild(style);
}

/**
 * Auto-inyectar estilos cuando se carga el script
 */
document.addEventListener('DOMContentLoaded', () => {
    inyectarEstilosWebSocket();
});

// Exportar para uso en módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { WebSocketClient, UIUpdates, initWebSocketClient };
}
