"""Descarga terraform y conftest para la imagen del sensor de drift.

Mismas versiones que el workflow pr-validate, para que el drift evalúe con el
mismo motor que el PR. Cada archivo se comprueba contra su sha256 publicado.
"""

import hashlib
import io
import os
import sys
import tarfile
import urllib.request
import zipfile

HERRAMIENTAS = [
    {
        "binario": "terraform",
        "url": "https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip",
        "sha256": "186e0145f5e5f2eb97cbd785bc78f21bae4ef15119349f6ad4fa535b83b10df8",
    },
    {
        "binario": "conftest",
        "url": "https://github.com/open-policy-agent/conftest/releases/download/v0.55.0/conftest_0.55.0_Linux_x86_64.tar.gz",
        "sha256": "1f2c78cdd2ad6bc4cbbdce5ca3e0d15fdc7d10303a629a56118614089c311385",
    },
]


def instalar(destino: str) -> None:
    os.makedirs(destino, exist_ok=True)
    for herramienta in HERRAMIENTAS:
        with urllib.request.urlopen(herramienta["url"], timeout=120) as respuesta:
            datos = respuesta.read()
        if hashlib.sha256(datos).hexdigest() != herramienta["sha256"]:
            raise SystemExit(f"El sha256 de {herramienta['binario']} no coincide")
        ruta = os.path.join(destino, herramienta["binario"])
        if herramienta["url"].endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(datos)) as archivo:
                contenido = archivo.read(herramienta["binario"])
        else:
            with tarfile.open(fileobj=io.BytesIO(datos), mode="r:gz") as archivo:
                contenido = archivo.extractfile(herramienta["binario"]).read()
        with open(ruta, "wb") as salida:
            salida.write(contenido)
        os.chmod(ruta, 0o755)
        print(f"{herramienta['binario']} instalado en {ruta}")


if __name__ == "__main__":
    instalar(sys.argv[1] if len(sys.argv) > 1 else "/usr/local/bin")
