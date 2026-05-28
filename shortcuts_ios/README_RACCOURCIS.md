# Raccourcis iOS pour Luna

Installez ces Raccourcis sur chaque iPhone de la famille pour que Luna puisse les contrôler.

---

## Méthode de communication recommandée

Luna dispose de **3 façons** de contacter un iPhone, par ordre de priorité :

| Méthode | Avantages | Prérequis |
|---------|-----------|-----------|
| **HTTP local (WiFi)** | Rapide, fiable, bidirectionnel | iPhone et Luna sur le même WiFi |
| **ntfy.sh** | Fonctionne hors WiFi, 4G/5G | App ntfy installée sur iPhone |
| **macOS URL** | Simple | Luna tourne sur un Mac |

---

## 1. Raccourci "Luna Serveur" (iPhone → reçoit les commandes)

> Ce raccourci est le cœur du système. Il tourne en tâche de fond et reçoit les commandes de Luna.

**Instructions (iOS 16+) :**

1. Ouvrez **Raccourcis** → `+` (nouveau raccourci)
2. Ajoutez l'action **"Recevoir une requête web"** (cherchez "web")
3. Ajoutez **"Répéter"** en boucle continue
4. Dans la boucle : ajoutez **"Exécuter le raccourci"** avec le nom reçu dans la requête
5. Nommez le raccourci : `Luna Serveur`
6. Dans les réglages du raccourci → **"Activer dans l'app"** → activez

**Configuration dans Luna :**
```
/ios owner wifi 192.168.1.XX     ← remplacez par l'IP de l'iPhone
```
Ou éditez `config/ios_config.json` :
```json
"devices": {
  "owner": { "ip": "192.168.1.XX" }
}
```

---

## 2. Raccourcis individuels à créer sur chaque iPhone

### Luna DND ON — Active Ne Pas Déranger
1. Action : **"Régler le mode Ne pas déranger"** → Activé
2. Nommer : `Luna DND ON`

### Luna DND OFF — Désactive Ne Pas Déranger
1. Action : **"Régler le mode Ne pas déranger"** → Désactivé
2. Nommer : `Luna DND OFF`

### Luna Volume+
1. Action : **"Régler le volume"** → 100%
2. Nommer : `Luna Volume+`

### Luna Volume-
1. Action : **"Régler le volume"** → 20%
2. Nommer : `Luna Volume-`

### Luna Musique
1. Action : **"Lire/Mettre en pause"** dans Musique
2. Nommer : `Luna Musique`

### Luna Réveil
1. Action : **"Créer une alarme"** → heure depuis l'entrée du raccourci
2. Nommer : `Luna Réveil`

### Luna Position — Envoie la GPS à Luna
1. Action : **"Obtenir l'emplacement actuel"**
2. Action : **"Obtenir les détails de l'emplacement"** → Adresse
3. Action : **"URL"** → `http://IP_LUNA:7777/location`
4. Action : **"Obtenir le contenu de l'URL"** (méthode POST) avec :
   ```json
   {
     "user_id": "owner",
     "lat": [Latitude],
     "lon": [Longitude],
     "address": [Adresse]
   }
   ```
5. Nommer : `Luna Position`

### Luna Éco — Mode économie d'énergie
1. Action : **"Régler le mode économie d'énergie"** → Activé
2. Nommer : `Luna Éco`

### Luna WiFi ON / OFF
1. Action : **"Régler le Wi-Fi"** → Activé / Désactivé
2. Nommer : `Luna WiFi ON` ou `Luna WiFi OFF`

---

## 3. Méthode ntfy.sh (sans WiFi local)

1. Installez l'app **ntfy** depuis l'App Store
2. Abonnez-vous au topic : `luna-VOTRE_NOM_UNIQUE` (choisissez quelque chose de secret)
3. Dans Luna, configurez :
   ```
   # Éditez config/ios_config.json
   "ntfy_topic": "luna-VOTRE_NOM_UNIQUE"
   ```
4. Créez une **Automation** dans Raccourcis :
   - Déclencheur : **"App"** → ntfy → Notification reçue
   - Action : **"Obtenir le texte de la notification"**
   - Action : **"Exécuter le raccourci"** avec le nom extrait du JSON

---

## 4. Raccourci "Luna Siri" (Siri → Luna)

Permet de dicter une commande à Siri qui la transmet à Luna.

1. Créez un raccourci
2. Action : **"Demander une entrée"** → "Que voulez-vous dire à Luna ?"
3. Action : **"URL"** → `http://IP_LUNA:7777/siri`
4. Action : **"Obtenir le contenu de l'URL"** (POST) avec :
   ```json
   { "user_id": "owner", "text": [Entrée] }
   ```
5. Nommez : `Luna Siri`
6. Ajoutez à Siri : dites "Luna écoute" pour déclencher

---

## Trouver l'IP locale de Luna

Lancez Luna et regardez le message au démarrage :
```
📱 Serveur iOS actif — Les iPhones peuvent joindre Luna sur 192.168.1.XX:7777
```

Ou dans Luna, tapez : `/appareils`
