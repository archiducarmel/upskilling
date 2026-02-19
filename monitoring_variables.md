# Variables de monitoring — Pipeline STT + Contrôles réglementaires

44 variables retenues. Chaque variable alimente directement au moins une alerte, un KPI ou une analyse de drift.

---

## Étape 1 — STT + Diarization

### Input audio

#### `audio_id`
- **Type** : `str`
- **Description** : Identifiant unique de l'audio source. Clé primaire reliant toutes les étapes du pipeline, utilisée comme jointure dans toutes les analyses croisées et pour la traçabilité en audit réglementaire.

#### `run_id`
- **Type** : `str`
- **Description** : Identifiant unique de l'exécution du pipeline. Un même `audio_id` peut avoir plusieurs `run_id` en cas de retraitement. La paire `audio_id` + `run_id` est la clé unique d'un résultat. Sert au dédoublonnage et à la comparaison de stabilité entre runs.

#### `ingestion_timestamp`
- **Type** : `datetime`
- **Description** : Date/heure d'entrée de l'audio dans le pipeline. Axe temporel de référence pour toutes les agrégations : KPIs journaliers, fenêtres de drift, ordonnancement des alertes. Ne pas confondre avec la date d'enregistrement de l'appel.

#### `source_system`
- **Type** : `str`
- **Description** : Identifiant du système d'origine (call center, autocom, SVI…). Axe de segmentation le plus important du monitoring : la majorité des dégradations proviennent d'une source spécifique. Tous les KPIs STT doivent être segmentés par cette variable.

#### `duration_sec`
- **Type** : `float`
- **Description** : Durée de l'audio en secondes. Variable de normalisation pour le WPM, le real-time factor et l'alerte timeout. Sa distribution est monitorée en drift input car un changement de profil de durée impacte la troncation LLM.

#### `sample_rate_hz`
- **Type** : `int`
- **Description** : Fréquence d'échantillonnage en Hz (8000 téléphonie, 16000 VoIP/Whisper). Un audio à 8kHz dégrade la transcription par perte d'information fréquentielle. Utilisé en drift input pour détecter un changement technique amont.

#### `snr_db`
- **Type** : `float`
- **Description** : Rapport signal/bruit en dB. Variable prédictive n°1 de la qualité STT (≥30 dB propre, <15 dB dégradé). Utilisé dans : alerte audio dégradé, SNR médian par `source_system`, test KS hebdomadaire, régression `avg_log_prob ~ snr_db`, stratification hallucination par tranche, quality gate.

#### `silence_ratio_ch0`
- **Type** : `float`
- **Description** : Proportion de silence sur le canal 0 (agent/gauche), entre 0.0 et 1.0. Ratio >0.95 = canal mort, compromettant la diarization. Alimente l'alerte « canal mort » et le taux journalier, segmenté par `source_system`.

#### `silence_ratio_ch1`
- **Type** : `float`
- **Description** : Même mesure sur le canal 1 (client/droit). Monitoré séparément car le problème peut n'affecter qu'un canal et l'interprétation métier diffère.

### Config STT

#### `stt_model_version`
- **Type** : `str`
- **Description** : Version complète du modèle STT (ex : `faster-whisper-large-v3`). Variable de segmentation temporelle principale. Toutes les métriques output sont comparées avant/après changement. Indispensable pour la reproductibilité en audit.

#### `hotwords_list_hash`
- **Type** : `str`
- **Description** : Hash SHA-256 de la liste de hotwords Whisper. Trace chaque changement sans stocker la liste. Permet d'isoler l'impact des hotwords sur la confiance STT et le taux d'hallucination.

#### `language_setting`
- **Type** : `str`
- **Description** : Paramètre de langue Whisper (`"fr"` fixe ou `"auto"`). Combiné avec `detected_language` pour l'alerte « langue inattendue » : si auto et langue ≠ fr, transcription inutilisable.

### Output STT

#### `stt_status`
- **Type** : `str`
- **Description** : Statut de la transcription (`"success"` / `"failure"`). Taux de succès journalier (seuil : 99%), segmenté par `source_system` et `stt_model_version`. Prérequis du quality gate.

#### `stt_preprocessing_time_sec`
- **Type** : `float`
- **Description** : Temps de prétraitement audio en secondes (conversion, resampling, normalisation). Diagnostique l'origine d'un ralentissement STT. Sommé avec inference et postprocessing pour le real-time factor.

#### `stt_inference_time_sec`
- **Type** : `float`
- **Description** : Temps d'inférence Whisper pur en secondes. Composante la plus lourde. Le ratio avec `duration_sec` donne le real-time factor (doit rester <1.0). Une hausse à durée constante pointe vers un problème GPU.

#### `stt_postprocessing_time_sec`
- **Type** : `float`
- **Description** : Temps de postprocessing en secondes (alignement, diarization, formatage). Une hausse isolée pointe vers un problème d'alignement ou de diarization.

#### `detected_language`
- **Type** : `str`
- **Description** : Code langue ISO détecté par Whisper (ex : `"fr"`, `"en"`). Alerte « langue inattendue » avec `language_setting`. Sa distribution révèle un élargissement de population traitée.

#### `avg_log_prob`
- **Type** : `float`
- **Description** : Moyenne des log-probabilités par segment Whisper (nominal -0.2 à -0.5, incertain sous -0.8). Variable output STT la plus polyvalente : médiane quotidienne, moyenne mobile 7j, régression avec `snr_db` pour séparer problème audio/modèle, analyse croisée avec les décisions LLM.

#### `avg_no_speech_prob`
- **Type** : `float`
- **Description** : Moyenne des probabilités de non-parole par segment. Valeur >0.6 avec `total_word_count > 50` = hallucination Whisper. Alimente la règle d'hallucination, le taux sur le dashboard, et le drift par tranche de SNR.

#### `avg_compression_ratio`
- **Type** : `float`
- **Description** : Moyenne des ratios de compression par segment (normal 0.8-2.0, >2.4 = hallucination en boucle). Deuxième pilier de détection d'hallucination, complémentaire à `avg_no_speech_prob`. Composante du quality gate.

#### `total_word_count`
- **Type** : `int`
- **Description** : Nombre total de mots transcrits. Sert au WPM (normal 120-180 en français, <40 = mots manqués, >280 = hallucination). Alerte WPM anormal, KPI médian, drift, et seuil anti-faux-positifs dans la règle d'hallucination.

#### `num_speakers_detected`
- **Type** : `int`
- **Description** : Nombre de locuteurs identifiés par la diarization. Comparé à `num_speakers_expected` pour l'alerte d'incohérence. Une erreur impacte directement les contrôles distinguant agent vs client.

#### `num_speakers_expected`
- **Type** : `int | null`
- **Description** : Nombre de locuteurs attendu (paramètre de diarization, `null` si auto). Référence pour distinguer appel atypique vs erreur de diarization.

#### `speaker_time_ratios`
- **Type** : `dict[str, float]`
- **Description** : Distribution du temps de parole par locuteur (ex : `{"speaker_0": 0.65, "speaker_1": 0.35}`). Un locuteur >95% est suspect. Pertinent pour les contrôles portant sur les obligations verbales de l'agent.

---

## Étape 2 — Contrôles réglementaires (LLM)

### Input LLM

#### `controller_uid`
- **Type** : `str`
- **Description** : Identifiant du déclencheur du contrôle (personne ou processus). Segmente les KPIs par déclencheur, détecte les biais de contrôle, et assure la traçabilité en audit.

#### `control_id`
- **Type** : `str`
- **Description** : Identifiant de la grille de contrôle (qualité, RGPD, MiFID…). Axe de segmentation obligatoire pour tous les KPIs LLM : sans lui, un drift apparent peut simplement refléter un changement de proportion des motifs.

#### `transcript_token_count`
- **Type** : `int`
- **Description** : Tokens de la transcription seule (hors prompt). Un drift à la hausse signale des conversations plus longues et un risque accru de troncation. Corrélation avec la qualité des décisions pour mesurer l'impact de la longueur.

#### `transcript_truncated`
- **Type** : `bool`
- **Description** : Transcription tronquée pour la context window. Si `true`, contrôles sur contenu incomplet. Alerte temps réel, taux de troncation sur dashboard, `quality_gate_passed = false`.

#### `prompt_version`
- **Type** : `str`
- **Description** : Version sémantique du prompt template. Segmentation temporelle n°1 côté LLM. Chaque changement déclenche une comparaison avant/après des KPIs pour détecter les régressions.

#### `schema_version`
- **Type** : `str`
- **Description** : Version du schéma Pydantic de sortie. Évolue indépendamment du prompt. Distingue « le LLM a changé » de « le schéma a changé » lors d'une hausse d'échec de parsing.

#### `llm_model_version`
- **Type** : `str`
- **Description** : Version complète du modèle LLM. `prompt_version × llm_model_version` définit la configuration du système. Variable de segmentation et marqueur d'événement dans les dashboards.

### Output LLM

#### `llm_status`
- **Type** : `str`
- **Description** : Statut de l'appel LLM (`"success"` / `"failure"`). Taux de succès journalier (seuil : 99.5%), segmenté par `llm_model_version`. Prérequis du quality gate.

#### `llm_preprocessing_time_sec`
- **Type** : `float`
- **Description** : Temps de preprocessing LLM en secondes (construction prompt, tokenization, appel réseau). Diagnostique si une hausse de latence vient de l'assemblage ou du réseau.

#### `llm_inference_time_sec`
- **Type** : `float`
- **Description** : Temps d'inférence LLM pur en secondes. Composante la plus variable de la latence. Hausse à `transcript_token_count` constant = problème provider. P95 quotidien = KPI de performance principal.

#### `llm_postprocessing_time_sec`
- **Type** : `float`
- **Description** : Temps de postprocessing LLM en secondes (parsing, validation Pydantic, grounding). Hausse possible si schéma plus complexe ou fuzzy matching plus coûteux.

#### `prompt_tokens`
- **Type** : `int`
- **Description** : Tokens totaux envoyés au LLM (prompt + transcription). Détermine la proximité de la context window. `prompt_tokens - transcript_token_count` isole la croissance du template.

#### `completion_tokens`
- **Type** : `int`
- **Description** : Tokens générés par le LLM. Hausse soudaine à `prompt_version` constant = changement de comportement provider. Prédicteur de coût/latence. Avec `llm_finish_reason == "length"`, diagnostique une troncation par verbosité.

#### `llm_finish_reason`
- **Type** : `str`
- **Description** : Raison d'arrêt : `"stop"` (normal), `"length"` (tronqué), `"content_filter"` (filtré). `"length"` = alerte critique, checkpoints probablement manquants.

#### `parsing_success`
- **Type** : `bool`
- **Description** : Réponse LLM parsée avec succès dans le schéma Pydantic. Canari dans la mine : hausse d'échecs = premier signal d'un changement de comportement LLM. Alimente KPI parsing, analyse d'impact, quality gate.

#### `retry_count`
- **Type** : `int`
- **Description** : Nombre de retries avant résultat exploitable. Croissance même avec statut success = instabilité grandissante. Indicateur avancé de dégradation. Alerte si ≥3.

#### `num_checkpoints_evaluated`
- **Type** : `int`
- **Description** : Checkpoints effectivement évalués. Doit correspondre au nombre demandé (via `prompt_version` + `control_id`). Écart = oubli LLM ou troncation.

#### `num_checkpoints_missing`
- **Type** : `int`
- **Description** : Checkpoints demandés mais absents. Toute valeur >0 = alerte (contrôle obligatoire non effectué). Composante du quality gate.

#### `checkpoints` (structure répétée)

##### `checkpoint_id`
- **Type** : `str`
- **Description** : Identifiant du point de contrôle réglementaire. Axe de segmentation fondamental : chaque KPI doit être calculé par checkpoint car les dégradations sont rarement uniformes.

##### `decision`
- **Type** : `str` (enum : `OUI`, `NON`, `NON_CONCERNÉ`)
- **Description** : Décision réglementaire du LLM. Distribution par `checkpoint_id` = objet principal de l'analyse de drift (Chi² hebdomadaire). Shift significatif sans changement métier = drift LLM.

##### `num_evidences`
- **Type** : `int`
- **Description** : Nombre d'extraits cités comme preuves. Décision OUI/NON avec 0 evidence = décision non fondée. Taux de « décisions sans evidence » = KPI de fiabilité.

##### `evidences_grounded`
- **Type** : `list[bool]`
- **Description** : Pour chaque evidence, booléen de présence dans la transcription (fuzzy match). Variable la plus critique du pipeline. Grounding rate = KPI de fiabilité n°1. Sous 90% par checkpoint = décisions non fiables. Composante du quality gate.

---

## Pipeline

#### `pipeline_status`
- **Type** : `str`
- **Description** : Statut global (`"success"`, `"partial_failure"`, `"failure"`). Déduit de `stt_status` + `llm_status`. Filtre de premier niveau et entrée du quality gate.

#### `pipeline_total_duration_sec`
- **Type** : `float`
- **Description** : Durée end-to-end incluant les attentes inter-étapes. Avec `duration_sec`, donne le ratio de traitement global. Alerte timeout, KPI P95 latence. Détecte les problèmes d'infrastructure invisibles dans les timings isolés.
