#!/usr/bin/env python3
"""Utilitarios de data/hora do experimento."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

FUSO_BAHIA = timezone(timedelta(hours=-3))
FORMATO_DATA_HORA = "%d/%m/%Y %H:%M"


def agora_bahia() -> str:
    """Retorna data/hora local em America/Bahia no formato dd/mm/aaaa hh:mm."""
    return datetime.now(FUSO_BAHIA).strftime(FORMATO_DATA_HORA)
