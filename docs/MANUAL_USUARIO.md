# Manual de funcionamiento

## Acceso y roles

En la instalación inicial ingrese con `admin` y contraseña `Admin123*`; cámbiela antes de operar. Desde **Usuarios** el administrador crea accesos para administrador, caja, mesero y cocina, opcionalmente vinculados a un empleado. El mesero que abre una comanda queda registrado en la venta. Cocina usa su propia pantalla para llevar cada preparación de pendiente a entregada.

## Operación de mesas y comandas

1. Entre a **Mesas y planos**. Cree las zonas que necesite: salón, terraza, barra o domicilios.
2. Agregue cada mesa con nombre y capacidad. Cada zona tiene un plano visual donde las mesas se distinguen por estado: verde libre y naranja ocupada.
3. Toque una mesa desde el computador, móvil o tableta. En la comanda, pulse los productos para agregarlos. El primer artículo abre automáticamente la cuenta y ocupa la mesa.
4. Revise el total y pulse **Cobrar y cerrar mesa**. Se descuenta el inventario y la mesa vuelve a estar disponible.

## Comprobantes y facturación interna

En **Configuración** defina NIT, dirección, teléfono, impuesto global, prefijo y siguiente consecutivo. Al finalizar un cobro el sistema asigna un consecutivo y abre un comprobante profesional, listo para imprimir desde el navegador. Esta función es un comprobante interno: la facturación electrónica debe conectarse al proveedor tecnológico autorizado según la normativa del país antes de usarla con efectos fiscales.

## Inventario y producción

El módulo **Inventario** muestra existencias y resalta las referencias por debajo de su mínimo. Cada producto tiene tipo `venta`, `insumo` o `elaborado`. En la siguiente iteración se deben habilitar formularios de entradas, ajustes, recetas y órdenes de producción; el modelo ya contiene movimientos de inventario para conservar trazabilidad.

### Costeo de materias primas y recetas

Registre las compras de materias primas desde **Compras**, seleccionando el producto y la cantidad recibida. El sistema aumenta las existencias y recalcula el costo promedio ponderado. En **Producción**, cree una receta de tipo `producción` para un producto elaborado, agregue sus componentes y la merma de cada uno, y ejecute los lotes. El costo de los componentes consumidos define el costo unitario del lote producido y actualiza el costo promedio del producto elaborado.

Para hamburguesas u otros platos, cree el artículo final como `venta` y una receta de tipo `venta`; incluya, por ejemplo, pan, carne preparada y vegetales. Al facturarlo, se consumen esos componentes y se guarda el costo histórico de esa venta. El informe gerencial presenta venta, costo y margen por producto.

## Domicilios y para llevar

En **Domicilios** cree el pedido indicando cliente, dirección, contacto, repartidor y cargo de envío. Agregue productos desde la pantalla del pedido y actualice el recorrido `recibido → preparando → listo → en camino → entregado`. Cuando corresponda, facture desde ese mismo pedido; no se requiere una mesa física.

## Administración

- **Gastos:** registre fecha, concepto, categoría, proveedor y valor.
- **Cartera:** cree clientes, asigne cupo y relacione ventas a crédito; gestione abonos y vencimientos.
- **Nómina y turnos:** cree empleados con cargo y salario; cada ingreso genera un turno y el retiro registra su salida.
- **Informes:** consulte ventas, gastos, utilidad, productos, inventario, cartera y asistencia por rango de fechas.

## Uso con tabletas

Abra la misma dirección del servidor desde una tableta conectada a la red del local, por ejemplo `http://IP-DEL-SERVIDOR:8000/mesas`. La vista se reordena automáticamente para pantalla táctil. Para operación real se debe habilitar acceso por usuario y asignar permisos de mesero/caja/cocina/administración.
