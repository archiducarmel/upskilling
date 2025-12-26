"""
Batch processing for PDO calculation.
Version with structured logging for production monitoring.
"""

import gc
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable

import polars as pl
from ml_utils.inference_decorator import duration_request
from ml_utils.logger_helper import configure_logger
from ml_utils.vault_connector import VaultConnector

from common.base_transformation import BaseTransformation
from common.config_context import ConfigContext
from common.constants import FILE_NAME_PROJECT_CONFIG, LOGGER_NAME
from config.load_config import load_app_config_file, load_config_domino_project_file, load_service_config_file
from settings import PROJECT_ROOT
from version import __version__

logger = logging.getLogger(LOGGER_NAME)


# =============================================================================
# LOGGING UTILITIES
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
    memory_freed: bool = False
    status: str = "PENDING"
    error_message: str = ""


@dataclass
class BatchMetrics:
    """Métriques globales du batch."""
    batch_start_time: datetime = field(default_factory=datetime.now)
    batch_end_time: datetime = None
    total_duration_seconds: float = 0.0
    steps: list = field(default_factory=list)
    total_rows_processed: int = 0
    final_output_rows: int = 0
    final_output_cols: int = 0
    status: str = "RUNNING"
    error_message: str = ""


# Global metrics collector
batch_metrics = BatchMetrics()


def log_separator(char: str = "=", length: int = 80) -> None:
    """Affiche un séparateur visuel."""
    logger.info(char * length)


def log_step_header(step_number: int, step_name: str, total_steps: int = 12) -> None:
    """Affiche l'en-tête d'une étape."""
    log_separator("=")
    logger.info(f"📌 STEP {step_number}/{total_steps}: {step_name}")
    log_separator("-", 40)


def log_dataframe_info(df: pl.DataFrame, df_name: str, prefix: str = "   ") -> None:
    """Affiche les informations d'un DataFrame."""
    rows, cols = df.shape
    memory_mb = df.estimated_size("mb")
    logger.info(f"{prefix}📊 {df_name}:")
    logger.info(f"{prefix}   └── Lignes: {rows:,} | Colonnes: {cols} | Mémoire: {memory_mb:.2f} MB")


def log_step_duration(step_name: str, duration: float) -> None:
    """Affiche la durée d'une étape."""
    if duration < 60:
        logger.info(f"   ⏱️  Durée: {duration:.2f} secondes")
    else:
        minutes = int(duration // 60)
        seconds = duration % 60
        logger.info(f"   ⏱️  Durée: {minutes}m {seconds:.2f}s")


def log_step_success(step_name: str) -> None:
    """Affiche le succès d'une étape."""
    logger.info(f"   ✅ {step_name} - SUCCÈS")


def log_step_error(step_name: str, error: Exception) -> None:
    """Affiche l'erreur d'une étape."""
    logger.error(f"   ❌ {step_name} - ÉCHEC: {str(error)}")


def step_tracker(step_number: int, step_name: str, total_steps: int = 12):
    """
    Décorateur pour tracker une étape de traitement.
    Mesure le temps, log les entrées/sorties, et collecte les métriques.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            metrics = StepMetrics(step_name=step_name)
            metrics.start_time = time.time()
            
            # Log header
            log_step_header(step_number, step_name, total_steps)
            
            # Log input DataFrames
            for i, arg in enumerate(args):
                if isinstance(arg, pl.DataFrame):
                    log_dataframe_info(arg, f"Input DataFrame {i+1}", "   ")
                    metrics.input_rows = arg.height
                    metrics.input_cols = arg.width
            
            for key, value in kwargs.items():
                if isinstance(value, pl.DataFrame):
                    log_dataframe_info(value, f"Input '{key}'", "   ")
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log output
                if isinstance(result, pl.DataFrame):
                    log_dataframe_info(result, "Output DataFrame", "   ")
                    metrics.output_rows = result.height
                    metrics.output_cols = result.width
                elif isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, pl.DataFrame):
                            log_dataframe_info(value, f"Output '{key}'", "   ")
                            metrics.output_rows = value.height
                            metrics.output_cols = value.width
                
                # Calculate duration
                metrics.end_time = time.time()
                metrics.duration_seconds = metrics.end_time - metrics.start_time
                metrics.status = "SUCCESS"
                
                log_step_duration(step_name, metrics.duration_seconds)
                log_step_success(step_name)
                
                # Store metrics
                batch_metrics.steps.append(metrics)
                
                return result
                
            except Exception as e:
                metrics.end_time = time.time()
                metrics.duration_seconds = metrics.end_time - metrics.start_time
                metrics.status = "FAILED"
                metrics.error_message = str(e)
                
                log_step_error(step_name, e)
                batch_metrics.steps.append(metrics)
                raise
        
        return wrapper
    return decorator


def log_sql_query_info(query_name: str, duration: float, df: pl.DataFrame) -> None:
    """Log les informations d'une requête SQL."""
    logger.info(f"      🔍 {query_name}")
    logger.info(f"         └── Lignes: {df.height:,} | Colonnes: {df.width} | Durée: {duration:.2f}s")


def log_memory_freed(data_name: str) -> None:
    """Log la libération de mémoire."""
    logger.info(f"   🗑️  Mémoire libérée: {data_name}")


def print_final_summary() -> None:
    """Affiche le récapitulatif final du batch."""
    batch_metrics.batch_end_time = datetime.now()
    batch_metrics.total_duration_seconds = (
        batch_metrics.batch_end_time - batch_metrics.batch_start_time
    ).total_seconds()
    
    log_separator("=")
    log_separator("=")
    logger.info("📋 RÉCAPITULATIF DU BATCH PDO")
    log_separator("=")
    
    # Informations générales
    logger.info(f"🕐 Début:        {batch_metrics.batch_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🕐 Fin:          {batch_metrics.batch_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    total_minutes = int(batch_metrics.total_duration_seconds // 60)
    total_seconds = batch_metrics.total_duration_seconds % 60
    logger.info(f"⏱️  Durée totale: {total_minutes}m {total_seconds:.2f}s")
    
    log_separator("-", 60)
    
    # Statut global
    failed_steps = [s for s in batch_metrics.steps if s.status == "FAILED"]
    if failed_steps:
        batch_metrics.status = "FAILED"
        logger.error(f"🔴 STATUT: ÉCHEC ({len(failed_steps)} étape(s) en erreur)")
    else:
        batch_metrics.status = "SUCCESS"
        logger.info(f"🟢 STATUT: SUCCÈS")
    
    log_separator("-", 60)
    
    # Tableau des étapes
    logger.info("📊 DÉTAIL DES ÉTAPES:")
    logger.info("")
    logger.info(f"{'#':<3} {'Étape':<40} {'Durée':<12} {'In rows':<12} {'Out rows':<12} {'Statut':<10}")
    logger.info("-" * 95)
    
    for i, step in enumerate(batch_metrics.steps, 1):
        duration_str = f"{step.duration_seconds:.2f}s"
        in_rows = f"{step.input_rows:,}" if step.input_rows > 0 else "-"
        out_rows = f"{step.output_rows:,}" if step.output_rows > 0 else "-"
        status_emoji = "✅" if step.status == "SUCCESS" else "❌"
        
        logger.info(f"{i:<3} {step.step_name:<40} {duration_str:<12} {in_rows:<12} {out_rows:<12} {status_emoji} {step.status}")
    
    log_separator("-", 95)
    
    # Statistiques finales
    total_processing_time = sum(s.duration_seconds for s in batch_metrics.steps)
    logger.info("")
    logger.info("📈 STATISTIQUES:")
    logger.info(f"   • Nombre d'étapes: {len(batch_metrics.steps)}")
    logger.info(f"   • Temps de processing cumulé: {total_processing_time:.2f}s")
    logger.info(f"   • Lignes en sortie finale: {batch_metrics.final_output_rows:,}")
    logger.info(f"   • Colonnes en sortie finale: {batch_metrics.final_output_cols}")
    
    # Top 3 des étapes les plus longues
    sorted_steps = sorted(batch_metrics.steps, key=lambda x: x.duration_seconds, reverse=True)[:3]
    logger.info("")
    logger.info("🐢 TOP 3 ÉTAPES LES PLUS LONGUES:")
    for i, step in enumerate(sorted_steps, 1):
        pct = (step.duration_seconds / total_processing_time * 100) if total_processing_time > 0 else 0
        logger.info(f"   {i}. {step.step_name}: {step.duration_seconds:.2f}s ({pct:.1f}%)")
    
    log_separator("=")
    logger.info("🏁 FIN DU BATCH PDO")
    log_separator("=")


# =============================================================================
# CONFIGURATION LOADING
# =============================================================================

def load_configurations() -> tuple[dict, dict]:
    """Load and return app and service configurations."""
    logger.info("📁 Chargement des configurations...")
    load_service_config_file()
    app_config = load_app_config_file()
    project_config_path = os.path.join(PROJECT_ROOT, "config", "domino", FILE_NAME_PROJECT_CONFIG)
    project_config = load_config_domino_project_file(project_config_path)
    logger.info("   ✅ Configurations chargées")
    return app_config, project_config


# =============================================================================
# MAIN BATCH FUNCTION
# =============================================================================

@duration_request
def main() -> None:
    """Run main method for batch - VERSION AVEC LOGS STRUCTURÉS."""
    
    # Initialize logging
    configure_logger()
    
    # Banner
    log_separator("=")
    logger.info("🚀 DÉMARRAGE DU BATCH PDO")
    log_separator("=")
    logger.info(f"📦 Version: {__version__}")
    logger.info(f"🕐 Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_separator("-", 40)
    
    # Reset metrics
    global batch_metrics
    batch_metrics = BatchMetrics()
    
    try:
        # =================================================================
        # STEP 0: Configuration
        # =================================================================
        log_step_header(0, "CONFIGURATION", 12)
        
        app_config, project_config = load_configurations()
        config_context = ConfigContext()
        config_context.set("app_config", app_config)

        yaml_config_path = "config/domino/starburst_dev1.yml"
        yaml_config_path_dhv2 = "config/domino/starburst_dev2.yml"
        VaultConnector(yaml_config_path)
        VaultConnector(yaml_config_path_dhv2)
        
        logger.info("   ✅ Vault connecté")
        
        # Initialize transformation pipeline
        base_transformation = BaseTransformation(app_config)
        
        # =================================================================
        # STEP 1: Chargement des données SQL
        # =================================================================
        log_step_header(1, "CHARGEMENT DONNÉES SQL", 12)
        
        step_start = time.time()
        logger.info("   📥 Exécution des requêtes Starburst...")
        
        initial_data = base_transformation.load_data()
        
        step_duration = time.time() - step_start
        
        # Log each loaded DataFrame
        total_rows_loaded = 0
        for key, df in initial_data.items():
            log_dataframe_info(df, key, "      ")
            total_rows_loaded += df.height
        
        logger.info(f"   📊 Total lignes chargées: {total_rows_loaded:,}")
        log_step_duration("Chargement SQL", step_duration)
        log_step_success("Chargement données SQL")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Chargement SQL",
            duration_seconds=step_duration,
            output_rows=total_rows_loaded,
            status="SUCCESS"
        ))
        
        # =================================================================
        # STEP 2: Preprocessing df_main
        # =================================================================
        log_step_header(2, "PREPROCESSING DF_MAIN", 12)
        step_start = time.time()
        
        unfiltered_df_main = initial_data["unfiltered_df_main"]
        log_dataframe_info(unfiltered_df_main, "Input: unfiltered_df_main", "   ")
        
        preprocessed_data = base_transformation.preprocess_df_main(unfiltered_df_main)
        df_main = preprocessed_data["df_main"]
        
        log_dataframe_info(df_main, "Output: df_main", "   ")
        
        step_duration = time.time() - step_start
        log_step_duration("Preprocessing df_main", step_duration)
        log_step_success("Preprocessing df_main")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Preprocessing df_main",
            duration_seconds=step_duration,
            input_rows=unfiltered_df_main.height,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        # Libération mémoire
        del unfiltered_df_main, preprocessed_data
        gc.collect()
        log_memory_freed("unfiltered_df_main, preprocessed_data")
        
        # =================================================================
        # STEP 3: Encoding features
        # =================================================================
        log_step_header(3, "ENCODING FEATURES", 12)
        step_start = time.time()
        
        input_rows = df_main.height
        df_main = base_transformation.preprocess_encoded_df_main(df_main)
        
        log_dataframe_info(df_main, "Output: df_main_encoded", "   ")
        
        step_duration = time.time() - step_start
        log_step_duration("Encoding features", step_duration)
        log_step_success("Encoding features")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Encoding features",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        # =================================================================
        # STEP 4: Risk features
        # =================================================================
        log_step_header(4, "AJOUT FEATURES RSC (RISK)", 12)
        step_start = time.time()
        
        rsc = initial_data["rsc"]
        log_dataframe_info(df_main, "Input: df_main", "   ")
        log_dataframe_info(rsc, "Input: rsc", "   ")
        
        input_rows = df_main.height
        df_main = base_transformation.preprocess_risk(df_main, rsc)
        
        log_dataframe_info(df_main, "Output: df_main_risk", "   ")
        logger.info(f"   🔗 Jointure sur RSC effectuée")
        
        step_duration = time.time() - step_start
        log_step_duration("Risk features", step_duration)
        log_step_success("Risk features")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Risk features (RSC)",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        del rsc
        initial_data["rsc"] = None
        gc.collect()
        log_memory_freed("rsc")
        
        # =================================================================
        # STEP 5: Soldes features
        # =================================================================
        log_step_header(5, "AJOUT FEATURES SOLDES", 12)
        step_start = time.time()
        
        soldes = initial_data["soldes"]
        log_dataframe_info(df_main, "Input: df_main", "   ")
        log_dataframe_info(soldes, "Input: soldes", "   ")
        
        input_rows = df_main.height
        df_main = base_transformation.preprocess_soldes(df_main, soldes)
        
        log_dataframe_info(df_main, "Output: df_main_soldes", "   ")
        logger.info(f"   🔗 Jointure sur SOLDES effectuée")
        
        step_duration = time.time() - step_start
        log_step_duration("Soldes features", step_duration)
        log_step_success("Soldes features")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Soldes features",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        del soldes
        initial_data["soldes"] = None
        gc.collect()
        log_memory_freed("soldes")
        
        # =================================================================
        # STEP 6: Reboot features
        # =================================================================
        log_step_header(6, "AJOUT FEATURES REBOOT", 12)
        step_start = time.time()
        
        reboot = initial_data["reboot"]
        log_dataframe_info(df_main, "Input: df_main", "   ")
        log_dataframe_info(reboot, "Input: reboot", "   ")
        
        input_rows = df_main.height
        df_main = base_transformation.preprocess_reboot(df_main, reboot)
        
        log_dataframe_info(df_main, "Output: df_main_reboot", "   ")
        logger.info(f"   🔗 Jointure sur REBOOT effectuée")
        
        step_duration = time.time() - step_start
        log_step_duration("Reboot features", step_duration)
        log_step_success("Reboot features")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Reboot features",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        del reboot
        initial_data["reboot"] = None
        gc.collect()
        log_memory_freed("reboot")
        
        # =================================================================
        # STEP 7: Transaction features
        # =================================================================
        log_step_header(7, "AJOUT FEATURES TRANSAC", 12)
        step_start = time.time()
        
        donnees_transac = initial_data["donnees_transac"]
        log_dataframe_info(df_main, "Input: df_main", "   ")
        log_dataframe_info(donnees_transac, "Input: donnees_transac", "   ")
        
        input_rows = df_main.height
        df_main = base_transformation.preprocess_donnees_transac(df_main, donnees_transac)
        
        log_dataframe_info(df_main, "Output: df_main_transac", "   ")
        logger.info(f"   🔗 Jointure sur TRANSAC effectuée")
        
        step_duration = time.time() - step_start
        log_step_duration("Transac features", step_duration)
        log_step_success("Transac features")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Transac features",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        del donnees_transac
        initial_data["donnees_transac"] = None
        gc.collect()
        log_memory_freed("donnees_transac")
        
        # =================================================================
        # STEP 8: Safir Conso features
        # =================================================================
        log_step_header(8, "AJOUT FEATURES SAFIR CONSO", 12)
        step_start = time.time()
        
        safir_cc = initial_data["safir_cc"]
        safir_cd = initial_data["safir_cd"]
        log_dataframe_info(df_main, "Input: df_main", "   ")
        log_dataframe_info(safir_cc, "Input: safir_cc", "   ")
        log_dataframe_info(safir_cd, "Input: safir_cd", "   ")
        
        input_rows = df_main.height
        df_main = base_transformation.preprocess_safir_conso(df_main, safir_cc, safir_cd)
        
        log_dataframe_info(df_main, "Output: df_main_safir_conso", "   ")
        logger.info(f"   🔗 Jointure sur SAFIR CONSO effectuée")
        
        step_duration = time.time() - step_start
        log_step_duration("Safir Conso features", step_duration)
        log_step_success("Safir Conso features")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Safir Conso features",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        del safir_cc, safir_cd
        initial_data["safir_cc"] = None
        initial_data["safir_cd"] = None
        gc.collect()
        log_memory_freed("safir_cc, safir_cd")
        
        # =================================================================
        # STEP 9: Safir Soc features
        # =================================================================
        log_step_header(9, "AJOUT FEATURES SAFIR SOC", 12)
        step_start = time.time()
        
        safir_sc = initial_data["safir_sc"]
        safir_sd = initial_data["safir_sd"]
        log_dataframe_info(df_main, "Input: df_main", "   ")
        log_dataframe_info(safir_sc, "Input: safir_sc", "   ")
        log_dataframe_info(safir_sd, "Input: safir_sd", "   ")
        
        input_rows = df_main.height
        df_main = base_transformation.preprocess_safir_soc(df_main, safir_sc, safir_sd)
        
        log_dataframe_info(df_main, "Output: df_main_safir_soc", "   ")
        logger.info(f"   🔗 Jointure sur SAFIR SOC effectuée")
        
        step_duration = time.time() - step_start
        log_step_duration("Safir Soc features", step_duration)
        log_step_success("Safir Soc features")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Safir Soc features",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        del safir_sc, safir_sd
        initial_data["safir_sc"] = None
        initial_data["safir_sd"] = None
        gc.collect()
        log_memory_freed("safir_sc, safir_sd")
        
        # Libérer complètement initial_data
        del initial_data
        gc.collect()
        log_memory_freed("initial_data (toutes sources)")
        
        # =================================================================
        # STEP 10: Filtres PDO scope
        # =================================================================
        log_step_header(10, "APPLICATION FILTRES PDO SCOPE", 12)
        step_start = time.time()
        
        log_dataframe_info(df_main, "Input: df_main", "   ")
        input_rows = df_main.height
        
        df_main = base_transformation.preprocess_filters(df_main)
        
        log_dataframe_info(df_main, "Output: df_main_filtered", "   ")
        rows_filtered = input_rows - df_main.height
        logger.info(f"   🔍 Lignes filtrées: {rows_filtered:,} ({rows_filtered/input_rows*100:.1f}%)")
        
        step_duration = time.time() - step_start
        log_step_duration("Filtres PDO", step_duration)
        log_step_success("Filtres PDO")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Filtres PDO scope",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        # =================================================================
        # STEP 11: Format variables
        # =================================================================
        log_step_header(11, "FORMATAGE VARIABLES", 12)
        step_start = time.time()
        
        log_dataframe_info(df_main, "Input: df_main", "   ")
        input_rows = df_main.height
        
        df_main = base_transformation.preprocess_format(df_main)
        
        log_dataframe_info(df_main, "Output: df_main_format", "   ")
        
        step_duration = time.time() - step_start
        log_step_duration("Format variables", step_duration)
        log_step_success("Format variables")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Formatage variables",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        # =================================================================
        # STEP 12: Calcul PDO
        # =================================================================
        log_step_header(12, "CALCUL PDO", 12)
        step_start = time.time()
        
        log_dataframe_info(df_main, "Input: df_main", "   ")
        input_rows = df_main.height
        
        df_main = base_transformation.calcul_pdo(df_main)
        
        log_dataframe_info(df_main, "Output: df_main_pdo", "   ")
        
        # Statistiques PDO
        pdo_stats = df_main.select("PDO").describe()
        logger.info(f"   📈 Statistiques PDO:")
        logger.info(f"      └── Min: {df_main['PDO'].min():.6f}")
        logger.info(f"      └── Max: {df_main['PDO'].max():.6f}")
        logger.info(f"      └── Mean: {df_main['PDO'].mean():.6f}")
        logger.info(f"      └── Median: {df_main['PDO'].median():.6f}")
        
        step_duration = time.time() - step_start
        log_step_duration("Calcul PDO", step_duration)
        log_step_success("Calcul PDO")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Calcul PDO",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_main.height,
            status="SUCCESS"
        ))
        
        # =================================================================
        # STEP 13: Postprocessing
        # =================================================================
        log_step_header(13, "POSTPROCESSING", 12)
        step_start = time.time()
        
        log_dataframe_info(df_main, "Input: df_main_pdo", "   ")
        input_rows = df_main.height
        
        df_final = base_transformation.postprocess_df_main(df_main)
        
        log_dataframe_info(df_final, "Output: df_main_final", "   ")
        
        step_duration = time.time() - step_start
        log_step_duration("Postprocessing", step_duration)
        log_step_success("Postprocessing")
        
        batch_metrics.steps.append(StepMetrics(
            step_name="Postprocessing",
            duration_seconds=step_duration,
            input_rows=input_rows,
            output_rows=df_final.height,
            status="SUCCESS"
        ))
        
        # Store final metrics
        batch_metrics.final_output_rows = df_final.height
        batch_metrics.final_output_cols = df_final.width
        batch_metrics.status = "SUCCESS"
        
        # =================================================================
        # FINAL SUMMARY
        # =================================================================
        print_final_summary()
        
    except Exception as e:
        batch_metrics.status = "FAILED"
        batch_metrics.error_message = str(e)
        logger.error(f"❌ ERREUR FATALE: {str(e)}")
        print_final_summary()
        raise


if __name__ == "__main__":
    main()
