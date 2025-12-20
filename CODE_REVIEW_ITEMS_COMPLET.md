# 🔴 RAPPORT DE CODE REVIEW DÉTAILLÉ - ASSISTANT VIRTUEL RASA

## Contexte
**Application** : Assistant Virtuel Bancaire basé sur Rasa Pro  
**Environnement cible** : Production (Fab IA)  
**Date de review** : Décembre 2025  
**Verdict** : ⛔ **NON PRÊT POUR LA PRODUCTION**

---

# TABLE DES ITEMS

| # | Catégorie | Sévérité | Fichier(s) |
|---|-----------|----------|------------|
| 1-11 | Sécurité | CRITIQUE | Adapters, YAML, Jenkinsfile |
| 12-16 | Code non finalisé | BLOQUANT | Adapters, junk.py |
| 17-26 | Bugs et erreurs | CRITIQUE | Exceptions, actions |
| 27-32 | Architecture | MAJEUR | Fichiers dupliqués, config |
| 33-53 | Qualité code (Black/Ruff/Mypy) | MAJEUR | Tous |
| 54-56 | Documentation | MINEUR/MAJEUR | README, docstrings |
| 57-58 | Tests | BLOQUANT | Absence totale |
| 59-60 | Configuration | MINEUR | pyproject.toml, requirements |

---

# 🔴 SECTION 1 : FAILLES DE SÉCURITÉ (CRITIQUES)

---

## ITEM #1 : Désactivation SSL `verify=False`

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/guardrails/guardrails_adapter.py` |
| **Ligne** | 122 |

```python
async with httpx.AsyncClient(verify=False, cert=self.cert) as client:
```

**Problème identifié** :

Le paramètre `verify=False` désactive complètement la vérification du certificat SSL lors des appels HTTPS. Le client accepte n'importe quel certificat, même un faux. Dans un contexte bancaire où des données sensibles transitent (identifiants clients, opérations de carte), c'est une faille béante. Un attaquant peut se placer entre l'application et l'API (attaque Man-in-the-Middle), intercepter et modifier les requêtes sans que l'application ne détecte rien.

**Solution proposée** :

Remplacer `verify=False` par le chemin vers le bundle de certificats CA de confiance. Le fichier `BNPPRootCa.crt` est déjà présent dans le projet, il suffit de l'utiliser :

```python
# CORRECT
async with httpx.AsyncClient(verify="./BNPPRootCa.crt", cert=self.cert) as client:
```

---

## ITEM #2 : Désactivation SSL `verify=False`

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/v360/v360_api_adapter.py` |
| **Ligne** | 92 |

```python
async with httpx.AsyncClient(verify=False, cert=self.cert) as client:
```

**Problème identifié** :

Même faille que l'item #1. L'API V360 contient des données clients sensibles (synthèse client, informations personnelles). Sans vérification SSL, toutes ces données peuvent être interceptées en clair par un attaquant.

**Solution proposée** :

Identique à l'item #1 : utiliser le certificat CA pour valider la connexion.

```python
async with httpx.AsyncClient(verify="./BNPPRootCa.crt", cert=self.cert) as client:
```

---

## ITEM #3 : Désactivation SSL `verify=False`

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/opposition/opposition_carte_adapter.py` |
| **Ligne** | 133 |

```python
async with httpx.AsyncClient(verify=False, cert=self.cert) as client:
```

**Problème identifié** :

L'adapter d'opposition carte gère des opérations critiques : vérifier l'éligibilité à l'opposition et effectuer l'opposition elle-même. Sans SSL valide, un attaquant pourrait bloquer une opposition légitime (le client pense avoir bloqué sa carte mais non) ou en déclencher une fausse.

**Solution proposée** :

```python
async with httpx.AsyncClient(verify="./BNPPRootCa.crt", cert=self.cert) as client:
```

---

## ITEM #4 : Désactivation SSL `verify=False`

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/rag/rag_adapter.py` |
| **Ligne** | 146 |

```python
async with httpx.AsyncClient(verify=False, cert=self.cert) as client:
```

**Problème identifié** :

Le RAG (Retrieval Augmented Generation) interroge un LLM avec le contexte de la conversation. Si un attaquant intercepte ces échanges, il a accès à toute la conversation client et peut potentiellement injecter des réponses malveillantes.

**Solution proposée** :

```python
async with httpx.AsyncClient(verify="./BNPPRootCa.crt", cert=self.cert) as client:
```

---

## ITEM #5 : Désactivation SSL `verify=False`

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/routing/routing_d3_adapter.py` |
| **Ligne** | 168 |

```python
async with httpx.AsyncClient(verify=False, cert=self.cert) as client:
```

**Problème identifié** :

L'adapter de routing D3 (moteur de règles ODM) détermine la stratégie de routage. Un attaquant pourrait modifier les décisions de routage et rediriger les clients vers des chemins non prévus.

**Solution proposée** :

```python
async with httpx.AsyncClient(verify="./BNPPRootCa.crt", cert=self.cert) as client:
```

---

## ITEM #6 : Désactivation SSL `verify=False`

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/restitution/restitution_contrat_carte_adapter.py` |
| **Ligne** | 139 |

```python
async with httpx.AsyncClient(verify=False, cert=self.cert) as client:
```

**Problème identifié** :

Cet adapter récupère les informations de contrat carte (liste des cartes, services associés). Sans vérification SSL, les données de carte bancaire sont exposées.

**Solution proposée** :

```python
async with httpx.AsyncClient(verify="./BNPPRootCa.crt", cert=self.cert) as client:
```

---

## ITEM #7 : Désactivation SSL `verify=False` (2 occurrences)

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/infrastructure/guardrails/guardrails_adapter_2.py` |
| **Lignes** | 65, 135 |

```python
response = requests.post(url, headers=headers, data=json.dumps(body), cert=cert, verify=False)
```

**Problème identifié** :

Double occurrence dans ce fichier. En plus du problème SSL, on utilise `requests` de manière synchrone dans un contexte async, ce qui bloque l'event loop. Donc deux problèmes : faille MITM + blocage du serveur.

**Solution proposée** :

Remplacer par httpx async avec SSL activé :

```python
async with httpx.AsyncClient(verify="./BNPPRootCa.crt", cert=cert) as client:
    response = await client.post(url, headers=headers, json=body)
```

---

## ITEM #8 : Token Vault exposé en clair dans le code

| Champ | Détail |
|-------|--------|
| **Script** | `config/local-conf.yaml` |
| **Ligne** | 81 |

```yaml
vault:
  enabled: false
  authentication: TOKEN
  token: hvs.CAESIP_...…………………………………………….
```

**Problème identifié** :

Le token Vault (HashiCorp Vault) est en clair dans un fichier YAML versionné. Toute personne ayant accès au repo Git peut récupérer ce token et accéder aux secrets Vault. Le token donne potentiellement accès à tous les secrets de l'application : clés API, mots de passe, certificats. C'est une faille gravissime.

**Solution proposée** :

1. Supprimer immédiatement le token du fichier YAML et de l'historique Git
2. Révoquer ce token dans Vault (le considérer comme compromis)
3. Générer un nouveau token
4. Utiliser une variable d'environnement

```yaml
vault:
  enabled: false
  authentication: TOKEN
  token: ${VAULT_TOKEN}  # Injecté via variable d'environnement
```

---

## ITEM #9 : Clés privées SSL versionnées dans Git

| Champ | Détail |
|-------|--------|
| **Script** | `ssl_certificats/dev/ap23928-pulsar-dev.key`, `ssl_certificats/dev/ap23928-pulsar-dev_1.key`, `ssl_certificats/vault/ap23928-hprod-dmn-ingestion.key` |
| **Ligne** | N/A (fichiers entiers) |

```
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASC...
-----END PRIVATE KEY-----
```

**Problème identifié** :

Des clés privées SSL sont versionnées dans le repository Git. Ces clés servent à l'authentification mTLS avec les APIs. Si quelqu'un récupère ces clés, il peut se faire passer pour l'application et appeler les APIs en son nom. Ces clés doivent être considérées comme compromises.

**Solution proposée** :

1. Supprimer les fichiers `.key` du repo et de l'historique Git
2. Régénérer les certificats
3. Stocker les clés dans Vault ou K8s Secrets
4. Ajouter `*.key` au `.gitignore`

```bash
# Nettoyage de l'historique Git
bfg --delete-files '*.key' .
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# Ajouter au .gitignore
echo "*.key" >> .gitignore
```

---

## ITEM #10 : Désactivation SSL dans Jenkins

| Champ | Détail |
|-------|--------|
| **Script** | `Jenkinsfile` |
| **Ligne** | 70 |

```groovy
sh(returnStdout: false, script: "git config --global http.sslVerify false")
```

**Problème identifié** :

La CI/CD désactive la vérification SSL pour Git. Le pipeline Jenkins peut se faire piéger par un faux serveur Git et récupérer du code malveillant sans s'en rendre compte. Compromission potentielle de toute la chaîne CI/CD.

**Solution proposée** :

Supprimer cette ligne et configurer correctement les certificats sur le serveur Jenkins :

```groovy
// SUPPRIMER cette ligne
// sh(returnStdout: false, script: "git config --global http.sslVerify false")
```

---

## ITEM #11 : Ressources externes non sécurisées (CDN)

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/channels/custom_channel.py` |
| **Lignes** | 179-183 |

```html
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@latest/swagger-ui.css" />
<script src="https://unpkg.com/swagger-ui-dist@latest/swagger-ui-bundle.js"></script>
```

**Problème identifié** :

L'application charge du JavaScript et du CSS depuis unpkg.com, un CDN tiers. Si ce CDN est compromis ou si quelqu'un fait une attaque DNS, du code malveillant peut être injecté. L'utilisation de `@latest` aggrave le problème car on ne contrôle pas la version.

**Solution proposée** :

Héberger les ressources localement ou utiliser SRI (Subresource Integrity) :

```html
<!-- Avec SRI pour vérifier l'intégrité -->
<script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"
        integrity="sha384-HASH_ICI"
        crossorigin="anonymous"></script>

<!-- OU héberger localement (préférable) -->
<script src="/static/swagger-ui-bundle.js"></script>
```

---

# 🔴 SECTION 2 : CODE NON FINALISÉ (BLOQUANTS)

---

## ITEM #12 : Code mocké actif

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/opposition/opposition_carte_adapter.py` |
| **Lignes** | 271-310 |

```python
# MOCK EN ATTENDANT LA CONNEXION A L'API DEFINITIVE
#result = await self._make_request('GET', url, headers, json_body)

result = {
  "labelProduct": "Carte de Crédit",
  "maskedPan": "1234-5678-9012-3456",
  "expirationDate": "12/25",
  # ... données mockées
}
```

**Problème identifié** :

Le vrai appel API est commenté et remplacé par des données en dur. L'application retourne des fausses informations de carte au lieu d'interroger le vrai système. En production, le client verrait des données fictives, pas ses vraies cartes. L'opposition ne fonctionnerait pas réellement.

**Solution proposée** :

Décommenter l'appel API réel et supprimer le mock :

```python
# Supprimer tout le bloc mocké et décommenter :
result = await self._make_request('GET', url, headers, json_body)
```

---

## ITEM #13 : Code mocké actif

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/routing/routing_d3_adapter.py` |
| **Lignes** | 99-113 |

```python
# Mock de données de routage
result = {
    "strategy": "default",
    "rules": [...]
}
```

**Problème identifié** :

Le moteur de règles D3 n'est pas appelé, les décisions de routage sont fictives. Les clients ne seront pas correctement routés selon les règles métier.

**Solution proposée** :

Décommenter l'appel réel vers le service ODM/D3.

---

## ITEM #14 : Code mocké actif

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/restitution/restitution_contrat_carte_adapter.py` |
| **Lignes** | 247-388 |

```python
# Plus de 140 lignes de données mockées
result = {
    "cards": [
        {"cardId": "MOCK001", "cardType": "VISA", ...},
        {"cardId": "MOCK002", "cardType": "MASTERCARD", ...},
    ]
}
```

**Problème identifié** :

Plus de 140 lignes de données mockées ! La liste des cartes du client est entièrement fictive. Le client ne verrait pas ses vraies cartes.

**Solution proposée** :

Supprimer le mock et activer l'appel API réel.

---

## ITEM #15 : TODOs non implémentés

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/nlu/virtual_assistant_orchestrator.py` |
| **Lignes** | 132-137 |

```python
# Détection de boucles conversationnelles
#TODO : implémentation des contrôles de boucles conversationnelles

# Si niveau de confiance trop faible ALORS déclencher les guardrails
# TODO : call input filtering
```

**Problème identifié** :

Des fonctionnalités essentielles ne sont pas implémentées. Les contrôles de boucles conversationnelles empêchent un utilisateur de tourner en rond. L'input filtering protège contre les injections. Ces TODO indiquent que le code n'est pas terminé.

**Solution proposée** :

Implémenter les fonctionnalités ou lever des exceptions explicites si non prêt :

```python
def check_conversational_loops(self):
    raise NotImplementedError("Contrôle de boucles non implémenté - requis pour production")
```

---

## ITEM #16 : Fichier junk.py versionné

| Champ | Détail |
|-------|--------|
| **Script** | `junk.py` |
| **Lignes** | 1-10 |

```python
from actions.conversational.rag_action import call_genius

url = "https://llmaas-ap88967-hprd-4c627b49.data.cloud.net.intra/v1/chat/completions"

data = {'question': {'sender': 'user', 'content': 'je veux connaitre les frais pour un virement ?'}}
response = call_genius(data)
```

**Problème identifié** :

Un fichier de "junk" (déchets/scratch) est versionné avec une URL interne de production. Ce fichier expose l'infrastructure interne et n'a rien à faire dans un repo.

**Solution proposée** :

Supprimer ce fichier :

```bash
rm junk.py
git add -A && git commit -m "Remove junk.py"
```

---

# 🔴 SECTION 3 : BUGS ET ERREURS DE LOGIQUE

---

## ITEM #17 : Ordre des exceptions incorrect

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/session/action_session_start.py` |
| **Lignes** | 95-126 |

```python
try:
    # ... code
except Exception as e:  # Ligne 95 - CAPTURE TOUT
    dispatcher.utter_message(text=f"Erreur: {str(e)}")
    return [SessionStarted(), ActionExecuted("action_listen")]

except UserNotFoundException:  # Ligne 102 - JAMAIS ATTEINT !
    dispatcher.utter_message(text="Désolé, je n'ai pas trouvé vos informations utilisateur.")
    return [ActionExecutionRejected(self.name())]

except AuthenticationException:  # JAMAIS ATTEINT !
    dispatcher.utter_message(text="Problème d'authentification.")
    return [ActionExecutionRejected(self.name())]
```

**Problème identifié** :

Le bloc `except Exception` est placé AVANT les exceptions spécifiques. En Python, les clauses except sont évaluées dans l'ordre. Comme `Exception` est la classe parente de toutes les exceptions, elle attrape tout. Les `except UserNotFoundException`, `except AuthenticationException`, etc. ne seront JAMAIS atteints. C'est du code mort qui donne un faux sentiment de sécurité.

**Solution proposée** :

Inverser l'ordre : les exceptions les plus spécifiques en premier, `Exception` en dernier :

```python
try:
    # ... code
except UserNotFoundException:
    dispatcher.utter_message(text="Désolé, je n'ai pas trouvé vos informations utilisateur.")
    return [ActionExecutionRejected(self.name())]
except AuthenticationException:
    dispatcher.utter_message(text="Problème d'authentification. Veuillez vous reconnecter.")
    return [ActionExecutionRejected(self.name())]
except ServiceUnavailableException:
    dispatcher.utter_message(text="Le service est temporairement indisponible.")
    return [ActionExecutionRejected(self.name())]
except TimeoutException:
    dispatcher.utter_message(text="La requête a pris trop de temps.")
    return [ActionExecutionRejected(self.name())]
except ConnectionException:
    dispatcher.utter_message(text="Impossible de se connecter au service.")
    return [ActionExecutionRejected(self.name())]
except Exception as e:  # TOUJOURS EN DERNIER
    logger.error(f"Erreur inattendue: {e}")
    dispatcher.utter_message(text="Une erreur inattendue s'est produite.")
    return [ActionExecutionRejected(self.name())]
```

---

## ITEM #18 : Ordre des exceptions incorrect

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/cards/action_get_list_cards.py` |
| **Lignes** | 76-100 |

```python
except Exception as e:  # CAPTURE TOUT EN PREMIER
    dispatcher.utter_message(text=f"Erreur: {str(e)}")
    return [...]

except CardNotFoundException:  # JAMAIS ATTEINT
    dispatcher.utter_message(text="Aucune carte trouvée.")
```

**Problème identifié** :

Identique à l'item #17. Le `except Exception` capture tout avant les handlers spécifiques.

**Solution proposée** :

Même correction : réordonner les blocs except avec les plus spécifiques en premier.

---

## ITEM #19 : Retours incohérents

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/application/intention_detection.py` |
| **Lignes** | 23, 31, 52, 80, 87 |

```python
async def execute(self, message: Message) -> Message:  # Annotation dit Message
    if not message_intentions:
        return False, message  # Retourne tuple (bool, Message)
    if confidence < threshold:
        return False, message  # Retourne tuple (bool, Message)
    return True, message       # Retourne tuple (bool, Message)

except Exception as e:
    return None                # Retourne None !
```

**Problème identifié** :

La signature de la fonction dit qu'elle retourne `Message`, mais en réalité elle retourne 3 types différents : un tuple `(bool, Message)` dans le cas normal, et `None` en cas d'exception. Le code appelant ne peut pas gérer correctement ces retours. C'est du typage mensonger.

**Solution proposée** :

Corriger l'annotation de type et uniformiser les retours :

```python
from typing import Tuple

async def execute(self, message: Message) -> Tuple[bool, Message]:
    """
    Returns:
        Tuple[bool, Message]: (success_flag, processed_message)
    """
    try:
        if not message_intentions:
            return False, message
        if confidence < self.confidence_threshold:
            return False, message
        # ... traitement ...
        return True, message
    except Exception as e:
        logger.error(f"Erreur IntentionDetection: {e}")
        return False, message  # Tuple cohérent même en cas d'erreur
```

---

## ITEM #20 : Exceptions dupliquées et incohérentes

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/common/exceptions.py` |
| **Lignes** | 1-59 |

```python
class APIException(Exception):
    """Exception de base pour les erreurs API"""
    pass

class CardNotFoundException(APIException):  # Ligne 20 - Hérite de APIException
    pass

# ... 20 lignes plus tard ...

class CardNotFoundException(Exception):     # Ligne 41 - REDÉFINITION ! Hérite de Exception
    pass

class APIException(Exception):              # Ligne 56 - REDÉFINIT LA CLASSE PARENTE !
    pass
```

**Problème identifié** :

Les classes d'exceptions sont définies deux fois dans le même fichier avec des hiérarchies différentes. `CardNotFoundException` hérite d'abord de `APIException`, puis est redéfinie pour hériter de `Exception`. Ensuite, `APIException` elle-même est redéfinie ! Python prend la dernière définition, donc la hiérarchie est cassée.

**Solution proposée** :

Supprimer les définitions dupliquées et garder une seule hiérarchie :

```python
class APIException(Exception):
    """Exception de base pour toutes les erreurs API"""
    pass

class UserNotFoundException(APIException):
    pass

class CardNotFoundException(APIException):
    pass

class AuthenticationException(APIException):
    pass

class ServiceUnavailableException(APIException):
    pass

class TimeoutException(APIException):
    pass

class ConnectionException(APIException):
    pass

# etc. - UNE SEULE définition par classe
```

---

## ITEM #21 : @classmethod avec self au lieu de cls

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/nlu/virtual_assistant_orchestrator.py` |
| **Lignes** | 142-143 |

```python
@classmethod
def _log(self, message: Message):  # self avec @classmethod !
    intent_data = message.get("intent")
    # ...
```

**Problème identifié** :

Le décorateur `@classmethod` implique que le premier paramètre est la classe (`cls`), pas l'instance (`self`). Ici, la méthode utilise `self` mais est décorée `@classmethod`, ce qui est incohérent. En pratique, `self` recevra la classe, pas l'instance.

**Solution proposée** :

Soit retirer le décorateur (si la méthode doit accéder à l'instance), soit utiliser `cls` :

```python
# Option 1 : C'est une méthode d'instance normale
def _log(self, message: Message):
    # ... utilise self normalement

# Option 2 : C'est vraiment une méthode de classe
@classmethod
def _log(cls, message: Message):
    # ... n'utilise que cls et les arguments
```

---

## ITEM #22 : @dataclass sur Enum

| Champ | Détail |
|-------|--------|
| **Script** | `actions/domain/entities/guardrails.py` |
| **Lignes** | 6-17 |

```python
from dataclasses import dataclass
from enum import Enum

@dataclass
class GuardrailLabel(Enum):
    SAFETY = "safety"
    TOXICITY = "toxicity"
    COMPETITOR = "competitor"

@dataclass
class GuardrailsAssesmentStatus(Enum):
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
```

**Problème identifié** :

`@dataclass` et `Enum` sont fondamentalement incompatibles. Une `Enum` a des valeurs fixes définies comme attributs de classe. Un `@dataclass` génère automatiquement un `__init__` pour initialiser des attributs d'instance. Mettre les deux ensemble n'a aucun sens et Mypy détectera ça comme une erreur.

**Solution proposée** :

Retirer simplement le décorateur `@dataclass` des Enum :

```python
from enum import Enum

class GuardrailLabel(Enum):
    SAFETY = "safety"
    TOXICITY = "toxicity"
    COMPETITOR = "competitor"
    IRRELEVANCY = "irrelevancy"
    LANGUAGE = "language"

class GuardrailsAssesmentStatus(Enum):
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
```

---

## ITEM #23 : @dataclass sur Enum

| Champ | Détail |
|-------|--------|
| **Script** | `actions/domain/entities/entities.py` |
| **Lignes** | 66-77 |

```python
@dataclass
class SomeEnum(Enum):
    VALUE_A = "a"
    VALUE_B = "b"
```

**Problème identifié** :

Même erreur conceptuelle que l'item #22.

**Solution proposée** :

Retirer `@dataclass` des classes Enum.

---

## ITEM #24 : @dataclass sur Enum (fichier dupliqué)

| Champ | Détail |
|-------|--------|
| **Script** | `actions/domain/entities/guardrails_1.py` |
| **Lignes** | 6-17 |

```python
@dataclass
class GuardrailLabel(Enum):
    # ...
```

**Problème identifié** :

Fichier dupliqué avec le même bug.

**Solution proposée** :

Supprimer ce fichier dupliqué et corriger l'original.

---

## ITEM #25 : __init__ redéfini dans @dataclass

| Champ | Détail |
|-------|--------|
| **Script** | `actions/domain/entities/conversation.py`, `actions/domain/entities/entities.py` |
| **Lignes** | 30-35 |

```python
@dataclass
class InteractionContext:
    channel: str
    media: str
    trace_id: str
    span_id: str

    def __init__(self, channel: str, media: str, trace_id: str, span_id: str):
        self.channel = channel  # REDONDANT !
        self.media = media
        self.trace_id = trace_id
        self.span_id = span_id
```

**Problème identifié** :

Le décorateur `@dataclass` génère automatiquement un `__init__` basé sur les attributs déclarés. Redéfinir manuellement `__init__` est inutile et contre-productif : ça écrase le comportement généré.

**Solution proposée** :

Supprimer le `__init__` manuel :

```python
@dataclass
class InteractionContext:
    channel: str
    media: str
    trace_id: str
    span_id: str
    # Pas de __init__ nécessaire, @dataclass le génère
```

---

## ITEM #26 : Faute de frappe "Assesment" (54 occurrences)

| Champ | Détail |
|-------|--------|
| **Script** | `actions/domain/entities/guardrails.py`, `actions/domain/entities/entities.py`, `custom_components/application/language_assesment.py`, `custom_components/infrastructure/guardrails/guardrails_mapper.py`, `actions/infrastructure/rag/rag_mapper.py` |
| **Lignes** | Multiples |

```python
class MessageAssesment:  # Manque un 's'
    guardrail: GuardrailLabel
    label: str
    score: float

class MessageAssesmentResult:  # Manque un 's'
    assessment_status: GuardrailsAssesmentStatus  # Manque un 's'
    message_assesment_results: List[MessageAssesment]  # Manque un 's'
```

**Problème identifié** :

La faute "Assesment" (1 seul 's') au lieu de "Assessment" (2 's') est répétée 54 fois dans le code. C'est une faute d'orthographe qui nuit à la qualité du code. Les développeurs anglophones ou les outils d'autocomplétion risquent de ne pas trouver les bonnes classes.

**Solution proposée** :

Faire un find & replace global :

```bash
find . -type f -name "*.py" -exec sed -i 's/Assesment/Assessment/g' {} +
mv language_assesment.py language_assessment.py
```

---

# 🟠 SECTION 4 : ARCHITECTURE

---

## ITEM #27 : Fichiers dupliqués non nettoyés

| Champ | Détail |
|-------|--------|
| **Script** | Multiples paires de fichiers |
| **Lignes** | N/A |

```
config_loader.py / config_loader_1.py
constants.py / constants_1.py
guardrails_adapter.py / guardrails_adapter_1.py / guardrails_adapter_2.py
enumerations.py / enumerations_1.py
exceptions.py / exceptions_1.py
local-conf.yaml / local-conf_1.yaml
Dockerfile / Dockerfile_1
```

**Problème identifié** :

Le projet est truffé de fichiers dupliqués avec des suffixes `_1`, `_2`. On ne sait pas lequel est le bon, lequel est obsolète, et ils peuvent avoir des implémentations différentes. Signe d'une gestion de version chaotique.

**Solution proposée** :

1. Identifier quel fichier est le "bon" (celui importé, celui à jour)
2. Supprimer les doublons
3. Vérifier que tous les imports pointent vers le bon fichier

```bash
rm config_loader_1.py constants_1.py exceptions_1.py guardrails_adapter_1.py ...
```

---

## ITEM #28 : Singleton non thread-safe

| Champ | Détail |
|-------|--------|
| **Script** | `actions/config/config_loader.py` |
| **Lignes** | 8-13 |

```python
class ConfigLoader:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:  # Race condition possible
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
```

**Problème identifié** :

Le pattern singleton est implémenté de manière non thread-safe. Dans un environnement async comme Rasa, plusieurs coroutines peuvent appeler `ConfigLoader()` en même temps. Si deux coroutines passent le test `if cls._instance is None` avant que l'une n'ait fini d'initialiser, on aura deux instances avec des états incohérents.

**Solution proposée** :

Utiliser un lock ou `functools.lru_cache` :

```python
import threading

class ConfigLoader:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._load_config()
            return cls._instance
```

---

## ITEM #29 : Mélange httpx et requests

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/infrastructure/guardrails/guardrails_adapter_2.py` |
| **Lignes** | 4-5, 65, 135 |

```python
import httpx
import requests

async def input_filtering(...):
    async with httpx.AsyncClient() as client:  # httpx async créé mais non utilisé
        response = requests.post(...)          # requests sync !
```

**Problème identifié** :

Le code importe `httpx` (async) et `requests` (sync) mais utilise `requests` dans un contexte async. Pire : il crée un `AsyncClient` httpx pour ensuite l'ignorer et utiliser `requests.post()`. `requests` est bloquant, donc dans un serveur async, ça bloque tout le serveur pendant l'appel HTTP.

**Solution proposée** :

Utiliser exclusivement `httpx` en mode async :

```python
async def input_filtering(...):
    async with httpx.AsyncClient(verify="./BNPPRootCa.crt", cert=cert) as client:
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
```

---

## ITEM #30 : Mapper trop volumineux

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/v360/v360_mapper.py` |
| **Lignes** | 978 lignes |

**Problème identifié** :

Un fichier de 978 lignes pour un mapper, c'est beaucoup trop. Le Single Responsibility Principle est violé. Ce fichier fait probablement plusieurs choses : mapping user, mapping cards, mapping accounts, etc.

**Solution proposée** :

Diviser en plusieurs mappers spécialisés :

```
v360_user_mapper.py
v360_card_mapper.py
v360_account_mapper.py
v360_product_mapper.py
```

---

## ITEM #31 : URLs hardcodées

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/infrastructure/guardrails/guardrails_adapter_2.py` |
| **Lignes** | 33, 110 |

```python
url = 'https://sav-guardrails-hellobank.dev.echonet/v1/guardrails/input-filtering'
```

**Problème identifié** :

Les URLs d'API sont écrites en dur dans le code au lieu d'être lues depuis la configuration. Impossible de changer d'environnement (dev, staging, prod) sans modifier le code source.

**Solution proposée** :

Lire les URLs depuis la configuration :

```python
url = self.config.get("guardrails", {}).get("base_url") + \
      self.config.get("guardrails", {}).get("input_filtering", {}).get("startpoint")
```

---

## ITEM #32 : Headers/credentials hardcodés

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/infrastructure/guardrails/guardrails_adapter_2.py` |
| **Lignes** | 35-43 |

```python
headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
    'X-B3-TraceId': 'af4e5f9c-2bcf-4e1a-91af-daade4e66be9',
    'X-B3-SpanId': 'af4e5f9c-2bcf-4e1a-91af-daade4e66be9',
    'Channel': '007',
    'Media': '083',
    'UserId': '000000'
}
```

**Problème identifié** :

Les headers de tracing (TraceId, SpanId) et les identifiants (UserId, Channel, Media) sont en dur. Le TraceId devrait être unique par requête. Le UserId '000000' est clairement un placeholder.

**Solution proposée** :

Générer dynamiquement les headers :

```python
import uuid

headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
    'X-B3-TraceId': str(uuid.uuid4()),
    'X-B3-SpanId': str(uuid.uuid4()),
    'Channel': self.interaction_context.channel,
    'Media': self.interaction_context.media,
    'UserId': self.user_id
}
```

---

# 🟠 SECTION 5 : QUALITÉ DU CODE (BLACK/RUFF/MYPY)

---

## ITEM #33 : Espaces avant les deux-points (OMNIPRÉSENT)

| Champ | Détail |
|-------|--------|
| **Script** | TOUS les fichiers Python |
| **Lignes** | 100+ occurrences |

```python
def name(self) -> Text :
    return "action_session_start"

async def run(
        self ,
        dispatcher: CollectingDispatcher ,
) -> List[ Dict[ Text , Any ] ] :
```

**Problème identifié** :

Le formatage du code viole PEP8 et les standards Black. Il y a des espaces avant les `:` partout, des espaces dans les crochets. Black refuserait ce code.

**Solution proposée** :

Lancer Black pour formatter automatiquement :

```bash
black .
```

Résultat :
```python
def name(self) -> Text:
    return "action_session_start"

async def run(
    self,
    dispatcher: CollectingDispatcher,
) -> List[Dict[Text, Any]]:
```

---

## ITEM #34 : Espaces dans les indices de liste/dict

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/common/map_to_data_class_actions.py`, `actions/infrastructure/rag/rag_mapper.py` |
| **Lignes** | Multiples |

```python
cards_data[ card.id_monetic_contract ] = {...}
tracker.events[ 0 ]
data[ "message_item" ][ "sender" ]
history[ -1 ]
```

**Problème identifié** :

Des espaces à l'intérieur des crochets d'indexation. Contraire à PEP8.

**Solution proposée** :

```python
cards_data[card.id_monetic_contract] = {...}
tracker.events[0]
data["message_item"]["sender"]
history[-1]
```

---

## ITEM #35 : Parenthèses vides sur les classes

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/infrastructure/guardrails/guardrails_adapter_2.py`, `custom_components/infrastructure/language/language_adapter.py`, `custom_components/infrastructure/intention/intention_adapter.py` |
| **Lignes** | 14, 12, 16 |

```python
class GuardrailsApiAdapter():
class LanguageAdapter():
class IntentionApiAdapter():
class ClassificationScore():
```

**Problème identifié** :

Les parenthèses vides après le nom de classe sont inutiles en Python.

**Solution proposée** :

```python
class GuardrailsApiAdapter:
class LanguageAdapter:
class IntentionApiAdapter:
class ClassificationScore:
```

---

## ITEM #36 : print() au lieu de logger (T20)

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/common/map_to_data_class_actions.py`, `custom_components/infrastructure/guardrails/guardrails_adapter_2.py`, `custom_components/infrastructure/intention/intention_adapter.py` |
| **Lignes** | 122, 88, 90, 149, 151, 94, 96 |

```python
print(f" tracker id {tracker.sender_id}")
print(f"Erreur HTTP : {e.response.status_code} - {e.response.text}")
print(f"Erreur de requête : {e}")
```

**Problème identifié** :

Ruff a la règle T20 activée dans `pyproject.toml` qui interdit `print()` en production. Ces `print()` sont des restes de debug. Les `print()` ne sont pas capturés par les systèmes de logging, pas de niveau de log, pas de timestamp.

**Solution proposée** :

```python
logger.debug(f"tracker id {tracker.sender_id}")
logger.error(f"Erreur HTTP : {e.response.status_code}")
```

---

## ITEM #37 : Imports non utilisés (F401)

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/nlu/virtual_assistant_orchestrator.py`, `custom_components/infrastructure/language/language_adapter.py`, `actions/exposition/common/read_headers.py` |
| **Lignes** | 4, 1-2, 1-2 |

```python
import requests  # Jamais utilisé (virtual_assistant_orchestrator.py)
import time      # Jamais utilisé (language_adapter.py)
import uuid      # Jamais utilisé (language_adapter.py)
from rasa_sdk import Action, Tracker  # Action jamais utilisé (read_headers.py)
```

**Problème identifié** :

Des modules sont importés mais jamais utilisés. Ruff détecte ça comme erreur F401.

**Solution proposée** :

```bash
ruff check --select F401 --fix .
```

---

## ITEM #38 : @staticmethod manquants

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/rag/rag_mapper.py` |
| **Lignes** | 15, 28, 47, 65, 84 |

```python
class RagMapper:
    def datetime_to_utc_iso_format(dt: datetime) -> str:  # Pas de self !
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    def map_json_to_objects(json_data):  # Pas de self !
        assessment_status = GuardrailsAssesmentStatus(json_data["messageAssessmentStatus"])
        # ...
```

**Problème identifié** :

Ces méthodes n'utilisent pas `self`, elles devraient être décorées `@staticmethod`. Sans ce décorateur, Python attend `self` comme premier argument.

**Solution proposée** :

```python
class RagMapper:
    @staticmethod
    def datetime_to_utc_iso_format(dt: datetime) -> str:
        ...
    
    @staticmethod
    def map_json_to_objects(json_data: Dict[str, Any]) -> MessageAssesmentResult:
        ...
```

---

## ITEM #39 : @staticmethod manquants

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/common/read_headers.py` |
| **Lignes** | 49, 86 |

```python
class ActionReadHeaders:
    async def get_header(tracker: Tracker) -> dict:  # Pas de self !
        # ...
    
    async def get_brand_market_user_type(headers: dict):  # Pas de self !
        # ...
```

**Problème identifié** :

Identique à item #38.

**Solution proposée** :

Ajouter `@staticmethod` aux méthodes concernées.

---

## ITEM #40 : Annotations de type manquantes

| Champ | Détail |
|-------|--------|
| **Script** | `actions/application/user/get_user_info_use_case.py`, `actions/infrastructure/rag/rag_mapper.py`, `actions/exposition/common/read_headers.py` |
| **Lignes** | 9, 28, 49, 86 |

```python
def __init__(self, config):  # config: Dict[str, Any] manquant
    self.config = config

def map_json_to_objects(json_data):  # json_data: Dict[str, Any] manquant

async def get_header(tracker: Tracker) -> dict:  # dict trop vague, devrait être Dict[str, str]
```

**Problème identifié** :

Des paramètres et retours n'ont pas de type annotation. Mypy ne peut pas faire son travail.

**Solution proposée** :

```python
def __init__(self, config: Dict[str, Any]) -> None:
    self.config = config

def map_json_to_objects(json_data: Dict[str, Any]) -> MessageAssesmentResult:

async def get_header(tracker: Tracker) -> Dict[str, str]:
```

---

## ITEM #41 : Mélange de styles d'annotation

| Champ | Détail |
|-------|--------|
| **Script** | `actions/domain/entities/conversation.py`, `actions/domain/entities/entities.py` |
| **Lignes** | 70, 63 |

```python
from typing import List, Optional
history: Optional[list[MessageItem]] = None  # list minuscule (3.9+)
message_assesment_results: List[MessageAssesment]  # List majuscule (typing)
```

**Problème identifié** :

Le code mélange deux styles d'annotation de type : Python 3.9+ (`list`, `dict`, `|`) et le module typing (`List`, `Dict`, `Optional`). Incohérent.

**Solution proposée** :

Choisir un style et s'y tenir :

```python
# Style Python 3.9+ uniforme
history: list[MessageItem] | None = None
message_assessment_results: list[MessageAssessment]
```

---

## ITEM #42 : Redéfinition de variable (F811)

| Champ | Détail |
|-------|--------|
| **Script** | `actions/infrastructure/common/exceptions.py` |
| **Lignes** | 20-21 puis 41-59 |

**Problème identifié** :

Déjà couvert dans item #20. Ruff détecte les redéfinitions comme erreur F811.

**Solution proposée** :

Voir item #20.

---

## ITEM #43 : Lignes trop longues (E501)

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/rag/action_rag_response.py` |
| **Lignes** | 11-13 |

```python
from actions.infrastructure.common.exceptions import AuthenticationException, ServiceUnavailableException, TimeoutException, ConnectionException, RagNotFoundException, InputFilteringNotFoundException, OutputFilteringNotFoundException
```

**Problème identifié** :

Certaines lignes dépassent la limite de 120 caractères configurée.

**Solution proposée** :

```python
from actions.infrastructure.common.exceptions import (
    AuthenticationException,
    ServiceUnavailableException,
    TimeoutException,
    ConnectionException,
    RagNotFoundException,
    InputFilteringNotFoundException,
    OutputFilteringNotFoundException,
)
```

---

## ITEM #44 : Complexité cyclomatique élevée (C901)

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/common/map_to_data_class_actions.py`, `actions/infrastructure/rag/rag_mapper.py` |
| **Lignes** | Fonctions `map_tracker_to_message`, `map_structure` |

**Problème identifié** :

Certaines fonctions ont trop de branches (if/else, try/except, for). La config Ruff limite à 10.

**Solution proposée** :

Refactorer en extrayant des sous-fonctions :

```python
def _validate_input(data):
    ...

def _build_question(data):
    ...

def map_structure(input_data):
    data = _validate_input(input_data)
    question = _build_question(data)
    return {"question": question}
```

---

## ITEM #45 : Encoding manquant sur open()

| Champ | Détail |
|-------|--------|
| **Script** | `actions/config/config_loader.py` |
| **Ligne** | 22 |

```python
with open(config_path, 'r') as file:
```

**Problème identifié** :

Le `open()` n'a pas de paramètre `encoding`. Sur certains systèmes, l'encoding par défaut n'est pas UTF-8.

**Solution proposée** :

```python
with open(config_path, 'r', encoding='utf-8') as file:
```

---

## ITEM #46 : Variable globale mutable non utilisée

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/nlu/virtual_assistant_orchestrator.py` |
| **Ligne** | 25 |

```python
intent_list: List[str] = []
```

**Problème identifié** :

Une variable globale `intent_list` est déclarée mais jamais utilisée. Les variables globales mutables sont une mauvaise pratique.

**Solution proposée** :

Supprimer cette ligne.

---

## ITEM #47 : Problèmes d'encodage UTF-8

| Champ | Détail |
|-------|--------|
| **Script** | Tous les fichiers Python |
| **Lignes** | Multiples |

```python
# Au lieu de : "Récupération des métadonnées de session"
# On trouve  : "RÃ©cupÃ©ration des mÃ©tadonnÃ©es de session"

# Au lieu de : "d'après le nlu"
# On trouve  : "d'aprÃ¨s le nlu"
```

**Problème identifié** :

Les fichiers ont été mal encodés. Tous les caractères accentués sont corrompus (é → Ã©, è → Ã¨). Les messages utilisateur seront illisibles.

**Solution proposée** :

Ré-encoder les fichiers en UTF-8 :

```bash
iconv -f ISO-8859-1 -t UTF-8 fichier.py > fichier_utf8.py
mv fichier_utf8.py fichier.py

# OU
sed -i 's/Ã©/é/g; s/Ã¨/è/g; s/Ã /à/g' *.py
```

---

## ITEM #48 : Mélange logging/loguru

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/infrastructure/language/language_adapter.py` vs autres |
| **Ligne** | 5 |

```python
# language_adapter.py
from loguru import logger

# Tous les autres fichiers
import logging
logger = logging.getLogger(__name__)
```

**Problème identifié** :

Un fichier utilise `loguru` pendant que tous les autres utilisent `logging` standard. Incohérence.

**Solution proposée** :

Utiliser le même système partout :

```python
import logging
logger = logging.getLogger(__name__)
```

---

## ITEM #49 : Exception avec arguments incorrects

| Champ | Détail |
|-------|--------|
| **Script** | `custom_components/infrastructure/language/language_adapter.py` |
| **Lignes** | 88-90 |

```python
raise Exception(
    "code", "type", "Error with lingua - " + str(e)
)
```

**Problème identifié** :

`Exception` prend un seul argument message. Passer plusieurs arguments ne fait pas ce qu'on pense.

**Solution proposée** :

```python
raise Exception(f"Error with lingua: code={code}, type={type}, {e}")

# OU mieux : exception personnalisée
class LanguageDetectionError(Exception):
    pass

raise LanguageDetectionError(f"Error with lingua: {e}")
```

---

## ITEM #50 : Nommage incohérent

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/common/read_headers.py`, `custom_components/application/language_assesment.py`, `custom_components/infrastructure/guardrails/guardrails_adapter_2.py`, `custom_components/infrastructure/guardrails/guardrails_maper.py` |
| **Lignes** | 65, 18-19, 93, nom de fichier |

```python
UserId = '01030024893200000'  # Variable avec majuscule = constante ?
langue_adapter                 # Français dans un projet anglophone
outputfiltering                # Pas de underscore
guardrails_maper               # Faute d'orthographe (mapper)
```

**Problème identifié** :

Le nommage est incohérent : mélange français/anglais, snake_case pas toujours respecté, fautes d'orthographe.

**Solution proposée** :

```python
user_id = '01030024893200000'
language_adapter
output_filtering
guardrails_mapper
```

---

## ITEM #51 : Fautes d'orthographe dans le code

| Champ | Détail |
|-------|--------|
| **Script** | `actions/domain/entities/card.py`, `actions/exposition/cards/action_get_list_cards.py`, `actions/exposition/common/read_headers.py` |
| **Lignes** | Multiples |

```python
OpppositionReason   # 3 'p'
rafactoring_parameter
user_fisrt_name
ancaires            # bancaires
infoirmations
hearders            # headers
```

**Problème identifié** :

Plusieurs fautes d'orthographe dans les noms.

**Solution proposée** :

```
OpppositionReason    → OppositionReason
rafactoring_parameter → refactoring_parameter
user_fisrt_name      → user_first_name
ancaires             → bancaires
infoirmations        → informations
hearders             → headers
```

---

## ITEM #52 : Magic strings/numbers

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/common/read_headers.py` |
| **Lignes** | 127-132 |

```python
if headers.get('Media') in ('111', '112', '113'):
    user_type = UserType.PROSPECT.value

if headers.get('Media') in ('082', '083', '091', '004', '066', '098'):
    user_type = UserType.CUSTOMER.value
```

**Problème identifié** :

Des valeurs littérales utilisées directement sans explication. Que signifie '111' ? '082' ? Il existe déjà une Enum `Media`.

**Solution proposée** :

```python
PROSPECT_MEDIA = {
    Media.INTERNET_PROSPECT_HB.value,
    Media.APP_MOBILE_PROSPECT_HB.value,
    Media.APP_TABLETTE_PROSPECT_HB.value,
}

if headers.get('Media') in PROSPECT_MEDIA:
    user_type = UserType.PROSPECT.value
```

---

## ITEM #53 : Lignes dupliquées

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/common/read_headers.py` |
| **Lignes** | 80-82 |

```python
logging.info(f"Extracted headers: {headers}")
logging.info(f"Extracted headers: {headers}")  # DUPLIQUÉE !
```

**Problème identifié** :

La même ligne de log est répétée deux fois. Copier-coller raté.

**Solution proposée** :

Supprimer la ligne dupliquée.

---

# 🟠 SECTION 6 : DOCUMENTATION

---

## ITEM #54 : README incomplet

| Champ | Détail |
|-------|--------|
| **Script** | `README.md` |
| **Lignes** | Fichier entier |

**Problème identifié** :

Le README ne contient pas les informations essentielles : pas d'instructions de déploiement, pas de documentation d'architecture, pas d'explication des flows métier.

**Solution proposée** :

Enrichir le README :

```markdown
# Assistant Virtuel Bancaire

## Architecture
[Diagramme]

## Prérequis
- Python 3.11+
- Docker

## Installation
poetry install

## Configuration
Copier local-conf.yaml.example...

## Déploiement
### Dev / Staging / Production

## Flows métier
- Opposition carte
- Consultation solde
```

---

## ITEM #55 : Docstrings incorrects ou incohérents

| Champ | Détail |
|-------|--------|
| **Script** | `actions/exposition/common/read_headers.py`, `actions/exposition/common/map_to_data_class_actions.py` |
| **Lignes** | 49-60, 43-54 |

```python
async def get_header(tracker: Tracker) -> dict:
    """
    Args:
        dispatcher: ...  # N'EXISTE PAS dans les paramètres !
        tracker: ...
        domain: ...      # N'EXISTE PAS dans les paramètres !

    Returns:
        List of events (empty in this case)  # Retourne dict, pas List !
    """
```

**Problème identifié** :

Les docstrings mentionnent des paramètres qui n'existent pas ou documentent le mauvais type de retour.

**Solution proposée** :

```python
async def get_header(tracker: Tracker) -> dict:
    """
    Extrait les headers de la conversation depuis le tracker.

    Args:
        tracker: L'objet Tracker de Rasa contenant les métadonnées

    Returns:
        dict: Les headers extraits de la conversation
    """
```

---

## ITEM #56 : Commentaire obsolète dans pyproject.toml

| Champ | Détail |
|-------|--------|
| **Script** | `pyproject.toml` |
| **Ligne** | ~5 |

```toml
[project]
name = "rasa-poc"  # Change this name
version = "1.0.0-dev.1"
```

**Problème identifié** :

Le nom du projet est toujours "rasa-poc" avec un commentaire demandant de le changer. Projet non finalisé.

**Solution proposée** :

```toml
[project]
name = "assistant-virtuel-bancaire"
version = "1.0.0"
```

---

# 🔴 SECTION 7 : TESTS

---

## ITEM #57 : Absence totale de tests unitaires

| Champ | Détail |
|-------|--------|
| **Script** | `tests/` |
| **Lignes** | N/A |

**Problème identifié** :

Il n'y a AUCUN test unitaire dans le projet. Zéro. Inadmissible pour du code en production bancaire.

**Solution proposée** :

Écrire des tests unitaires avec pytest. Objectif : 80% de couverture minimum.

```python
# tests/test_exceptions.py
import pytest
from actions.infrastructure.common.exceptions import (
    CardNotFoundException,
    APIException,
)

def test_card_not_found_is_api_exception():
    assert issubclass(CardNotFoundException, APIException)

# tests/test_guardrails_mapper.py
def test_map_json_to_objects_accepted():
    json_data = {
        "messageAssessmentStatus": "accepted",
        "messageAssessmentReason": "OK",
        "messageEvaluationResults": []
    }
    result = GuardrailsMapper.map_json_to_objects(json_data)
    assert result.assessment_status == GuardrailsAssessmentStatus.ACCEPTED
```

---

## ITEM #58 : Absence de tests d'intégration

| Champ | Détail |
|-------|--------|
| **Script** | `tests/` |
| **Lignes** | N/A |

**Problème identifié** :

Pas de tests d'intégration non plus. Les adapters HTTP, les connexions aux APIs, le flow complet ne sont jamais testés.

**Solution proposée** :

```python
# tests/integration/test_v360_adapter.py
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_get_user_info():
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value.json.return_value = {
            "userId": "12345",
            "firstName": "Jean",
        }
        mock_get.return_value.status_code = 200
        
        adapter = V360ApiAdapter(config)
        user = await adapter.get_user_info_by_party_id("12345")
        
        assert user.user_first_name == "Jean"
```

---

# 🟠 SECTION 8 : CONFIGURATION

---

## ITEM #59 : .gitignore mal nommé

| Champ | Détail |
|-------|--------|
| **Script** | `_gitignore` |
| **Lignes** | N/A |

**Problème identifié** :

Le fichier est nommé `_gitignore` au lieu de `.gitignore`. Git ne le reconnaît pas.

**Solution proposée** :

```bash
mv _gitignore .gitignore
```

Contenu recommandé :
```gitignore
__pycache__/
*.pyc
.env
venv/
*.log
*.key
*.crt
.idea/
.vscode/
.coverage
.pytest_cache/
.mypy_cache/
```

---

## ITEM #60 : Dépendances inutiles ou invalides

| Champ | Détail |
|-------|--------|
| **Script** | `requirements-actions.txt` |
| **Lignes** | Variable |

```txt
logging         # Module built-in, pas un package pip
dataclasses     # Built-in Python 3.7+
httpx==0.23.0   # Version ancienne (2022)
```

**Problème identifié** :

Le fichier requirements contient des modules built-in Python qui ne sont pas des packages pip. De plus, `httpx` est en version ancienne avec potentiellement des vulnérabilités.

**Solution proposée** :

```txt
# Retirer logging et dataclasses (built-in)
httpx>=0.27.0
```

---

# 📋 RÉSUMÉ EXÉCUTIF

## Statistiques

| Catégorie | Critique | Majeur | Mineur |
|-----------|----------|--------|--------|
| Sécurité | 11 | 0 | 0 |
| Code non finalisé | 5 | 0 | 0 |
| Bugs et erreurs | 10 | 0 | 0 |
| Architecture | 0 | 6 | 0 |
| Qualité code | 2 | 17 | 2 |
| Documentation | 0 | 2 | 1 |
| Tests | 2 | 0 | 0 |
| Configuration | 0 | 1 | 1 |
| **TOTAL** | **30** | **26** | **4** |

## Commandes de correction automatique

```bash
# Formatage
black .

# Linting avec corrections auto
ruff check --fix .

# Tri des imports
ruff check --select I --fix .

# Vérification types
mypy . --ignore-missing-imports

# Tests
pytest --cov=actions --cov-report=html
```

---

## ⛔ VERDICT FINAL

**NON PRÊT POUR LA PRODUCTION**

Estimation : 4-6 semaines de remédiation

---

*Rapport de code review généré le 20/12/2025*
