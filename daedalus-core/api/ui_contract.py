# api/ui_contract.py

from __future__ import annotations
from typing import Dict, Any

UI_VERSION = "1.4.0"


# ------------------------------------------------------------
# Existing Schemas
# ------------------------------------------------------------

def schema_status() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "status",
        "fields": {
            "drift": "dict",
            "stability": "dict",
            "governor": "dict",
        },
    }


def schema_health() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "health",
        "fields": {
            "drift": "dict",
            "stability": "dict",
            "readiness": "dict",
            "warnings": "dict",
            "patch_history": "dict",
        },
    }


def schema_cycle_result() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "cycle_result",
        "fields": {
            "cycle": "dict",
            "patch": "dict",
            "pre_metrics": "dict",
            "post_metrics": "dict",
            "state": "dict",
        },
    }


def schema_scheduler_result() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "scheduler_result",
        "fields": {
            "status": "str",
            "state": "dict",
            "cycle": "optional[dict]",
        },
    }


def schema_readiness() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "readiness",
        "fields": {
            "readiness_score": "float",
            "components": "dict",
        },
    }


def schema_governor_trace() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "governor_trace",
        "fields": {
            "trace": "list[dict]",
        },
    }


def schema_governor_thresholds() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "governor_thresholds",
        "fields": {
            "current_tier": "int",
            "strict_mode": "bool",
            "thresholds": "dict",
            "current_signals": "dict",
        },
    }


# ------------------------------------------------------------
# NEW: Governor Tuning API Schemas
# ------------------------------------------------------------

def schema_governor_set_thresholds() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "governor_set_thresholds",
        "fields": {
            "ok": "bool",
            "applied": "optional[dict]",
            "error": "optional[str]",
        },
    }


def schema_governor_save_thresholds() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "governor_save_thresholds",
        "fields": {
            "ok": "bool",
            "saved": "optional[dict]",
            "error": "optional[str]",
        },
    }


def schema_governor_load_thresholds() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "governor_load_thresholds",
        "fields": {
            "ok": "bool",
            "loaded": "optional[dict]",
            "error": "optional[str]",
            "expected": "optional[str]",
            "found": "optional[str]",
        },
    }


def schema_governor_reset_thresholds() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "type": "governor_reset_thresholds",
        "fields": {
            "ok": "bool",
            "reset_to": "optional[dict]",
        },
    }


# ------------------------------------------------------------
# Contract Registry
# ------------------------------------------------------------

def get_contract() -> Dict[str, Any]:
    return {
        "version": UI_VERSION,
        "commands": {
            "status": schema_status(),
            "health": schema_health(),
            "run_cycle": schema_cycle_result(),
            "run_scheduler": schema_scheduler_result(),
            "readiness": schema_readiness(),
            "governor_trace": schema_governor_trace(),
            "governor_thresholds": schema_governor_thresholds(),

            # NEW TUNING COMMANDS
            "governor_set_thresholds": schema_governor_set_thresholds(),
            "governor_save_thresholds": schema_governor_save_thresholds(),
            "governor_load_thresholds": schema_governor_load_thresholds(),
            "governor_reset_thresholds": schema_governor_reset_thresholds(),
        },
    }
