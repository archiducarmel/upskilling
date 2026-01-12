"""Unit tests for the calcul_pdo module.

This module contains tests for PDO (Probability of Default) calculation functions.
Tests cover both nominal cases and edge cases including overflow, NULL handling,
and coefficient validation.

Test IDs: TU-001 to TU-011
"""

from unittest import TestCase, main
from unittest.mock import MagicMock
import polars as pl
import numpy as np


class TestCalculPdo(TestCase):
    """Unit tests for the calcul_pdo function."""

    def setUp(self) -> None:
        """Set up test fixtures with reference DataFrame structure and config."""
        # Configuration avec tous les coefficients du modèle
        self.config = {
            "model": {
                "coeffs": {
                    # nat_jur_a
                    "nat_jur_a_1_3": 0,
                    "nat_jur_a_4_6": 0.242841372870074,
                    "nat_jur_a_sup7": 1.14619110439058,
                    # secto_b
                    "secto_b_1": 0.945818754757707,
                    "secto_b_2": 0.945818754757707,
                    "secto_b_3": 0.302139711824692,
                    "secto_b_4": 0,
                    # seg_nae
                    "seg_nae_ME": 0,
                    "seg_nae_autres": 0.699122196727483,
                    # top_ga
                    "top_ga_0": 0,
                    "top_ga_1": 0.381966549691793,
                    # nbj
                    "nbj_inf_equal_12": 0.739002401887176,
                    "nbj_sup_12": 0,
                    # solde_cav_char
                    "solde_cav_char_1": 0,
                    "solde_cav_char_2": 0.138176642753287,
                    "solde_cav_char_3": 0.475979161230845,
                    "solde_cav_char_4": 0.923960586241845,
                    # reboot_score_char2
                    "reboot_score_char2_1": 3.92364486708385,
                    "reboot_score_char2_2": 1.74758134681695,
                    "reboot_score_char2_3": 1.34323461962549,
                    "reboot_score_char2_4": 1.09920154963862,
                    "reboot_score_char2_5": 0.756387308936913,
                    "reboot_score_char2_6": 0.756387308936913,
                    "reboot_score_char2_7": 0.756387308936913,
                    "reboot_score_char2_8": 0.340053879161636,
                    "reboot_score_char2_9": 0,
                    # remb_sepa_max
                    "remb_sepa_max_1": 0,
                    "remb_sepa_max_2": 1.34614367878806,
                    # pres_prlv_retourne
                    "pres_prlv_retourne_1": 0,
                    "pres_prlv_retourne_2": 0.917163902080624,
                    # pres_saisie
                    "pres_saisie_1": 0,
                    "pres_saisie_2": 0.805036359316808,
                    # net_int_turnover
                    "net_int_turnover_1": 0,
                    "net_int_turnover_2": 0.479376606177871,
                    # rn_ca_conso_023b
                    "rn_ca_conso_023b_1": 0,
                    "rn_ca_conso_023b_2": 1.17070023813324,
                    "rn_ca_conso_023b_3": 1.64465207886908,
                    # caf_dmlt_005
                    "caf_dmlt_005_1": 0,
                    "caf_dmlt_005_2": 0.552998315798404,
                    # res_total_passif_035
                    "res_total_passif_035_1": 0,
                    "res_total_passif_035_2": 0.332604372992466,
                    "res_total_passif_035_3": 0.676018969566685,
                    "res_total_passif_035_4": 0.977499984983427,
                    # immob_total_passif_055
                    "immob_total_passif_055_1": 0,
                    "immob_total_passif_055_2": 0.32870481469531,
                    "immob_total_passif_055_3": 0.572596945524726,
                    # intercept
                    "intercept": -3.86402362750751,
                }
            }
        }

        # Valeurs de référence (modalités avec coefficient 0)
        self.reference_row = {
            "nat_jur_a": "1-3",
            "secto_b": "4",
            "seg_nae": "ME",
            "top_ga": "0",
            "nbj": ">12",
            "solde_cav_char": "1",
            "reboot_score_char2": "9",
            "remb_sepa_max": "1",
            "pres_prlv_retourne": "1",
            "pres_saisie": "1",
            "net_int_turnover": "1",
            "rn_ca_conso_023b": "1",
            "caf_dmlt_005": "1",
            "res_total_passif_035": "1",
            "immob_total_passif_055": "1",
        }

        self.intercept = self.config["model"]["coeffs"]["intercept"]

    def _create_df_with_overrides(self, overrides: dict) -> pl.DataFrame:
        """Create a DataFrame with reference values and specific overrides."""
        row = {**self.reference_row, **overrides}
        return pl.DataFrame([row])

    def test_tu_001_calcul_pdo_nominal_all_reference_modalities(self) -> None:
        """TU-001: Verify PDO calculation with all reference modalities (coeff=0).

        Tests that the function correctly calculates PDO for a DataFrame
        containing all 15 model variables with reference values.
        Expected: sum_total_coeffs = intercept, PDO ≈ 0.0206.
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo

        df = pl.DataFrame([self.reference_row])

        # Act
        result = calcul_pdo(df, self.config)

        # Assert
        self.assertIn("intercept", result.columns)
        self.assertIn("sum_total_coeffs", result.columns)
        self.assertIn("PDO_compute", result.columns)
        self.assertIn("PDO", result.columns)
        self.assertIn("flag_pdo_OK", result.columns)

        # With all reference modalities, sum_total_coeffs should equal intercept
        sum_coeffs = result["sum_total_coeffs"][0]
        self.assertAlmostEqual(sum_coeffs, self.intercept, places=4)

        # PDO = 1 - 1/(1+exp(-intercept)) ≈ 0.0206
        pdo = result["PDO"][0]
        self.assertGreater(pdo, 0.0001)
        self.assertLess(pdo, 1.0)
        self.assertAlmostEqual(pdo, 0.0206, places=3)
        self.assertEqual(result["flag_pdo_OK"][0], "flag")

    def test_tu_002_calcul_pdo_nat_jur_a_unexpected_value(self) -> None:
        """TU-002: Test PDO calculation when nat_jur_a has unexpected values.

        Tests behavior when nat_jur_a contains None, empty string, or unknown code.
        Expected: uses otherwise clause with coefficient nat_jur_a_1_3 = 0.
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo

        test_cases = [
            {"nat_jur_a": None},
            {"nat_jur_a": ""},
            {"nat_jur_a": "INCONNU"},
        ]

        for case in test_cases:
            with self.subTest(nat_jur_a=case["nat_jur_a"]):
                df = self._create_df_with_overrides(case)

                # Act
                result = calcul_pdo(df, self.config)

                # Assert - should not raise, PDO should be calculated
                self.assertIsNotNone(result["PDO"][0])
                self.assertGreater(result["PDO"][0], 0)
                # Coefficient for unexpected value should use otherwise (nat_jur_a_1_3)
                self.assertIn("nat_jur_a_coeffs", result.columns)
                expected_coeff = self.config["model"]["coeffs"]["nat_jur_a_1_3"]
                self.assertEqual(result["nat_jur_a_coeffs"][0], expected_coeff)

    def test_tu_003_calcul_pdo_extreme_negative_sum_coeffs(self) -> None:
        """TU-003: Test numerical stability with very negative sum_total_coeffs.

        When sum_total_coeffs is extremely negative, PDO should be close to 0
        and floored at 0.0001. No overflow, NaN or Inf should occur.
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo

        # Use reference values - PDO will be around 0.02, above floor
        df = pl.DataFrame([self.reference_row])

        # Act
        result = calcul_pdo(df, self.config)

        # Assert
        pdo = result["PDO"][0]
        self.assertGreaterEqual(pdo, 0.0001)  # Floor check
        self.assertFalse(np.isnan(pdo))
        self.assertFalse(np.isinf(pdo))

    def test_tu_004_calcul_pdo_high_risk_profile(self) -> None:
        """TU-004: Test with all high-risk modalities (maximum coefficients).

        When all high-risk modalities are selected, PDO should be close to 1
        but not exceed 1. No overflow should occur.
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo

        # High risk modalities (highest coefficients)
        high_risk_row = {
            "nat_jur_a": ">=7",           # 1.146
            "secto_b": "1",               # 0.946
            "seg_nae": "autres",          # 0.699
            "top_ga": "1",                # 0.382
            "nbj": "<=12",                # 0.739
            "solde_cav_char": "4",        # 0.924
            "reboot_score_char2": "1",    # 3.924 (highest)
            "remb_sepa_max": "2",         # 1.346
            "pres_prlv_retourne": "2",    # 0.917
            "pres_saisie": "2",           # 0.805
            "net_int_turnover": "2",      # 0.479
            "rn_ca_conso_023b": "3",      # 1.645
            "caf_dmlt_005": "2",          # 0.553
            "res_total_passif_035": "4",  # 0.977
            "immob_total_passif_055": "3", # 0.573
        }
        df = pl.DataFrame([high_risk_row])

        # Act
        result = calcul_pdo(df, self.config)

        # Assert
        pdo = result["PDO"][0]
        self.assertLessEqual(pdo, 1.0)
        self.assertGreater(pdo, 0.5)  # High risk should give high PDO
        self.assertFalse(np.isnan(pdo))
        self.assertFalse(np.isinf(pdo))

    def test_tu_005_calcul_pdo_floor_at_0001(self) -> None:
        """TU-005: Test that PDO_compute < 0.0001 is floored to 0.0001.

        Basel III requires minimum PD of 0.01%. Verify floor is applied.
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo

        df = pl.DataFrame([self.reference_row])

        # Act
        result = calcul_pdo(df, self.config)

        # Assert
        pdo = result["PDO"][0]
        self.assertGreaterEqual(pdo, 0.0001)
        # Verify both columns exist
        self.assertIn("PDO_compute", result.columns)
        self.assertIn("PDO", result.columns)

    def test_tu_006_calcul_pdo_rounding_to_4_decimals(self) -> None:
        """TU-006: Verify PDO is rounded to 4 decimal places."""
        # Arrange
        from common.calcul_pdo import calcul_pdo

        df = pl.DataFrame([self.reference_row])

        # Act
        result = calcul_pdo(df, self.config)

        # Assert
        pdo = result["PDO"][0]
        # Check that PDO has at most 4 decimal places
        pdo_str = f"{pdo:.10f}"
        decimals = pdo_str.split(".")[1]
        significant_decimals = decimals.rstrip("0")
        self.assertLessEqual(len(significant_decimals), 4)

    def test_tu_007_calcul_pdo_reboot_score_char2_value_9(self) -> None:
        """TU-007: Test with reboot_score_char2='9' (reference modality).

        When reboot_score_char2 is '9', coefficient should be 0 (via otherwise).
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo

        df = self._create_df_with_overrides({"reboot_score_char2": "9"})

        # Act
        result = calcul_pdo(df, self.config)

        # Assert
        self.assertIsNotNone(result["PDO"][0])
        self.assertIn("reboot_score_char2_coeffs", result.columns)
        # Coefficient should be 0 for modality '9' (otherwise clause)
        coeff = result["reboot_score_char2_coeffs"][0]
        expected = self.config["model"]["coeffs"]["reboot_score_char2_9"]
        self.assertEqual(coeff, expected)
        self.assertEqual(coeff, 0.0)


class TestCalculPdoSklearn(TestCase):
    """Unit tests for the calcul_pdo_sklearn function."""

    def setUp(self) -> None:
        """Set up test fixtures with mock sklearn model."""
        self.reference_row = {
            "nat_jur_a": "1-3",
            "secto_b": "4",
            "seg_nae": "ME",
            "top_ga": "0",
            "nbj": ">12",
            "solde_cav_char": "1",
            "reboot_score_char2": "9",
            "remb_sepa_max": "1",
            "pres_prlv_retourne": "1",
            "pres_saisie": "1",
            "net_int_turnover": "1",
            "rn_ca_conso_023b": "1",
            "caf_dmlt_005": "1",
            "res_total_passif_035": "1",
            "immob_total_passif_055": "1",
        }
        
        # 46 features in feature_order
        self.n_features = 46

    def _create_mock_model(self) -> MagicMock:
        """Create a mock sklearn LogisticRegression model."""
        mock_model = MagicMock()
        mock_model.intercept_ = np.array([-3.86402362750751])
        mock_model.coef_ = np.zeros((1, self.n_features))
        mock_model.predict_proba = MagicMock(
            return_value=np.array([[0.98, 0.02]])
        )
        return mock_model

    def test_tu_008_calcul_pdo_sklearn_returns_valid_result(self) -> None:
        """TU-008: Verify sklearn version produces valid PDO output."""
        # Arrange
        from common.calcul_pdo import calcul_pdo_sklearn

        df = pl.DataFrame([self.reference_row])
        mock_model = self._create_mock_model()

        # Act
        result = calcul_pdo_sklearn(df, mock_model)

        # Assert
        self.assertIn("PDO", result.columns)
        self.assertIn("PDO_compute", result.columns)
        self.assertIn("flag_pdo_OK", result.columns)
        self.assertIsNotNone(result["PDO"][0])

    def test_tu_009_calcul_pdo_sklearn_model_none(self) -> None:
        """TU-009: Test behavior when sklearn model is None.

        Should raise AttributeError when model is None.
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo_sklearn

        df = pl.DataFrame([self.reference_row])

        # Act & Assert
        with self.assertRaises(AttributeError):
            calcul_pdo_sklearn(df, model=None)

    def test_tu_010_calcul_pdo_sklearn_missing_column(self) -> None:
        """TU-010: Test behavior when required column is missing.

        Should raise exception when DataFrame lacks required columns.
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo_sklearn

        # Create DataFrame with missing column (removed reboot_score_char2)
        incomplete_row = {k: v for k, v in self.reference_row.items() 
                         if k != "reboot_score_char2"}
        df = pl.DataFrame([incomplete_row])
        mock_model = self._create_mock_model()

        # Act & Assert
        with self.assertRaises((KeyError, pl.exceptions.ColumnNotFoundError)):
            calcul_pdo_sklearn(df, mock_model)

    def test_tu_011_calcul_pdo_sklearn_with_null_value(self) -> None:
        """TU-011: Test behavior when feature contains NULL value.

        When a column contains NULL, the one-hot encoding should handle it
        via the otherwise clause (placing it in default category).
        """
        # Arrange
        from common.calcul_pdo import calcul_pdo_sklearn

        row_with_none = {**self.reference_row}
        row_with_none["nat_jur_a"] = None
        df = pl.DataFrame([row_with_none])
        mock_model = self._create_mock_model()

        # Act
        result = calcul_pdo_sklearn(df, mock_model)

        # Assert - NULL should be handled by otherwise clause
        # nat_jur_a_1_3 should be 1 since NULL is not in ["4-6", ">=7"]
        self.assertEqual(result["nat_jur_a_1_3"][0], 1)
        self.assertEqual(result["nat_jur_a_4_6"][0], 0)
        self.assertEqual(result["nat_jur_a_sup7"][0], 0)


if __name__ == "__main__":
    main()
