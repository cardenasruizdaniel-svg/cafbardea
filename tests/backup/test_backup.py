"""Copias de seguridad: creacion, verificacion, restauracion y retencion."""
import zipfile
from pathlib import Path

import pytest

from app.domains.backup.services import BackupService


@pytest.fixture
def base_sqlite(tmp_path):
    """Crea una BD sqlite minima y devuelve su URL."""
    import sqlite3
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.execute("INSERT INTO t (v) VALUES ('dato1'), ('dato2')")
    conn.commit()
    conn.close()
    return f"sqlite:///{db}", tmp_path


@pytest.fixture
def svc(base_sqlite):
    url, tmp = base_sqlite
    return BackupService(url, backup_dir=str(tmp / "backups"))


class TestCrear:
    def test_crea_zip_verificado(self, svc):
        m = svc.crear(etiqueta="test")
        assert Path(m["ruta_zip"]).exists()
        assert m["motor"] == "sqlite"
        assert m["sha256"]
        # el zip debe ser mas pequeno que el original (comprimido)
        assert m["tamano_zip"] < m["tamano_bytes"]

    def test_zip_contiene_manifiesto(self, svc):
        m = svc.crear()
        with zipfile.ZipFile(m["ruta_zip"]) as z:
            assert "backup_info.json" in z.namelist()


class TestVerificar:
    def test_copia_sana_es_integra(self, svc):
        m = svc.crear()
        assert svc.verificar(m["nombre"]) is True

    def test_copia_corrupta_se_detecta(self, svc):
        m = svc.crear()
        ruta = Path(m["ruta_zip"])
        with open(ruta, "r+b") as f:
            f.seek(60)
            f.write(b"BASURA_CORRUPTA")
        assert svc.verificar(m["nombre"]) is False


class TestListar:
    def test_lista_las_copias(self, svc):
        svc.crear(etiqueta="a")
        svc.crear(etiqueta="b")
        copias = svc.listar()
        assert len(copias) == 2


class TestRestaurar:
    def test_restaura_y_respalda_antes(self, svc):
        m = svc.crear(etiqueta="original")
        r = svc.restaurar(m["nombre"])
        assert r["restaurado"] == m["nombre"]
        # debe existir una copia pre_restauracion
        assert any("pre_restauracion" in c["nombre"] for c in svc.listar())

    def test_no_restaura_copia_corrupta(self, svc):
        m = svc.crear()
        with open(m["ruta_zip"], "r+b") as f:
            f.seek(60)
            f.write(b"CORRUPTO")
        with pytest.raises(RuntimeError):
            svc.restaurar(m["nombre"])


class TestRetencion:
    def test_conserva_n_mas_recientes(self, svc):
        for i in range(5):
            svc.crear(etiqueta=f"c{i}")
        borradas = svc.aplicar_retencion(conservar=2)
        assert borradas == 3
        normales = [c for c in svc.listar()
                    if "pre_restauracion" not in c["nombre"]]
        assert len(normales) == 2

    def test_no_borra_pre_restauracion(self, svc):
        m = svc.crear()
        svc.restaurar(m["nombre"])  # genera pre_restauracion
        for i in range(3):
            svc.crear(etiqueta=f"x{i}")
        svc.aplicar_retencion(conservar=1)
        # la pre_restauracion sigue ahi
        assert any("pre_restauracion" in c["nombre"] for c in svc.listar())


class TestDatosSensibles:
    def test_no_expone_url_con_credenciales(self, svc):
        # El manifiesto no debe guardar la URL de conexion.
        m = svc.crear()
        with zipfile.ZipFile(m["ruta_zip"]) as z:
            contenido = z.read("backup_info.json").decode()
        assert "sqlite://" not in contenido
        assert "password" not in contenido.lower()
