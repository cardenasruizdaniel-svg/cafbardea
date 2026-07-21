# Manual de parametrización y marca blanca

## Identidad de la empresa

La tabla `empresas` contiene una única organización por instalación: `nombre`, `nit`, `logo_url`, `color_primario`, `color_secundario` y `moneda`. Los colores se inyectan como variables CSS (`--primary`, `--soft`) y todo el aplicativo se adapta inmediatamente a la marca.

Ejemplo en PostgreSQL:

```sql
UPDATE empresas
SET nombre = 'Bar La Plaza', nit = '901234567-8',
    logo_url = 'https://midominio.com/logo.svg',
    color_primario = '#6d28d9', color_secundario = '#ede9fe', moneda = 'COP'
WHERE id = 1;
```

## Parámetros operativos

1. Cree zonas según el plano físico del negocio.
2. Cree mesas identificables para el equipo (M1, Barra-2, Terraza-5) y asigne su capacidad.
3. Cree categorías y productos con código único, precio, costo, existencias y mínimo.
4. Defina los tipos: `insumo` para materia prima, `elaborado` para preparación con receta y `venta` para ítems vendidos directamente.
5. Cree clientes de crédito, empleados, cargos y salarios.

## Parámetros colombianos y electrónicos

Registre si la instalación corresponde a una persona natural o jurídica, su tipo societario (por ejemplo SAS), el régimen tributario y el modo de operación electrónica. Para pasar a **producción** con facturación electrónica, el sistema exige indicar un proveedor tecnológico; las credenciales, certificado digital, rangos autorizados y el identificador de software se deben cargar únicamente con los datos suministrados por la DIAN o el proveedor.

En **Liquidar nómina**, registre los valores oficiales por vigencia (salario mínimo, auxilio, tope y porcentajes que correspondan). Las liquidaciones dejan los devengados, deducciones y el estado electrónico listos para la integración; CUNE, firma y transmisión solo deben generarse por la integración habilitada, nunca simulados localmente.

## Multiempresa y sucursales

Esta entrega es una instalación por empresa, ideal para marca blanca. Para SaaS multiempresa se debe añadir `empresa_id` a todas las entidades operativas, filtrar todas las consultas por el tenant del usuario y agregar `sucursal_id` cuando una empresa tenga varias sedes. Nunca se debe mezclar información entre tenants.
