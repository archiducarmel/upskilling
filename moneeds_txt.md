# Analyse des Besoins de Monitoring ML : Décryptage du Dashboard

## Vue d'ensemble

Ce dashboard offre une vision complète des besoins de monitoring pour les 24 use cases ML de la plateforme. Les **5 KPIs en haut** donnent immédiatement le pouls : 75% des UC nécessitent un input monitoring, 79% un output monitoring, et deux tiers demandent des capacités d'annotation. Les barres de progression permettent de visualiser d'un coup d'œil le taux de couverture.

## Input vs Output Monitoring

Les deux sections principales comparent les besoins d'entrée et de sortie. Côté **Input**, on observe une dominance du type "Texte" (12 UC) sur "Tableau numérique" (6 UC), ce qui reflète la forte présence de modèles NLP dans le portefeuille. La temporalité est unanime : 100% périodique, indiquant que le monitoring en temps réel des entrées n'est pas prioritaire.

Côté **Output**, la tendance s'inverse : les sorties "Tableau numérique" (14 UC) dominent largement les sorties "Texte" (5 UC). C'est logique : même les modèles NLP produisent souvent des classifications ou scores numériques. Point crucial : **5 UC requièrent un monitoring temps réel** des outputs, notamment les modèles génératifs (CR-Auto Summary, SmartInbox Outlook, Réclamation).

## Word Clouds : Les Métriques Clés

Les nuages de mots révèlent les priorités métier. Pour l'**Input**, "longueur" et "message" dominent (11 occurrences), suivis de "distribution" et des tests statistiques (PSI, KS) pour la détection de drift. C'est le vocabulaire classique du data quality monitoring.

Pour l'**Output**, "distribution" arrive en tête (14 occurrences), accompagné des statistiques descriptives classiques. L'émergence de "LLM Juge", "sémantique" et "token" témoigne de l'adoption croissante des modèles génératifs et de leurs métriques spécifiques.

## Top Métriques : Le Ranking

Les barres horizontales classent les métriques par fréquence de demande. Côté input, la **longueur de message** et l'**analyse de distribution** sont quasi-universelles. Côté output, la **distribution des prédictions** est incontournable, suivie des stats descriptives. Ces rankings guident directement les priorités de développement de la plateforme.

## Besoins par Type de Modèle

Cette grille est stratégique. Les **NLP Classification** (8 UC) et **NLP Génératif** (3 UC) affichent une couverture quasi-totale de leurs besoins. À l'inverse, les **Speech-to-Text** (2 UC) n'ont aucun besoin formalisé — un chantier à ouvrir. Les modèles tabulaires montrent une maturité intermédiaire avec quelques gaps en annotation.

## Annotation & Gestion des Datasets

Les 4 donuts finaux révèlent une forte demande d'outillage collaboratif. **16 UC sur 24** demandent des capacités d'annotation des traces, de collaboration entre équipes, et de création de datasets à partir des logs de production. C'est un signal fort : la plateforme doit intégrer un workflow complet de data labeling.

Le **User Feedback** concerne 14 UC, principalement les modèles en interaction directe avec les utilisateurs finaux (chatbots, assistants, génératifs).

---

**En résumé**, ce dashboard met en lumière trois priorités : (1) industrialiser le monitoring de distribution pour tous les UC, (2) développer des métriques spécifiques LLM pour les modèles génératifs, et (3) construire un pipeline d'annotation intégré à la plateforme.
