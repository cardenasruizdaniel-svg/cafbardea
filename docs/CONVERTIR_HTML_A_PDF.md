# 📖 GUÍA: Convertir Documentación HTML a PDF

## 🎯 Problema

Los archivos de documentación están en formato HTML. Para convertirlos a PDF, tienes varias opciones:

## ✅ Opción 1: Navegador (Más Fácil)

### Pasos:
1. **Abrir archivo HTML en navegador**
   - Haz doble clic en: `MANUAL_COMPLETO.html`
   - O arrastra a navegador (Chrome, Edge, Firefox)

2. **Guardar como PDF**
   - Presiona: **Ctrl + P** (Windows) o **Cmd + P** (Mac)
   - En impresora, selecciona: "Guardar como PDF"
   - Haz clic en "Guardar"

3. **Archivos PDF generados**
   - `MANUAL_COMPLETO.pdf`
   - `CLOUD_DEPLOYMENT_GUIDE.pdf`

---

## ✅ Opción 2: Instalar Pandoc + Motor PDF

Si quieres automatizar la conversión:

### Windows (PowerShell como Admin):

```powershell
# 1. Instalar Pandoc (si no está instalado)
choco install pandoc -y

# 2. Instalar motor PDF
pip install weasyprint

# 3. Convertir
pandoc MANUAL_COMPLETO.html -o MANUAL_COMPLETO.pdf --pdf-engine=weasyprint
pandoc CLOUD_DEPLOYMENT_GUIDE.html -o CLOUD_DEPLOYMENT_GUIDE.pdf --pdf-engine=weasyprint
```

### Mac/Linux:

```bash
# 1. Instalar Pandoc
brew install pandoc

# 2. Instalar motor PDF
pip install weasyprint

# 3. Convertir
pandoc MANUAL_COMPLETO.html -o MANUAL_COMPLETO.pdf --pdf-engine=weasyprint
pandoc CLOUD_DEPLOYMENT_GUIDE.html -o CLOUD_DEPLOYMENT_GUIDE.pdf --pdf-engine=weasyprint
```

---

## ✅ Opción 3: Servicios Online

Si no quieres instalar nada:

1. **CloudConvert** (https://cloudconvert.com)
   - Sube el archivo HTML
   - Selecciona formato: PDF
   - Descarga

2. **Online-Convert** (https://www.online-convert.com)
   - Sube archivo
   - Selecciona: HTML to PDF
   - Convierte

---

## 📋 Checklist Final

- [ ] Archivos HTML disponibles en `docs/`
- [ ] Navegador instalado (Chrome, Edge, Firefox)
- [ ] Convertir a PDF usando Ctrl+P
- [ ] Guardar archivos PDF en carpeta `docs/`
- [ ] Verificar que PDFs se ven correctamente
- [ ] Incluir PDFs en distribución final

---

**Nota:** Los archivos HTML son funcionales y pueden ser consultados directamente en navegador. La conversión a PDF es solo para archivado e impresión.
