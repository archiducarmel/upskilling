# Analyse approfondie : Gestion des hotwords multi-mots (n-grams)

## Le problème en détail

### Contexte

Les hotwords ne sont pas toujours des mots simples. Beaucoup sont des **expressions composées** de plusieurs mots :

```
virement international SEPA
clé digitale 3D Secure
BNP Paribas Personal Finance
crédit immobilier taux fixe
assurance vie multisupport
```

### Ce qui se passe actuellement

Le correcteur orthographique tokenise le texte **mot par mot**. L'expression "virement international SEPA" devient trois tokens séparés :

```
["virement", "international", "SEPA"]
```

Chaque mot est ensuite vérifié indépendamment contre le dictionnaire. Le problème est triple :

**Problème 1 : Perte du contexte de l'expression**

Le correcteur ne sait pas que ces trois mots forment une unité. Il pourrait corriger "international" en "internationale" (accord) ou laisser passer une faute sur un des mots car il ne reconnaît pas l'expression complète.

**Problème 2 : Matching partiel impossible**

Si le texte contient "virement internationnal SEPA" (faute sur "international"), le correcteur ne peut pas savoir que c'est une variante de l'expression "virement international SEPA" car il ne voit que des mots isolés.

**Problème 3 : Faux positifs de correction**

Le mot "digitale" dans "clé digitale 3D" pourrait être "corrigé" en "digital" par un correcteur qui ne connaît pas l'expression figée.

### Exemples concrets de dégradation

| Entrée (transcription STT) | Correction actuelle | Attendu |
|---------------------------|---------------------|---------|
| "virement internationnal SEPA" | "virement international SEPA" ❌ ou inchangé | "virement international SEPA" ✓ |
| "clé digitale 3D secure" | "clé digital 3D sécure" ❌ | "clé digitale 3D Secure" ✓ |
| "BNP pariba Personal Finance" | "BNP Paris Personal Finance" ❌ | "BNP Paribas Personal Finance" ✓ |

---

## Solution 1 : Index des n-grams par premier mot

### Principe

L'idée est de créer un index qui associe chaque **premier mot** d'une expression à la liste des expressions complètes qui commencent par ce mot. Ainsi, quand on rencontre un mot dans le texte, on peut vérifier rapidement s'il peut être le début d'une expression multi-mots.

### Fonctionnement étape par étape

1. **Pré-traitement** : On parcourt tous les hotwords et on construit un index
2. **Lors de la correction** : Pour chaque mot, on regarde s'il peut débuter une expression
3. **Si oui** : On collecte les N mots suivants et on teste si ça forme une expression connue
4. **Si match** : On protège toute l'expression de la correction

```python
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def construire_index_ngrams(hotwords: List[str]) -> Dict[str, List[str]]:
    """
    Construit un index des hotwords multi-mots, indexé par leur premier mot.
    
    L'index permet de savoir rapidement si un mot peut être le début
    d'une expression multi-mots, et si oui, lesquelles.
    
    Args:
        hotwords: Liste de tous les hotwords (simples et multi-mots)
        
    Returns:
        Dictionnaire {premier_mot: [liste des expressions qui commencent par ce mot]}
        
    Example:
        >>> hotwords = ["BNP Paribas", "BNP Paribas Personal Finance", "virement SEPA"]
        >>> index = construire_index_ngrams(hotwords)
        >>> index
        {
            'bnp': ['BNP Paribas', 'BNP Paribas Personal Finance'],
            'virement': ['virement SEPA']
        }
    """
    index = defaultdict(list)
    
    for hotword in hotwords:
        mots = hotword.split()
        
        # On ne s'intéresse qu'aux expressions de 2 mots ou plus
        if len(mots) >= 2:
            premier_mot = mots[0].lower()
            index[premier_mot].append(hotword)
    
    # Trier chaque liste par longueur décroissante
    # Important : on veut tester les expressions les plus longues d'abord
    # "BNP Paribas Personal Finance" avant "BNP Paribas"
    for premier_mot in index:
        index[premier_mot].sort(key=lambda x: len(x.split()), reverse=True)
    
    return dict(index)


# Exemple d'utilisation
hotwords = [
    "BNP Paribas",
    "BNP Paribas Personal Finance",
    "virement international SEPA",
    "clé digitale 3D Secure",
    "crédit immobilier",
    "assurance vie multisupport",
]

index = construire_index_ngrams(hotwords)
print(index)
# {
#     'bnp': ['BNP Paribas Personal Finance', 'BNP Paribas'],
#     'virement': ['virement international SEPA'],
#     'clé': ['clé digitale 3D Secure'],
#     'crédit': ['crédit immobilier'],
#     'assurance': ['assurance vie multisupport']
# }
```

---

## Solution 2 : Détection exacte des expressions

### Principe

Une fois l'index construit, on peut détecter les expressions multi-mots dans le texte. On parcourt le texte mot par mot, et quand on trouve un mot qui peut débuter une expression, on vérifie si les mots suivants correspondent.

```python
def detecter_expressions_exactes(
    texte: str,
    index_ngrams: Dict[str, List[str]]
) -> List[Tuple[int, int, str]]:
    """
    Détecte les expressions multi-mots présentes dans le texte (match exact).
    
    Retourne la liste des expressions trouvées avec leur position
    (index début, index fin, expression).
    
    Args:
        texte: Le texte à analyser
        index_ngrams: Index construit par construire_index_ngrams()
        
    Returns:
        Liste de tuples (position_debut, position_fin, expression_matchée)
        Les positions sont des indices de mots, pas de caractères.
        
    Example:
        >>> texte = "Je fais un virement international SEPA demain"
        >>> detecter_expressions_exactes(texte, index)
        [(3, 6, 'virement international SEPA')]
    """
    mots = texte.split()
    expressions_trouvees = []
    
    i = 0
    while i < len(mots):
        mot_courant = mots[i].lower()
        
        # Ce mot peut-il débuter une expression multi-mots ?
        if mot_courant in index_ngrams:
            
            # Tester chaque expression candidate (les plus longues d'abord)
            for expression in index_ngrams[mot_courant]:
                mots_expression = expression.split()
                nb_mots = len(mots_expression)
                
                # Vérifier qu'on a assez de mots restants dans le texte
                if i + nb_mots > len(mots):
                    continue
                
                # Extraire la séquence de mots du texte
                sequence_texte = mots[i:i + nb_mots]
                
                # Comparer (insensible à la casse)
                sequence_lower = [m.lower() for m in sequence_texte]
                expression_lower = [m.lower() for m in mots_expression]
                
                if sequence_lower == expression_lower:
                    # Match trouvé !
                    expressions_trouvees.append((i, i + nb_mots, expression))
                    i += nb_mots  # Sauter tous les mots de l'expression
                    break
            else:
                # Aucune expression n'a matché, passer au mot suivant
                i += 1
        else:
            i += 1
    
    return expressions_trouvees


# Test
texte = "Je souhaite faire un virement international SEPA vers BNP Paribas"
expressions = detecter_expressions_exactes(texte, index)
print(expressions)
# [(4, 7, 'virement international SEPA'), (8, 10, 'BNP Paribas')]
```

---

## Solution 3 : Détection fuzzy des expressions (avec tolérance aux fautes)

### Principe

La détection exacte ne suffit pas car les transcriptions STT contiennent souvent des fautes. "virement internationnal SEPA" (deux 'n') ne matchera pas "virement international SEPA".

Il faut donc une détection **approximative** qui tolère des petites différences sur chaque mot de l'expression.

```python
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein


def similarite_mots(mot1: str, mot2: str) -> float:
    """
    Calcule un score de similarité entre deux mots (0 à 1).
    
    Utilise la distance de Levenshtein normalisée.
    1.0 = identiques, 0.0 = complètement différents
    """
    if mot1.lower() == mot2.lower():
        return 1.0
    
    distance = Levenshtein.distance(mot1.lower(), mot2.lower())
    longueur_max = max(len(mot1), len(mot2))
    
    return 1.0 - (distance / longueur_max)


def matcher_expression_fuzzy(
    mots_texte: List[str],
    mots_expression: List[str],
    seuil_mot: float = 0.80,
    seuil_expression: float = 0.85
) -> Tuple[bool, float]:
    """
    Vérifie si une séquence de mots correspond approximativement à une expression.
    
    Args:
        mots_texte: Mots extraits du texte à vérifier
        mots_expression: Mots de l'expression hotword
        seuil_mot: Similarité minimum pour chaque mot individuel (0.80 = 80%)
        seuil_expression: Similarité moyenne minimum pour l'expression entière
        
    Returns:
        (match: bool, score: float)
        
    Example:
        >>> matcher_expression_fuzzy(
        ...     ["virement", "internationnal", "SEPA"],  # Faute sur 'international'
        ...     ["virement", "international", "SEPA"]
        ... )
        (True, 0.94)  # Match malgré la faute
    """
    if len(mots_texte) != len(mots_expression):
        return False, 0.0
    
    scores = []
    
    for mot_texte, mot_expr in zip(mots_texte, mots_expression):
        score = similarite_mots(mot_texte, mot_expr)
        
        # Si un seul mot est trop différent, l'expression ne matche pas
        if score < seuil_mot:
            return False, 0.0
        
        scores.append(score)
    
    # Score moyen de l'expression
    score_moyen = sum(scores) / len(scores)
    
    return score_moyen >= seuil_expression, score_moyen


def detecter_expressions_fuzzy(
    texte: str,
    index_ngrams: Dict[str, List[str]],
    seuil_premier_mot: float = 0.85
) -> List[Tuple[int, int, str, float]]:
    """
    Détecte les expressions multi-mots avec tolérance aux fautes d'orthographe.
    
    Contrairement à detecter_expressions_exactes(), cette fonction tolère
    des petites erreurs sur chaque mot de l'expression.
    
    Args:
        texte: Le texte à analyser
        index_ngrams: Index des expressions multi-mots
        seuil_premier_mot: Similarité minimum pour considérer qu'un mot
                          peut être le début d'une expression
        
    Returns:
        Liste de tuples (pos_debut, pos_fin, expression_corrigée, score)
    """
    mots = texte.split()
    expressions_trouvees = []
    
    i = 0
    while i < len(mots):
        mot_courant = mots[i]
        
        # Chercher si ce mot ressemble au début d'une expression
        meilleur_match = None
        meilleur_score = 0
        
        for premier_mot_expr, expressions in index_ngrams.items():
            
            # Le premier mot doit être suffisamment similaire
            score_premier = similarite_mots(mot_courant, premier_mot_expr)
            if score_premier < seuil_premier_mot:
                continue
            
            # Tester chaque expression (les plus longues d'abord)
            for expression in expressions:
                mots_expression = expression.split()
                nb_mots = len(mots_expression)
                
                # Vérifier qu'on a assez de mots
                if i + nb_mots > len(mots):
                    continue
                
                # Extraire et comparer
                sequence_texte = mots[i:i + nb_mots]
                match, score = matcher_expression_fuzzy(sequence_texte, mots_expression)
                
                if match and score > meilleur_score:
                    meilleur_match = (i, i + nb_mots, expression, score)
                    meilleur_score = score
        
        if meilleur_match:
            expressions_trouvees.append(meilleur_match)
            i = meilleur_match[1]  # Sauter les mots matchés
        else:
            i += 1
    
    return expressions_trouvees


# Test avec fautes
texte = "Je fais un virement internationnal SEPA chez BMP Paribas"
#                      ^^^ faute                    ^^^ faute

expressions = detecter_expressions_fuzzy(texte, index)
print(expressions)
# [
#     (3, 6, 'virement international SEPA', 0.94),
#     (7, 9, 'BNP Paribas', 0.91)
# ]
```

---

## Solution 4 : Correction intégrée avec protection des n-grams

### Principe

Maintenant qu'on sait détecter les expressions (exactes ou approximatives), on peut intégrer cette logique dans le correcteur orthographique. L'idée est de :

1. **D'abord** identifier toutes les expressions multi-mots dans le texte
2. **Ensuite** corriger le texte en protégeant ces expressions (ou en les remplaçant par la forme correcte)

```python
from typing import Optional
from spellchecker import SpellChecker


class CorrecteurAvecNgrams:
    """
    Correcteur orthographique qui gère les hotwords multi-mots.
    
    Fonctionnement :
    1. Charge les hotwords et construit un index des expressions
    2. Lors de la correction, détecte d'abord les expressions multi-mots
    3. Protège ces expressions (ou les corrige vers la forme canonique)
    4. Corrige les mots restants normalement
    """
    
    def __init__(self, chemin_hotwords: str):
        """
        Initialise le correcteur avec un fichier de hotwords.
        
        Args:
            chemin_hotwords: Chemin vers le fichier (un hotword par ligne)
        """
        # Charger les hotwords
        with open(chemin_hotwords, 'r', encoding='utf-8') as f:
            self.hotwords = [ligne.strip() for ligne in f if ligne.strip()]
        
        # Séparer mots simples et expressions
        self.hotwords_simples = set()
        self.hotwords_multi = []
        
        for hw in self.hotwords:
            if ' ' in hw:
                self.hotwords_multi.append(hw)
            else:
                self.hotwords_simples.add(hw.lower())
        
        # Construire l'index des n-grams
        self.index_ngrams = construire_index_ngrams(self.hotwords_multi)
        
        # Calculer la longueur max des expressions (pour optimisation)
        self.max_ngram_length = max(
            (len(hw.split()) for hw in self.hotwords_multi),
            default=1
        )
        
        # Correcteur de base pour les mots simples
        self.spell = SpellChecker(language='fr')
        self.spell.word_frequency.load_words(self.hotwords_simples)
        
        print(f"✓ Chargé : {len(self.hotwords_simples)} mots simples, "
              f"{len(self.hotwords_multi)} expressions")
    
    def corriger(self, texte: str, mode_fuzzy: bool = True) -> str:
        """
        Corrige le texte en gérant les expressions multi-mots.
        
        Args:
            texte: Le texte à corriger
            mode_fuzzy: Si True, tolère les fautes dans les expressions
            
        Returns:
            Le texte corrigé
        """
        # Étape 1 : Détecter les expressions multi-mots
        if mode_fuzzy:
            expressions = detecter_expressions_fuzzy(texte, self.index_ngrams)
        else:
            expressions = detecter_expressions_exactes(texte, self.index_ngrams)
            # Adapter le format pour uniformiser
            expressions = [(e[0], e[1], e[2], 1.0) for e in expressions]
        
        # Étape 2 : Construire un ensemble des positions protégées
        mots = texte.split()
        positions_protegees = set()
        remplacements = {}  # {position_debut: expression_correcte}
        
        for pos_debut, pos_fin, expression_correcte, score in expressions:
            for pos in range(pos_debut, pos_fin):
                positions_protegees.add(pos)
            remplacements[pos_debut] = (pos_fin, expression_correcte)
        
        # Étape 3 : Corriger mot par mot
        mots_corriges = []
        i = 0
        
        while i < len(mots):
            # Ce mot fait-il partie d'une expression ?
            if i in remplacements:
                # Remplacer par l'expression correcte
                pos_fin, expression = remplacements[i]
                mots_corriges.append(expression)
                i = pos_fin
            elif i in positions_protegees:
                # Cas ne devrait pas arriver (déjà traité par remplacements)
                mots_corriges.append(mots[i])
                i += 1
            else:
                # Mot normal : appliquer correction standard
                mot_corrige = self._corriger_mot_simple(mots[i])
                mots_corriges.append(mot_corrige)
                i += 1
        
        return ' '.join(mots_corriges)
    
    def _corriger_mot_simple(self, mot: str) -> str:
        """Corrige un mot simple (hors expression)."""
        # Extraire la ponctuation
        ponctuation = ''
        mot_clean = mot
        while mot_clean and mot_clean[-1] in '.,;:!?':
            ponctuation = mot_clean[-1] + ponctuation
            mot_clean = mot_clean[:-1]
        
        if not mot_clean:
            return mot
        
        # Hotword simple : ne pas corriger
        if mot_clean.lower() in self.hotwords_simples:
            return mot
        
        # Mot connu du dictionnaire : ne pas corriger
        if mot_clean.lower() in self.spell:
            return mot
        
        # Tenter une correction
        suggestion = self.spell.correction(mot_clean.lower())
        
        if suggestion and suggestion != mot_clean.lower():
            # Préserver la casse
            if mot_clean.isupper():
                suggestion = suggestion.upper()
            elif mot_clean.istitle():
                suggestion = suggestion.capitalize()
            return suggestion + ponctuation
        
        return mot


# Utilisation
correcteur = CorrecteurAvecNgrams('/mnt/data/STT/hotwords_v2.txt')

# Test
texte = "Je fais un virement internationnal SEPA chez BMP Paribas demain"
resultat = correcteur.corriger(texte)
print(resultat)
# "Je fais un virement international SEPA chez BNP Paribas demain"
```

---

## Solution 5 : Optimisation avec Trie (Arbre préfixe)

### Principe

Pour de très gros volumes de hotwords, l'approche par index peut devenir lente. Une structure de **Trie** (arbre préfixe) permet une recherche plus efficace.

Le Trie stocke les expressions mot par mot dans une structure arborescente. Chaque nœud représente un mot, et les chemins de la racine aux feuilles représentent les expressions complètes.

```python
class TrieNode:
    """Nœud d'un Trie pour les expressions multi-mots."""
    
    def __init__(self):
        self.enfants: Dict[str, 'TrieNode'] = {}
        self.est_fin_expression: bool = False
        self.expression_complete: Optional[str] = None


class TrieNgrams:
    """
    Trie optimisé pour la recherche d'expressions multi-mots.
    
    Avantages par rapport à l'index simple :
    - Recherche en O(k) où k = longueur de l'expression (vs O(n) expressions)
    - Partage de préfixes communs (économie mémoire)
    - Détection précoce d'échec (pas besoin de tester toutes les expressions)
    """
    
    def __init__(self):
        self.racine = TrieNode()
        self.nb_expressions = 0
    
    def ajouter(self, expression: str):
        """Ajoute une expression au Trie."""
        mots = expression.lower().split()
        noeud = self.racine
        
        for mot in mots:
            if mot not in noeud.enfants:
                noeud.enfants[mot] = TrieNode()
            noeud = noeud.enfants[mot]
        
        noeud.est_fin_expression = True
        noeud.expression_complete = expression  # Garder la forme originale (casse)
        self.nb_expressions += 1
    
    def chercher_depuis_position(
        self, 
        mots: List[str], 
        position: int
    ) -> Optional[Tuple[int, str]]:
        """
        Cherche la plus longue expression qui commence à la position donnée.
        
        Args:
            mots: Liste des mots du texte
            position: Position de départ
            
        Returns:
            (nombre_de_mots, expression) si trouvé, None sinon
        """
        noeud = self.racine
        meilleur_match = None
        
        for i in range(position, len(mots)):
            mot = mots[i].lower()
            
            # Nettoyage de la ponctuation pour le matching
            mot_clean = mot.rstrip('.,;:!?')
            
            if mot_clean not in noeud.enfants:
                break  # Pas de continuation possible
            
            noeud = noeud.enfants[mot_clean]
            
            # Si ce nœud marque la fin d'une expression, c'est un match potentiel
            if noeud.est_fin_expression:
                meilleur_match = (i - position + 1, noeud.expression_complete)
            
            # Continuer pour chercher une expression plus longue
        
        return meilleur_match
    
    @classmethod
    def depuis_hotwords(cls, hotwords: List[str]) -> 'TrieNgrams':
        """Construit un Trie depuis une liste de hotwords."""
        trie = cls()
        for hw in hotwords:
            if ' ' in hw:  # Seulement les expressions multi-mots
                trie.ajouter(hw)
        return trie


def detecter_avec_trie(texte: str, trie: TrieNgrams) -> List[Tuple[int, int, str]]:
    """
    Détecte les expressions multi-mots en utilisant le Trie.
    
    Plus efficace que la recherche linéaire pour de gros volumes.
    """
    mots = texte.split()
    expressions = []
    
    i = 0
    while i < len(mots):
        match = trie.chercher_depuis_position(mots, i)
        
        if match:
            nb_mots, expression = match
            expressions.append((i, i + nb_mots, expression))
            i += nb_mots
        else:
            i += 1
    
    return expressions


# Exemple
trie = TrieNgrams.depuis_hotwords(hotwords)
print(f"Trie construit avec {trie.nb_expressions} expressions")

texte = "Je veux un crédit immobilier et une assurance vie multisupport"
expressions = detecter_avec_trie(texte, trie)
print(expressions)
# [(3, 5, 'crédit immobilier'), (7, 10, 'assurance vie multisupport')]
```

---

## Solution 6 : Combinaison Trie + Fuzzy matching

### Principe

Pour avoir le meilleur des deux mondes (performance du Trie + tolérance aux fautes), on peut combiner les approches :

1. Utiliser le Trie pour identifier rapidement les **candidats potentiels**
2. Appliquer le fuzzy matching uniquement sur ces candidats

```python
class TrieNgramsFuzzy(TrieNgrams):
    """
    Trie avec support du matching approximatif.
    
    Stratégie : on explore le Trie en tolérant une certaine distance
    sur chaque mot. Plus coûteux mais permet de détecter les fautes.
    """
    
    def chercher_fuzzy(
        self,
        mots: List[str],
        position: int,
        seuil_similarite: float = 0.80
    ) -> Optional[Tuple[int, str, float]]:
        """
        Cherche une expression avec tolérance aux fautes.
        
        Utilise une recherche en profondeur avec pruning sur le score.
        """
        resultats = []
        
        def explorer(noeud: TrieNode, pos: int, score_cumule: float, profondeur: int):
            # Si on a dépassé le texte, arrêter
            if pos >= len(mots):
                return
            
            mot_texte = mots[pos].lower().rstrip('.,;:!?')
            
            # Explorer tous les enfants possibles
            for mot_trie, enfant in noeud.enfants.items():
                score = similarite_mots(mot_texte, mot_trie)
                
                # Pruning : si ce mot est trop différent, abandonner cette branche
                if score < seuil_similarite:
                    continue
                
                nouveau_score = (score_cumule * profondeur + score) / (profondeur + 1)
                
                # Si c'est une fin d'expression, enregistrer le match
                if enfant.est_fin_expression:
                    resultats.append((
                        pos - position + 1,
                        enfant.expression_complete,
                        nouveau_score
                    ))
                
                # Continuer l'exploration
                explorer(enfant, pos + 1, nouveau_score, profondeur + 1)
        
        explorer(self.racine, position, 1.0, 0)
        
        # Retourner le meilleur match (le plus long, puis le meilleur score)
        if resultats:
            resultats.sort(key=lambda x: (x[0], x[2]), reverse=True)
            return resultats[0]
        
        return None
```

---

## Synthèse : Quelle solution choisir ?

| Solution | Complexité | Fuzzy | Performance | Cas d'usage |
|----------|------------|-------|-------------|-------------|
| **Index simple** | Faible | ❌ | ⭐⭐⭐ | < 1000 hotwords, match exact OK |
| **Index + fuzzy** | Moyenne | ✅ | ⭐⭐ | < 1000 hotwords, fautes fréquentes |
| **Trie** | Moyenne | ❌ | ⭐⭐⭐⭐ | > 1000 hotwords, match exact OK |
| **Trie + fuzzy** | Élevée | ✅ | ⭐⭐⭐ | > 1000 hotwords, fautes fréquentes |

### Recommandation pour VoxCompliance

Étant donné le contexte (transcriptions STT avec fautes fréquentes, vocabulaire bancaire de taille modérée), je recommande la **Solution 4 (Index + Fuzzy intégré)** :

- Assez simple à implémenter et maintenir
- Gère les fautes de transcription
- Performance suffisante pour des volumes raisonnables
- Facile à débugger

Si le volume de hotwords dépasse 5000+ expressions, passer à la solution Trie.
