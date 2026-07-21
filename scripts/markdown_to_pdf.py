#!/usr/bin/env python3
"""Convertir Markdown a PDF para documentación de CafBarDLA"""

import subprocess
import os
from pathlib import Path

def convert_markdown_to_pdf(md_file, pdf_file):
    """Convertir Markdown a PDF usando pandoc + navegador"""
    
    md_path = Path(md_file)
    pdf_path = Path(pdf_file)
    html_temp = pdf_path.parent / f"{pdf_path.stem}_temp.html"
    
    print(f"📄 Procesando: {md_path.name}")
    
    try:
        # Paso 1: Convertir Markdown a HTML con pandoc
        print(f"  1️⃣  Convertir a HTML...")
        result = subprocess.run(
            ["pandoc", str(md_path), "-o", str(html_temp), 
             "--standalone", "--css=style.css"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  ❌ Error en pandoc: {result.stderr}")
            return False
        
        # Paso 2: Crear HTML con estilos CSS mejorados
        print(f"  2️⃣  Agregar estilos CSS...")
        with open(html_temp, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Inyectar CSS personalizado
        css_styles = """
        <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            line-height: 1.6; 
            color: #333;
            margin: 40px;
        }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }
        h3 { color: #7f8c8d; }
        code { 
            background-color: #f4f4f4; 
            padding: 2px 6px; 
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        pre { 
            background-color: #2c3e50; 
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 0.9em;
        }
        table { 
            border-collapse: collapse; 
            width: 100%; 
            margin: 20px 0;
        }
        th, td { 
            border: 1px solid #bdc3c7; 
            padding: 12px; 
            text-align: left;
        }
        th { 
            background-color: #34495e; 
            color: white;
        }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .emoji { font-size: 1.2em; }
        blockquote {
            border-left: 4px solid #3498db;
            margin: 20px 0;
            padding-left: 20px;
            font-style: italic;
            color: #7f8c8d;
        }
        </style>
        """
        
        if "</head>" in html_content:
            html_content = html_content.replace("</head>", css_styles + "</head>")
        else:
            html_content = css_styles + html_content
        
        # Paso 3: Usar print-to-PDF de navegador (Chrome)
        print(f"  3️⃣  Generar PDF...")
        with open(html_temp, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Intentar con Chrome
        try:
            subprocess.run([
                "chrome.exe",
                f"--headless=new",
                f"--disable-gpu",
                f"--print-to-pdf={pdf_path}",
                str(html_temp.absolute())
            ], capture_output=True, timeout=30)
            
            if pdf_path.exists():
                size_mb = pdf_path.stat().st_size / (1024 * 1024)
                print(f"  ✅ PDF generado: {pdf_path.name} ({size_mb:.2f} MB)")
                return True
        except:
            pass
        
        # Si Chrome falla, intentar con Edge
        try:
            subprocess.run([
                "msedge.exe",
                f"--headless",
                f"--disable-gpu",
                f"--print-to-pdf={pdf_path}",
                str(html_temp.absolute())
            ], capture_output=True, timeout=30)
            
            if pdf_path.exists():
                size_mb = pdf_path.stat().st_size / (1024 * 1024)
                print(f"  ✅ PDF generado: {pdf_path.name} ({size_mb:.2f} MB)")
                return True
        except:
            pass
        
        # Fallback: Simplemente guardar como HTML
        print(f"  ⚠️  Chrome/Edge no disponibles")
        print(f"  💾 Guardando como HTML: {html_temp}")
        print(f"  📖 Puede convertir a PDF manualmente abriendo en navegador y Ctrl+P")
        
        # Copiar HTML como alternativa
        import shutil
        shutil.copy(html_temp, str(pdf_path).replace('.pdf', '.html'))
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        # Limpiar temporal
        if html_temp.exists():
            try:
                os.remove(html_temp)
            except:
                pass

def main():
    """Convertir documentos de CafBarDLA a PDF"""
    
    docs = [
        ("docs/MANUAL_COMPLETO.md", "docs/MANUAL_COMPLETO.pdf"),
        ("docs/CLOUD_DEPLOYMENT_GUIDE.md", "docs/CLOUD_DEPLOYMENT_GUIDE.pdf"),
    ]
    
    print("\n" + "="*60)
    print("🔄 Convirtiendo Markdown a PDF...")
    print("="*60 + "\n")
    
    success_count = 0
    for md, pdf in docs:
        if Path(md).exists():
            if convert_markdown_to_pdf(md, pdf):
                success_count += 1
        else:
            print(f"❌ Archivo no encontrado: {md}\n")
    
    print("\n" + "="*60)
    print(f"✓ Resultado: {success_count}/{len(docs)} documentos procesados")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
