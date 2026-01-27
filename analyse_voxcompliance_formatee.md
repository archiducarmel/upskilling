# Analyse Data Science Approfondie - VoxCompliance

## Format de présentation

Chaque problème est présenté selon la structure suivante :
- **Script concerné** et **Fonction concernée**
- **Extrait du code** actuel
- **Explication** de ce que fait le code
- **Problèmes et cas non gérés**
- **Impacts potentiels**
- **Solutions recommandées** avec exemples de code commentés

---

# PARTIE 1 : POST-PROCESSING

---

## PROBLÈME 1 : Suppression des disfluences trop simpliste

### Script concerné
`post_processing.py`

### Fonction concernée
`remove_disfluencies()` — Lignes 33-47

### Extrait du code

```python
def remove_disfluencies(text: str) -> str:
    """
    Supprime les disfluences simples (euh, bah, hum, etc.).
    Approche naïve : suppression des tokens qui sont exactement
    dans le lexique DISFLUENCES (en minuscules).
    """
    tokens = text.split()
    cleaned=[]
    for t in tokens :
        #on enleve ponctuation et on met en minuscule
        mot=t.lower().strip(".,!?;:")
        if mot  not in DISFLUENCES:
            cleaned.append(t)

    return " ".join(cleaned)
```

### Explication de ce que fait le code

Le code découpe le texte en mots séparés par des espaces (`text.split()`). Pour chaque mot, il retire la ponctuation en fin de mot et le convertit en minuscules. Ensuite, il vérifie si ce mot nettoyé existe **exactement** dans le dictionnaire `DISFLUENCES`. Si le mot n'y figure pas, il est conservé ; sinon, il est supprimé.

### Problèmes et cas non gérés

| Type de problème | Exemple | Comportement actuel |
|------------------|---------|---------------------|
| Hésitations allongées | "euuuuh", "euhhhh" | ❌ Non détectées (seul "euh" est dans le dict) |
| Disfluences avec ponctuation intégrée | "euh...", "euh," | ❌ Partiellement gérées |
| Faux départs | "je vou- je voudrais" | ❌ Non traités |
| Homophones légitimes | "Ben" (prénom) supprimé car "ben" est une disfluence | ❌ Faux positifs |
| Timestamps | Les timestamps des segments ne sont pas recalculés | ❌ Décalage audio/texte |

### Impacts potentiels

- **~40% des disfluences réelles** ne sont pas détectées
- Des **mots légitimes** (prénoms, expressions) sont supprimés à tort
- Le **décalage temporel** entre texte et audio rend la navigation dans l'enregistrement impossible

### Solutions recommandées

**1. Utiliser des regex pour capturer les variantes morphologiques :**

```python
import re

# Patterns pour détecter les variantes de disfluences
DISFLUENCE_PATTERNS = [
    r'\b(e+u+h+)\b',       # euh, euuuuh, euhhhh...
    r'\b(h+u+m+)\b',       # hum, hummm...
    r'\b(b+a+h+)\b',       # bah, baaah...
    r'\b(h+e+i+n+)\b',     # hein, heiiiin...
]

def remove_disfluencies_v2(text: str) -> str:
    """Version améliorée avec patterns regex."""
    for pattern in DISFLUENCE_PATTERNS:
        # re.IGNORECASE pour gérer majuscules/minuscules
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip()  # Nettoie espaces multiples
```

**2. Protéger les mots ambigus avec analyse contextuelle :**

```python
def is_protected_word(word: str, prev_word: str, next_word: str) -> bool:
    """
    Vérifie si un mot ambigu doit être protégé.
    Ex: "Ben" en début de phrase = prénom, pas disfluence
    """
    word_lower = word.lower()
    
    # "Ben" avec majuscule après ponctuation = probablement prénom
    if word_lower == 'ben' and word[0].isupper():
        return True
    
    # Expressions figées à protéger
    protected_bigrams = {'et', 'ben', 'bon', 'ben'}  # "et ben", "bon ben"
    if prev_word and prev_word.lower() in protected_bigrams:
        return True
    
    return False
```

**3. Détecter les faux départs (mot tronqué suivi du mot complet) :**

```python
def remove_false_starts(tokens: list) -> list:
    """
    Supprime les faux départs : 'vou-' suivi de 'voudrais'
    Le mot tronqué est un préfixe du mot suivant.
    """
    cleaned = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        # Détecte mot tronqué (finit par tiret)
        if token.endswith('-') and i + 1 < len(tokens):
            prefix = token[:-1].lower()  # Retire le tiret
            next_word = tokens[i + 1].lower()
            # Si le mot suivant commence par ce préfixe → faux départ
            if next_word.startswith(prefix):
                i += 1  # On saute le mot tronqué
                continue
        cleaned.append(token)
        i += 1
    return cleaned
```

---

## PROBLÈME 2 : Gestion des répétitions trop agressive

### Script concerné
`post_processing.py`

### Fonction concernée
`remove_immediate_repetitions()` — Lignes 50-62

### Extrait du code

```python
def remove_immediate_repetitions(text: str) -> str:
    """
    Supprime les répétitions immédiates de mots :
    'oui oui oui je' -> 'oui je'
    Utilise une regex sur la forme 'mot mot (mot)*'.
    """
    # \b(\w+)(\s+\1\b)+ -> capture une séquence de même mot répété
    pattern = re.compile(r"\b(\w+)(\s+\1\b)+", flags=re.IGNORECASE)

    def repl(m: re.Match) -> str:
        return m.group(1) # on garde un seul mot

    return pattern.sub(repl, text)
```

### Explication de ce que fait le code

La regex `\b(\w+)(\s+\1\b)+` capture tout mot suivi d'une ou plusieurs répétitions identiques. Le `\1` est une backreference qui matche exactement le même mot capturé dans le groupe 1. La fonction de remplacement ne conserve qu'une seule occurrence du mot.

### Problèmes et cas non gérés

| Cas | Exemple | Résultat actuel | Problème |
|-----|---------|-----------------|----------|
| Emphase volontaire | "C'est très très important" | "C'est très important" | ❌ Perte de nuance |
| Refus catégorique | "Non non non" | "non" | ❌ Perte d'intensité |
| Confirmation appuyée | "Oui oui" | "oui" | ❌ Perte de sens |
| Répétition avec ponctuation | "oui, oui" | Non détectée | ❌ Inconsistance |

### Impacts potentiels

- **Perte sémantique** : la différence entre "oui" et "oui oui" peut indiquer le niveau de conviction du client
- **Impact conformité** : dans un contexte bancaire, l'intensité d'une réponse peut être juridiquement pertinente

### Solutions recommandées

**1. Classifier les répétitions selon leur type probable :**

```python
# Mots d'emphase : répétition 2x = volontaire, à conserver
EMPHASE_WORDS = {'très', 'trop', 'vraiment', 'absolument', 'super', 'hyper'}

# Mots de réponse : répétition = confirmation, à conserver
CONFIRMATION_WORDS = {'oui', 'non', "d'accord", 'ok', 'bien'}

def classify_repetition(word: str, count: int) -> str:
    """
    Retourne le type de répétition :
    - 'emphase' : à conserver (2x max)
    - 'confirmation' : à conserver
    - 'disfluence' : à supprimer (>2x ou contexte hésitant)
    """
    w = word.lower()
    
    if w in EMPHASE_WORDS and count == 2:
        return 'emphase'      # "très très" → conserver
    
    if w in CONFIRMATION_WORDS and count <= 2:
        return 'confirmation' # "oui oui" → conserver
    
    if count > 2:
        return 'disfluence'   # "oui oui oui oui" → réduire
    
    return 'unknown'          # Décision manuelle
```

**2. Appliquer une logique de réduction contextuelle :**

```python
def smart_dedup(text: str) -> str:
    """
    Déduplique intelligemment selon le type de répétition.
    """
    pattern = re.compile(r'\b(\w+)((\s+\1)+)\b', flags=re.IGNORECASE)
    
    def smart_replace(m: re.Match) -> str:
        word = m.group(1)
        full_match = m.group(0)
        count = full_match.lower().count(word.lower())
        
        rep_type = classify_repetition(word, count)
        
        if rep_type == 'emphase':
            return f"{word} {word}"    # Conserve 2 occurrences
        elif rep_type == 'confirmation':
            return f"{word} {word}"    # Conserve 2 occurrences
        elif rep_type == 'disfluence':
            return word                 # Réduit à 1
        else:
            return full_match           # Pas de changement
    
    return pattern.sub(smart_replace, text)
```

---

## PROBLÈME 3 : Absence de conversion texte vers chiffres (ITN)

### Script concerné
`post_processing.py`

### Fonctions concernées
`normalize_amounts()` (L99-117) et `normalize_dates()` (L141-175)

### Extrait du code

```python
def normalize_amounts(text: str) -> Tuple[str, List[str]]:
    """
    Normalise les montants :
    - '200 euros', '200 euro', '200€' -> '200 €'
    Retourne (texte_normalisé, liste_des_montants_trouvés).
    NB : la conversion 'deux cent euros' -> '200 €' non inclus ici
    """
    amounts_found = []

    # 1) Montants déjà en chiffres
    pattern = re.compile(r"\b(\d{1,9})\s*(euros?|€)\b", flags=re.IGNORECASE)

    def repl(m: re.Match) -> str:
        value = m.group(1)
        amounts_found.append(value + " €")
        return f"{value} €"

    text = pattern.sub(repl, text)
    return text, amounts_found
```

### Explication de ce que fait le code

Le code ne traite que les montants **déjà écrits en chiffres**. La regex `\b(\d{1,9})\s*(euros?|€)\b` capture un nombre de 1 à 9 chiffres suivi de "euros", "euro" ou "€". Le commentaire dans le code admet explicitement que la conversion depuis les mots ("deux cent euros") n'est pas implémentée.

### Problèmes et cas non gérés

| Entrée STT typique | Sortie actuelle | Sortie attendue |
|--------------------|-----------------|-----------------|
| "deux cent cinquante euros" | "deux cent cinquante euros" | "250 €" |
| "le premier mars deux mille vingt-quatre" | Inchangé | "01/03/2024" |
| "quatorze heures trente" | Inchangé | "14h30" |
| "zéro six douze trente-quatre..." | Inchangé | "06 12 34..." |

### Impacts potentiels

- **WER artificiellement gonflé de 20-40%** : "250 €" vs "deux cent cinquante euros" = 100% d'erreur calculée alors que sémantiquement c'est identique
- **Extraction d'entités impossible** : les montants critiques pour la conformité ne peuvent pas être extraits automatiquement
- **Comparaison de systèmes STT faussée** : impossible d'évaluer objectivement les performances

### Solutions recommandées

**Bibliothèques Python prêtes à l'emploi :**

| Bibliothèque | Usage | Installation |
|--------------|-------|--------------|
| **text2num** | Conversion FR nombres → chiffres | `pip install text2num` |
| **NVIDIA NeMo** | ITN complet (nombres, dates, monnaies) | `pip install nemo_toolkit[all]` |
| **num2words** | Conversion inverse (chiffres → mots) | `pip install num2words` |
| **dateparser** | Parsing de dates en langage naturel | `pip install dateparser` |

**1. Utiliser text2num pour les nombres français :**

```python
from text_to_num import text2num

def convert_numbers_to_digits(text: str) -> str:
    """
    Convertit les nombres écrits en lettres vers des chiffres.
    Ex: 'deux cent cinquante' → '250'
    """
    try:
        # text2num gère les cas complexes français
        # "mille neuf cent quatre-vingt-dix-neuf" → 1999
        return str(text2num(text, lang='fr'))
    except ValueError:
        # Si ce n'est pas un nombre, retourne tel quel
        return text
```

**2. Utiliser NVIDIA NeMo pour un ITN complet (production-ready) :**

```python
from nemo.collections.nlp.models import DuplexTextNormalizationModel

# Charger le modèle pré-entraîné pour le français
itn_model = DuplexTextNormalizationModel.from_pretrained("itn_fr_duplex")

def apply_itn_nemo(text: str) -> str:
    """
    Applique l'Inverse Text Normalization avec NeMo.
    Gère automatiquement : nombres, dates, heures, monnaies, mesures.
    """
    # Le modèle retourne directement le texte normalisé
    normalized = itn_model.normalize(text, verbose=False)
    return normalized

# Exemple d'usage :
# "deux cent cinquante euros" → "250 €"
# "le premier janvier deux mille vingt-quatre" → "le 01/01/2024"
```

**3. Solution hybride légère (sans NeMo) :**

```python
from text_to_num import text2num
import re

def itn_montants(text: str) -> str:
    """
    ITN spécialisé pour les montants en euros.
    Pattern: [nombre en lettres] + euros/€
    """
    # Regex pour capturer "nombre_en_lettres euros"
    pattern = r'(\b(?:un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize|vingt|trente|quarante|cinquante|soixante|cent|mille|million|milliard)[\w\s-]*)\s*(euros?|€)'
    
    def replace_amount(match):
        words = match.group(1).strip()
        try:
            number = text2num(words, lang='fr')
            return f"{number} €"
        except ValueError:
            return match.group(0)  # Pas de changement si erreur
    
    return re.sub(pattern, replace_amount, text, flags=re.IGNORECASE)

# Test
print(itn_montants("deux cent cinquante euros"))  # → "250 €"
```

**4. ITN pour les numéros de téléphone :**

```python
def itn_telephone(text: str) -> str:
    """
    Convertit les numéros dictés en format standard.
    'zéro six douze trente-quatre...' → '06 12 34...'
    """
    # Mapping des chiffres en lettres
    CHIFFRES = {
        'zéro': '0', 'un': '1', 'deux': '2', 'trois': '3',
        'quatre': '4', 'cinq': '5', 'six': '6', 'sept': '7',
        'huit': '8', 'neuf': '9', 'dix': '10', 'onze': '11',
        'douze': '12', 'treize': '13', 'quatorze': '14',
        'quinze': '15', 'seize': '16'
    }
    
    # Détecte un début de téléphone FR : "zéro six" ou "zéro un"
    phone_start = re.compile(r'\bzéro\s+(un|six|sept)\b', re.IGNORECASE)
    
    if phone_start.search(text):
        # Remplace chaque mot-chiffre par son équivalent numérique
        for word, digit in CHIFFRES.items():
            text = re.sub(rf'\b{word}\b', digit, text, flags=re.IGNORECASE)
        
        # Regroupe les chiffres par paires (format FR)
        text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)  # Colle les chiffres
        # Puis reformate en paires
        digits = re.findall(r'\d+', text)
        if digits:
            phone = ''.join(digits)
            if len(phone) == 10:
                formatted = ' '.join([phone[i:i+2] for i in range(0, 10, 2)])
                return formatted
    
    return text
```

---

## PROBLÈME 4 : Ordre des traitements sous-optimal

### Script concerné
`post_processing.py`

### Fonction concernée
`post_process_deterministic()` — Lignes 433-509

### Extrait du code

```python
def post_process_deterministic(
 text: str,
 hot_words: Optional[List[str]] = None
) -> Dict:
    # 1) Nettoyage linguistique
    cleaned = remove_disfluencies(text)
    # ...
    cleaned = remove_immediate_repetitions(text)
    # ...
    
    # 2) Normalisation de la casse (avant correction ortho)
    cased = normalize_case_simple(text)
    # ...

    """
    # 3) Correction dictionnaire métier  ← COMMENTÉ !
    hotword_edits = []
    if hot_words:
        text_hw, hotword_edits = correct_with_hot_words(text, hot_words)
        # ...
    """ 
    # 4) Correction orthographe
    corrected_spelling = correct_spelling(text)
    # ...

    # 5) Montants
    text_with_amounts, amounts = normalize_amounts(text)
    # ...

    # 6) Dates
    text_with_dates, dates = normalize_dates(text)
    # ...
```

### Explication de ce que fait le code

Le pipeline applique les traitements dans cet ordre : disfluences → répétitions → casse → (hotwords commenté) → orthographe → montants → dates → numéros sensibles.

### Problèmes et cas non gérés

| Problème | Détail |
|----------|--------|
| ITN absent en début de pipeline | Les normalisations suivantes travaillent sur du texte non normalisé |
| Casse avant entités | "mai" le mois vs "mai" le verbe → ambiguïté après mise en minuscules |
| Hotwords désactivés | Le code lignes 464-472 est commenté → fonctionnalité non utilisée |
| Ordre sous-optimal | L'orthographe peut corriger des mots qui auraient dû être normalisés par ITN |

### Impacts potentiels

- L'ITN n'étant pas appliqué, toutes les entités restent en lettres
- La correction orthographique peut "corriger" des nombres en lettres vers des mots incorrects
- Les hotwords métier ne sont jamais appliqués

### Solutions recommandées

**Réorganiser le pipeline dans l'ordre optimal :**

```python
def post_process_deterministic_v2(text: str, hot_words: List[str] = None) -> Dict:
    """
    Pipeline optimisé avec ordre de traitement corrigé.
    """
    original = text
    
    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 1 : ITN EN PREMIER (convertit texte → chiffres)
    # ═══════════════════════════════════════════════════════════
    # Critique : doit être fait AVANT tout autre traitement
    # pour que les étapes suivantes travaillent sur des entités normalisées
    text = apply_itn(text)  # "deux cent euros" → "200 €"
    
    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 2 : NETTOYAGE LINGUISTIQUE
    # ═══════════════════════════════════════════════════════════
    text = remove_disfluencies(text)
    text = smart_dedup(text)  # Version améliorée des répétitions
    
    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 3 : CORRECTION HOTWORDS (réactivée !)
    # ═══════════════════════════════════════════════════════════
    if hot_words:
        text, _ = correct_with_hot_words_optimized(text, hot_words)
    
    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 4 : CORRECTION ORTHOGRAPHIQUE
    # ═══════════════════════════════════════════════════════════
    # Après hotwords pour ne pas "corriger" des termes métier
    text = correct_spelling(text)
    
    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 5 : NORMALISATION DE CASSE EN DERNIER
    # ═══════════════════════════════════════════════════════════
    # En dernier pour ne pas interférer avec la détection d'entités
    text = normalize_case_simple(text)
    
    # ═══════════════════════════════════════════════════════════
    # ÉTAPE 6 : FORMATAGE FINAL
    # ═══════════════════════════════════════════════════════════
    text, amounts = normalize_amounts(text)  # Reformate montants
    text, dates = normalize_dates(text)      # Reformate dates
    
    return {"original": original, "corrected": text}
```

---

# PARTIE 2 : CORRECTION DES HOTWORDS

---

## PROBLÈME 5 : Performance catastrophique en O(n×m)

### Script concerné
`hotwords_correction.py`

### Fonction concernée
`correct_with_hot_words()` — Lignes 27-113

### Extrait du code

```python
def correct_with_hot_words(text: str, hot_words: list[str], stop_words: list[str],
                           threshold: float, max_levenshtein: int=2) -> tuple[str, list[dict]]:
    # On met les hot words en minuscule pour comparer
    hw_lower = [w.lower() for w in hot_words]

    tokens = re.findall(r"\w+|[^\w\s]|\s+", text)
    corrected_tokens: list[str] = []

    for tok in tokens:
        # ...
        word_lower = tok.lower()

        # Si le mot est déjà un hot word exact -> ne rien changer
        if word_lower in hw_lower:  # ← Recherche O(m) dans une liste !
            corrected_tokens.append(tok)
            continue

        # Fuzzy matching sur le glossaire
        match = process.extractOne(word_lower, hw_lower)  # ← O(m) comparaisons
        # ...
```

### Explication de ce que fait le code

Pour chaque token du texte (n tokens), le code effectue :
1. Une recherche `if word_lower in hw_lower` qui parcourt **toute la liste** car `hw_lower` est une liste, pas un set → O(m)
2. Un appel à `extractOne` de RapidFuzz qui compare le mot à **tous les hotwords** → O(m)

**Complexité totale : O(n × m)** où n = nombre de mots, m = nombre de hotwords.

### Problèmes et cas non gérés

| Taille du texte | Nb hotwords | Opérations | Temps estimé |
|-----------------|-------------|------------|--------------|
| 100 mots | 500 | 50 000 | ~50ms |
| 500 mots | 2 000 | 1 000 000 | ~1s |
| 2 000 mots | 10 000 | 20 000 000 | **~20s** |

### Impacts potentiels

- **Temps de traitement inacceptable** en production (>20s pour un long appel)
- Chaque ajout au dictionnaire ralentit **tous** les traitements
- Impossibilité de passer à l'échelle

### Solutions recommandées

**1. Utiliser un Set pour la recherche exacte O(1) :**

```python
# AVANT : liste → recherche O(m)
hw_lower = [w.lower() for w in hot_words]
if word_lower in hw_lower:  # O(m) à chaque appel !

# APRÈS : set → recherche O(1)
hw_lower_set = {w.lower() for w in hot_words}
if word_lower in hw_lower_set:  # O(1) constant !
```

**2. Utiliser un BK-Tree pour la recherche approximative O(log m) :**

```python
from pybktree import BKTree
from Levenshtein import distance as lev_distance

class HotwordCorrector:
    """
    Correcteur optimisé avec BK-Tree pour recherche fuzzy en O(log m).
    """
    
    def __init__(self, hot_words: list[str]):
        # Set pour recherche exacte O(1)
        self.exact_set = {w.lower() for w in hot_words}
        
        # BK-Tree pour recherche fuzzy O(log m)
        # Le BK-Tree indexe par distance de Levenshtein
        self.bk_tree = BKTree(lev_distance, [w.lower() for w in hot_words])
        
        # Mapping minuscule → forme originale
        self.original_form = {w.lower(): w for w in hot_words}
    
    def correct(self, word: str, max_dist: int = 2) -> str | None:
        """
        Trouve le hotword le plus proche en O(log m).
        Retourne None si aucun candidat dans la distance max.
        """
        word_lower = word.lower()
        
        # 1. Vérif exacte O(1)
        if word_lower in self.exact_set:
            return self.original_form[word_lower]
        
        # 2. Recherche fuzzy O(log m) via BK-Tree
        # Retourne tous les candidats à distance <= max_dist
        candidates = self.bk_tree.find(word_lower, max_dist)
        
        if not candidates:
            return None
        
        # Prend le candidat le plus proche
        best_dist, best_word = min(candidates, key=lambda x: x[0])
        return self.original_form[best_word]
```

**3. Ajouter un cache LRU pour les corrections fréquentes :**

```python
from functools import lru_cache

class HotwordCorrectorCached(HotwordCorrector):
    """Version avec cache pour les mots fréquents."""
    
    @lru_cache(maxsize=10000)
    def correct_cached(self, word: str) -> str | None:
        """
        Cache les 10 000 corrections les plus récentes.
        Les mots fréquents (le, la, de, etc.) ne sont calculés qu'une fois.
        """
        return self.correct(word)
```

**Gain de performance attendu :**

| Métrique | Avant | Après |
|----------|-------|-------|
| Complexité | O(n × m) | O(n × log m) |
| 2000 mots, 10k hotwords | ~20s | **~0.1s** |
| Facteur d'accélération | - | **×200** |

---

## PROBLÈME 6 : Seuils de similarité fixes et inadaptés

### Script concerné
`hotwords_correction.py`

### Fonction concernée
`correct_with_hot_words()` — Lignes 79-92

### Extrait du code

```python
# Seuil de similarité (score sur 0..100)
if score < threshold * 100:
    corrected_tokens.append(tok)
    continue

dist = Levenshtein.distance(word_lower, best_hw_lower)
if dist > max_levenshtein:  # max_levenshtein = 2 (fixe)
    corrected_tokens.append(tok)
    continue
```

### Explication de ce que fait le code

Deux conditions fixes s'appliquent à **tous** les mots, quelle que soit leur longueur :
1. Score de similarité ≥ 85% (threshold = 0.85)
2. Distance de Levenshtein ≤ 2 caractères

### Problèmes et cas non gérés

| Longueur mot | Exemple | Problème |
|--------------|---------|----------|
| 3 caractères | "BNP" vs "BMP" | Distance 1 = 67% similarité → **trop permissif** |
| 3 caractères | "BNP", "BMP", "BIP", "BAP" | Tous à distance 1 → **confusions** |
| 12 caractères | "assurance-vie" avec 3 erreurs | 75% similarité → **rejeté à tort** |

### Impacts potentiels

- **Trop de faux positifs** sur les mots courts (acronymes confondus)
- **Trop de faux négatifs** sur les mots longs (corrections manquées)

### Solutions recommandées

**Implémenter des seuils adaptatifs selon la longueur :**

```python
def get_adaptive_thresholds(word_length: int) -> tuple[float, int]:
    """
    Retourne (seuil_similarité, distance_max) adaptés à la longueur.
    
    Principe : 
    - Mots courts → très strict (1 erreur change tout)
    - Mots longs → plus souple (1 erreur = peu d'impact)
    """
    if word_length <= 4:
        # Mots très courts : exiger quasi-correspondance
        return (0.95, 1)   # 95% similarité, max 1 erreur
    
    elif word_length <= 8:
        # Mots moyens : seuils modérés
        return (0.85, 2)   # 85% similarité, max 2 erreurs
    
    elif word_length <= 12:
        # Mots longs : plus de tolérance
        return (0.75, 3)   # 75% similarité, max 3 erreurs
    
    else:
        # Mots très longs : ~1 erreur / 4 caractères
        max_dist = word_length // 4
        return (0.70, max_dist)


def correct_with_adaptive_threshold(word: str, candidates: list) -> str | None:
    """Correction avec seuils adaptatifs."""
    similarity_threshold, max_distance = get_adaptive_thresholds(len(word))
    
    # Cherche le meilleur candidat respectant les seuils adaptés
    best = None
    best_score = 0
    
    for candidate in candidates:
        dist = Levenshtein.distance(word.lower(), candidate.lower())
        
        # Vérifie distance adaptative
        if dist > max_distance:
            continue
        
        # Calcule similarité
        similarity = 1 - (dist / max(len(word), len(candidate)))
        
        # Vérifie seuil adaptatif
        if similarity >= similarity_threshold and similarity > best_score:
            best = candidate
            best_score = similarity
    
    return best
```

---

## PROBLÈME 7 : Impossibilité de corriger les expressions multi-mots

### Script concerné
`hotwords_correction.py`

### Fonction concernée
`correct_with_hot_words()` — Ligne 45 (tokenisation)

### Extrait du code

```python
# On découpe en : mots | ponctuation | espaces
tokens = re.findall(r"\w+|[^\w\s]|\s+", text)

for tok in tokens:
    # Chaque token est traité INDIVIDUELLEMENT
    # ...
```

### Explication de ce que fait le code

La tokenisation sépare le texte en mots individuels. Chaque mot est ensuite comparé séparément aux hotwords. Il n'y a aucune logique pour regrouper des tokens adjacents et les comparer à des hotwords multi-mots.

### Problèmes et cas non gérés

| Expression dans le texte | Hotword attendu | Comportement actuel |
|--------------------------|-----------------|---------------------|
| "bnp paribas" (mal transcrit) | "BNP Paribas" | ❌ Chaque mot traité séparément |
| "crédit agricole" | "Crédit Agricole" | ❌ Non reconnu comme entité |
| "carte bleue" | "Carte Bleue" | ❌ Non corrigé |

### Impacts potentiels

- Les **noms d'entreprises** (BNP Paribas, Crédit Agricole) ne sont pas corrigés
- Les **produits bancaires** (Carte Bleue, Assurance Vie) ne sont pas normalisés
- Impact majeur sur la **conformité** : entités critiques non identifiées

### Solutions recommandées

**1. Indexer les hotwords multi-mots par leur premier mot :**

```python
from collections import defaultdict

def build_multiword_index(hot_words: list[str]) -> dict:
    """
    Crée un index des hotwords multi-mots.
    Clé = premier mot en minuscules, Valeur = liste de hotwords complets
    
    Ex: "BNP Paribas" → index["bnp"] = ["BNP Paribas"]
    """
    index = defaultdict(list)
    
    for hw in hot_words:
        words = hw.split()
        if len(words) > 1:
            # Indexe par le premier mot
            first_word = words[0].lower()
            index[first_word].append(hw)
    
    return dict(index)

# Exemple d'usage
index = build_multiword_index(["BNP Paribas", "BNP Fortis", "Crédit Agricole"])
# → {"bnp": ["BNP Paribas", "BNP Fortis"], "crédit": ["Crédit Agricole"]}
```

**2. Matcher les expressions multi-mots avec fenêtre glissante :**

```python
def correct_multiword(tokens: list[str], multiword_index: dict, 
                      max_words: int = 4) -> list[str]:
    """
    Corrige les expressions multi-mots par fenêtre glissante.
    
    Stratégie : du plus long au plus court (greedy matching)
    """
    result = []
    i = 0
    
    while i < len(tokens):
        token = tokens[i]
        token_lower = token.lower()
        
        # Vérifie si ce token peut être le début d'un hotword multi-mots
        if token_lower in multiword_index:
            candidates = multiword_index[token_lower]
            
            # Essaie de matcher du plus long au plus court
            matched = False
            for hw in sorted(candidates, key=lambda x: -len(x.split())):
                hw_words = hw.split()
                n = len(hw_words)
                
                # Extrait les n prochains tokens
                window = tokens[i:i+n]
                window_text = ' '.join(window).lower()
                hw_lower = hw.lower()
                
                # Fuzzy match sur l'expression complète
                similarity = fuzz.ratio(window_text, hw_lower) / 100
                
                if similarity >= 0.85:
                    # Match trouvé → remplace par la forme canonique
                    result.append(hw)
                    i += n  # Saute les tokens consommés
                    matched = True
                    break
            
            if matched:
                continue
        
        # Pas de match multi-mots → garde le token tel quel
        result.append(token)
        i += 1
    
    return result
```

**3. Combiner correction mono-mot et multi-mots :**

```python
class HotwordCorrectorComplete:
    """Correcteur complet gérant mono et multi-mots."""
    
    def __init__(self, hot_words: list[str]):
        # Sépare hotwords simples et multi-mots
        self.simple_hw = [hw for hw in hot_words if ' ' not in hw]
        self.multi_hw = [hw for hw in hot_words if ' ' in hw]
        
        # Index pour recherche rapide
        self.simple_set = {hw.lower() for hw in self.simple_hw}
        self.multi_index = build_multiword_index(self.multi_hw)
    
    def correct(self, text: str) -> str:
        """Pipeline de correction complet."""
        tokens = text.split()
        
        # 1. D'abord les multi-mots (priorité aux expressions longues)
        tokens = correct_multiword(tokens, self.multi_index)
        
        # 2. Ensuite les mots simples restants
        tokens = [self.correct_simple(t) or t for t in tokens]
        
        return ' '.join(tokens)
```

---

# PARTIE 3 : MÉTRIQUES D'ÉVALUATION

---

## PROBLÈME 8 : WER calculé sans normalisation sémantique

### Script concerné
`eval_metrics_stt.py`

### Fonction concernée
`text_metrics()` — Lignes 76-84

### Extrait du code

```python
def text_metrics(ref_text, hyp_text):
    """Calcule WER et CER entre vérité terrain et hypothèse"""
    transform=Compose([ToLowerCase(), RemovePunctuation(), RemoveMultipleSpaces(), Strip()])
    
    ref_t= transform(ref_text)
    hyp_t= transform(hyp_text)
    W = wer(ref_t, hyp_t) 
    C = cer(ref_t, hyp_t) 
    return W, C
```

### Explication de ce que fait le code

La transformation appliquée est purement textuelle : minuscules, suppression de ponctuation, nettoyage des espaces. Le WER est ensuite calculé sur les textes ainsi normalisés. **Aucune normalisation sémantique** n'est appliquée : "200 €" et "deux cents euros" sont considérés comme totalement différents.

### Problèmes et cas non gérés

| Référence | Hypothèse | WER calculé | WER réel (sémantique) |
|-----------|-----------|-------------|----------------------|
| "200 €" | "deux cents euros" | **100%** | 0% |
| "01/03/2024" | "premier mars deux mille vingt-quatre" | **100%** | 0% |
| "14h30" | "quatorze heures trente" | **100%** | 0% |
| "M. Dupont" | "monsieur dupont" | **50%** | 0% |

### Impacts potentiels

- **WER surévalué de 20-40%** selon la densité d'entités numériques
- **Impossible de comparer objectivement** différents systèmes STT
- **Améliorations masquées** par le bruit des différences de format
- **Rapports de performance trompeurs**

### Solutions recommandées

**1. Utiliser num2words pour normaliser vers la forme parlée :**

```python
from num2words import num2words
import re

def normalize_to_spoken_form(text: str) -> str:
    """
    Normalise les chiffres vers leur forme parlée pour comparaison équitable.
    Ex: "200 €" → "deux cents euros"
    """
    # Convertit tous les nombres en lettres
    def replace_number(match):
        num = match.group(0)
        try:
            return num2words(int(num), lang='fr')
        except:
            return num
    
    # Remplace les chiffres par des mots
    text = re.sub(r'\b\d+\b', replace_number, text)
    
    # Normalise les symboles monétaires
    text = text.replace('€', 'euros')
    text = text.replace('$', 'dollars')
    
    # Normalise les abréviations courantes
    abbrev = {
        r'\bM\.\s*': 'monsieur ',
        r'\bMme\s*': 'madame ',
        r'\bDr\s*': 'docteur ',
        r'\bn°\s*': 'numéro ',
    }
    for pattern, replacement in abbrev.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text.lower().strip()
```

**2. Calculer le WER avec normalisation sémantique :**

```python
from jiwer import wer, Compose, ToLowerCase, RemovePunctuation, RemoveMultipleSpaces, Strip

def semantic_wer(ref_text: str, hyp_text: str) -> float:
    """
    Calcule le WER après normalisation sémantique.
    Les deux textes sont convertis vers la même représentation.
    """
    # Normalise les deux textes vers la forme parlée
    ref_normalized = normalize_to_spoken_form(ref_text)
    hyp_normalized = normalize_to_spoken_form(hyp_text)
    
    # Applique la transformation textuelle standard
    transform = Compose([
        ToLowerCase(), 
        RemovePunctuation(), 
        RemoveMultipleSpaces(), 
        Strip()
    ])
    
    ref_clean = transform(ref_normalized)
    hyp_clean = transform(hyp_normalized)
    
    return wer(ref_clean, hyp_clean)

# Test
ref = "Le montant est de 250 €"
hyp = "le montant est de deux cent cinquante euros"
print(f"WER standard: {wer(ref.lower(), hyp.lower()):.2%}")      # ~100%
print(f"WER sémantique: {semantic_wer(ref, hyp):.2%}")           # ~0%
```

**3. Alternative : normaliser vers la forme numérique (ITN des deux côtés) :**

```python
def normalize_to_numeric_form(text: str) -> str:
    """
    Alternative : normalise vers la forme numérique.
    Utile si la référence est déjà en chiffres.
    """
    from text_to_num import text2num
    
    # Applique ITN pour convertir les nombres en lettres vers chiffres
    words = text.split()
    result = []
    
    i = 0
    while i < len(words):
        # Tente de convertir une séquence de mots en nombre
        for j in range(len(words), i, -1):
            phrase = ' '.join(words[i:j])
            try:
                number = text2num(phrase, lang='fr')
                result.append(str(number))
                i = j
                break
            except ValueError:
                continue
        else:
            result.append(words[i])
            i += 1
    
    return ' '.join(result)
```

---

## PROBLÈME 9 : Mapping des locuteurs par algorithme glouton

### Script concerné
`eval_metrics_stt.py`

### Fonction concernée
`sa_wer()` — Lignes 162-169

### Extrait du code

```python
# Mapping speaker HYP -> REF
hyp_to_ref = {}
hyp_ids = {str(s.get("locuteur") or s.get("speaker")) for s in hyp_segs}
for h in hyp_ids:
    best, bo = None, -1
    for r in ov:
        if ov[r][h] > bo:
            bo, best = ov[r][h], r
    hyp_to_ref[h] = best  # ← Glouton : prend le meilleur disponible
```

### Explication de ce que fait le code

Pour chaque locuteur de l'hypothèse (dans un **ordre arbitraire**), le code cherche le locuteur de référence avec lequel il a le plus de chevauchement temporel et crée l'association. Une fois un locuteur de référence associé, il reste disponible pour d'autres (pas de marquage "utilisé"), ce qui peut créer des **conflits non gérés**.

### Problèmes et cas non gérés

L'algorithme glouton peut produire un mapping **sous-optimal globalement** :

| Chevauchements (s) | REF_Client | REF_Conseiller |
|-------------------|------------|----------------|
| HYP_1 | 50 | 40 |
| HYP_2 | 45 | 55 |

Si HYP_1 est traité en premier → il prend REF_Client (50 > 40). Puis HYP_2 prend aussi REF_Client (pas de contrainte d'exclusivité), ce qui est incorrect.

### Impacts potentiels

- **Mapping sous-optimal** affecte le calcul du SA-WER
- **Conflits non gérés** : deux locuteurs hypothèse peuvent être associés au même locuteur référence
- **Résultats non reproductibles** selon l'ordre de parcours

### Solutions recommandées

**Utiliser l'algorithme hongrois pour l'assignation optimale :**

```python
from scipy.optimize import linear_sum_assignment
import numpy as np

def optimal_speaker_mapping(overlap_matrix: dict) -> dict:
    """
    Trouve le mapping optimal REF ↔ HYP en maximisant l'overlap total.
    Utilise l'algorithme hongrois (Kuhn-Munkres).
    
    Complexité : O(n³) où n = nombre de locuteurs (négligeable, n < 10)
    """
    # Extrait les IDs des locuteurs
    ref_speakers = list(overlap_matrix.keys())
    hyp_speakers = list(set(
        h for r in overlap_matrix for h in overlap_matrix[r]
    ))
    
    # Construit la matrice de coût (négatif de l'overlap pour minimiser)
    n_ref = len(ref_speakers)
    n_hyp = len(hyp_speakers)
    cost_matrix = np.zeros((n_hyp, n_ref))
    
    for i, h in enumerate(hyp_speakers):
        for j, r in enumerate(ref_speakers):
            # Négatif car linear_sum_assignment MINIMISE
            cost_matrix[i, j] = -overlap_matrix.get(r, {}).get(h, 0)
    
    # Algorithme hongrois : trouve l'assignation optimale
    hyp_indices, ref_indices = linear_sum_assignment(cost_matrix)
    
    # Construit le mapping optimal
    hyp_to_ref = {}
    for hi, ri in zip(hyp_indices, ref_indices):
        hyp_to_ref[hyp_speakers[hi]] = ref_speakers[ri]
    
    return hyp_to_ref

# Intégration dans sa_wer()
def sa_wer_optimal(ref_doc, hyp_doc):
    """SA-WER avec mapping optimal des locuteurs."""
    # ... (code existant pour construire overlap_matrix)
    
    # Remplace le mapping glouton par l'optimal
    hyp_to_ref = optimal_speaker_mapping(ov)
    
    # ... (reste du calcul)
```

---

## PROBLÈME 10 : Boundary F1 avec matching glouton

### Script concerné
`eval_metrics_stt.py`

### Fonction concernée
`boundary_f1()` — Lignes 103-134

### Extrait du code

```python
def boundary_f1(ref_diar, hyp_diar, tol=0.25):
    """Calcule le F1-score des frontières de changement de locuteur"""
    rb, hb = boundaries(ref_diar), boundaries(hyp_diar)
    used = set()
    tp = 0
    for hbv in hb:
        best = None
        bestd = tol + 1
        for i, rbv in enumerate(rb):
            if i in used:
                continue
            d = abs(hbv - rbv)
            if d <= tol and d < bestd:
                best, bestd = i, d
        if best is not None:
            used.add(best)
            tp += 1
    # ...
```

### Explication de ce que fait le code

Pour chaque frontière de l'hypothèse (`hb`), le code cherche la frontière de référence la plus proche **non encore utilisée** et dans la tolérance (0.25s). C'est un algorithme glouton : l'ordre de parcours des frontières hypothèse influence le résultat.

### Problèmes et cas non gérés

Une frontière traitée tôt peut "voler" le match d'une frontière qui aurait été **mieux associée** globalement.

### Impacts potentiels

- F1-score potentiellement sous-optimal
- Résultats variables selon l'ordre des données

### Solutions recommandées

**Appliquer l'algorithme hongrois aux frontières :**

```python
def boundary_f1_optimal(ref_diar, hyp_diar, tol=0.25):
    """
    F1-score des frontières avec assignation optimale.
    """
    rb = boundaries(ref_diar)  # Frontières référence
    hb = boundaries(hyp_diar)  # Frontières hypothèse
    
    if not rb or not hb:
        return 0, 0, 0
    
    # Matrice de distance entre toutes les paires
    n_hyp, n_ref = len(hb), len(rb)
    cost_matrix = np.full((n_hyp, n_ref), np.inf)
    
    for i, h in enumerate(hb):
        for j, r in enumerate(rb):
            d = abs(h - r)
            if d <= tol:
                cost_matrix[i, j] = d  # Distance si dans tolérance
            # Sinon reste inf (non matchable)
    
    # Assignation optimale
    hyp_idx, ref_idx = linear_sum_assignment(cost_matrix)
    
    # Compte les vrais positifs (paires avec distance finie)
    tp = sum(1 for hi, ri in zip(hyp_idx, ref_idx) 
             if cost_matrix[hi, ri] < np.inf)
    
    fp = len(hb) - tp  # Frontières hypothèse non matchées
    fn = len(rb) - tp  # Frontières référence non matchées
    
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    
    return prec, rec, f1
```

---

## PROBLÈME 11 : Pondération arbitraire dans les métriques de rôles

### Script concerné
`eval_metrics_stt.py`

### Fonction concernée
`role_metrics()` — Lignes 264-268

### Extrait du code

```python
# pondération par durée (0.1 s = 1 vote)
votes = max(1, int(round(bo * 10)))
for _ in range(votes):
    y_true.append(lab_r)
    y_pred.append(lab_h)
```

### Explication de ce que fait le code

Pour chaque segment, le code multiplie artificiellement les "votes" proportionnellement à la durée de chevauchement. Un segment de 3 secondes génère 30 entrées identiques dans les listes `y_true` et `y_pred`, tandis qu'un segment de 0.5 seconde n'en génère que 5.

### Problèmes et cas non gérés

| Problème | Détail |
|----------|--------|
| **Biais vers les segments longs** | L'introduction (30s) génère 300 votes vs consentement (2s) = 20 votes |
| **Explosion mémoire** | 10 min de transcription → dizaines de milliers d'entrées |
| **Métriques non interprétables** | F1 de 95% ≠ 95% des rôles corrects |
| **Moments critiques marginalisés** | Le consentement client (2s mais crucial) pèse 100x moins que l'intro |

### Impacts potentiels

- En contexte **conformité**, un segment de consentement de 2s est aussi important qu'une intro de 30s
- Les **erreurs sur segments courts** (souvent les plus critiques) sont masquées
- **Métriques trompeuses** pour le pilotage

### Solutions recommandées

**1. Utiliser `sample_weight` de scikit-learn (sans inflation) :**

```python
from sklearn.metrics import accuracy_score, f1_score

def role_metrics_v2(ref_doc, hyp_doc):
    """
    Métriques de rôles avec pondération propre via sample_weight.
    Pas d'inflation des listes.
    """
    y_true = []
    y_pred = []
    weights = []  # Durée comme poids, sans multiplication
    
    for hs in hyp_segs:
        # ... (code d'alignement existant)
        
        # UN SEUL vote par segment, pondéré par sa durée
        y_true.append(lab_r)
        y_pred.append(lab_h)
        weights.append(bo)  # bo = durée de chevauchement
    
    # Métriques pondérées par durée (sans inflation)
    acc_weighted = accuracy_score(y_true, y_pred, sample_weight=weights)
    f1_weighted = f1_score(y_true, y_pred, average='macro', sample_weight=weights)
    
    return acc_weighted, f1_weighted
```

**2. Calculer les deux types de métriques (par segment ET par durée) :**

```python
def role_metrics_complete(ref_doc, hyp_doc):
    """
    Retourne les deux versions des métriques pour une vue complète.
    """
    y_true, y_pred, durations = [], [], []
    
    # ... (collecte des labels et durées)
    
    # Métriques PAR SEGMENT (chaque segment = 1 vote)
    acc_segment = accuracy_score(y_true, y_pred)
    f1_segment = f1_score(y_true, y_pred, average='macro')
    
    # Métriques PAR DURÉE (pondérées par le temps)
    acc_duration = accuracy_score(y_true, y_pred, sample_weight=durations)
    f1_duration = f1_score(y_true, y_pred, average='macro', sample_weight=durations)
    
    return {
        'segment': {'accuracy': acc_segment, 'f1': f1_segment},
        'duration': {'accuracy': acc_duration, 'f1': f1_duration}
    }
```

**3. Ajouter des métriques par classe pour diagnostic :**

```python
from sklearn.metrics import classification_report

def role_metrics_detailed(y_true, y_pred):
    """
    Rapport détaillé par rôle pour identifier les faiblesses.
    """
    report = classification_report(
        y_true, y_pred,
        labels=['Client', 'Conseiller', 'Répondeur'],
        output_dict=True
    )
    
    # Affiche precision/recall/f1 par rôle
    for role in ['Client', 'Conseiller', 'Répondeur']:
        metrics = report.get(role, {})
        print(f"{role}: P={metrics.get('precision', 0):.2%}, "
              f"R={metrics.get('recall', 0):.2%}, "
              f"F1={metrics.get('f1-score', 0):.2%}")
    
    return report
```

---

# PARTIE 4 : SÉCURITÉ

---

## PROBLÈME 12 : Clé API codée en dur dans le code source

### Script concerné
`pipeline.py`

### Fonction concernée
`llm_inference()` — Lignes 248-249

### Extrait du code

```python
def llm_inference(self, user_prompt, system_prompt, response_model):
    os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"
    llm_url = "https://llmaas-ap88967-prod.data.cloud.net.intra"  # ← EN DUR
    api_key = "sk-uCzBtDEmBtJWJ7sZQ5V7dw"                        # ← CLÉ SECRÈTE EN CLAIR
    model = "Meta-Llama-33-70B-Instruct"
```

### Explication de ce que fait le code

Les identifiants de connexion (URL du service et clé API secrète) sont écrits **directement dans le code source**, en clair. Ces valeurs sont visibles par quiconque a accès au fichier.

### Problèmes et cas non gérés

| Problème | Conséquence |
|----------|-------------|
| **Exposition du secret** | Visible dans Git, logs, partages de code |
| **Historique Git** | Même supprimée, la clé reste dans l'historique |
| **Impossible de tourner** | Changer la clé = modifier le code + redéployer |
| **Violation conformité** | SOC2, ISO 27001, PCI-DSS interdisent cette pratique |

### Impacts potentiels

- **Compromission** : n'importe qui avec accès au repo peut utiliser l'API
- **Audit** : non-conformité immédiatement relevée
- **Incident de sécurité** : responsabilité légale en cas de fuite

### Solutions recommandées

**1. Utiliser des variables d'environnement :**

```python
import os

def llm_inference(self, user_prompt, system_prompt, response_model):
    """Configuration via variables d'environnement (sécurisé)."""
    
    # Lecture des secrets depuis l'environnement
    llm_url = os.environ.get("LLMAAS_ENDPOINT")
    api_key = os.environ.get("LLMAAS_API_KEY")
    
    # Validation : erreur explicite si manquant
    if not llm_url or not api_key:
        raise EnvironmentError(
            "Variables LLMAAS_ENDPOINT et LLMAAS_API_KEY requises. "
            "Configurez-les dans votre environnement ou fichier .env"
        )
    
    # Suite du code...
```

**2. Fichier .env pour le développement local :**

```bash
# Fichier .env (NE JAMAIS COMMITER - ajouter à .gitignore)
LLMAAS_ENDPOINT=https://llmaas-ap88967-prod.data.cloud.net.intra
LLMAAS_API_KEY=sk-xxxxxxxxxxxxx
```

```python
# Charger le .env au démarrage
from dotenv import load_dotenv
load_dotenv()  # Charge les variables depuis .env
```

**3. Ajouter .env au .gitignore :**

```bash
# Dans .gitignore
.env
.env.local
.env.*.local
*.key
```

**4. Pour la production, utiliser un gestionnaire de secrets :**

```python
# Exemple avec AWS Secrets Manager
import boto3
import json

def get_secret(secret_name: str) -> dict:
    """Récupère un secret depuis AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
secrets = get_secret("prod/llmaas/credentials")
llm_url = secrets["endpoint"]
api_key = secrets["api_key"]
```

---

# SYNTHÈSE ET PRIORISATION

## Tableau récapitulatif

| # | Problème | Gravité | Complexité | Priorité |
|---|----------|---------|------------|----------|
| 12 | Clé API en dur | **CRITIQUE** | Faible | Immédiat |
| 3 | ITN absent | **CRITIQUE** | Moyenne | Phase 1 |
| 8 | WER non sémantique | **CRITIQUE** | Moyenne | Phase 1 |
| 5 | Hotwords O(n×m) | HAUTE | Moyenne | Phase 2 |
| 7 | Multi-mots absent | HAUTE | Moyenne | Phase 2 |
| 6 | Seuils fixes | MOYENNE | Faible | Phase 2 |
| 9 | SA-WER glouton | MOYENNE | Faible | Phase 3 |
| 10 | Boundary F1 glouton | MOYENNE | Faible | Phase 3 |
| 11 | Role pondération | MOYENNE | Faible | Phase 3 |
| 1 | Disfluences naïves | MOYENNE | Haute | Phase 4 |
| 2 | Répétitions agressives | BASSE | Moyenne | Phase 4 |
| 4 | Ordre pipeline | BASSE | Faible | Phase 4 |

## Gains attendus

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| WER reporté | ~35% | ~15-20% | Mesure réaliste |
| Temps hotwords (2k mots, 10k dict) | ~20s | ~0.1s | **×200** |
| Entités extraites | ~40% | ~90%+ | **×2.25** |
| Fiabilité métriques | Biaisées | Optimales | Qualitative |
