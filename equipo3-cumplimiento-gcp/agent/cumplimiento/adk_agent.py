"""Agente Google ADK. Solo se construye si el paquete está instalado."""

import os

from cumplimiento.herramientas import INSTRUCCION, herramientas_de_lectura


def construir(catalogo: dict | None = None):
    try:
        from google.adk.agents import Agent
    except ImportError:
        from google.adk.agents import LlmAgent as Agent
    return Agent(
        name="cumplimiento",
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        instruction=INSTRUCCION,
        tools=herramientas_de_lectura(catalogo or {}),
    )
