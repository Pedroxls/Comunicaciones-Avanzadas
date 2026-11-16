"""Agente Google ADK sobre Gemini en Vertex AI.

Solo se importa `google.adk` al construir el agente: las pruebas y el arranque
sin Vertex no necesitan el paquete. ADK toma el proyecto y la región de
GOOGLE_CLOUD_PROJECT y GOOGLE_CLOUD_LOCATION, con GOOGLE_GENAI_USE_VERTEXAI=TRUE.
"""

import asyncio
import json
import os

from cumplimiento.herramientas import INSTRUCCION, herramientas_de_lectura

MODELO_POR_DEFECTO = "gemini-3.8-flash"
TIEMPO_MAXIMO_SEG = 25


def construir(catalogo: dict | None = None, modelo=None):
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="cumplimiento",
        description="Explica hallazgos de cumplimiento. No decide ni modifica nada.",
        model=modelo or os.environ.get("GEMINI_MODEL") or MODELO_POR_DEFECTO,
        instruction=INSTRUCCION,
        tools=herramientas_de_lectura(catalogo or {}),
    )


class ExplicadorADK:
    """Llama al agente con los datos de un hallazgo y devuelve (texto, herramientas usadas)."""

    def __init__(self, catalogo: dict | None = None, modelo=None):
        self._agente = construir(catalogo, modelo)
        self.modelo = self._agente.model if isinstance(self._agente.model, str) else type(self._agente.model).__name__

    def __call__(self, datos: dict) -> tuple[str, list[str]]:
        return asyncio.run(asyncio.wait_for(self._preguntar(datos), TIEMPO_MAXIMO_SEG))

    async def _preguntar(self, datos: dict) -> tuple[str, list[str]]:
        from google.adk.runners import InMemoryRunner
        from google.genai import types

        runner = InMemoryRunner(agent=self._agente, app_name="cumplimiento")
        try:
            sesion = await runner.session_service.create_session(app_name="cumplimiento", user_id="bus")
            mensaje = types.Content(
                role="user",
                parts=[types.Part(text=json.dumps(datos, ensure_ascii=False))],
            )
            texto, herramientas = "", []
            async for evento in runner.run_async(user_id="bus", session_id=sesion.id, new_message=mensaje):
                herramientas += [llamada.name for llamada in evento.get_function_calls()]
                if evento.is_final_response() and evento.content and evento.content.parts:
                    texto = "".join(parte.text or "" for parte in evento.content.parts)
            return texto.strip(), herramientas
        finally:
            await runner.close()
