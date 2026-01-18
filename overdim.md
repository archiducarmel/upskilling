# Dashboard Dimensionnement : Comprendre les Volumétries

## Vue d'ensemble

Ce dashboard répond à une question cruciale : **quelle capacité prévoir pour la plateforme de monitoring ?** Les 4 KPIs en tête synthétisent l'essentiel. Avec **93K interactions/heure** et **25M interactions/mois**, on mesure immédiatement l'ampleur du système à dimensionner. La distinction entre appels API (32K/h) et data points Batch (16.5M/mois) permet d'anticiper deux architectures très différentes.

## Section Batch : Les Géants du Volume

Le panneau cyan à gauche analyse les **7 use cases Batch**. Le donut montre une concentration extrême : **ML4AML** (42%) et **Scores de FID** (30%) représentent à eux seuls 72% du volume total. C'est un signal d'alerte pour l'infrastructure — ces deux UC dicteront le dimensionnement stockage.

Les **Top 3 cards** détaillent les champions : ML4AML avec 7M de data points mensuels, suivi de Scores de FID (5M) et PitchEasy (4.5M). Les badges "En dév" ou "En prod" permettent d'anticiper : ML4AML n'est pas encore en production, son arrivée doublera la charge actuelle.

Le **bar chart horizontal** complète le tableau avec les 4 UC restants. On y découvre une longue traîne : ILC/PDO (70K), puis les trois UC Advocacy/Vox à seulement 1.5K chacun. Ces petits volumes ne pèsent pas sur l'infra mais restent importants fonctionnellement.

## Section API : La Vélocité en Temps Réel

Le panneau violet à droite traite les **12 use cases API**. Ici, c'est le débit horaire qui compte. Le donut révèle un leader incontesté : **Fraude Virement** capture 56% des appels avec 18K calls/heure. C'est le UC critique — toute latence impactera directement la détection de fraude en temps réel.

Les **Top 3 cards** montrent le podium : Fraude Virement (18K/h), Simplimmo (5K/h), et Fraude Chèque (2.7K/h). Deux UC fraude dans le top 3, confirmant leur criticité business.

Le **bar chart des 12 UC** dévoile la distribution complète. Après le top 3, on trouve CR-Auto Summary (1.6K/h), puis un plateau de 6 UC Guardrails/SAV autour de 650/h chacun. SmartInbox Outlook (467/h) et Réclamations (25/h) ferment la marche.

## Métriques Agrégées : La Vision Consolidée

La section ambrée/verte en bas fusionne Batch et API. Les deux grandes métriques — **93K interactions/heure** et **25.2M interactions/mois** — servent de référence pour le capacity planning. La règle de calcul affichée (270h/mois) assure la transparence méthodologique.

Le **donut de répartition** montre que le Batch domine en volume mensuel (66% vs 34% API), mais cette vision est trompeuse : en termes de charge système temps réel, l'API est bien plus exigeante.

---

**À retenir** : ce dashboard identifie les "éléphants" (ML4AML, Fraude Virement) qui dimensionneront l'infrastructure, tout en gardant une vision exhaustive des 19 UC. Indispensable avant tout sizing technique.

---

# Dashboard Vue d'Ensemble : Cartographier le Portefeuille ML

## Les KPIs : Une Photo Instantanée

Les **6 stat cards** offrent un snapshot immédiat du portefeuille. **24 use cases** au total, répartis entre 9 Batch et 13 API — l'API domine légèrement (54%). Côté maturité, l'équilibre est presque parfait : 10 en production, 13 en développement, et 1 suspendu (PFM). Cette parité prod/dev témoigne d'un pipeline actif.

## Répartition par Pattern : Batch vs API

Le premier donut décompose les patterns d'intégration. L'**API** (13 UC) domine, reflétant la tendance vers des services ML temps réel. Le **Batch** (9 UC) reste significatif pour les traitements massifs. Un UC hybride "Batch + API" (Simplimmo) et un "Intégré" (Guardrails Language) complètent le panorama.

## Répartition par Type de Modèle : La Diversité ML

Ce donut est stratégique pour comprendre les compétences requises. **NLP Classification** domine avec 8 UC — c'est le cœur historique. Les modèles **Tabulaires** (6 UC) couvrent les cas classiques de scoring. L'émergence du **NLP Génératif** (3 UC) et **NLP RAG** (2 UC) marque le virage GenAI. Les **Speech-to-Text** (2 UC) et **Recommandation** (1 UC) complètent l'offre. Les 2 UC "Non défini" (RASA, PFM) appellent une clarification.

## Répartition par Statut : Le Pipeline de Delivery

Le troisième donut visualise la maturité. **10 UC en production** (42%) assurent la valeur actuelle. **13 UC en développement** (54%) alimentent le backlog — un ratio sain indiquant une roadmap chargée. Le seul UC **suspendu** (PFM) mérite investigation.

## Le Tableau : La Référence Exhaustive

La table des 24 UC est le cœur documentaire du dashboard. Chaque ligne combine :
- **Numéro et nom** pour l'identification rapide
- **Badge Pattern** (cyan/violet) pour distinguer Batch/API visuellement
- **Type de modèle** avec icône contextuelle (🤖 NLP, 📊 Tabulaire, 🎤 Speech...)
- **Badge Statut** (vert prod, jaune dév, gris suspendu)
- **Volumétrie** colorée selon l'importance (rose=fort, jaune=moyen, gris=faible ou N/A)

Les 5 UC sans volumétrie (tiret "—") correspondent aux projets early-stage ou aux composants intégrés sans métriques propres.

---

**Usage recommandé** : ce dashboard sert de référentiel partagé entre équipes Data, MLOps et Product. Il répond aux questions "Combien de modèles ?", "Quels types ?", "Où en sont-ils ?" — le point de départ de toute discussion portfolio.
