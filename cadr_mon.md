# Analyse de votre besoin et méthodologie proposée

## Compréhension approfondie du besoin

Votre chantier s'inscrit dans une problématique centrale du MLOps : assurer l'observabilité et la fiabilité des modèles ML en production. La complexité de votre contexte réside dans l'hétérogénéité des use cases (tabulaire, NLP classique, GenAI), qui impliquent des métriques, des modes de dégradation et des temporalités de monitoring très différents.

L'enjeu n'est pas seulement technique mais aussi organisationnel : vous devez réconcilier les besoins métiers (qualité des prédictions, confiance utilisateur), les besoins techniques (performance, coûts, latence) et les besoins opérationnels (alerting, debugging, auditabilité).

---

## Méthodologie structurée en 5 phases

### Phase 1 — Cadrage et taxonomie préliminaire (Semaine 1-2)

Avant de collecter les besoins, il est essentiel de construire un référentiel commun qui servira de grille de lecture. Je vous propose d'établir une **taxonomie du monitoring ML** organisée selon plusieurs axes.

**Axe 1 : Les couches de monitoring**

La première couche concerne le **monitoring des inputs** (data quality monitoring) : détection de drift sur les features d'entrée, validation de schéma, détection d'outliers, complétude des données. La deuxième couche porte sur le **monitoring du modèle lui-même** : métriques de performance (accuracy, precision, recall, F1 pour la classification ; MAE, RMSE pour la régression ; BLEU, ROUGE, perplexité pour le NLP), drift de concept, calibration des probabilités. La troisième couche adresse le **monitoring des outputs** : distribution des prédictions, taux de confiance, cohérence temporelle des sorties. La quatrième couche, souvent négligée, est le **monitoring opérationnel** : latence, throughput, consommation de ressources, taux d'erreur technique. Enfin, la cinquième couche est le **feedback loop monitoring** : collecte des labels réels (ground truth), user feedback explicite et implicite, correction humaine.

**Axe 2 : La temporalité du monitoring**

Distinguez le monitoring **temps réel** (alerting immédiat sur anomalies critiques), le monitoring **batch/périodique** (rapports quotidiens ou hebdomadaires de santé du modèle), et le monitoring **rétrospectif** (analyse post-mortem, audit de performance sur période).

**Axe 3 : Les spécificités par typologie de modèle**

Pour les modèles tabulaires, le drift se mesure principalement par des tests statistiques (PSI, KS-test, chi-squared) sur les distributions de features. Pour le NLP classique, on surveille la distribution du vocabulaire, la longueur des textes, l'apparition de tokens inconnus. Pour le NLP GenAI, la complexité explose : vous devez monitorer la toxicité, les hallucinations, la cohérence sémantique, le respect des guardrails, et potentiellement mettre en place des évaluations LLM-as-a-judge.

**Livrable intermédiaire** : Document de cadrage avec la taxonomie complète et un glossaire partagé.

---

### Phase 2 — Collecte structurée des besoins (Semaine 3-4)

**Préparation des entretiens**

Construisez un guide d'entretien semi-directif autour de cinq thèmes : la description du use case et de son cycle de vie, les incidents passés et leur mode de détection, les métriques actuellement suivies (si existantes), les métriques souhaitées mais non implémentées, et les contraintes spécifiques (latence acceptable, fréquence de rafraîchissement des labels, sensibilité métier).

**Stratégie de collecte**

Menez des entretiens individuels avec chaque MLE/DS responsable d'un modèle en production (45-60 min par entretien). Complétez par un atelier collectif pour identifier les besoins transverses et favoriser le partage de bonnes pratiques. Distribuez également un questionnaire standardisé pour quantifier les priorités (criticité métier, maturité actuelle du monitoring, effort estimé).

**Grille d'analyse par use case**

Pour chaque modèle, documentez : le nom et la finalité du modèle, le type (classification, régression, génération, etc.), la fréquence d'inférence, le volume de données traitées, la disponibilité du ground truth et son délai d'obtention, les métriques de performance pertinentes, les risques spécifiques (drift saisonnier, sensibilité aux données manquantes, etc.), et les dépendances amont/aval.

**Livrable intermédiaire** : Matrice des besoins par use case, cartographie des risques.

---

### Phase 3 — Benchmark des outils (Semaine 5-6)

**Critères d'évaluation**

Évaluez les outils selon plusieurs dimensions : la couverture fonctionnelle (quels types de monitoring supportés nativement), l'intégration technique (compatibilité avec votre stack existante — cloud provider, orchestrateur, feature store), la flexibilité (possibilité d'ajouter des métriques custom), l'ergonomie (dashboards, alerting, API), le coût (licence, infrastructure, maintenance), et la maturité (communauté, documentation, roadmap).

**Panorama des outils à investiguer**

Dans la catégorie des plateformes MLOps intégrées, examinez Evidently AI (open source, excellente couverture du drift et de la data quality), Fiddler AI (fort sur l'explicabilité et le monitoring GenAI), Arize AI (très complet, bon support du NLP et des embeddings), WhyLabs (open source avec whylogs, léger et scalable), et MLflow + plugins (si déjà utilisé pour le tracking).

Pour le monitoring GenAI spécifiquement, regardez Langfuse (open source, conçu pour les applications LLM), LangSmith (écosystème LangChain), Weights & Biases Prompts, et Helicone.

Du côté des solutions de monitoring génériques adaptables, considérez Prometheus + Grafana (métriques custom, alerting), Datadog ML Monitoring, et les solutions natives cloud (AWS SageMaker Model Monitor, Azure ML Monitoring, Vertex AI Model Monitoring).

**Méthodologie de benchmark**

Pour chaque outil, réalisez un POC minimal sur un use case représentatif de chaque typologie (un modèle tabulaire, un modèle NLP classique, un modèle GenAI). Évaluez le temps d'intégration, la qualité des insights produits, et la capacité à répondre aux besoins spécifiques identifiés en Phase 2.

**Livrable intermédiaire** : Matrice comparative des outils avec scoring multicritère.

---

### Phase 4 — Analyse de convergence et recommandations (Semaine 7-8)

**Question centrale : un outil unique est-il viable ?**

L'analyse doit répondre à cette question en considérant plusieurs scénarios.

Le **scénario 1** est celui de l'outil unique. Il est envisageable si vous trouvez une plateforme suffisamment flexible pour couvrir 80% des besoins avec des métriques natives et permettant d'intégrer des métriques custom pour les 20% restants. Avantages : réduction de la complexité opérationnelle, cohérence des dashboards, courbe d'apprentissage unique. Inconvénients : risque de compromis sur certains use cases, dépendance à un vendor unique.

Le **scénario 2** est celui de l'architecture hybride. Il consiste à utiliser un socle commun pour le monitoring infrastructure et opérationnel (ex: Prometheus/Grafana ou Datadog), et des outils spécialisés par typologie de modèle. C'est souvent le compromis réaliste, surtout si vos use cases GenAI ont des besoins très spécifiques (évaluation de toxicité, détection d'hallucinations).

Le **scénario 3** est l'approche "build". Il s'agit de développer un framework interne de monitoring s'appuyant sur des briques open source. Ce scénario convient uniquement si vous avez des besoins très spécifiques non couverts par le marché et les ressources pour maintenir cette solution.

**Critères de décision**

La décision dépendra du ratio coût/bénéfice par scénario, de l'effort d'intégration et de maintenance, de la capacité à évoluer avec l'ajout de nouveaux modèles, et de l'acceptation par les équipes (adoption).

**Livrable intermédiaire** : Analyse comparative des scénarios avec recommandation argumentée.

---

### Phase 5 — Rédaction de la note de synthèse (Semaine 9)

**Structure recommandée pour le livrable final**

Le document devrait s'ouvrir sur un **executive summary** d'une à deux pages présentant le contexte et les enjeux, la méthodologie suivie, les principales conclusions, et la recommandation stratégique.

La première section développerait le **contexte et périmètre** : présentation de la squad et des use cases couverts, définition du monitoring ML et de ses enjeux, et périmètre de l'étude.

La deuxième section exposerait la **taxonomie du monitoring ML** avec le framework de classification retenu, les spécificités par typologie de modèle, et le mapping besoins/couches de monitoring.

La troisième section présenterait la **cartographie des besoins** : synthèse des besoins collectés, priorisation par criticité et faisabilité, et gaps identifiés par rapport à l'existant.

La quatrième section détaillerait le **benchmark des outils** avec la méthodologie d'évaluation, la matrice comparative, les retours sur les POC réalisés, et l'analyse coût/bénéfice.

La cinquième section formulerait les **recommandations** : l'architecture cible proposée, la roadmap d'implémentation avec les quick wins et les chantiers structurants, les prérequis techniques et organisationnels, et les KPIs de succès du projet.

Les **annexes** incluraient le guide d'entretien utilisé, les fiches détaillées par use case, les fiches détaillées par outil, et le glossaire.

---

## Facteurs clés de succès

**Sur le plan méthodologique**, impliquez les équipes dès la phase de cadrage pour favoriser l'appropriation, privilégiez des critères de décision objectifs et mesurables, et documentez les arbitrages pour faciliter la maintenance future.

**Sur le plan technique**, ne sous-estimez pas l'importance du ground truth : un monitoring sans feedback réel reste aveugle. Anticipez la question de l'alerting : trop d'alertes tue l'alerte. Prévoyez une stratégie de seuils adaptatifs.

**Sur le plan organisationnel**, clarifiez les responsabilités : qui monitore, qui réagit aux alertes, qui décide d'un retraining ? Formalisez les processus de réponse aux incidents.

---

Souhaitez-vous que j'approfondisse un aspect particulier de cette méthodologie, que je vous propose un template de guide d'entretien, ou que je détaille davantage le benchmark des outils avec une recherche actualisée ?

---

# Analyse de votre proposition taxonomique

Votre intuition est pertinente et rejoint une distinction fondamentale en MLOps. Cependant, je vous propose de l'affiner pour en faire un framework robuste et opérationnel.

---

## Validation et enrichissement du modèle

Votre équation **Monitoring = Observabilité + Évaluation** capture bien deux dimensions complémentaires, mais elle mérite d'être précisée car ces termes sont souvent utilisés de manière interchangeable dans la littérature, ce qui crée de la confusion.

Je vous propose un modèle en trois couches qui explicite mieux les responsabilités et les flux :

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MONITORING ML                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │  COUCHE 1 — INSTRUMENTATION (Collecte)                    │    │
│   │  "Capturer ce qui se passe"                               │    │
│   │                                                           │    │
│   │  • Logging des inputs/outputs                             │    │
│   │  • Traces d'exécution                                     │    │
│   │  • Métriques techniques (latence, throughput)             │    │
│   │  • Snapshots des données                                  │    │
│   └───────────────────────────────────────────────────────────┘    │
│                            │                                        │
│                            ▼                                        │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │  COUCHE 2 — OBSERVABILITÉ (Visibilité)                    │    │
│   │  "Rendre visible et compréhensible"                       │    │
│   │                                                           │    │
│   │  • Agrégation et stockage                                 │    │
│   │  • Dashboards et visualisations                           │    │
│   │  • Exploration ad hoc                                     │    │
│   │  • Traçabilité bout-en-bout                               │    │
│   └───────────────────────────────────────────────────────────┘    │
│                            │                                        │
│                            ▼                                        │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │  COUCHE 3 — ÉVALUATION (Jugement)                         │    │
│   │  "Décider si c'est conforme aux attentes"                 │    │
│   │                                                           │    │
│   │  • Analyse quantitative (métriques, seuils, drift)        │    │
│   │  • Analyse qualitative (revue humaine, feedback)          │    │
│   │  • Comparaison au comportement attendu                    │    │
│   │  • Alerting et détection d'anomalies                      │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Définitions précises pour votre taxonomie

### Couche 1 — Instrumentation

C'est le **prérequis technique** : la capacité à capturer les données nécessaires au monitoring. Sans instrumentation, pas d'observabilité possible.

Elle répond à la question : *"Quelles données dois-je collecter et comment ?"*

**Composantes concrètes :**
- Logging structuré des requêtes (input features, timestamps, metadata contextuelles)
- Logging des réponses (prédictions, scores de confiance, tokens générés pour GenAI)
- Métriques d'infrastructure (CPU, mémoire, latence p50/p95/p99)
- Versioning implicite (quel modèle, quelle version de features)

### Couche 2 — Observabilité

L'observabilité est la **capacité à comprendre l'état interne d'un système à partir de ses outputs externes**. C'est un concept emprunté à la théorie des systèmes.

Elle répond à la question : *"Que s'est-il passé et puis-je le comprendre ?"*

**Distinction clé** : l'observabilité ne porte pas de jugement de valeur. Elle rend les choses *visibles* mais ne dit pas si c'est *bien ou mal*. Un dashboard qui montre la distribution des prédictions fait de l'observabilité. Ce dashboard ne vous dit pas si cette distribution est problématique.

**Composantes concrètes :**
- Stockage des logs et métriques (data lake, time-series DB)
- Dashboards de visualisation
- Capacité de drill-down et d'investigation
- Corrélation entre événements

### Couche 3 — Évaluation

L'évaluation introduit la **dimension normative** : on compare ce qui est observé à ce qui est attendu.

Elle répond à la question : *"Est-ce que le modèle se comporte comme il devrait ?"*

**C'est ici que se joue la valeur métier du monitoring.** L'évaluation nécessite de définir :
- Des **références** (baseline de performance, distribution historique, ground truth)
- Des **seuils** (à partir de quand considère-t-on qu'il y a un problème ?)
- Des **critères qualitatifs** (pour les cas où une métrique ne suffit pas)

---

## La dimension souvent oubliée : le Feedback Loop

Votre mention du "user feedback = golden source" est cruciale. Je vous suggère d'intégrer explicitement une quatrième dimension transverse :

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FEEDBACK LOOP                                  │
│            (Alimente l'évaluation en ground truth)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Source explicite          │    Source implicite                   │
│   ─────────────────         │    ──────────────────                 │
│   • Labels manuels          │    • Comportement utilisateur         │
│   • Corrections humaines    │    • Taux de clic / conversion        │
│   • Votes qualité           │    • Temps passé sur résultat         │
│   • Feedback verbatim       │    • Reformulation de requête         │
│                             │    • Abandon / retry                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

Ce feedback est ce qui permet de **fermer la boucle** et de passer d'un monitoring passif à un monitoring qui améliore réellement le système.

---

## Application par typologie de use case

Cette taxonomie prend des formes différentes selon vos use cases :

### Modèles tabulaires (classification/régression)

| Couche | Application concrète |
|--------|---------------------|
| Instrumentation | Log des feature vectors, prédictions, probabilités |
| Observabilité | Distribution des features dans le temps, histogrammes des prédictions |
| Évaluation quantitative | PSI/KS-test sur features, accuracy vs baseline si labels disponibles |
| Évaluation qualitative | Revue d'échantillons de prédictions extrêmes |
| Feedback | Labels différés (ex: défaut de paiement confirmé à J+30) |

### NLP classique

| Couche | Application concrète |
|--------|---------------------|
| Instrumentation | Texte brut, embeddings, prédictions, scores |
| Observabilité | Distribution de longueur de textes, fréquence de vocabulaire, taux de tokens OOV |
| Évaluation quantitative | Drift d'embeddings (distance cosine), métriques de classification |
| Évaluation qualitative | Revue de cas de faible confiance, analyse d'erreurs par catégorie |
| Feedback | Corrections utilisateur, escalades au support |

### NLP GenAI

| Couche | Application concrète |
|--------|---------------------|
| Instrumentation | Prompt complet, réponse générée, tokens consommés, latence, metadata (température, modèle) |
| Observabilité | Distribution de longueur de réponses, patterns de prompts, coûts |
| Évaluation quantitative | Scores de toxicité, détection d'hallucination (NLI-based), respect de format |
| Évaluation qualitative | LLM-as-judge, revue humaine d'échantillons, analyse de cas de guardrail triggered |
| Feedback | Thumbs up/down, régénérations, éditions manuelles de réponses |

---

## Proposition de formulation finale pour votre taxonomie

Je vous suggère d'adopter cette formulation dans votre livrable :

> **Le monitoring ML est un processus en trois couches :**
> 
> 1. **L'instrumentation** assure la collecte exhaustive et structurée des données de fonctionnement du modèle (inputs, outputs, métadonnées, métriques techniques).
> 
> 2. **L'observabilité** transforme ces données brutes en informations exploitables, permettant de visualiser et comprendre le comportement du modèle dans le temps.
> 
> 3. **L'évaluation** confronte ce comportement observé aux attentes fonctionnelles et techniques, via des analyses quantitatives (métriques, tests statistiques, seuils) et qualitatives (revue humaine, feedback utilisateur).
> 
> Ces trois couches sont alimentées par un **feedback loop** qui collecte progressivement la vérité terrain (ground truth) et permet d'affiner l'évaluation.

---

Cette structuration vous convient-elle ? Souhaitez-vous que je développe davantage l'une de ces couches, ou que je travaille sur le guide d'entretien qui permettrait de collecter les besoins selon cette grille ?

---

Je reprends l'exercice avec un focus strict sur les solutions **open-source self-hostables** et des architectures **production-ready** complètes.J'ai maintenant toutes les informations nécessaires. Voici trois architectures **100% open-source self-hostables** avec tous les composants de production détaillés.

---

# 3 Architectures MLOps Monitoring — Open-Source Self-Hosted

## Synthèse comparative rapide

| Critère | Scénario 1 | Scénario 2 | Scénario 3 |
|---------|------------|------------|------------|
| **Philosophie** | Tout-en-un minimaliste | Spécialisation maximale | Équilibre optimal |
| **Outils monitoring** | Phoenix (1 seul) | Evidently + Langfuse (2) | Phoenix + Evidently (2) |
| **Licence** | Elastic License 2.0 | Apache 2.0 + MIT | ELv2 + Apache 2.0 |
| **Stockage principal** | PostgreSQL | PostgreSQL + ClickHouse | PostgreSQL |
| **Complexité déploiement** | ⭐ Faible | ⭐⭐⭐ Élevée | ⭐⭐ Moyenne |
| **Couverture fonctionnelle** | ⭐⭐⭐ Bonne | ⭐⭐⭐⭐⭐ Excellente | ⭐⭐⭐⭐ Très bonne |

---

## Scénario 1 — Ultra-minimaliste : Phoenix + Prometheus/Grafana

### Principe

Phoenix est construit sur OpenTelemetry, agnostique du vendor, framework et langage. Phoenix est entièrement open source et self-hostable — sans restrictions de fonctionnalités.

C'est l'option la plus simple : **un seul outil** couvre à la fois le ML traditionnel et le GenAI.

### Architecture complète

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        SCÉNARIO 1 — ARCHITECTURE PHOENIX                        │
│                         (Ultra-minimaliste : 1 outil ML)                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                           KUBERNETES CLUSTER                              │ │
│  │                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    NAMESPACE: ml-applications                       │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │ │ │
│  │  │  │ Modèles         │  │ Modèles NLP     │  │ Applications GenAI  │ │ │ │
│  │  │  │ Tabulaires      │  │ Classique       │  │ (LLM/RAG/Agents)    │ │ │ │
│  │  │  │                 │  │                 │  │                     │ │ │ │
│  │  │  │ FastAPI/Flask   │  │ FastAPI/Flask   │  │ LangChain/LlamaIndex│ │ │ │
│  │  │  │ Deployment      │  │ Deployment      │  │ Deployment          │ │ │ │
│  │  │  │ (2-4 replicas)  │  │ (2-4 replicas)  │  │ (2-4 replicas)      │ │ │ │
│  │  │  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘ │ │ │
│  │  │           │                    │                      │            │ │ │
│  │  │           │    INSTRUMENTATION OPENINFERENCE / OTLP   │            │ │ │
│  │  │           └────────────────────┼──────────────────────┘            │ │ │
│  │  │                                │                                   │ │ │
│  │  │                                ▼                                   │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐  │ │ │
│  │  │  │                    PHOENIX SDK                              │  │ │ │
│  │  │  │                                                             │  │ │ │
│  │  │  │  # Tabulaire/NLP classique (batch)                          │  │ │ │
│  │  │  │  px.Client().log_evaluations(eval_df)                       │  │ │ │
│  │  │  │                                                             │  │ │ │
│  │  │  │  # GenAI (streaming via OpenTelemetry)                      │  │ │ │
│  │  │  │  from phoenix.otel import register                          │  │ │ │
│  │  │  │  register(project_name="my-app", auto_instrument=True)      │  │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘  │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                   │                                       │ │
│  │                                   │ OTLP (gRPC :4317 / HTTP :6006)        │ │
│  │                                   ▼                                       │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    NAMESPACE: monitoring                            │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │                 PHOENIX SERVER                              │   │ │ │
│  │  │  │                 (Deployment: 2 replicas)                    │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Image: arizephoenix/phoenix:latest                         │   │ │ │
│  │  │  │  Resources: 2 CPU / 4 GB RAM par pod                        │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Ports exposés:                                             │   │ │ │
│  │  │  │  ├── 6006: UI Web + API HTTP + OTLP HTTP                    │   │ │ │
│  │  │  │  ├── 4317: OTLP gRPC (traces streaming)                     │   │ │ │
│  │  │  │  └── 9090: Prometheus metrics endpoint                      │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Fonctionnalités:                                           │   │ │ │
│  │  │  │  ├── Tracing LLM/Agents (OpenTelemetry)                     │   │ │ │
│  │  │  │  ├── Embeddings analysis (drift NLP/CV)                     │   │ │ │
│  │  │  │  ├── LLM-as-Judge evaluations                               │   │ │ │
│  │  │  │  ├── Prompt playground & versioning                         │   │ │ │
│  │  │  │  └── Dataset management                                     │   │ │ │
│  │  │  └──────────────────────┬──────────────────────────────────────┘   │ │ │
│  │  │                         │                                          │ │ │
│  │  │                         ▼                                          │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │              POSTGRESQL (StatefulSet)                       │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Image: postgres:16-alpine                                  │   │ │ │
│  │  │  │  Resources: 2 CPU / 4 GB RAM                                │   │ │ │
│  │  │  │  Storage: PVC 100 GB (expandable)                           │   │ │ │
│  │  │  │  StorageClass: gp3 (AWS) / pd-ssd (GCP)                     │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Contenu stocké:                                            │   │ │ │
│  │  │  │  ├── Traces et spans                                        │   │ │ │
│  │  │  │  ├── Evaluations et scores                                  │   │ │ │
│  │  │  │  ├── Datasets et experiments                                │   │ │ │
│  │  │  │  └── Prompts et versions                                    │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  ⚠️  Pour PROD: utiliser RDS/Cloud SQL managé              │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │              PROMETHEUS (StatefulSet)                       │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Image: prom/prometheus:v2.50.0                             │   │ │ │
│  │  │  │  Resources: 1 CPU / 2 GB RAM                                │   │ │ │
│  │  │  │  Storage: PVC 50 GB                                         │   │ │ │
│  │  │  │  Retention: 15 jours                                        │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Scrape targets:                                            │   │ │ │
│  │  │  │  ├── phoenix:9090/metrics (ML metrics)                      │   │ │ │
│  │  │  │  ├── node-exporter (infra)                                  │   │ │ │
│  │  │  │  └── kube-state-metrics (K8s)                               │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  │                         │                                          │ │ │
│  │  │                         ▼                                          │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │              GRAFANA (Deployment)                           │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Image: grafana/grafana:10.3.0                              │   │ │ │
│  │  │  │  Resources: 1 CPU / 1 GB RAM                                │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Dashboards préconfigurés:                                  │   │ │ │
│  │  │  │  ├── Infrastructure (CPU, RAM, latence)                     │   │ │ │
│  │  │  │  ├── ML Models Health (métriques Phoenix)                   │   │ │ │
│  │  │  │  └── Alerting (Slack, PagerDuty, Email)                     │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                      SERVICES EXTERNES (Optionnel)                        │ │
│  │                                                                           │ │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────────────────┐│ │
│  │  │  OBJECT STORAGE     │  │  MANAGED POSTGRESQL                         ││ │
│  │  │  (COS)              │  │  (Recommandé PROD)                          ││ │
│  │  │                     │  │                                             ││ │
│  │  │  MinIO / S3 / GCS   │  │  AWS RDS / GCP Cloud SQL / Azure PostgreSQL ││ │
│  │  │                     │  │                                             ││ │
│  │  │  Usage:             │  │  Specs recommandées:                        ││ │
│  │  │  • Backup snapshots │  │  • db.r6g.large (2 vCPU, 16 GB)            ││ │
│  │  │  • Export reports   │  │  • 200 GB gp3 storage                       ││ │
│  │  │  • Archivage        │  │  • Multi-AZ pour HA                         ││ │
│  │  │                     │  │                                             ││ │
│  │  │  Volume: ~50 GB/an  │  │  Coût: ~$150-300/mois                       ││ │
│  │  └─────────────────────┘  └─────────────────────────────────────────────┘│ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Flux de données

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FLUX DE DONNÉES                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  FLUX 1: GenAI/LLM (STREAMING - API temps réel)                          │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                          │  │
│  │  User Request                                                            │  │
│  │       │                                                                  │  │
│  │       ▼                                                                  │  │
│  │  Application LLM ──► @observe() decorator                                │  │
│  │       │                     │                                            │  │
│  │       │                     ▼                                            │  │
│  │       │              OpenInference auto-instrumentation                  │  │
│  │       │                     │                                            │  │
│  │       │                     ├── span: user_input                         │  │
│  │       │                     ├── span: retrieval (RAG)                    │  │
│  │       │                     ├── span: llm_generation                     │  │
│  │       │                     └── span: post_processing                    │  │
│  │       │                     │                                            │  │
│  │       │                     ▼                                            │  │
│  │       │              OTLP gRPC (:4317) ──► Phoenix Server                │  │
│  │       │                                         │                        │  │
│  │       ▼                                         ▼                        │  │
│  │  Response to user                         PostgreSQL                     │  │
│  │                                                                          │  │
│  │  Latence ajoutée: < 5ms (async, non-blocking)                           │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  FLUX 2: ML Tabulaire/NLP classique (BATCH - jobs schedulés)            │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                          │  │
│  │  Airflow/Prefect DAG (scheduled: daily/hourly)                           │  │
│  │       │                                                                  │  │
│  │       ▼                                                                  │  │
│  │  1. Extract inference logs from Feature Store / Data Lake                │  │
│  │       │                                                                  │  │
│  │       ▼                                                                  │  │
│  │  2. Compute evaluations with Phoenix SDK                                 │  │
│  │     ┌────────────────────────────────────────────────────┐              │  │
│  │     │  import phoenix as px                              │              │  │
│  │     │  from phoenix.evals import llm_classify            │              │  │
│  │     │                                                    │              │  │
│  │     │  # Log tabular evaluations                         │              │  │
│  │     │  px.Client().log_evaluations(                      │              │  │
│  │     │      project_name="tabular-model",                 │              │  │
│  │     │      evaluations=eval_results                      │              │  │
│  │     │  )                                                 │              │  │
│  │     └────────────────────────────────────────────────────┘              │  │
│  │       │                                                                  │  │
│  │       ▼                                                                  │  │
│  │  3. Results stored in PostgreSQL                                         │  │
│  │       │                                                                  │  │
│  │       ▼                                                                  │  │
│  │  4. Metrics exposed to Prometheus (:9090)                                │  │
│  │       │                                                                  │  │
│  │       ▼                                                                  │  │
│  │  5. Grafana dashboards updated                                           │  │
│  │                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Fichiers de déploiement

**docker-compose.yml (développement/petit déploiement)**

```yaml
# docker-compose.yml
version: '3.8'

services:
  phoenix:
    image: arizephoenix/phoenix:latest
    depends_on:
      - postgres
    ports:
      - "6006:6006"   # UI + API HTTP
      - "4317:4317"   # OTLP gRPC
      - "9090:9090"   # Prometheus metrics
    environment:
      - PHOENIX_SQL_DATABASE_URL=postgresql://phoenix:phoenix@postgres:5432/phoenix
      - PHOENIX_ENABLE_PROMETHEUS=true
    restart: unless-stopped
    
  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=phoenix
      - POSTGRES_PASSWORD=phoenix
      - POSTGRES_DB=phoenix
    volumes:
      - phoenix_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v2.50.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9091:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=15d'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.3.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    restart: unless-stopped

volumes:
  phoenix_data:
  prometheus_data:
  grafana_data:
```

**Helm values.yaml (Kubernetes production)**

```yaml
# values-phoenix-prod.yaml
phoenix:
  replicaCount: 2
  image:
    repository: arizephoenix/phoenix
    tag: "latest"  # Pinner une version en PROD
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"
  
  postgresql:
    enabled: false  # Utiliser PostgreSQL externe
  
  externalPostgresql:
    host: "phoenix-db.xxx.rds.amazonaws.com"
    port: 5432
    database: "phoenix"
    existingSecret: "phoenix-db-credentials"
    
  prometheus:
    enabled: true
    port: 9090

  ingress:
    enabled: true
    className: "nginx"
    hosts:
      - host: phoenix.internal.company.com
        paths:
          - path: /
            pathType: Prefix
```

### Couverture fonctionnelle

| Besoin | Tabulaire | NLP Classique | GenAI/LLM | Couvert par |
|--------|-----------|---------------|-----------|-------------|
| Data drift | ⚠️ Partiel | ✅ Embedding drift | ✅ Prompt drift | Phoenix |
| Performance metrics | ⚠️ Via evals custom | ⚠️ Via evals custom | ✅ Natif | Phoenix |
| Data quality | ⚠️ Limité | ⚠️ Limité | ✅ Guardrails | Phoenix |
| Tracing | ❌ | ❌ | ✅ Excellent | Phoenix |
| LLM evaluations | N/A | N/A | ✅ LLM-as-Judge | Phoenix |
| Alerting | ✅ | ✅ | ✅ | Grafana |
| Cost tracking | ❌ | ❌ | ✅ Token counting | Phoenix |

### Coûts infrastructure

| Composant | Specs | Coût mensuel (AWS) |
|-----------|-------|-------------------|
| EKS Cluster | 3 nodes t3.medium | ~$150 |
| Phoenix pods | 2 × (2 CPU, 4 GB) | Inclus dans nodes |
| RDS PostgreSQL | db.r6g.large, 200 GB | ~$200 |
| Prometheus/Grafana | 1 × (1 CPU, 2 GB) | Inclus dans nodes |
| **Total** | | **~$350/mois** |

### Avantages / Inconvénients

| ✅ Avantages | ❌ Inconvénients |
|-------------|-----------------|
| Un seul outil à maîtriser | Phoenix utilise Elastic License 2.0, pas MIT/Apache |
| Déploiement très simple | Drift detection ML tabulaire moins mature qu'Evidently |
| Phoenix fournit des insights ML avec zero-config pour le drift, performance et data quality | Moins de métriques statistiques pour données tabulaires |
| Excellent pour GenAI | Communauté plus petite qu'Evidently |

---

## Scénario 2 — Spécialisé : Evidently + Langfuse + Prometheus/Grafana

### Principe

Combiner deux outils open-source spécialisés : **Evidently** (Apache 2.0) excelle sur le ML tabulaire/NLP classique avec 100+ métriques, **Langfuse** (MIT) est le leader open-source pour le GenAI. Langfuse ne dépend que de composants open source et peut être déployé localement, sur infrastructure cloud ou on-premises.

### Architecture complète

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     SCÉNARIO 2 — ARCHITECTURE EVIDENTLY + LANGFUSE              │
│                        (Spécialisé : 2 outils ML, couverture maximale)          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                           KUBERNETES CLUSTER                              │ │
│  │                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    NAMESPACE: ml-applications                       │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │          MODÈLES TABULAIRES + NLP CLASSIQUE                 │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  ┌─────────────────┐  ┌─────────────────┐                   │   │ │ │
│  │  │  │  │ Classification  │  │ NLP Sentiment/  │                   │   │ │ │
│  │  │  │  │ Regression      │  │ NER/Topic       │                   │   │ │ │
│  │  │  │  │ Models          │  │ Models          │                   │   │ │ │
│  │  │  │  │                 │  │                 │                   │   │ │ │
│  │  │  │  │ FastAPI/Flask   │  │ FastAPI/Flask   │                   │   │ │ │
│  │  │  │  └────────┬────────┘  └────────┬────────┘                   │   │ │ │
│  │  │  │           │                    │                            │   │ │ │
│  │  │  │           └────────┬───────────┘                            │   │ │ │
│  │  │  │                    ▼                                        │   │ │ │
│  │  │  │           Inference logs → MinIO (S3)                       │   │ │ │
│  │  │  │           (features, predictions, timestamps)               │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │          APPLICATIONS GENAI (LLM/RAG/AGENTS)                │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  ┌─────────────────┐  ┌─────────────────┐                   │   │ │ │
│  │  │  │  │ RAG Chatbot     │  │ AI Agents       │                   │   │ │ │
│  │  │  │  │ (LangChain)     │  │ (LlamaIndex)    │                   │   │ │ │
│  │  │  │  │                 │  │                 │                   │   │ │ │
│  │  │  │  └────────┬────────┘  └────────┬────────┘                   │   │ │ │
│  │  │  │           │                    │                            │   │ │ │
│  │  │  │           └────────┬───────────┘                            │   │ │ │
│  │  │  │                    ▼                                        │   │ │ │
│  │  │  │           Langfuse SDK @observe()                           │   │ │ │
│  │  │  │           (streaming traces via HTTPS)                      │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    NAMESPACE: batch-jobs                            │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │                AIRFLOW / PREFECT                            │   │ │ │
│  │  │  │                (Deployment: 1 scheduler + 2 workers)        │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  DAGs:                                                      │   │ │ │
│  │  │  │  ├── evidently_drift_daily        (06:00 UTC)              │   │ │ │
│  │  │  │  ├── evidently_performance_daily  (07:00 UTC)              │   │ │ │
│  │  │  │  ├── evidently_data_quality_hourly                         │   │ │ │
│  │  │  │  └── ground_truth_sync            (when available)         │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  Workflow type:                                             │   │ │ │
│  │  │  │  1. Read inference logs from MinIO                          │   │ │ │
│  │  │  │  2. Run Evidently Report()                                  │   │ │ │
│  │  │  │  3. Store results in PostgreSQL                             │   │ │ │
│  │  │  │  4. Push metrics to Prometheus (pushgateway)                │   │ │ │
│  │  │  │  5. Archive HTML reports to MinIO                           │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    NAMESPACE: monitoring                            │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────┬─────────────────────────────┐ │ │ │
│  │  │  │                                 │                             │ │ │ │
│  │  │  │      EVIDENTLY UI SERVICE       │       LANGFUSE STACK        │ │ │ │
│  │  │  │      (ML Tabulaire + NLP)       │       (GenAI/LLM)           │ │ │ │
│  │  │  │                                 │                             │ │ │ │
│  │  │  │  ┌───────────────────────────┐  │  ┌───────────────────────┐ │ │ │ │
│  │  │  │  │  evidently-ui             │  │  │  langfuse-web         │ │ │ │ │
│  │  │  │  │  (Deployment: 1 replica)  │  │  │  (Deployment: 2 rep.) │ │ │ │ │
│  │  │  │  │                           │  │  │                       │ │ │ │ │
│  │  │  │  │  Image: evidently/ui      │  │  │  Image: langfuse:3    │ │ │ │ │
│  │  │  │  │  Port: 8000               │  │  │  Port: 3000           │ │ │ │ │
│  │  │  │  │  CPU: 1 / RAM: 2GB        │  │  │  CPU: 2 / RAM: 4GB    │ │ │ │ │
│  │  │  │  └───────────────────────────┘  │  └───────────────────────┘ │ │ │ │
│  │  │  │              │                  │              │             │ │ │ │
│  │  │  │              ▼                  │              │             │ │ │ │
│  │  │  │  ┌───────────────────────────┐  │  ┌───────────────────────┐ │ │ │ │
│  │  │  │  │  WORKSPACE STORAGE        │  │  │  langfuse-worker      │ │ │ │ │
│  │  │  │  │                           │  │  │  (Deployment: 2 rep.) │ │ │ │ │
│  │  │  │  │  Option A: Local PVC      │  │  │                       │ │ │ │ │
│  │  │  │  │  Option B: MinIO (S3)     │  │  │  CPU: 2 / RAM: 4GB    │ │ │ │ │
│  │  │  │  │                           │  │  │                       │ │ │ │ │
│  │  │  │  │  Contenu:                 │  │  │  Processes:           │ │ │ │ │
│  │  │  │  │  • JSON snapshots         │  │  │  • Event ingestion    │ │ │ │ │
│  │  │  │  │  • HTML reports           │  │  │  • Eval computation   │ │ │ │ │
│  │  │  │  │  • Project configs        │  │  │  • Background jobs    │ │ │ │ │
│  │  │  │  └───────────────────────────┘  │  └───────────────────────┘ │ │ │ │
│  │  │  │                                 │                             │ │ │ │
│  │  │  └─────────────────────────────────┴─────────────────────────────┘ │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │                    DATA LAYER                               │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────┐ │   │ │ │
│  │  │  │  │ PostgreSQL  │ │ ClickHouse  │ │   Redis     │ │ MinIO │ │   │ │ │
│  │  │  │  │             │ │             │ │   /Valkey   │ │  (S3) │ │   │ │ │
│  │  │  │  │ Langfuse    │ │ Langfuse    │ │             │ │       │ │   │ │ │
│  │  │  │  │ metadata    │ │ traces OLAP │ │ Cache +     │ │ Blobs │ │   │ │ │
│  │  │  │  │ + Evidently │ │             │ │ Queue       │ │       │ │   │ │ │
│  │  │  │  │             │ │             │ │             │ │       │ │   │ │ │
│  │  │  │  │ 2CPU/4GB    │ │ 4CPU/8GB    │ │ 1CPU/2GB    │ │ 500GB │ │   │ │ │
│  │  │  │  │ 100GB SSD   │ │ 200GB SSD   │ │ 10GB        │ │       │ │   │ │ │
│  │  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └───────┘ │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │              OBSERVABILITY INFRA                            │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  ┌─────────────────────┐  ┌─────────────────────────────┐  │   │ │ │
│  │  │  │  │     Prometheus      │  │         Grafana              │  │   │ │ │
│  │  │  │  │                     │  │                              │  │   │ │ │
│  │  │  │  │  Scrape targets:    │  │  Dashboards:                 │  │   │ │ │
│  │  │  │  │  • Evidently /metrics│  │  • ML Drift (Evidently)     │  │   │ │ │
│  │  │  │  │  • Langfuse metrics │  │  • LLM Health (Langfuse)     │  │   │ │ │
│  │  │  │  │  • Pushgateway      │  │  • Infrastructure            │  │   │ │ │
│  │  │  │  │  • Node exporter    │  │  • Cost tracking             │  │   │ │ │
│  │  │  │  │                     │  │                              │  │   │ │ │
│  │  │  │  │  1CPU/2GB, 50GB     │  │  Alerting:                   │  │   │ │ │
│  │  │  │  │  Retention: 30d     │  │  → Slack, PagerDuty, Email   │  │   │ │ │
│  │  │  │  └─────────────────────┘  └─────────────────────────────┘  │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Composants de stockage détaillés

Langfuse consiste en deux containers applicatifs et des composants de stockage : PostgreSQL pour les workloads transactionnels, ClickHouse comme base OLAP haute-performance pour stocker traces, observations et scores, Redis/Valkey comme cache in-memory.

| Composant | Rôle | Specs recommandées | Volume estimé |
|-----------|------|-------------------|---------------|
| **PostgreSQL** | Metadata Langfuse + Evidently results | 2 vCPU, 4 GB RAM, 100 GB SSD | ~1-5 GB/mois |
| **ClickHouse** | Traces Langfuse (OLAP) | 4 vCPU, 8 GB RAM, 200 GB SSD | ~10-50 GB/mois |
| **Redis/Valkey** | Cache + Queue Langfuse | 1 vCPU, 2 GB RAM | ~1 GB |
| **MinIO (S3)** | Blobs, inference logs, reports | N/A | ~50-200 GB/an |

### Flux de données

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FLUX DE DONNÉES SCÉNARIO 2                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗ │
│  ║  FLUX TABULAIRE + NLP CLASSIQUE (BATCH via Evidently)                     ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════╝ │
│                                                                                 │
│   ML API                                                                        │
│   (FastAPI)   ───────────► MinIO Bucket: inference-logs/                        │
│       │                    ├── model_a/2024-01-15/                              │
│       │                    │   ├── features.parquet                             │
│       │                    │   ├── predictions.parquet                          │
│       │                    │   └── metadata.json                                │
│       │                    └── model_b/2024-01-15/...                           │
│       │                                │                                        │
│       │                                │ (Airflow trigger: daily 06:00)         │
│       │                                ▼                                        │
│       │                    ┌───────────────────────────────┐                   │
│       │                    │  EVIDENTLY BATCH JOB          │                   │
│       │                    │                               │                   │
│       │                    │  from evidently import Report │                   │
│       │                    │  from evidently.presets import│                   │
│       │                    │      DataDriftPreset,         │                   │
│       │                    │      DataQualityPreset,       │                   │
│       │                    │      ClassificationPreset     │                   │
│       │                    │                               │                   │
│       │                    │  report = Report([            │                   │
│       │                    │      DataDriftPreset(),       │                   │
│       │                    │      DataQualityPreset(),     │                   │
│       │                    │      ClassificationPreset()   │                   │
│       │                    │  ])                           │                   │
│       │                    │  report.run(current, ref)     │                   │
│       │                    └───────────────┬───────────────┘                   │
│       │                                    │                                    │
│       │                    ┌───────────────┼───────────────┐                   │
│       │                    ▼               ▼               ▼                   │
│       │              PostgreSQL       MinIO            Prometheus              │
│       │              (metrics DB)     (HTML reports)   (pushgateway)           │
│       │                    │                               │                   │
│       │                    └───────────────┬───────────────┘                   │
│       │                                    ▼                                    │
│       │                            EVIDENTLY UI                                 │
│       │                            + GRAFANA                                    │
│       │                                                                         │
│  ╔═══════════════════════════════════════════════════════════════════════════╗ │
│  ║  FLUX GENAI/LLM (STREAMING via Langfuse)                                  ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════╝ │
│                                                                                 │
│   LLM App                                                                       │
│   (LangChain)  ───► @observe() ───► Langfuse Web (HTTPS :3000)                 │
│       │                                    │                                    │
│       │                                    ▼                                    │
│       │                            ┌──────────────┐                            │
│       │                            │  S3 (MinIO)  │ ◄── Raw events stored first│
│       │                            └──────┬───────┘                            │
│       │                                   │                                     │
│       │                                   ▼                                     │
│       │                            ┌──────────────┐                            │
│       │                            │    Redis     │ ◄── Queue for processing   │
│       │                            └──────┬───────┘                            │
│       │                                   │                                     │
│       │                                   ▼                                     │
│       │                            ┌──────────────┐                            │
│       │                            │   Worker     │                            │
│       │                            │  (async)     │                            │
│       │                            └──────┬───────┘                            │
│       │                                   │                                     │
│       │                    ┌──────────────┼──────────────┐                     │
│       │                    ▼              ▼              ▼                     │
│       │              PostgreSQL      ClickHouse     Langfuse UI                │
│       │              (metadata)      (traces OLAP)  (dashboards)               │
│       │                                                                         │
│       ▼                                                                         │
│   Response                                                                      │
│   to user                                                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Couverture fonctionnelle

| Besoin | Tabulaire | NLP Classique | GenAI/LLM | Outil |
|--------|-----------|---------------|-----------|-------|
| Data drift | ✅ 20+ tests statistiques | ✅ Text descriptors | ⚠️ Custom | Evidently |
| Concept drift | ✅ Prediction drift | ✅ Embedding drift | ⚠️ Custom | Evidently |
| Data quality | ✅ Excellent (100+ metrics) | ✅ Excellent | ⚠️ Partiel | Evidently |
| Performance ML | ✅ Classification/Régression | ✅ Complet | N/A | Evidently |
| LLM Tracing | N/A | N/A | ✅ Excellent | Langfuse |
| LLM Evaluations | N/A | N/A | ✅ LLM-as-Judge | Langfuse |
| Prompt versioning | N/A | N/A | ✅ Natif | Langfuse |
| Cost tracking | ❌ | ❌ | ✅ Token tracking | Langfuse |
| User feedback | ⚠️ Custom | ⚠️ Custom | ✅ Natif | Langfuse |
| Alerting | ✅ | ✅ | ✅ | Grafana |

### Coûts infrastructure

| Composant | Specs | Coût mensuel (AWS) |
|-----------|-------|-------------------|
| EKS Cluster | 5 nodes t3.large | ~$350 |
| Langfuse (web + worker) | 4 × (2 CPU, 4 GB) | Inclus |
| Evidently UI | 1 × (1 CPU, 2 GB) | Inclus |
| Airflow | 1 scheduler + 2 workers | Inclus |
| RDS PostgreSQL | db.r6g.large | ~$200 |
| ClickHouse (self-hosted) | 4 vCPU, 8 GB | Inclus |
| Redis | cache.t3.small | ~$30 |
| MinIO / S3 | 500 GB | ~$15 |
| **Total** | | **~$595/mois** |

### Avantages / Inconvénients

| ✅ Avantages | ❌ Inconvénients |
|-------------|-----------------|
| Evidently offre 100+ évaluations built-in incluant drift, data quality, metrics ML et LLM | 2 UI séparées à consulter |
| Licences 100% permissives (Apache 2.0 + MIT) | Complexité de déploiement plus élevée |
| Plus de 1000 déploiements self-hosted Langfuse tournent en production avec ClickHouse, certains ingérant des milliards de lignes | Plus de composants à maintenir |
| Couverture fonctionnelle maximale | Coût infrastructure plus élevé |
| Communautés très actives | Nécessite expertise DevOps |

---

## Scénario 3 — Équilibré : Phoenix + Evidently + Prometheus/Grafana

### Principe

Combiner **Phoenix** pour le GenAI (excellent tracing) et **Evidently** pour le ML tabulaire/NLP (meilleur drift detection). Cette combinaison offre le meilleur des deux mondes tout en restant plus simple que le Scénario 2 (pas de ClickHouse).

### Architecture complète

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     SCÉNARIO 3 — ARCHITECTURE PHOENIX + EVIDENTLY               │
│                           (Équilibre optimal : 2 outils ML)                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                           KUBERNETES CLUSTER                              │ │
│  │                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    NAMESPACE: ml-applications                       │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌──────────────────────────────────────────────────────────────┐  │ │ │
│  │  │  │           MODÈLES ML (Tabulaire + NLP Classique)             │  │ │ │
│  │  │  │                                                              │  │ │ │
│  │  │  │  ┌─────────────────┐  ┌─────────────────┐                    │  │ │ │
│  │  │  │  │ Regression/     │  │ NLP Models      │                    │  │ │ │
│  │  │  │  │ Classification  │  │ (Sentiment,     │                    │  │ │ │
│  │  │  │  │ Models          │  │ NER, Topic)     │                    │  │ │ │
│  │  │  │  │                 │  │                 │                    │  │ │ │
│  │  │  │  │ → Log to MinIO  │  │ → Log to MinIO  │                    │  │ │ │
│  │  │  │  │   (batch)       │  │   (batch)       │                    │  │ │ │
│  │  │  │  └─────────────────┘  └─────────────────┘                    │  │ │ │
│  │  │  │                                                              │  │ │ │
│  │  │  │  Instrumentation: Custom logging → Parquet → MinIO           │  │ │ │
│  │  │  │  Processing: Airflow DAG → Evidently Reports                 │  │ │ │
│  │  │  └──────────────────────────────────────────────────────────────┘  │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌──────────────────────────────────────────────────────────────┐  │ │ │
│  │  │  │           APPLICATIONS GENAI (LLM/RAG/Agents)                │  │ │ │
│  │  │  │                                                              │  │ │ │
│  │  │  │  ┌─────────────────┐  ┌─────────────────┐                    │  │ │ │
│  │  │  │  │ RAG Pipeline    │  │ AI Agents       │                    │  │ │ │
│  │  │  │  │                 │  │                 │                    │  │ │ │
│  │  │  │  │ → OpenInference │  │ → OpenInference │                    │  │ │ │
│  │  │  │  │   auto-trace    │  │   auto-trace    │                    │  │ │ │
│  │  │  │  └─────────────────┘  └─────────────────┘                    │  │ │ │
│  │  │  │                                                              │  │ │ │
│  │  │  │  Instrumentation: OpenTelemetry → Phoenix (streaming)        │  │ │ │
│  │  │  └──────────────────────────────────────────────────────────────┘  │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    NAMESPACE: monitoring                            │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────┬───────────────────────────────┐   │ │ │
│  │  │  │     EVIDENTLY STACK         │        PHOENIX STACK          │   │ │ │
│  │  │  │     (ML Tabulaire + NLP)    │        (GenAI/LLM)            │   │ │ │
│  │  │  │                             │                               │   │ │ │
│  │  │  │  ┌───────────────────────┐  │  ┌───────────────────────┐   │   │ │ │
│  │  │  │  │  Evidently UI         │  │  │  Phoenix Server       │   │   │ │ │
│  │  │  │  │                       │  │  │                       │   │   │ │ │
│  │  │  │  │  evidently ui         │  │  │  arizephoenix/phoenix │   │   │ │ │
│  │  │  │  │  --workspace s3://... │  │  │                       │   │   │ │ │
│  │  │  │  │                       │  │  │  Ports:               │   │   │ │ │
│  │  │  │  │  Port: 8000           │  │  │  • 6006: UI + API     │   │   │ │ │
│  │  │  │  │  CPU: 1 / RAM: 2GB    │  │  │  • 4317: OTLP gRPC    │   │   │ │ │
│  │  │  │  │                       │  │  │  • 9090: Prometheus   │   │   │ │ │
│  │  │  │  │  Features:            │  │  │                       │   │   │ │ │
│  │  │  │  │  • Data drift reports │  │  │  CPU: 2 / RAM: 4GB    │   │   │ │ │
│  │  │  │  │  • Data quality       │  │  │  (2 replicas)         │   │   │ │ │
│  │  │  │  │  • Model performance  │  │  │                       │   │ │   │ │ │
│  │  │  │  │  • Test suites        │  │  │  Features:            │   │   │ │ │
│  │  │  │  │                       │  │  │  • LLM tracing        │   │   │ │ │
│  │  │  │  └───────────────────────┘  │  │  • Evaluations        │   │   │ │ │
│  │  │  │                             │  │  • Prompt playground  │   │   │ │ │
│  │  │  │  ┌───────────────────────┐  │  │  • Dataset mgmt       │   │   │ │ │
│  │  │  │  │  Airflow/Prefect      │  │  └───────────────────────┘   │   │ │ │
│  │  │  │  │                       │  │                               │   │ │ │
│  │  │  │  │  Batch jobs pour      │  │                               │   │ │ │
│  │  │  │  │  Evidently reports    │  │                               │   │ │ │
│  │  │  │  │                       │  │                               │   │ │ │
│  │  │  │  │  CPU: 2 / RAM: 4GB    │  │                               │   │ │ │
│  │  │  │  └───────────────────────┘  │                               │   │ │ │
│  │  │  └─────────────────────────────┴───────────────────────────────┘   │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │                    DATA LAYER (Simplifié)                   │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  ┌─────────────────────────┐  ┌─────────────────────────┐  │   │ │ │
│  │  │  │  │      PostgreSQL         │  │        MinIO (S3)       │  │   │ │ │
│  │  │  │  │                         │  │                         │  │   │ │ │
│  │  │  │  │  • Phoenix traces       │  │  • Inference logs       │  │   │ │ │
│  │  │  │  │  • Phoenix evaluations  │  │  • Evidently workspace  │  │   │ │ │
│  │  │  │  │  • Airflow metadata     │  │  • HTML reports archive │  │   │ │ │
│  │  │  │  │                         │  │  • Backups              │  │   │ │ │
│  │  │  │  │  2 CPU / 4 GB RAM       │  │                         │  │   │ │ │
│  │  │  │  │  100 GB SSD             │  │  500 GB                 │  │   │ │ │
│  │  │  │  └─────────────────────────┘  └─────────────────────────┘  │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  ⚠️  Pas de ClickHouse = architecture simplifiée            │   │ │ │
│  │  │  │      mais moins scalable pour très hauts volumes LLM        │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  │                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │              OBSERVABILITY (Unifié)                         │   │ │ │
│  │  │  │                                                             │   │ │ │
│  │  │  │  ┌─────────────────────┐  ┌─────────────────────────────┐  │   │ │ │
│  │  │  │  │     Prometheus      │  │         Grafana              │  │   │ │ │
│  │  │  │  │                     │  │                              │  │   │ │ │
│  │  │  │  │  Scrape:            │  │  ┌─────────────────────────┐│  │   │ │ │
│  │  │  │  │  • Phoenix :9090    │  │  │  Dashboard unifié       ││  │   │ │ │
│  │  │  │  │  • Pushgateway      │  │  │                         ││  │   │ │ │
│  │  │  │  │    (Evidently)      │  │  │  Panels:                ││  │   │ │ │
│  │  │  │  │  • Node exporter    │  │  │  • ML Drift (Evidently) ││  │   │ │ │
│  │  │  │  │                     │  │  │  • Data Quality         ││  │   │ │ │
│  │  │  │  │                     │  │  │  • LLM Traces (Phoenix) ││  │   │ │ │
│  │  │  │  │                     │  │  │  • LLM Costs            ││  │   │ │ │
│  │  │  │  │                     │  │  │  • Infrastructure       ││  │   │ │ │
│  │  │  │  │                     │  │  └─────────────────────────┘│  │   │ │ │
│  │  │  │  └─────────────────────┘  └─────────────────────────────┘  │   │ │ │
│  │  │  └─────────────────────────────────────────────────────────────┘   │ │ │
│  │  └─────────────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Répartition des responsabilités

| Domaine | Outil principal | Mode | Justification |
|---------|----------------|------|---------------|
| **ML Tabulaire** | Evidently | Batch | Evidently offre 100+ métriques pour ML et LLM, modulaire avec Reports et Test Suites pour expérimentations ou service de monitoring complet |
| **NLP Classique** | Evidently | Batch | Meilleur drift detection avec descriptors texte |
| **GenAI/LLM** | Phoenix | Streaming | Phoenix offre visibilité sur chaque étape des applications LLM via tracing distribué avec support natif pour LlamaIndex, LangChain, DSPy et providers comme OpenAI, Bedrock, Anthropic |
| **Infrastructure** | Prometheus/Grafana | Scraping | Standard de l'industrie |

### Coûts infrastructure

| Composant | Specs | Coût mensuel (AWS) |
|-----------|-------|-------------------|
| EKS Cluster | 4 nodes t3.large | ~$280 |
| Phoenix (2 replicas) | 2 × (2 CPU, 4 GB) | Inclus |
| Evidently UI | 1 × (1 CPU, 2 GB) | Inclus |
| Airflow | 1 scheduler + 1 worker | Inclus |
| RDS PostgreSQL | db.r6g.medium | ~$130 |
| MinIO / S3 | 500 GB | ~$15 |
| **Total** | | **~$425/mois** |

### Couverture fonctionnelle

| Besoin | Tabulaire | NLP Classique | GenAI/LLM |
|--------|-----------|---------------|-----------|
| Data drift | ✅ Excellent (Evidently) | ✅ Excellent (Evidently) | ✅ Embedding drift (Phoenix) |
| Data quality | ✅ Excellent (Evidently) | ✅ Excellent (Evidently) | ⚠️ Partiel (Phoenix) |
| Performance | ✅ Excellent (Evidently) | ✅ Excellent (Evidently) | ✅ LLM evals (Phoenix) |
| Tracing | ❌ | ❌ | ✅ Excellent (Phoenix) |
| Cost tracking | ❌ | ❌ | ✅ (Phoenix) |
| Test suites CI/CD | ✅ (Evidently) | ✅ (Evidently) | ⚠️ Partiel (Phoenix) |

### Avantages / Inconvénients

| ✅ Avantages | ❌ Inconvénients |
|-------------|-----------------|
| Meilleur drift detection ML (Evidently) | 2 UI à consulter |
| Excellent tracing GenAI (Phoenix) | Licence Phoenix = ELv2 (pas Apache) |
| Architecture simplifiée (pas de ClickHouse) | Moins scalable pour très hauts volumes LLM |
| Coût intermédiaire | 2 outils à maintenir |
| Grafana unifie la vue d'ensemble | |

---

## Tableau de synthèse final

| Critère | Scénario 1 (Phoenix) | Scénario 2 (Evidently+Langfuse) | Scénario 3 (Phoenix+Evidently) |
|---------|---------------------|--------------------------------|-------------------------------|
| **Outils ML** | 1 | 2 | 2 |
| **Licence** | Elastic License 2.0 | Apache 2.0 + MIT | ELv2 + Apache 2.0 |
| **Self-hosted** | ✅ | ✅ | ✅ |
| **Bases de données** | PostgreSQL | PostgreSQL + ClickHouse + Redis | PostgreSQL |
| **Object Storage** | Optionnel | Requis (S3/MinIO) | Requis (S3/MinIO) |
| **Batch orchestrator** | Optionnel | Requis (Airflow/Prefect) | Requis (Airflow/Prefect) |
| **Drift ML tabulaire** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **LLM tracing** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Complexité déploiement** | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Coût infra estimé** | ~$350/mois | ~$595/mois | ~$425/mois |
| **Équipe cible** | Petite équipe, GenAI-first | Grande équipe, couverture max | Équipe moyenne, équilibre |

---

## Recommandation par contexte

| Votre contexte | Scénario recommandé | Raison |
|----------------|---------------------|--------|
| Startup/PME, principalement GenAI | **Scénario 1** | Simplicité maximale, un seul outil |
| Enterprise, conformité stricte, données sensibles | **Scénario 2** | Licences 100% permissives, ClickHouse pour scale |
| Équipe ML mature, mix use cases équilibré | **Scénario 3** | Meilleur compromis fonctionnalités/complexité |
| Budget limité, besoin de démarrer vite | **Scénario 1** | Coût et effort minimum |
| Hauts volumes (>100k traces/jour) | **Scénario 2** | ClickHouse permet d'ingérer des milliards de lignes en production |

Souhaitez-vous que je développe les fichiers de déploiement Helm/Docker-compose complets pour l'un de ces scénarios, ou que je prépare un plan de migration depuis votre stack actuel ?

---
