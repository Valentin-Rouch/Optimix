# Optimix

> **Outil d’optimisation de portefeuilles fondé sur le modèle de Black–Litterman, développé pour l'entreprise ERES Gestion.**

---

## Présentation

**Optimix** est une application web interactive permettant d’optimiser la composition de portefeuilles sous contraintes réglementaires et opérationnelles, en intégrant à la fois les **données de marché** et les **convictions des gérants**.

Ce projet a été réalisé au sein d’**ERES Gestion** dans le cadre d’un stage d’application à l’**ENSAE Paris**.

Optimix s’appuie sur le **modèle de Black–Litterman** pour concilier :
- les **rendements d’équilibre** issus du marché
- les **vues subjectives** des gérants

L’outil permet ainsi de produire des allocations optimales conformes aux **contraintes réglementaires, prospectus et internes**, tout en offrant une **interface intuitive**.

---

## Fonctionnalités principales

### Modélisation Black–Litterman
- Implémentation complète des quatre briques du modèle :
  1. **Modèle de référence**
  2. **Équilibre général (marché)**
  3. **Création de vues**
  4. **Agrégation (Theil & Goldberg)**
- Gestion des **vues relatives** (ex. : Actions Europe vs Actions US)
- Pondération automatique selon le niveau de confiance (matrice Ω)

### Optimisation sous contraintes
- Optimisation quadratique via **cvxpy** et **SCIP**
- Respect de plus de **40 contraintes réglementaires et prospectus**
- Intégration :
  - des contraintes d’exposition (actions, obligations, devises, etc.)
  - des contraintes d’environnement (ISR, FIA, UCITS…)
  - des contraintes de fonctionnalité (liquidité, concentration)

### Interface utilisateur (Dash)
- Interface web développée avec **Dash** (framework Python)
- Saisie des **vues** et des **paramètres**
- Visualisation des résultats

  <img width="959" height="478" alt="interface_optim_2" src="https://github.com/user-attachments/assets/49638951-a583-4036-bc6d-1b5c79f82b47" />


### Backtests & validation
- Backtests réalisés sur **7 fonds ERES** (2023–2025)
- Comparaison entre les allocations du modèle et celles décidées en comité d’allocation stratégique (CAST)
- Analyse de la **sur/sous-performance** du modèle par rapport aux gérants

---

## Fondements théoriques

Le modèle repose sur une approche bayésienne combinant les rendements d’équilibre du marché et les vues exprimées par les gérants :

μ_BL = [ (τΣ)^(-1) + PᵀΩ^(-1)P ]^(-1) [ (τΣ)^(-1)π + PᵀΩ^(-1)Q ]

avec :
- \(π\) : rendements d’équilibre du marché  
- \(P, Q, Ω\) : matrices des vues et incertitudes  
- \(Σ\) : matrice de covariance  
- \(τ\) : paramètre global d’incertitude

L’optimisation repose sur la maximisation de la fonction d’utilité :

G(w) = wᵀμ_BL − (δ / 2) * wᵀΣ_BLw

sous l’ensemble des contraintes réglementaires et fonctionnelles.

---

## Exemple d’utilisation

1. Sélectionner le **fonds** à optimiser  
2. Choisir la **date de prise en compte** (fenêtre historique)  
3. Définir les **vues relatives** via les menus déroulants  
4. Régler le **paramètre τ** (incertitude globale)  
5. Cliquer sur **« Optimiser »** pour lancer le calcul  
6. Visualiser et exporter le portefeuille optimal au format `.xlsx`

---

## Résultats clés

- L’outil produit des **allocations cohérentes** avec celles des gérants  
- Sur un horizon de **3 mois**, le modèle surperforme dans **5 cas sur 7**  
- Les écarts résiduels sont liés à des **événements exogènes** ou à la **fréquence trimestrielle** des vues  
- Le modèle démontre une **robustesse et une pertinence opérationnelle** dans un cadre de gestion réel

---

## Technologies utilisées

