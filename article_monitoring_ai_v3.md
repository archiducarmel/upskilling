# Critères d'évaluation d'une plateforme de monitoring IA

## Observabilité

La plateforme doit capturer automatiquement les entrées et sorties de chaque appel à un modèle, qu'il soit ML classique ou génératif. Elle décompose les pipelines complexes en spans distincts pour isoler les goulots d'étranglement. Les métriques de latence, throughput et coût sont calculées et associées à des métadonnées contextuelles.

## Évaluation – Annotation

Les utilisateurs doivent pouvoir annoter les traces directement depuis l'interface pour constituer un ground truth. Le travail collaboratif entre plusieurs annotateurs est supporté avec gestion des conflits. Les traces annotées sont transformables en datasets exploitables pour le fine-tuning ou les tests automatisés.

## Évaluation – ML Tabulaire

La plateforme détecte les changements de distribution des features d'entrée via des tests statistiques. Elle surveille la qualité des données entrantes et calcule les métriques de performance réelle lorsque les labels deviennent disponibles. Le concept drift est identifié même lorsque les distributions individuelles restent stables.

## Évaluation – NLP Prédictif

Le monitoring couvre les caractéristiques spécifiques aux données textuelles : évolution de la longueur, diversité lexicale et dérive des représentations vectorielles. L'augmentation de tokens inconnus du vocabulaire signale un changement de domaine. Les métriques classiques sont calculées par classe dès réception des labels.

## Évaluation – NLP Génératif

Un LLM évalue automatiquement la qualité des réponses générées selon des critères configurables. La plateforme détecte les hallucinations en vérifiant la fidélité aux sources et identifie les contenus toxiques. Le feedback utilisateur est collecté et les prompts sont versionnés pour permettre des comparaisons contrôlées.

## Visualisation et Alerting

Des tableaux de bord personnalisables présentent les métriques par modèle, période ou segment. L'exploration des traces individuelles permet d'investiguer les cas problématiques. Les alertes sont routées automatiquement vers les canaux de l'entreprise lorsque les seuils configurés sont dépassés.

## Protection des données (RGPD)

L'accès aux données est cloisonné par projet et par niveau hiérarchique. La durée de rétention est configurable globalement et par projet selon la sensibilité. Les données personnelles sont détectées automatiquement ou masquées manuellement. Le chiffrement protège les données au repos et en transit.

## Sécurité

Tout service qui ingère des traces doit s'authentifier auprès de la plateforme. Chaque credential est associé à un projet unique pour garantir l'isolation des données dès l'ingestion. La création de clés distinctes par environnement limite l'impact d'une éventuelle compromission.

## Architecture et Intégration

La plateforme supporte des bases de données adaptées aux requêtes analytiques et permet l'export vers un datalake pour l'archivage. L'authentification s'intègre aux fournisseurs d'identité de l'entreprise. L'ingestion fonctionne en temps réel ou en batch. Un SDK facilite l'instrumentation des applications.

## Maturité et Écosystème

La licence doit permettre un usage commercial sans restriction. Une communauté active et des releases fréquentes garantissent la pérennité du projet. La documentation couvre les cas d'usage courants. Une offre de support entreprise et une roadmap publique renforcent la confiance pour un déploiement en production.
