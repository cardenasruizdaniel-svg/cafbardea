#!/usr/bin/env python
"""Script de copia de seguridad de CafBarDLA.

Uso:
  python scripts/backup.py                    # crea una copia
  python scripts/backup.py --listar           # lista las copias
  python scripts/backup.py --verificar NOMBRE # verifica integridad
  python scripts/backup.py --restaurar NOMBRE # restaura (destructivo)
  python scripts/backup.py --retencion 30     # conserva las 30 mas recientes

Programar automatico:
  Windows (Task Scheduler): programa
    python D:\\ruta\\scripts\\backup.py --retencion 30
  Linux (cron), copia diaria a las 2am:
    0 2 * * *  cd /ruta && python scripts/backup.py --retencion 30
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.domains.backup.services import BackupService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backups de CafBarDLA")
    parser.add_argument("--dir", default=os.environ.get("BACKUP_DIR", "backups"),
                        help="Carpeta de copias (def: backups)")
    parser.add_argument("--listar", action="store_true")
    parser.add_argument("--verificar", metavar="NOMBRE")
    parser.add_argument("--restaurar", metavar="NOMBRE")
    parser.add_argument("--retencion", type=int, metavar="N",
                        help="Conservar las N copias mas recientes")
    parser.add_argument("--si", action="store_true",
                        help="Confirmar restauracion sin preguntar")
    args = parser.parse_args()

    svc = BackupService(settings.database_url, backup_dir=args.dir)

    if args.listar:
        copias = svc.listar()
        if not copias:
            print("No hay copias.")
            return 0
        print(f"{'NOMBRE':<45} {'MOTOR':<12} {'TAMANO':>10}  INTEGRIDAD")
        for c in copias:
            estado = "corrupto" if c.get("corrupto") else "ok"
            print(f"{c['nombre']:<45} {c.get('motor','?'):<12} "
                  f"{c['tamano_bytes']:>10}  {estado}")
        return 0

    if args.verificar:
        ok = svc.verificar(args.verificar)
        print("INTEGRA" if ok else "CORRUPTA O NO ENCONTRADA")
        return 0 if ok else 1

    if args.restaurar:
        if not args.si:
            resp = input(f"Restaurar '{args.restaurar}' REEMPLAZARA la base "
                         f"actual. Escriba RESTAURAR para continuar: ")
            if resp.strip() != "RESTAURAR":
                print("Cancelado.")
                return 1
        r = svc.restaurar(args.restaurar)
        print(f"Restaurado: {r['restaurado']}")
        return 0

    # Por defecto: crear una copia
    etiqueta = "automatico" if args.retencion else "manual"
    m = svc.crear(etiqueta=etiqueta)
    print(f"Copia creada: {m['nombre']} ({m['tamano_zip']} bytes, verificada)")

    if args.retencion:
        borradas = svc.aplicar_retencion(conservar=args.retencion)
        if borradas:
            print(f"Retencion: {borradas} copia(s) antigua(s) eliminada(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
