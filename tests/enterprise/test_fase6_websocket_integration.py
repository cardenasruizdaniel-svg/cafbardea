"""
Tests para FASE 6: Frontend WebSocket Integration
Valida la integración de WebSocket en templates
"""
import pytest
import os


class TestWebSocketIntegration:
    """Tests de integración WebSocket con frontend"""
    
    def test_websocket_client_archivo_existe(self):
        """Verifica que el archivo cliente WebSocket existe"""
        assert os.path.exists("app/static/js/websocket-client.js"), "websocket-client.js debe existir"
    
    def test_base_html_template_existe(self):
        """Verifica que base.html template existe"""
        assert os.path.exists("app/templates/base.html"), "base.html debe existir"
    
    def test_comanda_html_template_existe(self):
        """Verifica que comanda.html template existe"""
        assert os.path.exists("app/templates/comanda.html"), "comanda.html debe existir"
    
    def test_dashboard_html_template_existe(self):
        """Verifica que dashboard.html template existe"""
        assert os.path.exists("app/templates/dashboard.html"), "dashboard.html debe existir"


class TestUIUpdates:
    """Tests unitarios para funciones UIUpdates"""
    
    def test_ui_updates_functions_exist(self):
        """Verifica que las funciones UIUpdates existen en el JS"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        # Verificar que UIUpdates está definido
        assert "const UIUpdates = {" in js_file
        assert "initWebSocketClient" in js_file
    
    def test_websocket_client_class_methods(self):
        """Verifica que WebSocketClient tenga los métodos necesarios"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        # Métodos principales
        assert "connect()" in js_file
        assert "on(evento, callback)" in js_file
        assert "emit(evento" in js_file
        assert "disconnect()" in js_file
        assert "getStatus()" in js_file
        
        # Métodos UIUpdates
        assert "actualizarMesa" in js_file
        assert "actualizarComanda" in js_file
        assert "mostrarNotificacion" in js_file
        assert "actualizarStat" in js_file
        assert "mostrarIndicadorVivo" in js_file


class TestWebSocketMessageFormat:
    """Tests del formato de mensajes WebSocket"""
    
    def test_mensaje_ws_format(self):
        """Verifica el formato de mensaje WebSocket"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        # Verificar estructura de mensaje
        assert "tipo:" in js_file
        assert "evento:" in js_file
        assert "datos:" in js_file
        assert "timestamp:" in js_file
        assert "remitente_id:" in js_file


class TestEventHandlers:
    """Tests de registración de event handlers"""
    
    def test_handler_registration(self):
        """Verifica que se puedan registrar handlers"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        # Verificar métodos de handler
        assert "this.handlers[evento] = []" in js_file
        assert "this.handlers[evento].push(callback)" in js_file
        assert "_fireHandler" in js_file
    
    def test_built_in_event_handlers(self):
        """Verifica handlers predefinidos en templates"""
        # Dashboard
        with open("app/templates/dashboard.html", "r", encoding="utf-8") as f:
            dashboard = f.read()
        assert "wsClient.on('venta.pagada'" in dashboard
        assert "wsClient.on('comanda.creada'" in dashboard
        assert "wsClient.on('comanda.entregada'" in dashboard
        assert "wsClient.on('producto.stock_bajo'" in dashboard
        
        # Comanda
        with open("app/templates/comanda.html", "r", encoding="utf-8") as f:
            comanda = f.read()
        assert "wsClient.on('comanda.actualizada'" in comanda
        assert "wsClient.on('mesa.cambio_estado'" in comanda
        assert "wsClient.emit('comanda.producto_agregado'" in comanda
        assert "wsClient.emit('comanda.pagada'" in comanda


class TestReconnection:
    """Tests de reconexión automática"""
    
    def test_reconnection_logic(self):
        """Verifica que el cliente tiene lógica de reconexión"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        assert "_attemptReconnect" in js_file
        assert "maxReconnectAttempts" in js_file
        assert "reconnectDelay" in js_file
        assert "setTimeout" in js_file


class TestNotifications:
    """Tests del sistema de notificaciones"""
    
    def test_notification_styles_included(self):
        """Verifica que los estilos de notificación están incluidos"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        # Estilos predefinidos
        assert ".notificacion {" in js_file
        assert ".notificacion-info" in js_file
        assert ".notificacion-success" in js_file
        assert ".notificacion-warning" in js_file
        assert ".notificacion-error" in js_file
    
    def test_notification_types(self):
        """Verifica tipos de notificación disponibles"""
        with open("app/templates/dashboard.html", "r", encoding="utf-8") as f:
            dashboard = f.read()
        
        assert "'success'" in dashboard
        assert "'info'" in dashboard
        assert "'warning'" in dashboard


class TestStatusIndicator:
    """Tests del indicador de estado de conexión"""
    
    def test_status_indicator_implementation(self):
        """Verifica que el indicador de estado está implementado"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        assert "websocket-indicator" in js_file
        assert "mostrarIndicadorVivo" in js_file
        assert "ocultarIndicadorVivo" in js_file
        assert ".pulse" in js_file


class TestWebSocketInitialization:
    """Tests de inicialización de WebSocket"""
    
    def test_websocket_client_constructor(self):
        """Verifica constructor de WebSocketClient"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        assert "constructor(usuarioId, sucursalId, dispositivo = 'web')" in js_file
        assert "this.token = `" in js_file
        assert "this.ws = null" in js_file
        assert "this.handlers = {}" in js_file
    
    def test_websocket_token_format(self):
        """Verifica formato del token WebSocket"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        # Formato: usuarioId:sucursalId:dispositivo
        assert "${usuarioId}:${sucursalId}:${dispositivo}" in js_file


class TestEventQueueing:
    """Tests del sistema de cola de eventos"""
    
    def test_event_queuing_while_disconnected(self):
        """Verifica que se encolan eventos cuando desconectado"""
        with open("app/static/js/websocket-client.js", "r", encoding="utf-8") as f:
            js_file = f.read()
        
        assert "this.eventQueue = []" in js_file
        assert "this.eventQueue.push(mensaje)" in js_file
        assert "while (this.eventQueue.length > 0)" in js_file or "eventQueue.forEach" in js_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

