"""
LOGIQUE DES COEFFICIENTS - MODÈLE P(NON-DÉFAUT)
===============================================

ATTENTION : Les coefficients de ce modèle ont été calibrés pour prédire
P(NON-DÉFAUT), pas P(défaut). Cette logique est INVERSÉE par rapport à
l'interprétation habituelle.

Formule utilisée :
    PDO = 1 - σ(z) où z = intercept + Σ(coefficients × indicatrices)
    
    Équivalent à : PDO = σ(-z)

Interprétation des coefficients :
- Coefficient POSITIF → augmente P(non-défaut) → DIMINUE le risque (PDO)
- Coefficient NÉGATIF → diminue P(non-défaut) → AUGMENTE le risque (PDO)
- Modalité de RÉFÉRENCE (coeff=0) → RISQUE MAXIMUM (pas de protection)

Exemples :
- reboot_score_char2="1" (coeff=+3.924) : score REBOOT le plus bas, PROTECTEUR
- reboot_score_char2="9" (coeff=0, référence) : score REBOOT le plus élevé, RISQUÉ

Profils types :
- Entreprise RISQUÉE : toutes modalités de référence → sum_coeffs ≈ -3.864 → PDO ≈ 98%
- Entreprise SAINE : toutes modalités protectrices → sum_coeffs ≈ +12 → PDO ≈ 0.01%
"""
