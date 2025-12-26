/*
 * =============================================================================
 * REQUÊTE CORRIGÉE : query_starburst_transac_corrected_v2.sql
 * =============================================================================
 * 
 * CORRECTION CRITIQUE APPLIQUÉE :
 * -------------------------------
 * Bug LIKE avec | corrigé.
 * 
 * Le caractère | dans LIKE n'est PAS un opérateur OR !
 * 'A|B%' cherche littéralement le caractère |, pas "A OU B".
 * 
 * Lignes corrigées :
 *   - Ligne 9 (atd_tres_pub) : LIKE 'A|B%' → OR entre deux LIKE
 *   - Ligne 29 (tax) : LIKE 'DGFIP|D.G.F.I.P%' → OR entre deux LIKE
 *   - Ligne 30 (tax_credit>>sie) : LIKE 'SIE |S.I.E%' → OR entre deux LIKE
 * 
 * IMPACT DU BUG :
 * ---------------
 * La catégorie "atd_tres_pub" n'était JAMAIS détectée !
 * Cette catégorie est agrégée dans "saisie__" qui est utilisée pour 
 * calculer la feature "pres_saisie" du modèle.
 * 
 * Avec la correction, les ATD (Avis à Tiers Détenteur) seront maintenant
 * correctement identifiés, ce qui impactera les prédictions du modèle.
 * 
 * STRUCTURE PRÉSERVÉE :
 * ---------------------
 * - Window functions conservées (optimisées par Starburst)
 * - Pas de modification de l'agrégation
 * - ORDER BY final conservé
 * 
 * =============================================================================
 */

-------------Transactions-------------------------------------------------------
WITH
FUNCTION fct_find_category(code bigint, sens varchar, lib varchar)
RETURNS varchar
BEGIN
CASE
          WHEN code IN (9) and sens='debit' THEN return 'agios';
          WHEN code IN (32, 37, 46, 57, 91, 92, 93, 1191, 1192, 11939) AND lib LIKE 'AMORTISSEMENT PRET%' AND sens='credit' THEN return 'amort_pret';
          
          /* CORRECTION : Séparation du | en deux conditions OR */
          /* AVANT: LIKE 'AVIS A TIERS DETENTEUR TRESOR PUBLIC|OPPOSITION A TIERS DETENTEUR COLLECTIVIT%' */
          WHEN lib LIKE 'AVIS A TIERS DETENTEUR TRESOR PUBLIC%' 
            OR lib LIKE 'OPPOSITION A TIERS DETENTEUR COLLECTIVIT%' 
          THEN return 'atd_tres_pub';
          
          WHEN lib LIKE 'SAISIE ATTRIBUTION-BLOCAGE%' THEN return 'attri_blocage';
          WHEN code IN (98,557,1371,1372,1373,4160,5151,5152) AND sens='credit' THEN return 'centr_treso>>credit';
          WHEN code IN (89,511,1321,1322,506,1323,4110,5101,5102,9102) AND sens='debit' THEN return 'centr_treso>>debit';
          WHEN code IN (1,2,6,8,11,12,13,18,19,21,22,23,24,25,27,28,31,32,33,34,35,37,38,39,41,42,43,44,46,47,48,53,58,61,76,82,83,85,86,87,90,94,101,103,
                        104,105,106,107,109,110,404,503,507,508,509,510,512,513,514,515,516,519,529,548,549,801,802,803,804,805,806,807,808,809,810,811,
                        812,813,814,815,817,818,819,820,821,822,856,1101,1102,1103,1110,1111,1112,1113,1115,1116,1117,1118,1120,1121,1122,1123,1125,1126,
                        1127,1128,1130,1324,1325,1326,1327,1328,1329,3001,4201,6101,6201,6202,6203,9101,9103,9104,9105,9106,9107,9108,9111)
                        AND sens='debit' THEN return 'cost>>debit';
          WHEN code IN (569,1191,1192,1193,1194) AND sens='credit' THEN return 'cost>>credit';
          WHEN code IN (60, 84, 403, 405, 1104) AND sens='debit' THEN return 'cost>>cash';
          WHEN code IN (52, 73) AND sens='debit' THEN return 'cost>>provision';
          WHEN code IN (29, 54, 70, 1114, 1119, 1124, 1129, 1164, 1169, 1174, 1179, 6102) AND sens='debit' THEN return 'interets';
          WHEN code IN (856, 859) AND sens='credit' THEN return 'prlv_sepa_retourne';
          WHEN code IN (26, 78) AND sens='credit' THEN return 'recept_pret>>credit';
          WHEN code IN (74) AND sens='debit' THEN return 'recept_pret>>debit';
          WHEN code IN (1) AND sens='credit' THEN return 'rejected_check';
          WHEN code IN (36) AND sens='debit' THEN return 'remb_billet_fin';
          WHEN code IN (56) AND sens='debit' THEN return 'remb_dette';
          WHEN code IN (857) AND sens='credit' THEN return 'rembt_prlv_sepa';
          
          /* CORRECTION : Séparation du | en deux conditions OR */
          /* AVANT: lib LIKE 'DGFIP|D\.G\.F\.I\.P%' */
          WHEN code IN (568, 809, 810, 811, 812, 813, 814, 815, 817, 818, 819, 820, 821, 854, 855, 856, 857, 858, 859, 860) 
            AND (lib LIKE 'DGFIP%' OR lib LIKE 'D.G.F.I.P%') 
          THEN return 'tax';
          
          /* CORRECTION : Séparation du | en deux conditions OR */
          /* AVANT: lib LIKE 'SIE | S\.I\.E%' */
          WHEN code IN (568) 
            AND (lib LIKE 'SIE %' OR lib LIKE 'S.I.E%') 
            AND sens='credit' 
          THEN return 'tax_credit>>sie';
          
          WHEN code IN (4, 7, 10, 14, 21, 24, 25, 26, 32, 36, 37, 40, 46, 57, 67, 68, 86, 90, 91, 92, 93, 97, 99, 101, 103, 105, 106, 151, 152, 155, 158, 451,
                        553, 558, 560, 561, 563, 568, 814, 821, 854, 855, 858, 1101, 1102, 1103, 1191, 1192, 1193, 1194, 1351, 1352, 4201, 4251, 4252, 6101)
                        AND sens='credit' THEN return 'turnover';
          WHEN code IN (568,854,855,858,859,860) AND lib LIKE 'URSSAF%' AND sens='credit' THEN return 'urssaf>>credit';
          WHEN code IN (529,809,810,811,812,813,814,815,817,818,819,820,821) AND lib LIKE 'URSSAF%' AND sens='debit' THEN return 'urssaf>>debit';
END CASE;
RETURN NULL;
END

WITH f197 AS (
SELECT DISTINCT 
       w197_i_uniq_kpi_i
FROM "cat_ap80414_ice"."ap00382_refined_view"."v_fam197s_current"
WHERE w197_c_mrche_b = 'EN' AND w197_c_etat_prsne = 'C'
),

f096 AS (
SELECT DISTINCT 
       w096_i_uniq_kpi_i, 
       w096_i_intrn, 
       w096_i_uniq_kpi
FROM "cat_ap80414_ice"."ap00382_refined_view"."v_fam096s_current"
),

f197_f096 AS (
SELECT w197_i_uniq_kpi_i, 
       w096_i_uniq_kpi
FROM f197
LEFT OUTER JOIN f096 ON f197.w197_i_uniq_kpi_i = f096.w096_i_uniq_kpi_i
WHERE f096.w096_i_intrn IS NOT NULL and f096.w096_i_uniq_kpi IS NOT NULL
),

f165 AS (
SELECT DISTINCT 
       w165_i_uniq_kpi_membr, 
       w165_i_uniq_tit
FROM "cat_ap80414_ice"."ap00382_refined_view"."v_fam165s_current"
),

f161 AS (
SELECT DISTINCT 
       w161_i_uniq_kac_intne , 
       w161_i_uniq_ttlre
FROM "cat_ap80414_ice"."ap00382_refined_view"."v_fam161s_current"
),

mvts AS (
SELECT p_i_uniq_cpt,
       amount,
       fct_find_category(code, sens, lib) as category    
FROM
(
SELECT operations.p_i_uniq_cpt,
       CAST(operations.p_c_mvt_mc AS int) AS code,
       operations.p_l_extrt_mc AS lib,
       CAST(operations.p_m_comptabilise_mc AS decimal(38,2)) / 100 AS amount,
       CASE
            WHEN CAST(operations.p_m_comptabilise_mc AS decimal(38,2)) / 100 > 0  THEN 'credit'
            WHEN CAST(operations.p_m_comptabilise_mc AS decimal(38,2)) / 100 <= 0 THEN 'debit'
       END AS sens
FROM "cat_ap80414_ice"."ap00325_refined_view"."v_hsta92b0_detail" operations
LEFT JOIN "cat_ap80414_ice"."ap00325_refined_view"."v_hsta1100_detail" cancels ON (operations.p_i_mvt = cancels.i_mvt AND operations.p_d_opert = cancels.d_opert)
WHERE
  1=1
  AND operations.extract_date >  last_day_of_month(date_add('month', -7, CURRENT_DATE))
  AND operations.extract_date <= last_day_of_month(date_add('month', -1, CURRENT_DATE))
  AND operations.p_n_fam_type_cpt_mc = '100' /* les transactions sur les comptes à vue */
  AND cancels.i_uniq_cpt IS NULL
)
)

SELECT w096_i_uniq_kpi AS i_uniq_kpi, 
       category, 
       netamount, 
       nops_category, 
       min_amount, 
       max_amount, 
       nops_total
FROM
(
SELECT f197_f096.w096_i_uniq_kpi, 
       mvts.category, 
       amount,
       sum(amount)   over (partition by f197_f096.w096_i_uniq_kpi, mvts.category) netamount,
       count(amount) over (partition by f197_f096.w096_i_uniq_kpi, mvts.category) nops_category,
       min(amount)   over (partition by f197_f096.w096_i_uniq_kpi, mvts.category) min_amount,
       max(amount)   over (partition by f197_f096.w096_i_uniq_kpi, mvts.category) max_amount,
       count(amount) over (partition by f197_f096.w096_i_uniq_kpi) nops_total,
       row_number()  over (partition by f197_f096.w096_i_uniq_kpi, mvts.category order by 1) Rang
FROM f197_f096
JOIN f165 ON (f197_f096.w096_i_uniq_kpi = f165.w165_i_uniq_kpi_membr)
JOIN f161 ON (f165.w165_i_uniq_tit = f161.w161_i_uniq_ttlre)
JOIN mvts ON (f161.w161_i_uniq_kac_intne = mvts.p_i_uniq_cpt)
) SR
WHERE rang=1 AND category IS NOT NULL
ORDER BY w096_i_uniq_kpi, category
