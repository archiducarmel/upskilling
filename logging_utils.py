"""
Logging utilities for batch processing.
Contains all logging, metrics collection and display functions.
"""

import gc
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import polars as pl

from common.constants import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


# =============================================================================
# DATA CLASSES FOR METRICS
# =============================================================================

@dataclass
class StepMetrics:
    """Métriques pour une étape de traitement."""
    step_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0
    input_rows: int = 0
    input_cols: int = 0
    output_rows: int = 0
    output_cols: int = 0
    status: str = "PENDING"
    error_message: str = ""


@dataclass
class BatchMetrics:
    """Métriques globales du batch."""
    batch_start_time: datetime = field(default_factory=datetime.now)
    batch_end_time: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    steps: list = field(default_factory=list)
    final_output_rows: int = 0
    final_output_cols: int = 0
    status: str = "RUNNING"
    error_message: str = ""
    
    def reset(self):
        """Reset metrics for a new batch run."""
        self.batch_start_time = datetime.now()
        self.batch_end_time = None
        self.total_duration_seconds = 0.0
        self.steps = []
        self.final_output_rows = 0
        self.final_output_cols = 0
        self.status = "RUNNING"
        self.error_message = ""


# Global metrics collector
batch_metrics = BatchMetrics()


# =============================================================================
# STEP TRACKER CLASS
# =============================================================================

class StepTracker:
    """
    Context manager pour tracker une étape de traitement.
    
    Usage:
        with StepTracker(1, "Chargement SQL", 12) as tracker:
            tracker.log_input(df, "df_main")
            # ... processing ...
            tracker.log_output(result_df, "result")
    """
    
    def __init__(self, step_number: int, step_name: str, total_steps: int = 12):
        self.step_number = step_number
        self.step_name = step_name
        self.total_steps = total_steps
        self.metrics = StepMetrics(step_name=step_name)
        self.start_time = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        self.metrics.start_time = self.start_time
        _log_step_header(self.step_number, self.step_name, self.total_steps)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metrics.end_time = time.time()
        self.metrics.duration_seconds = self.metrics.end_time - self.metrics.start_time
        
        if exc_type is not None:
            self.metrics.status = "FAILED"
            self.metrics.error_message = str(exc_val)
            _log_step_error(self.step_name, exc_val)
        else:
            self.metrics.status = "SUCCESS"
            _log_step_duration(self.metrics.duration_seconds)
            _log_step_success(self.step_name)
        
        batch_metrics.steps.append(self.metrics)
        return False  # Don't suppress exceptions
    
    def log_input(self, df: pl.DataFrame, name: str = "Input") -> None:
        """Log un DataFrame d'entrée."""
        _log_dataframe_info(df, name, "   ")
        self.metrics.input_rows = df.height
        self.metrics.input_cols = df.width
    
    def log_input_dict(self, data_dict: dict, name: str = "Data") -> None:
        """Log un dictionnaire de DataFrames."""
        total_rows = 0
        for key, df in data_dict.items():
            if isinstance(df, pl.DataFrame):
                _log_dataframe_info(df, key, "      ")
                total_rows += df.height
        logger.info(f"   📊 Total lignes chargées: {total_rows:,}")
        self.metrics.input_rows = total_rows
    
    def log_output(self, df: pl.DataFrame, name: str = "Output") -> None:
        """Log un DataFrame de sortie."""
        _log_dataframe_info(df, name, "   ")
        self.metrics.output_rows = df.height
        self.metrics.output_cols = df.width
    
    def log_join(self, source_name: str) -> None:
        """Log une opération de jointure."""
        logger.info(f"   🔗 Jointure sur {source_name} effectuée")
    
    def log_filter_stats(self, input_rows: int, output_rows: int) -> None:
        """Log les statistiques de filtrage."""
        rows_filtered = input_rows - output_rows
        pct = (rows_filtered / input_rows * 100) if input_rows > 0 else 0
        logger.info(f"   🔍 Lignes filtrées: {rows_filtered:,} ({pct:.1f}%)")
    
    def log_pdo_stats(self, df: pl.DataFrame) -> None:
        """Log les statistiques PDO."""
        logger.info(f"   📈 Statistiques PDO:")
        logger.info(f"      └── Min: {df['PDO'].min():.6f}")
        logger.info(f"      └── Max: {df['PDO'].max():.6f}")
        logger.info(f"      └── Mean: {df['PDO'].mean():.6f}")
        logger.info(f"      └── Median: {df['PDO'].median():.6f}")


# =============================================================================
# LOGGING FUNCTIONS (PRIVATE)
# =============================================================================

def _log_separator(char: str = "=", length: int = 80) -> None:
    """Affiche un séparateur visuel."""
    logger.info(char * length)


def _log_step_header(step_number: int, step_name: str, total_steps: int) -> None:
    """Affiche l'en-tête d'une étape."""
    _log_separator("=")
    logger.info(f"📌 STEP {step_number}/{total_steps}: {step_name}")
    _log_separator("-", 40)


def _log_dataframe_info(df: pl.DataFrame, df_name: str, prefix: str = "") -> None:
    """Affiche les informations d'un DataFrame."""
    rows, cols = df.shape
    memory_mb = df.estimated_size("mb")
    logger.info(f"{prefix}📊 {df_name}:")
    logger.info(f"{prefix}   └── Lignes: {rows:,} | Colonnes: {cols} | Mémoire: {memory_mb:.2f} MB")


def _log_step_duration(duration: float) -> None:
    """Affiche la durée d'une étape."""
    if duration < 60:
        logger.info(f"   ⏱️  Durée: {duration:.2f} secondes")
    else:
        minutes = int(duration // 60)
        seconds = duration % 60
        logger.info(f"   ⏱️  Durée: {minutes}m {seconds:.2f}s")


def _log_step_success(step_name: str) -> None:
    """Affiche le succès d'une étape."""
    logger.info(f"   ✅ {step_name} - SUCCÈS")


def _log_step_error(step_name: str, error: Exception) -> None:
    """Affiche l'erreur d'une étape."""
    logger.error(f"   ❌ {step_name} - ÉCHEC: {str(error)}")


# =============================================================================
# PUBLIC LOGGING FUNCTIONS
# =============================================================================

def log_batch_start(version: str) -> None:
    """Log le démarrage du batch."""
    batch_metrics.reset()
    _log_separator("=")
    logger.info("🚀 DÉMARRAGE DU BATCH PDO")
    _log_separator("=")
    logger.info(f"📦 Version: {version}")
    logger.info(f"🕐 Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    _log_separator("-", 40)


def log_config_loaded() -> None:
    """Log le chargement de la configuration."""
    logger.info("   ✅ Configurations chargées")


def log_vault_connected() -> None:
    """Log la connexion au Vault."""
    logger.info("   ✅ Vault connecté")


def log_memory_freed(data_name: str) -> None:
    """Log la libération de mémoire et force gc."""
    gc.collect()
    logger.info(f"   🗑️  Mémoire libérée: {data_name}")


def set_final_metrics(df: pl.DataFrame) -> None:
    """Enregistre les métriques finales."""
    batch_metrics.final_output_rows = df.height
    batch_metrics.final_output_cols = df.width
    batch_metrics.status = "SUCCESS"


def log_batch_error(error: Exception) -> None:
    """Log une erreur fatale du batch."""
    batch_metrics.status = "FAILED"
    batch_metrics.error_message = str(error)
    logger.error(f"❌ ERREUR FATALE: {str(error)}")


def print_final_summary() -> None:
    """Affiche le récapitulatif final du batch."""
    batch_metrics.batch_end_time = datetime.now()
    batch_metrics.total_duration_seconds = (
        batch_metrics.batch_end_time - batch_metrics.batch_start_time
    ).total_seconds()
    
    _log_separator("=")
    _log_separator("=")
    logger.info("📋 RÉCAPITULATIF DU BATCH PDO")
    _log_separator("=")
    
    # Informations générales
    logger.info(f"🕐 Début:        {batch_metrics.batch_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🕐 Fin:          {batch_metrics.batch_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    total_minutes = int(batch_metrics.total_duration_seconds // 60)
    total_seconds = batch_metrics.total_duration_seconds % 60
    logger.info(f"⏱️  Durée totale: {total_minutes}m {total_seconds:.2f}s")
    
    _log_separator("-", 60)
    
    # Statut global
    failed_steps = [s for s in batch_metrics.steps if s.status == "FAILED"]
    if failed_steps:
        logger.error(f"🔴 STATUT: ÉCHEC ({len(failed_steps)} étape(s) en erreur)")
    else:
        logger.info(f"🟢 STATUT: SUCCÈS")
    
    _log_separator("-", 60)
    
    # Tableau des étapes
    logger.info("📊 DÉTAIL DES ÉTAPES:")
    logger.info("")
    logger.info(f"{'#':<3} {'Étape':<35} {'Durée':<12} {'In rows':<12} {'Out rows':<12} {'Statut':<10}")
    logger.info("-" * 90)
    
    for i, step in enumerate(batch_metrics.steps, 1):
        duration_str = f"{step.duration_seconds:.2f}s"
        in_rows = f"{step.input_rows:,}" if step.input_rows > 0 else "-"
        out_rows = f"{step.output_rows:,}" if step.output_rows > 0 else "-"
        status_emoji = "✅" if step.status == "SUCCESS" else "❌"
        
        logger.info(f"{i:<3} {step.step_name:<35} {duration_str:<12} {in_rows:<12} {out_rows:<12} {status_emoji}")
    
    _log_separator("-", 90)
    
    # Statistiques finales
    total_processing_time = sum(s.duration_seconds for s in batch_metrics.steps)
    logger.info("")
    logger.info("📈 STATISTIQUES:")
    logger.info(f"   • Nombre d'étapes: {len(batch_metrics.steps)}")
    logger.info(f"   • Temps de processing cumulé: {total_processing_time:.2f}s")
    logger.info(f"   • Lignes en sortie finale: {batch_metrics.final_output_rows:,}")
    logger.info(f"   • Colonnes en sortie finale: {batch_metrics.final_output_cols}")
    
    # Top 3 des étapes les plus longues
    if batch_metrics.steps:
        sorted_steps = sorted(batch_metrics.steps, key=lambda x: x.duration_seconds, reverse=True)[:3]
        logger.info("")
        logger.info("🐢 TOP 3 ÉTAPES LES PLUS LONGUES:")
        for i, step in enumerate(sorted_steps, 1):
            pct = (step.duration_seconds / total_processing_time * 100) if total_processing_time > 0 else 0
            logger.info(f"   {i}. {step.step_name}: {step.duration_seconds:.2f}s ({pct:.1f}%)")
    
    _log_separator("=")
    logger.info("🏁 FIN DU BATCH PDO")
    _log_separator("=")
