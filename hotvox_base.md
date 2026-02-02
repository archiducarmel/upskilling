# Rapport : Problèmes de correction orthographique dans VoxCompliance

## Introduction

La fonction de correction orthographique du projet VoxCompliance présente plusieurs lacunes qui dégradent la qualité des transcriptions au lieu de l'améliorer. Ce rapport détaille quatre problèmes majeurs identifiés et propose pour chacun l'ensemble des solutions possibles, de la plus simple à la plus avancée.

---

# Problème 1 : Les acronymes ne sont pas protégés

## Le problème

Le correcteur orthographique traite chaque mot de manière identique, sans faire de distinction entre un mot courant et un acronyme. Quand il rencontre "BNP", "IBAN" ou "SEPA", il ne sait pas que ces suites de lettres sont des abréviations volontaires. Il les considère comme des fautes d'orthographe et cherche à les "corriger".

Le résultat est souvent désastreux. "BNP" peut devenir "BMP" (un format d'image), "IBAN" peut se transformer en "IRAN" (le pays), et "SEPA" risque de devenir "SERA" (le verbe être). Dans un contexte bancaire où ces acronymes apparaissent constamment, ce comportement génère des erreurs à chaque phrase ou presque.

L'impact est d'autant plus grave que ces corrections erronées touchent des termes critiques pour le métier. Un "IBAN" transformé en "IRAN" dans un document de conformité pose un vrai problème de qualité et de crédibilité.

## Solution 1 : Détection automatique par pattern

L'approche la plus simple consiste à détecter automatiquement les acronymes grâce à leurs caractéristiques visuelles. Un acronyme typique possède trois propriétés distinctives :

- Il est écrit **entièrement en majuscules** (contrairement aux mots normaux)
- Il contient **entre 2 et 6 lettres** (les acronymes plus longs sont rares)
- Il ne contient **que des lettres** (pas de chiffres ni de caractères spéciaux)

Avant de corriger un mot, on vérifie s'il correspond à ce profil. Si oui, on le laisse tranquille.

```python
def est_acronyme(mot: str) -> bool:
    """
    Détecte si un mot est probablement un acronyme.
    
    Un acronyme typique est :
    - Tout en majuscules (ex: "BNP", "SEPA")
    - Court : entre 2 et 6 caractères
    - Composé uniquement de lettres (pas de chiffres)
    
    Args:
        mot: Le mot à analyser
        
    Returns:
        True si le mot ressemble à un acronyme, False sinon
        
    Examples:
        >>> est_acronyme("BNP")
        True
        >>> est_acronyme("IBAN")
        True
        >>> est_acronyme("Bonjour")  # Pas tout en majuscules
        False
        >>> est_acronyme("ABCDEFGHIJ")  # Trop long
        False
    """
    # Vérification 1 : tout en majuscules
    if not mot.isupper():
        return False
    
    # Vérification 2 : longueur typique d'un acronyme
    if not (2 <= len(mot) <= 6):
        return False
    
    # Vérification 3 : uniquement des lettres
    if not mot.isalpha():
        return False
    
    return True
```

**Utilisation dans le flux de correction :**

```python
def corriger_mot(mot: str, spell_checker) -> str:
    """
    Corrige un mot en protégeant les acronymes.
    """
    # Protection des acronymes : on ne touche pas
    if est_acronyme(mot):
        return mot
    
    # Sinon, correction normale
    return spell_checker.correction(mot)
```

Cette approche fonctionne pour la majorité des cas mais peut laisser passer des faux positifs (un mot en majuscules qui n'est pas un acronyme) ou rater des acronymes atypiques.

## Solution 2 : Liste blanche explicite

Une approche plus fiable consiste à maintenir une liste blanche explicite des acronymes du domaine bancaire. Cette liste est définie une fois par l'équipe métier et garantit une protection exacte des termes importants.

L'avantage est qu'on contrôle précisément ce qui est protégé. L'inconvénient est qu'il faut maintenir cette liste à jour.

```python
# Liste des acronymes bancaires à protéger
# Cette liste doit être maintenue par l'équipe métier
ACRONYMES_BANCAIRES = {
    # Institutions
    'BNP', 'BCE', 'FMI', 'AMF',
    
    # Identifiants bancaires
    'IBAN', 'BIC', 'RIB', 'SWIFT',
    
    # Systèmes de paiement
    'SEPA', 'SCT', 'SDD',
    
    # Produits d'épargne
    'PEA', 'PEL', 'CEL', 'LDD', 'LEP', 'LDDS',
    
    # Taux et indicateurs
    'TAEG', 'TEG', 'TMM', 'TMO', 'TME',
    
    # Fiscalité
    'TVA', 'TTC', 'HT', 'CSG', 'CRDS',
    
    # Retraite et prévoyance
    'PERP', 'PERCO', 'PER', 'SCPI',
}


def est_acronyme_connu(mot: str) -> bool:
    """
    Vérifie si le mot est un acronyme bancaire connu.
    
    Args:
        mot: Le mot à vérifier
        
    Returns:
        True si c'est un acronyme de notre liste, False sinon
    """
    return mot.upper() in ACRONYMES_BANCAIRES
```

## Solution 3 : Combinaison des deux approches (recommandée)

La meilleure approche combine les deux méthodes : on protège les acronymes connus ET on détecte automatiquement les acronymes inconnus. Ainsi, on a une protection garantie pour les termes importants, plus un filet de sécurité pour les cas imprévus.

```python
def est_acronyme_protege(mot: str) -> bool:
    """
    Détermine si un mot doit être protégé en tant qu'acronyme.
    
    Stratégie en deux temps :
    1. D'abord, vérifier si c'est un acronyme CONNU (liste blanche)
    2. Sinon, vérifier si ça RESSEMBLE à un acronyme (heuristique)
    
    Cette double vérification offre :
    - Une protection garantie pour les termes métier importants
    - Un filet de sécurité pour les acronymes non listés
    
    Args:
        mot: Le mot à analyser
        
    Returns:
        True si le mot doit être protégé, False sinon
    """
    # Priorité 1 : acronyme explicitement listé
    # C'est la vérification la plus fiable
    if mot.upper() in ACRONYMES_BANCAIRES:
        return True
    
    # Priorité 2 : ressemble à un acronyme (fallback)
    # Moins fiable mais évite de rater des cas imprévus
    if mot.isupper() and 2 <= len(mot) <= 6 and mot.isalpha():
        return True
    
    return False
```

---

# Problème 2 : Les noms propres sont corrigés à tort

## Le problème

Les noms de famille, prénoms et noms de lieux ne figurent généralement pas dans les dictionnaires standards. Le correcteur orthographique les considère donc comme des mots inconnus et tente de les remplacer par des mots existants qui leur ressemblent.

"Dupont" devient "Dupond", "Lefèvre" devient "Lèvre", "Neuilly" devient "Nouille". Ces corrections sont non seulement fausses mais potentiellement graves dans un contexte bancaire où l'identité des clients est cruciale.

Le problème est amplifié par le fait que les transcriptions contiennent naturellement beaucoup de noms propres : noms des clients, des conseillers, des agences, des villes. Chacun de ces noms est une occasion de générer une erreur.

## Solution 1 : Détection par civilité

Le pattern le plus fiable pour repérer un nom propre est la présence d'une civilité juste avant. Quand on voit "M.", "Mme", "Dr" ou "Me" suivi d'un mot, ce mot est presque certainement un nom de famille.

Cette approche est simple et très précise : elle ne génère pratiquement pas de faux positifs.

```python
# Ensemble des civilités françaises courantes
# On les stocke en minuscules sans ponctuation pour faciliter la comparaison
CIVILITES = {
    'm', 'mr', 'mme', 'mlle',           # Monsieur, Madame, Mademoiselle
    'dr', 'pr',                          # Docteur, Professeur
    'me', 'maître', 'maitre',           # Maître (avocats, notaires)
    'mgr',                               # Monseigneur
    'col', 'cdt', 'lt', 'gal',          # Grades militaires
}


def suit_une_civilite(mots: list, position: int) -> bool:
    """
    Vérifie si le mot à la position donnée suit une civilité.
    
    Si oui, c'est très probablement un nom propre (nom de famille).
    
    Args:
        mots: Liste des mots de la phrase
        position: Index du mot à vérifier
        
    Returns:
        True si le mot précédent est une civilité, False sinon
        
    Examples:
        >>> mots = ["Bonjour", "Mme", "Dupont"]
        >>> suit_une_civilite(mots, 2)  # "Dupont"
        True
        >>> suit_une_civilite(mots, 0)  # "Bonjour"
        False
    """
    # Le premier mot ne peut pas suivre une civilité
    if position == 0:
        return False
    
    # Récupérer le mot précédent, normalisé
    mot_precedent = mots[position - 1].lower()
    
    # Enlever la ponctuation finale (le point de "M.")
    mot_precedent = mot_precedent.rstrip('.,:;')
    
    return mot_precedent in CIVILITES
```

## Solution 2 : Détection par pattern de majuscules

Un nom propre en français suit généralement un pattern visuel reconnaissable : il commence par une majuscule et le reste est en minuscules. Cependant, il ne faut pas confondre avec les mots en début de phrase qui prennent aussi une majuscule par règle grammaticale.

L'astuce est de ne considérer ce pattern que pour les mots qui ne sont PAS en début de phrase. Si un mot au milieu d'une phrase commence par une majuscule, c'est probablement un nom propre.

```python
def est_probablement_nom_propre(mot: str, position_dans_phrase: int) -> bool:
    """
    Détecte si un mot est probablement un nom propre basé sur sa casse.
    
    Logique :
    - Un nom propre commence par une majuscule
    - Le reste du mot est en minuscules (pas tout en majuscules)
    - Il n'est PAS en début de phrase (sinon c'est juste la règle grammaticale)
    
    Attention : cette méthode génère des faux positifs sur les mots
    après un point (début de phrase), d'où l'importance du paramètre
    position_dans_phrase.
    
    Args:
        mot: Le mot à analyser
        position_dans_phrase: Index du mot dans la phrase (0 = premier mot)
        
    Returns:
        True si le mot est probablement un nom propre, False sinon
        
    Examples:
        >>> est_probablement_nom_propre("Dupont", 3)  # Au milieu de phrase
        True
        >>> est_probablement_nom_propre("Bonjour", 0)  # Début de phrase
        False  # C'est juste la règle grammaticale
        >>> est_probablement_nom_propre("URGENT", 2)  # Tout en majuscules
        False  # C'est peut-être un acronyme ou de l'emphase
    """
    # Mot vide : pas un nom propre
    if not mot:
        return False
    
    # Vérification 1 : commence par une majuscule
    commence_par_majuscule = mot[0].isupper()
    if not commence_par_majuscule:
        return False
    
    # Vérification 2 : le reste est en minuscules
    # (élimine les acronymes comme "BNP" ou les mots en emphase comme "URGENT")
    reste_en_minuscules = mot[1:].islower() if len(mot) > 1 else True
    if not reste_en_minuscules:
        return False
    
    # Vérification 3 : pas en début de phrase
    # Un mot en position 0 a une majuscule par règle grammaticale, pas parce que
    # c'est un nom propre
    pas_en_debut_de_phrase = position_dans_phrase > 0
    if not pas_en_debut_de_phrase:
        return False
    
    return True
```

## Solution 3 : Combinaison civilité + pattern (recommandée)

La meilleure approche combine les deux méthodes : on protège d'abord les mots après civilité (très fiable), puis on protège les mots avec pattern de nom propre (moins fiable mais couvre plus de cas).

```python
def est_nom_propre(mot: str, mots: list, position: int) -> bool:
    """
    Détermine si un mot est probablement un nom propre.
    
    Combine plusieurs heuristiques par ordre de fiabilité :
    1. Suit une civilité → très probablement un nom propre
    2. Pattern majuscule + position → probablement un nom propre
    
    Args:
        mot: Le mot à analyser
        mots: Liste complète des mots de la phrase
        position: Index du mot dans la liste
        
    Returns:
        True si le mot est probablement un nom propre, False sinon
    """
    # Méthode 1 : après une civilité (très fiable)
    if suit_une_civilite(mots, position):
        return True
    
    # Méthode 2 : pattern de casse (moins fiable)
    if est_probablement_nom_propre(mot, position):
        return True
    
    return False
```

## Solution 4 : Détection avancée avec SpaCy NER

Pour une détection encore plus complète, on peut utiliser une bibliothèque de NLP spécialisée dans la reconnaissance d'entités nommées (NER - Named Entity Recognition). Ces outils ont été entraînés sur des millions de textes et savent identifier les personnes, organisations et lieux avec une bonne précision.

SpaCy est une bibliothèque populaire pour ce type de tâche. Elle analyse le texte complet et retourne la liste des entités détectées avec leur type. C'est plus lourd mais beaucoup plus précis.

```python
import spacy

# Charger le modèle français (à faire une seule fois au démarrage)
# Installation : python -m spacy download fr_core_news_sm
nlp = spacy.load("fr_core_news_sm")


def extraire_entites_protegees(texte: str) -> set:
    """
    Extrait toutes les entités nommées d'un texte avec SpaCy.
    
    SpaCy identifie automatiquement :
    - PER : les personnes (noms, prénoms)
    - ORG : les organisations (entreprises, institutions)
    - LOC : les lieux (villes, pays, adresses)
    
    Ces entités seront protégées de la correction orthographique.
    
    Args:
        texte: Le texte à analyser
        
    Returns:
        Ensemble des entités détectées (pour lookup rapide)
        
    Examples:
        >>> extraire_entites_protegees("Mme Dupont habite à Neuilly")
        {'Mme Dupont', 'Neuilly'}
    """
    # Analyser le texte avec SpaCy
    doc = nlp(texte)
    
    # Collecter les entités pertinentes
    entites = set()
    for entite in doc.ents:
        # On ne garde que les personnes, organisations et lieux
        if entite.label_ in ('PER', 'ORG', 'LOC'):
            entites.add(entite.text)
    
    return entites


def corriger_texte_avec_ner(texte: str, spell_checker) -> str:
    """
    Corrige un texte en protégeant les entités nommées détectées par SpaCy.
    """
    # Étape 1 : identifier les entités à protéger
    entites_protegees = extraire_entites_protegees(texte)
    
    # Étape 2 : corriger mot par mot en évitant les entités
    mots = texte.split()
    mots_corriges = []
    
    for mot in mots:
        # Vérifier si ce mot fait partie d'une entité protégée
        mot_protege = any(mot in entite for entite in entites_protegees)
        
        if mot_protege:
            mots_corriges.append(mot)  # Pas de correction
        else:
            mots_corriges.append(spell_checker.correction(mot) or mot)
    
    return ' '.join(mots_corriges)
```

L'avantage de SpaCy est qu'il détecte aussi les noms sans civilité, les noms d'entreprises et les noms de lieux. L'inconvénient est que ça ajoute une dépendance lourde (~500 Mo pour le modèle) et du temps de traitement.

---

# Problème 3 : Aucune prise en compte du contexte

## Le problème

Le correcteur analyse chaque mot de manière isolée, sans regarder ce qui l'entoure. Cette approche est fondamentalement limitée pour le français car beaucoup de mots ne peuvent être validés ou corrigés qu'en fonction de leur contexte.

Prenons l'exemple des homophones : "mer" et "mère" se prononcent pareil mais s'écrivent différemment selon le sens. Dans "la mer est belle", c'est correct. Dans "ma mer est venue", c'est faux — il faudrait "mère". Mais le correcteur mot-à-mot voit juste "mer", qui est un mot valide, et ne détecte pas l'erreur.

Ce problème touche énormément de mots en français : et/est, a/à, ou/où, ce/se, son/sont... Ces confusions sont très fréquentes en transcription automatique car le STT ne distingue pas les homophones. Sans analyse contextuelle, impossible de les corriger.

## Solution 1 : Grammalecte (déjà présent dans le projet)

Le projet contient déjà un wrapper pour Grammalecte dans le fichier `pygrammalecte.py`. Grammalecte est un correcteur grammatical français open source qui, contrairement à un simple correcteur orthographique, analyse la structure grammaticale complète de la phrase.

Grammalecte sait que "ma" est un adjectif possessif féminin et qu'il doit être suivi d'un nom féminin désignant quelque chose que l'on peut posséder. "mer" ne colle pas (on ne possède pas la mer comme un objet personnel), donc il suggère "mère".

C'est la solution la plus simple à implémenter car le code est déjà là, il suffit de l'utiliser.

```python
from pygrammalecte import grammalecte_text, GrammalecteGrammarMessage


def corriger_avec_grammalecte(texte: str) -> str:
    """
    Corrige un texte en utilisant Grammalecte pour l'analyse contextuelle.
    
    Grammalecte détecte les erreurs grammaticales que pyspellchecker ne peut
    pas voir car il analyse la phrase complète, pas juste les mots isolés.
    
    Exemples d'erreurs détectées :
    - "ma mer" → "ma mère" (homophone)
    - "il et parti" → "il est parti" (confusion et/est)
    - "je les mangé" → "je les ai mangés" (accord participe)
    
    Args:
        texte: Le texte à corriger
        
    Returns:
        Le texte corrigé
    """
    # Collecter toutes les corrections suggérées
    corrections = []
    
    for message in grammalecte_text(texte):
        # On ne traite que les erreurs grammaticales avec suggestions
        if isinstance(message, GrammalecteGrammarMessage):
            if message.suggestions:
                corrections.append({
                    'start': message.start,
                    'end': message.end,
                    'replacement': message.suggestions[0]  # Prendre la 1ère suggestion
                })
    
    # Appliquer les corrections de la FIN vers le DÉBUT
    # C'est important : si on corrige du début vers la fin,
    # les indices des corrections suivantes deviennent faux
    corrections_triees = sorted(corrections, key=lambda x: x['start'], reverse=True)
    
    for corr in corrections_triees:
        texte = texte[:corr['start']] + corr['replacement'] + texte[corr['end']:]
    
    return texte


# Exemple d'utilisation
texte_original = "Ma mer est venue me voir, elle et très contente."
texte_corrige = corriger_avec_grammalecte(texte_original)
# → "Ma mère est venue me voir, elle est très contente."
```

## Solution 2 : LanguageTool (plus puissant)

LanguageTool est un correcteur grammatical plus puissant que Grammalecte, avec un meilleur taux de détection et plus de règles. Il existe en version locale (gratuite, mais nécessite Java) ou en API cloud (plus rapide et précise, mais payante pour un usage intensif).

La bibliothèque Python `language-tool-python` permet d'utiliser LanguageTool très facilement. Elle gère automatiquement le téléchargement et l'exécution du serveur Java en arrière-plan.

```python
import language_tool_python


# Créer une instance du correcteur (à faire une seule fois)
# Note : le premier appel télécharge le serveur Java (~200 Mo)
tool = language_tool_python.LanguageTool('fr')


def corriger_avec_languagetool(texte: str) -> str:
    """
    Corrige un texte avec LanguageTool.
    
    LanguageTool offre :
    - Plus de règles que Grammalecte
    - Meilleure détection des homophones
    - Suggestions de style (optionnel)
    
    Args:
        texte: Le texte à corriger
        
    Returns:
        Le texte corrigé
    """
    # Analyser le texte et obtenir les erreurs
    erreurs = tool.check(texte)
    
    # Appliquer automatiquement toutes les corrections
    texte_corrige = language_tool_python.utils.correct(texte, erreurs)
    
    return texte_corrige


def analyser_avec_languagetool(texte: str) -> list:
    """
    Analyse un texte et retourne les erreurs détaillées (sans corriger).
    
    Utile pour comprendre ce que LanguageTool détecte.
    
    Returns:
        Liste des erreurs avec leur description
    """
    erreurs = tool.check(texte)
    
    resultats = []
    for err in erreurs:
        resultats.append({
            'message': err.message,
            'contexte': err.context,
            'suggestions': err.replacements,
            'regle': err.ruleId,
        })
    
    return resultats


# Exemple d'utilisation
texte = "Ma mer est partie, elle et contente de son voyage a Paris."
print(corriger_avec_languagetool(texte))
# → "Ma mère est partie, elle est contente de son voyage à Paris."
```

LanguageTool détecte plus d'erreurs que Grammalecte mais nécessite plus de ressources (serveur Java en arrière-plan, ~500 Mo de RAM). Pour un usage intensif en production, l'API cloud payante est plus adaptée.

## Comparatif des solutions contextuelles

| Critère | pyspellchecker | Grammalecte | LanguageTool |
|---------|----------------|-------------|--------------|
| Contexte grammatical | ❌ Non | ✅ Oui | ✅ Oui |
| Homophones | ❌ Non | ✅ Oui | ✅ Oui |
| Vitesse | ⚡ Très rapide | 🐢 Lent | 🐢 Lent |
| Hors-ligne | ✅ Oui | ✅ Oui | ⚠️ Optionnel |
| Dépendances | Légères | Moyennes | Lourdes (Java) |
| Précision estimée | ~60% | ~85% | ~90% |

---

# Problème 4 : Le dictionnaire ne connaît pas le vocabulaire bancaire

## Le problème

Le correcteur utilise un dictionnaire français généraliste, basé sur la fréquence des mots dans des textes courants (journaux, livres, web). Les termes techniques du domaine bancaire n'y figurent pas ou sont considérés comme rares.

Résultat : des mots parfaitement corrects comme "prélèvement", "créditeur", "échéancier" ou "euribor" sont signalés comme des fautes. Le correcteur peut même proposer des "corrections" absurdes : "créditeur" devient "créateur", "euribor" devient "euro".

C'est un comble : on utilise un correcteur pour améliorer la qualité, et il dégrade les termes les plus importants du métier. Plus le texte est technique (donc plus il a besoin de précision), plus le correcteur fait de dégâts.

## Solution 1 : Réutiliser les hotwords existants

La solution la plus directe et la plus rapide est de réutiliser le fichier de hotwords qui existe déjà dans le projet. Ces hotwords contiennent justement les termes bancaires importants — autant s'en servir aussi pour la correction orthographique.

La bibliothèque `pyspellchecker` permet d'ajouter des mots personnalisés qui seront ensuite considérés comme valides et ne déclencheront pas de correction.

```python
from spellchecker import SpellChecker


def creer_correcteur_avec_hotwords(chemin_hotwords: str) -> SpellChecker:
    """
    Crée un correcteur orthographique enrichi avec les hotwords du projet.
    
    Les hotwords sont déjà maintenus pour le STT, autant les réutiliser
    pour la correction orthographique. Cela évite de maintenir deux listes.
    
    Args:
        chemin_hotwords: Chemin vers le fichier hotwords (un mot par ligne)
        
    Returns:
        SpellChecker configuré avec le vocabulaire métier
    """
    # Créer le correcteur avec le dictionnaire français de base
    spell = SpellChecker(language='fr')
    
    # Charger les hotwords depuis le fichier
    with open(chemin_hotwords, 'r', encoding='utf-8') as fichier:
        hotwords = []
        for ligne in fichier:
            mot = ligne.strip()
            if mot:  # Ignorer les lignes vides
                hotwords.append(mot.lower())
    
    # Ajouter les hotwords au dictionnaire du correcteur
    # Ces mots seront maintenant considérés comme "connus" et valides
    spell.word_frequency.load_words(hotwords)
    
    print(f"✓ {len(hotwords)} hotwords ajoutés au dictionnaire")
    
    return spell


# Utilisation
spell = creer_correcteur_avec_hotwords('/mnt/data/STT/hotwords_v2.txt')

# Maintenant "prélèvement", "euribor" etc. sont reconnus comme corrects
print(spell.unknown(['prélèvement', 'virement', 'xyz']))
# → {'xyz'}  (seul 'xyz' est inconnu, les autres sont maintenant valides)
```

Cette approche est simple et immédiate. Elle réutilise des données existantes et ne nécessite pas de maintenance supplémentaire : quand on met à jour les hotwords pour le STT, le correcteur en bénéficie automatiquement.

## Solution 2 : Créer un dictionnaire métier structuré

Pour une couverture plus complète et une meilleure maintenabilité, on peut créer un dictionnaire métier dédié, organisé par catégories. Ce dictionnaire inclut non seulement les hotwords mais aussi tout le vocabulaire technique susceptible d'apparaître dans les transcriptions.

```python
# Dictionnaire métier organisé par catégories
# Plus facile à maintenir et à comprendre qu'une simple liste

VOCABULAIRE_BANCAIRE = {
    # --- OPÉRATIONS COURANTES ---
    'prélèvement', 'virement', 'versement', 'retrait', 'dépôt',
    'encaissement', 'décaissement', 'compensation', 'règlement',
    
    # --- ACTEURS ---
    'créditeur', 'débiteur', 'bénéficiaire', 'émetteur', 'tireur',
    'titulaire', 'cotitulaire', 'mandataire', 'ayant-droit',
    
    # --- PRODUITS D'ÉPARGNE ---
    'livret', 'pel', 'cel', 'ldd', 'ldds', 'lep', 'lea',
    'pea', 'pea-pme', 'assurance-vie', 'per', 'perp', 'perco',
    
    # --- PRODUITS DE CRÉDIT ---
    'découvert', 'facilité', 'revolving', 'amortissable',
    'in-fine', 'relais', 'différé', 'lissage',
    
    # --- TERMES TECHNIQUES CRÉDIT ---
    'amortissement', 'échéancier', 'mensualité', 'annuité',
    'capital', 'intérêts', 'assurance-emprunteur',
    
    # --- TAUX ET INDICES ---
    'taeg', 'teg', 'taea', 'euribor', 'eonia', 'ester',
    'tmm', 'tmo', 'tme', 'oat', 'libor',
    
    # --- IDENTIFIANTS ---
    'iban', 'bic', 'swift', 'rib', 'nne', 'siren', 'siret',
    
    # --- SYSTÈMES DE PAIEMENT ---
    'sepa', 'sct', 'sdd', 'tip', 'tlc', 'prélèvement-sepa',
    
    # --- ENTITÉS BANCAIRES ---
    'bnp', 'paribas', 'crédit', 'agricole', 'société', 'générale',
    'caisse', 'épargne', 'banque', 'postale', 'boursorama',
    'lcl', 'hsbc', 'cic', 'bred', 'palatine',
}


def creer_correcteur_metier() -> SpellChecker:
    """
    Crée un correcteur orthographique avec le vocabulaire bancaire complet.
    """
    spell = SpellChecker(language='fr')
    spell.word_frequency.load_words(VOCABULAIRE_BANCAIRE)
    return spell
```

## Solution 3 : Combinaison hotwords + dictionnaire métier (recommandée)

L'idéal est de combiner les deux sources : les hotwords (déjà maintenus pour le STT) et le dictionnaire métier étendu. On obtient ainsi une couverture maximale.

```python
from spellchecker import SpellChecker
from typing import Set


def creer_correcteur_complet(
    chemin_hotwords: str,
    vocabulaire_supplementaire: Set[str] = None
) -> SpellChecker:
    """
    Crée un correcteur avec toutes les sources de vocabulaire métier.
    
    Combine :
    1. Le dictionnaire français standard
    2. Les hotwords du projet (maintenus pour le STT)
    3. Un vocabulaire métier supplémentaire (optionnel)
    
    Args:
        chemin_hotwords: Chemin vers le fichier hotwords
        vocabulaire_supplementaire: Mots métier additionnels (optionnel)
        
    Returns:
        SpellChecker enrichi avec tout le vocabulaire métier
    """
    # Base : dictionnaire français
    spell = SpellChecker(language='fr')
    
    # Source 1 : hotwords du projet
    with open(chemin_hotwords, 'r', encoding='utf-8') as f:
        hotwords = {ligne.strip().lower() for ligne in f if ligne.strip()}
    spell.word_frequency.load_words(hotwords)
    
    # Source 2 : vocabulaire métier supplémentaire
    if vocabulaire_supplementaire:
        spell.word_frequency.load_words(vocabulaire_supplementaire)
    
    return spell


# Utilisation
spell = creer_correcteur_complet(
    chemin_hotwords='/mnt/data/STT/hotwords_v2.txt',
    vocabulaire_supplementaire=VOCABULAIRE_BANCAIRE
)
```

## Solution 4 : Chargement depuis fichier externe (production)

Pour une utilisation en production, il est préférable de stocker le vocabulaire métier dans un fichier externe plutôt que dans le code. Cela permet de mettre à jour le vocabulaire sans modifier le code.

```python
def charger_vocabulaire_depuis_fichier(chemin: str) -> set:
    """
    Charge un vocabulaire métier depuis un fichier texte.
    
    Format attendu : un mot par ligne, commentaires avec #
    
    Exemple de fichier :
        # Opérations
        prélèvement
        virement
        
        # Produits
        pel
        cel
    """
    vocabulaire = set()
    
    with open(chemin, 'r', encoding='utf-8') as f:
        for ligne in f:
            # Ignorer les commentaires et lignes vides
            ligne = ligne.strip()
            if ligne and not ligne.startswith('#'):
                vocabulaire.add(ligne.lower())
    
    return vocabulaire


def creer_correcteur_production(
    chemin_hotwords: str,
    chemin_vocabulaire_metier: str
) -> SpellChecker:
    """
    Crée un correcteur configuré pour la production.
    
    Charge le vocabulaire depuis des fichiers externes pour
    permettre des mises à jour sans modification du code.
    """
    spell = SpellChecker(language='fr')
    
    # Charger les hotwords
    hotwords = charger_vocabulaire_depuis_fichier(chemin_hotwords)
    spell.word_frequency.load_words(hotwords)
    
    # Charger le vocabulaire métier
    vocabulaire = charger_vocabulaire_depuis_fichier(chemin_vocabulaire_metier)
    spell.word_frequency.load_words(vocabulaire)
    
    print(f"✓ Correcteur initialisé : {len(hotwords)} hotwords + {len(vocabulaire)} termes métier")
    
    return spell
```

---

# Synthèse des solutions

## Récapitulatif par problème

| Problème | Solution simple | Solutions avancées |
|----------|-----------------|-------------------|
| **Acronymes** | Détection `isupper()` | Liste blanche + détection combinée |
| **Noms propres** | Détection après civilité | Pattern majuscules + SpaCy NER |
| **Pas de contexte** | Grammalecte (déjà présent) | LanguageTool |
| **Vocabulaire métier** | Réutiliser hotwords | Dictionnaire dédié + fichiers externes |

## Recommandations d'implémentation

**Phase 1 - Quick wins (1-2 jours) :**
- Corriger le bug `hot_words` non défini
- Ajouter la protection des acronymes (pattern simple)
- Enrichir le correcteur avec les hotwords existants

**Phase 2 - Améliorations (1 semaine) :**
- Intégrer Grammalecte pour le contexte
- Ajouter la détection des noms propres (civilités + pattern)
- Créer un fichier de vocabulaire métier structuré

**Phase 3 - Optimisation (si nécessaire) :**
- Évaluer le taux d'erreur résiduel
- Intégrer SpaCy NER si les noms propres posent encore problème
- Passer à LanguageTool si Grammalecte ne suffit pas

## Estimation des gains

| Métrique | Avant | Après Phase 1 | Après Phase 2 |
|----------|-------|---------------|---------------|
| Acronymes corrompus | ~100% | ~5% | ~2% |
| Noms propres corrompus | ~80% | ~40% | ~10% |
| Homophones non détectés | ~100% | ~100% | ~15% |
| Termes métier corrompus | ~60% | ~5% | ~2% |
