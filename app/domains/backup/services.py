"""Servicio de copias de seguridad (backup) y restauracion.

Soporta los dos motores que usa el sistema:
  - SQLite: usa la API de backup nativa de sqlite3 (copia consistente aunque
    haya escrituras en curso; un simple copy del archivo podria corromperse).
  - PostgreSQL: usa pg_dump (debe estar en el PATH).

Cada copia se comprime en un .zip y se verifica su integridad al crearla. Las
copias viven en la carpeta configurada (BACKUP_DIR). El servicio tambien lista,
restaura y aplica una politica de retencion (conservar las N mas recientes).

La restauracion es una operacion destructiva: reemplaza la base actual. Por eso
antes de restaurar se hace una copia de seguridad automatica del estado vigente.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("backup")

MANIFIESTO = "backup_info.json"


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


class BackupService:
    def __init__(self, database_url: str, backup_dir: str = "backups"):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

    @property
    def es_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def _ruta_sqlite(self) -> Path:
        # sqlite:///./cafbardla.db  ->  ./cafbardla.db
        ruta = self.database_url.split("///", 1)[-1]
        return Path(ruta)

    # ------------------------------------------------------------------
    # Crear
    # ------------------------------------------------------------------
    def crear(self, *, etiqueta: str = "manual") -> dict:
        """Crea una copia comprimida y verificada. Devuelve el manifiesto."""
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"cafbardla_{marca}_{etiqueta}"
        tmp_dir = self.backup_dir / f".tmp_{marca}"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        try:
            if self.es_sqlite:
                dump = tmp_dir / "cafbardla.db"
                self._dump_sqlite(dump)
                motor = "sqlite"
            else:
                dump = tmp_dir / "cafbardla.sql"
                self._dump_postgres(dump)
                motor = "postgresql"

            checksum = _sha256(dump)
            manifiesto = {
                "nombre": nombre,
                "creado": datetime.now().isoformat(),
                "motor": motor,
                "archivo_datos": dump.name,
                "sha256": checksum,
                "tamano_bytes": dump.stat().st_size,
                "version_backup": 1,
            }
            (tmp_dir / MANIFIESTO).write_text(
                json.dumps(manifiesto, indent=2, ensure_ascii=False))

            # Comprimir
            zip_path = self.backup_dir / f"{nombre}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(dump, dump.name)
                z.write(tmp_dir / MANIFIESTO, MANIFIESTO)

            # Verificar integridad del zip recien creado
            if not self._verificar_zip(zip_path):
                zip_path.unlink(missing_ok=True)
                raise RuntimeError("La copia creada no paso la verificacion")

            manifiesto["ruta_zip"] = str(zip_path)
            manifiesto["tamano_zip"] = zip_path.stat().st_size
            self.logger.info("Backup creado: %s (%s bytes)", zip_path,
                             manifiesto["tamano_zip"])
            return manifiesto
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _dump_sqlite(self, destino: Path) -> None:
        origen = self._ruta_sqlite()
        if not origen.exists():
            raise FileNotFoundError(f"Base de datos no encontrada: {origen}")
        # API de backup de sqlite: copia consistente aunque haya escrituras.
        src = sqlite3.connect(str(origen))
        dst = sqlite3.connect(str(destino))
        try:
            with dst:
                src.backup(dst)
        finally:
            src.close()
            dst.close()

    def _dump_postgres(self, destino: Path) -> None:
        # pg_dump lee la URL directamente. Debe estar instalado en el servidor.
        try:
            with open(destino, "w") as f:
                subprocess.run(
                    ["pg_dump", "--no-owner", "--no-privileges",
                     self.database_url],
                    stdout=f, stderr=subprocess.PIPE, check=True, timeout=600)
        except FileNotFoundError:
            raise RuntimeError(
                "pg_dump no esta instalado. Instale las herramientas de "
                "PostgreSQL en el servidor para respaldar.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"pg_dump fallo: {e.stderr.decode(errors='ignore')}")

    def _verificar_zip(self, zip_path: Path) -> bool:
        """Verifica que el zip abra, contenga el manifiesto y que el checksum
        del archivo de datos coincida."""
        try:
            with zipfile.ZipFile(zip_path) as z:
                if z.testzip() is not None:
                    return False
                nombres = z.namelist()
                if MANIFIESTO not in nombres:
                    return False
                manifiesto = json.loads(z.read(MANIFIESTO))
                datos = manifiesto["archivo_datos"]
                if datos not in nombres:
                    return False
                h = hashlib.sha256()
                h.update(z.read(datos))
                return h.hexdigest() == manifiesto["sha256"]
        except Exception as e:
            self.logger.error("Verificacion de zip fallo: %s", e)
            return False

    # ------------------------------------------------------------------
    # Listar / verificar
    # ------------------------------------------------------------------
    def listar(self) -> list[dict]:
        copias = []
        for zip_path in sorted(self.backup_dir.glob("cafbardla_*.zip"),
                               reverse=True):
            info = {"ruta": str(zip_path), "nombre": zip_path.stem,
                    "tamano_bytes": zip_path.stat().st_size,
                    "modificado": datetime.fromtimestamp(
                        zip_path.stat().st_mtime).isoformat()}
            try:
                with zipfile.ZipFile(zip_path) as z:
                    if MANIFIESTO in z.namelist():
                        info.update(json.loads(z.read(MANIFIESTO)))
            except Exception:
                info["corrupto"] = True
            copias.append(info)
        return copias

    def verificar(self, nombre_o_ruta: str) -> bool:
        zip_path = self._resolver(nombre_o_ruta)
        return self._verificar_zip(zip_path)

    # ------------------------------------------------------------------
    # Restaurar
    # ------------------------------------------------------------------
    def restaurar(self, nombre_o_ruta: str) -> dict:
        """Restaura una copia. Antes hace un backup del estado actual.

        Operacion destructiva: reemplaza la base vigente por la de la copia.
        """
        zip_path = self._resolver(nombre_o_ruta)
        if not self._verificar_zip(zip_path):
            raise RuntimeError(
                "La copia no paso la verificacion de integridad; no se restaura")

        # Respaldo de seguridad del estado actual antes de sobrescribir.
        try:
            self.crear(etiqueta="pre_restauracion")
        except Exception as e:
            self.logger.warning("No se pudo respaldar antes de restaurar: %s", e)

        with zipfile.ZipFile(zip_path) as z:
            manifiesto = json.loads(z.read(MANIFIESTO))
            datos = manifiesto["archivo_datos"]
            contenido = z.read(datos)

        if manifiesto["motor"] == "sqlite":
            destino = self._ruta_sqlite()
            tmp = destino.with_suffix(".restore.tmp")
            tmp.write_bytes(contenido)
            # Validar que el archivo restaurado es una BD sqlite valida.
            conn = sqlite3.connect(str(tmp))
            try:
                ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
            finally:
                conn.close()
            if ok != "ok":
                tmp.unlink(missing_ok=True)
                raise RuntimeError("La base restaurada no paso integrity_check")
            os.replace(tmp, destino)
        else:
            raise RuntimeError(
                "La restauracion de PostgreSQL debe hacerse con psql/pg_restore "
                "por un administrador; el archivo .sql esta dentro del zip.")

        self.logger.info("Restauracion completada desde %s", zip_path)
        return {"restaurado": manifiesto["nombre"], "motor": manifiesto["motor"]}

    # ------------------------------------------------------------------
    # Retencion
    # ------------------------------------------------------------------
    def aplicar_retencion(self, conservar: int = 30) -> int:
        """Conserva las N copias mas recientes, borra el resto. Devuelve cuantas
        borro. Las copias 'pre_restauracion' no se cuentan para no perderlas."""
        copias = sorted(self.backup_dir.glob("cafbardla_*.zip"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
        normales = [c for c in copias if "pre_restauracion" not in c.name]
        borradas = 0
        for c in normales[conservar:]:
            c.unlink(missing_ok=True)
            borradas += 1
        return borradas

    def _resolver(self, nombre_o_ruta: str) -> Path:
        p = Path(nombre_o_ruta)
        if p.exists():
            return p
        candidato = self.backup_dir / nombre_o_ruta
        if candidato.exists():
            return candidato
        if not nombre_o_ruta.endswith(".zip"):
            candidato = self.backup_dir / f"{nombre_o_ruta}.zip"
            if candidato.exists():
                return candidato
        raise FileNotFoundError(f"Copia no encontrada: {nombre_o_ruta}")
