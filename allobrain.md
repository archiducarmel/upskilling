### 1. Architecture & déploiement

1. **Modèle de déploiement :**
   *“Décrivez précisément vos options de déploiement (SaaS multi-tenant, single-tenant, VPC dédié, on-prem, air-gapped). Laquelle est réellement supportée en production chez un client bancaire de taille Tier-1, et quels sont les prérequis techniques côté client ?”*

2. **Séparation logique & isolation :**
   *“Comment garantissez-vous l’isolation forte des données entre clients dans votre architecture (namespaces, VPC, KMS, tenants logiques) et quels mécanismes empêchent la fuite inter-client (erreur de config, bug, compromission) ?”*

---

### 2. Données, confidentialité & conformité banque

3. **Classification & PII / PCI :**
   *“Comment votre solution gère-t-elle des conversations contenant des données hautement sensibles (PII, PCI, secrets) : masquage, tokenisation, redaction à la volée ? Pouvez-vous démontrer que ces données ne sont jamais envoyées vers des LLM tiers ou des services non approuvés par la banque ?”*

4. **Résidence & gouvernance des données :**
   *“Où sont stockées physiquement les données (logs, embeddings, modèles fine-tunés) ? Pouvez-vous garantir une résidence exclusive dans l’UE ou dans notre propre infrastructure, et fournir un modèle de gouvernance des données compatible avec nos politiques internes (data ownership, retention, droit à l’oubli, purge complète) ?”*

5. **Journalisation & audit :**
   *“Quels types de logs conservez-vous (prompts, outputs, métadonnées, user IDs) et pendant combien de temps ? Disposez-vous d’un audit trail complet, horodaté, exportable, capable de répondre aux exigences d’audit interne / régulateur sur plusieurs années ?”*

---

### 3. Stack IA / LLM & évolutivité

6. **Choix des modèles & portabilité :**
   *“Sur quels types de modèles vous appuyez-vous (open source, propriétaires, mix) pour la transcription, le NLP et la génération ? Que se passe-t-il si, pour des raisons de conformité, nous imposons un modèle interne (LLM maison) ou un autre fournisseur de LLM : votre plateforme sait-elle ‘swapper’ de modèle sans refonte complète ?”*

7. **Fine-tuning & contamination des modèles :**
   *“Quand vous adaptez vos modèles à notre vocabulaire métier, comment garantissez-vous que nos données ne contaminent pas un modèle mutualisé ? Travaillez-vous exclusivement avec des modèles fine-tunés dédiés par client, et comment prouvez-vous l’absence de fuite cross-client dans les weights ou l’espace d’embeddings ?”*

8. **Versioning & roll-back des modèles :**
   *“Comment gérez-vous le versioning des modèles (model registry, promotion, canary, A/B testing) et le roll-back contrôlé ? Pouvez-vous nous montrer un processus concret de ‘rollback’ après détection d’un incident en production (drift, bug, dérive comportementale) ?”*

---

### 4. Performance, scalabilité & résilience

9. **Scalabilité & SLO :**
   *“Quelles sont vos garanties de performance (latence P95/P99, throughput) pour des volumes de type banque globale (plusieurs millions de conversations/jour) ? Disposez-vous de SLO/SLA chiffrés et de cas réels à cette échelle ?”*

10. **Résilience, DR & RPO/RTO :**
    *“Décrivez votre architecture de haute disponibilité (zones, régions, redondance) et votre plan de disaster recovery. Quels RPO/RTO garantissez-vous réellement, et comment testez-vous régulièrement vos procédures de bascule ?”*

---

### 5. Intégration SI & observabilité “JP Morgan-like”

11. **Intégration avec notre stack existante :**
    *“Comment votre plateforme s’intègre-t-elle avec un SI bancaire complexe :

* outils de contact center (Genesys/Avaya/etc.),
* CRM interne,
* bus d’événements (Kafka/AMQP),
* annuaires (AD/LDAP),
* outils internes de monitoring (Prometheus, Grafana, Splunk) ?
  Pouvez-vous fournir des connecteurs et schémas d’architecture détaillés pour ce type d’écosystème ?”*

12. **Observabilité & monitoring des modèles :**
    *“Quels métriques exposez-vous nativement pour le monitoring :

* input (distribution, drift, outliers),
* modèle (qualité, stabilité, temps de réponse),
* output (toxicity, hallucinations, conformité),
* feedback utilisateur ?
  Comment ces métriques sont-elles exportables vers notre stack d’observabilité (logs, métriques, traces) ?”*

---

### 6. Sécurité, accès & gouvernance IA

13. **Sécurité applicative & IAM :**
    *“Quel est votre modèle d’authentification / autorisation (RBAC/ABAC), la granularité de vos rôles, et votre intégration possible avec notre IAM (SAML, OIDC, Kerberos, MFA) ? Disposez-vous d’un contrôle d’accès au niveau des projets, des environnements (prod / pré-prod / sandbox) et des types de données ?”*

14. **Sécurité IA & risques spécifiques LLM :**
    *“Comment gérez-vous les risques spécifiques aux LLM (prompt injection, data exfiltration par le modèle, jailbreak, toxicité, biais) ? Avez-vous une politique et des garde-fous techniques (content filters, policy engine, red teaming régulier) documentés et auditables ?”*

---

### 7. Vendor lock-in, réversibilité & échec du partenariat

15. **Réversibilité & plan de sortie :**
    *“En cas de fin de contrat ou de décision stratégique de rapatrier la solution en interne, quels sont :

* les formats d’export de nos données (conversations, embeddings, modèles, métriques),
* la couverture de la documentation technique,
* les dépendances à vos composants propriétaires,
* les délais et coûts de réversibilité ?
  Pouvez-vous détailler un scénario concret de ‘sortie propre’ pour une banque de notre taille ?”*
