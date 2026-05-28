# Luna — Intelligence Artificielle Familiale

Luna est une IA personnelle de type Jarvis, conçue pour votre famille avec un système de priorité strict.

## Hiérarchie

| Priorité | Rôle | Accès |
|----------|------|-------|
| 1 | **Propriétaire** (vous) | Tout — configuration, gestion des comptes, accès complet |
| 2 | **Épouse** | Toutes les fonctions assistant, contenu adulte, finances |
| 3 | **Fille** | Contenu adapté à l'âge, mode éducatif, pas de config système |

## Installation

```bash
# 1. Cloner et entrer dans le dossier
cd Luna-

# 2. Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer la clé API
cp .env.example .env
# Éditez .env et ajoutez votre clé Anthropic

# 5. Configuration initiale (une seule fois)
python setup_wizard.py

# 6. Lancer Luna
python main.py
```

## Dépendances vocales (optionnel)

Pour activer la synthèse vocale et la reconnaissance vocale :

```bash
# Linux
sudo apt-get install portaudio19-dev espeak
pip install pyttsx3 SpeechRecognition pyaudio

# Mac
brew install portaudio espeak
pip install pyttsx3 SpeechRecognition pyaudio
```

Luna fonctionne parfaitement en mode texte si ces dépendances ne sont pas disponibles.

## Commandes

| Commande | Description |
|----------|-------------|
| `/aide` | Affiche l'aide complète |
| `/note <texte>` | Sauvegarde une note longue durée |
| `/notes` | Affiche vos notes |
| `/effacer` | Efface l'historique de cette session |
| `/utilisateurs` | Liste les comptes (propriétaire seulement) |
| `/quitter` | Quitter Luna |

### Contrôle iOS

| Commande | Description |
|----------|-------------|
| `/ios <id>` | Déclenche un raccourci sur votre iPhone |
| `/ios <uid> <id>` | Contrôle l'iPhone d'un membre (propriétaire) |
| `/appareils` | Liste les iPhones enregistrés + statut |
| `/raccourcis` | Affiche tous les raccourcis disponibles |
| `/position [uid]` | Dernière position GPS reçue |

**Raccourcis intégrés :** `dnd_on`, `dnd_off`, `volume_up`, `volume_down`, `play_music`, `alarm_morning`, `send_location`, `take_photo`, `low_power`, `wifi_on`, `wifi_off`, `lock_daughter`

Voir **`shortcuts_ios/README_RACCOURCIS.md`** pour la procédure d'installation iOS.

## Confidentialité

- Les données sont stockées localement dans `data/`
- `data/users/users.json` contient les comptes (PINs hashés en SHA-256)
- `data/conversations/` contient l'historique par utilisateur
- Ces fichiers sont dans `.gitignore` et ne sont jamais poussés sur GitHub

## Obtenir une clé API Anthropic

Créez un compte sur [console.anthropic.com](https://console.anthropic.com) et générez une clé API.
