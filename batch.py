"""
Batch processing for PDO calculation.
Main entry point for runtime execution.
"""

import gc
import logging
import os

from ml_utils.inference_decorator import duration_request
from ml_utils.logger_helper import configure_logger
from ml_utils.vault_connector import VaultConnector

from common.base_transformation import BaseTransformation
from common.config_context import ConfigContext
from common.constants import FILE_NAME_PROJECT_CONFIG, LOGGER_NAME
from common.logging_utils import (
    StepTracker,
    log_batch_start,
    log_config_loaded,
    log_vault_connected,
    log_memory_freed,
    log_batch_error,
    set_final_metrics,
    print_final_summary,
)
from config.load_config import load_app_config_file, load_config_domino_project_file, load_service_config_file
from settings import PROJECT_ROOT
from version import __version__

logger = logging.getLogger(LOGGER_NAME)

TOTAL_STEPS = 13


def load_configurations() -> tuple[dict, dict]:
    """Load and return app and service configurations."""
    load_service_config_file()
    app_config = load_app_config_file()
    project_config_path = os.path.join(PROJECT_ROOT, "config", "domino", FILE_NAME_PROJECT_CONFIG)
    project_config = load_config_domino_project_file(project_config_path)
    log_config_loaded()
    return app_config, project_config


@duration_request
def main() -> None:
    """Run main method for batch."""
    configure_logger()
    log_batch_start(__version__)
    
    try:
        # ==================== STEP 0: Configuration ====================
        with StepTracker(0, "CONFIGURATION", TOTAL_STEPS):
            app_config, project_config = load_configurations()
            config_context = ConfigContext()
            config_context.set("app_config", app_config)
            
            VaultConnector("config/domino/starburst_dev1.yml")
            VaultConnector("config/domino/starburst_dev2.yml")
            log_vault_connected()
            
            base_transformation = BaseTransformation(app_config)
        
        # ==================== STEP 1: Chargement SQL ====================
        with StepTracker(1, "CHARGEMENT DONNÉES SQL", TOTAL_STEPS) as tracker:
            initial_data = base_transformation.load_data()
            tracker.log_input_dict(initial_data, "Sources SQL")
        
        # ==================== STEP 2: Preprocessing df_main ====================
        with StepTracker(2, "PREPROCESSING DF_MAIN", TOTAL_STEPS) as tracker:
            tracker.log_input(initial_data["unfiltered_df_main"], "unfiltered_df_main")
            preprocessed_data = base_transformation.preprocess_df_main(initial_data["unfiltered_df_main"])
            df_main = preprocessed_data["df_main"]
            tracker.log_output(df_main, "df_main")
        
        del preprocessed_data
        log_memory_freed("preprocessed_data")
        
        # ==================== STEP 3: Encoding features ====================
        with StepTracker(3, "ENCODING FEATURES", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            df_main = base_transformation.preprocess_encoded_df_main(df_main)
            tracker.log_output(df_main, "df_main_encoded")
        
        # ==================== STEP 4: Risk features ====================
        with StepTracker(4, "FEATURES RSC (RISK)", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            tracker.log_input(initial_data["rsc"], "rsc")
            df_main = base_transformation.preprocess_risk(df_main, initial_data["rsc"])
            tracker.log_output(df_main, "df_main_risk")
            tracker.log_join("RSC")
        
        del initial_data["rsc"]
        log_memory_freed("rsc")
        
        # ==================== STEP 5: Soldes features ====================
        with StepTracker(5, "FEATURES SOLDES", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            tracker.log_input(initial_data["soldes"], "soldes")
            df_main = base_transformation.preprocess_soldes(df_main, initial_data["soldes"])
            tracker.log_output(df_main, "df_main_soldes")
            tracker.log_join("SOLDES")
        
        del initial_data["soldes"]
        log_memory_freed("soldes")
        
        # ==================== STEP 6: Reboot features ====================
        with StepTracker(6, "FEATURES REBOOT", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            tracker.log_input(initial_data["reboot"], "reboot")
            df_main = base_transformation.preprocess_reboot(df_main, initial_data["reboot"])
            tracker.log_output(df_main, "df_main_reboot")
            tracker.log_join("REBOOT")
        
        del initial_data["reboot"]
        log_memory_freed("reboot")
        
        # ==================== STEP 7: Transac features ====================
        with StepTracker(7, "FEATURES TRANSAC", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            tracker.log_input(initial_data["donnees_transac"], "donnees_transac")
            df_main = base_transformation.preprocess_donnees_transac(df_main, initial_data["donnees_transac"])
            tracker.log_output(df_main, "df_main_transac")
            tracker.log_join("TRANSAC")
        
        del initial_data["donnees_transac"]
        log_memory_freed("donnees_transac")
        
        # ==================== STEP 8: Safir Conso features ====================
        with StepTracker(8, "FEATURES SAFIR CONSO", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            tracker.log_input(initial_data["safir_cc"], "safir_cc")
            tracker.log_input(initial_data["safir_cd"], "safir_cd")
            df_main = base_transformation.preprocess_safir_conso(
                df_main, initial_data["safir_cc"], initial_data["safir_cd"]
            )
            tracker.log_output(df_main, "df_main_safir_conso")
            tracker.log_join("SAFIR CONSO")
        
        del initial_data["safir_cc"], initial_data["safir_cd"]
        log_memory_freed("safir_cc, safir_cd")
        
        # ==================== STEP 9: Safir Soc features ====================
        with StepTracker(9, "FEATURES SAFIR SOC", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            tracker.log_input(initial_data["safir_sc"], "safir_sc")
            tracker.log_input(initial_data["safir_sd"], "safir_sd")
            df_main = base_transformation.preprocess_safir_soc(
                df_main, initial_data["safir_sc"], initial_data["safir_sd"]
            )
            tracker.log_output(df_main, "df_main_safir_soc")
            tracker.log_join("SAFIR SOC")
        
        del initial_data
        log_memory_freed("initial_data (toutes sources)")
        
        # ==================== STEP 10: Filtres PDO ====================
        with StepTracker(10, "FILTRES PDO SCOPE", TOTAL_STEPS) as tracker:
            input_rows = df_main.height
            tracker.log_input(df_main, "df_main")
            df_main = base_transformation.preprocess_filters(df_main)
            tracker.log_output(df_main, "df_main_filtered")
            tracker.log_filter_stats(input_rows, df_main.height)
        
        # ==================== STEP 11: Format variables ====================
        with StepTracker(11, "FORMATAGE VARIABLES", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            df_main = base_transformation.preprocess_format(df_main)
            tracker.log_output(df_main, "df_main_format")
        
        # ==================== STEP 12: Calcul PDO ====================
        with StepTracker(12, "CALCUL PDO", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main")
            df_main = base_transformation.calcul_pdo(df_main)
            tracker.log_output(df_main, "df_main_pdo")
            tracker.log_pdo_stats(df_main)
        
        # ==================== STEP 13: Postprocessing ====================
        with StepTracker(13, "POSTPROCESSING", TOTAL_STEPS) as tracker:
            tracker.log_input(df_main, "df_main_pdo")
            df_final = base_transformation.postprocess_df_main(df_main)
            tracker.log_output(df_final, "df_main_final")
        
        set_final_metrics(df_final)
        print_final_summary()
        
    except Exception as e:
        log_batch_error(e)
        print_final_summary()
        raise


if __name__ == "__main__":
    main()
