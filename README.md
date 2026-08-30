# ✂️ GIMP 3 — AI Background Removal Plugin
 
**Ultra-stable GIMP 3.0 plugin for automatic AI background removal, powered by [`rembg`](https://github.com/danielgatis/rembg).**
 
Unlike other plugins, this script runs the AI model in a **separate subprocess** instead of inside GIMP's own memory space — so your image editor will never crash, no matter what happens. It automatically locates a suitable Python installation on your system, includes an animated progress bar, and shows smart error dialogs to help you fix missing dependencies quickly.
 
🇬🇧 [English](#-english) · 🇫🇷 [Français](#-français)
 
---
 
## 🇬🇧 English
 
### Features
 
- 🛡️ **Crash-proof** — the AI model runs outside GIMP's process
- 🔍 **Automatic Python detection** — no configuration file to edit, the plugin finds a working Python installation on its own
- 📊 **Live progress bar** while the image is processed
- 🩺 **Smart error dialogs** if a dependency is missing or misconfigured
- 💻 **CPU-only mode** — works on any machine, no GPU required
### Requirements
 
| Requirement | Version |
|---|---|
| GIMP | 3.0+ |
| Python | 3.9+ (with `pip`), installed **separately from GIMP** |
| OS | Windows (see notes below for macOS/Linux) |
 
> ℹ️ GIMP 3 ships with its own internal Python interpreter (used to run this very plugin). That internal copy is intentionally **never used** to run the AI model — the plugin always looks for a separate, regular Python installation on your system instead.
 
### Installation
 
#### Step 1 — Install Python
 
1. Download Python from [python.org/downloads](https://www.python.org/downloads/).
2. Run the installer.
3. ✅ **Recommended:** on the first installation screen, check the box **"Add python.exe to PATH"** before clicking **Install Now**. This isn't strictly required anymore (see below), but it keeps things simple and lets you use `pip`/`python` directly from the Command Prompt.
4. If GIMP is already open, restart it after installing Python so it picks up the new installation.
#### Step 2 — Install the AI engine
 
This plugin uses standard **CPU mode** for universal hardware compatibility — no GPU required.
 
1. Open the Windows **Command Prompt** (search `cmd` in the Start menu).
2. Install the `rembg` library:
```cmd
   pip install "rembg[cpu,cli]"
```
3. *(Recommended)* Pre-download the AI model (~40 MB) so your first run inside GIMP is fast:
```cmd
   python -c "from rembg import new_session; new_session('u2netp')"
```
 
#### Step 3 — Install the GIMP plugin
 
1. Download `ia_detourage.py` from this repository.
2. Open **GIMP 3.0** and go to **Edit ▸ Preferences ▸ Folders ▸ Plug-ins**.
3. Copy `ia_detourage.py` into your personal plug-ins folder (usually `C:\Users\<YourName>\AppData\Roaming\GIMP\3.0\plug-ins`).
4. Restart GIMP.
**That's it — no file to edit, no path to configure.** The plugin is now available under:
**Image ▸ Layer ▸ Transparency ▸ Remove Background (AI)...**
 
### Usage
 
1. Open or select the layer you want to process.
2. Go to **Image ▸ Layer ▸ Transparency ▸ Remove Background (AI)...**.
3. On the very first run, the plugin searches your system for a valid Python installation with `rembg` installed — this adds a few extra seconds one time only; the result is then cached.
4. Wait for the progress bar — processing takes roughly **40 seconds per image**, depending on your CPU.
5. The background is automatically converted to transparency once processing completes.
### How the automatic Python detection works
 
Older versions of this plugin required manually editing the `.py` file to hardcode a Python path, because GIMP 3 bundles its own internal `python.exe` which would otherwise get picked up by mistake (it doesn't have `rembg` installed, and never will). This version detects a valid, separate Python installation on its own, trying several independent methods in order until one works — so it doesn't rely on a single fragile mechanism (like an outdated system PATH):
 
1. **PATH lookup** (`where`/`which python`) — works most of the time, but can fail if GIMP was started before Python was added to the system PATH.
2. **The `py` launcher** (Windows) — reads Python installations directly from the Windows registry, independent of PATH.
3. **Direct registry lookup** (Windows) — same idea, queried directly as a fallback.
4. **Disk scan** (Windows) — checks standard install locations (`AppData\Local\Programs\Python`, `Program Files`) as a last resort.
Each candidate is actually tested (`import rembg`) before being accepted — the plugin never guesses. The GIMP-internal Python is always explicitly excluded. The result is cached (in GIMP's own config folder) so this search only runs once; if that cached Python later becomes invalid (e.g. `rembg` was uninstalled), the cache is automatically cleared and the plugin searches again on the next run — no manual cache-clearing needed.
 
### Troubleshooting
 
| Symptom | Likely cause | Fix |
|---|---|---|
| Plugin doesn't appear in the menu | Wrong plug-ins folder, or GIMP not restarted | Double-check the folder path in Step 3 and restart GIMP |
| "Module IA introuvable" error | No Python installation with `rembg` could be found automatically | Open Command Prompt and run `pip install "rembg[cpu,cli]"`, then simply try the plugin again — no file editing needed |
| Detection picks a stale/invalid Python | The system changed since the last successful detection (Python moved, uninstalled, etc.) | Just run the plugin again — the invalid entry is detected and a fresh search happens automatically |
| First run is very slow | AI model not pre-downloaded, or first-time Python detection | Run the `new_session('u2netp')` command from Step 2 to pre-download the model; the one-time detection delay is normal and only happens once |
 
### macOS / Linux — untested adaptation notes
 
> ⚠️ **These instructions are only a proposal.** This plugin was written and tested on Windows only. The automatic detection includes a `which python3` fallback that should work on macOS/Linux, but the `py` launcher, registry lookup, and disk-scan strategies are Windows-specific and simply skip themselves on other platforms — detection there relies on PATH alone, so keep Python properly on your PATH. Expect to debug paths and permissions yourself.
 
- **Python & pip**: macOS and most Linux distributions already ship with Python 3. Check with `python3 --version` in a terminal. If missing, install it via [python.org](https://www.python.org/downloads/) (macOS) or your package manager, e.g. `sudo apt install python3 python3-pip` (Debian/Ubuntu).
- **Installing rembg**: use `pip3` instead of `pip` if both Python 2 and 3 are present:
```bash
  pip3 install "rembg[cpu,cli]"
```
- **Pre-downloading the model**:
```bash
  python3 -c "from rembg import new_session; new_session('u2netp')"
```
- **Plug-ins folder** — this is the part most likely to need adjustment:
  - **macOS**: typically `~/Library/Application Support/GIMP/3.0/plug-ins`
  - **Linux**: typically `~/.config/GIMP/3.0/plug-ins`
  - You can confirm the exact path from inside GIMP via **Edit ▸ Preferences ▸ Folders ▸ Plug-ins**.
- **Script permissions**: on macOS/Linux, the plugin file may need to be made executable:
```bash
  chmod +x ia_detourage.py
```
- **Shebang line**: the script already starts with `#!/usr/bin/env python3`, which should be enough for GIMP to detect it correctly outside Windows.
If you get it working reliably on macOS or Linux, contributions/PRs documenting the exact steps are welcome.
 
### License
 
*license MIT*
 
---
 
## 🇫🇷 Français
 
### Fonctionnalités
 
- 🛡️ **Anti-crash** — le modèle IA s'exécute en dehors du processus de GIMP
- 🔍 **Détection automatique de Python** — aucun fichier de configuration à modifier, le greffon trouve lui-même une installation Python fonctionnelle
- 📊 **Barre de progression animée** pendant le traitement
- 🩺 **Messages d'erreur clairs** en cas de dépendance manquante ou mal configurée
- 💻 **Mode CPU** — fonctionne sur n'importe quel ordinateur, sans carte graphique dédiée
### Prérequis
 
| Élément | Version |
|---|---|
| GIMP | 3.0+ |
| Python | 3.9+ (avec `pip`), installé **séparément de GIMP** |
| Système | Windows (voir remarques ci-dessous pour macOS/Linux) |
 
> ℹ️ GIMP 3 embarque son propre interpréteur Python interne (celui qui exécute ce greffon). Cette copie interne n'est volontairement **jamais utilisée** pour exécuter le modèle IA — le greffon recherche toujours une installation Python distincte et classique sur votre système.
 
### Installation
 
#### Étape 1 — Installer Python
 
L'IA a besoin d'une installation Python distincte de celle de GIMP pour fonctionner.
 
1. Téléchargez la dernière version de Python sur le site officiel : [python.org/downloads](https://www.python.org/downloads/).
2. Lancez le programme d'installation.
3. ✅ **Recommandé :** sur le premier écran de l'installateur, cochez la case **« Add python.exe to PATH »** avant de cliquer sur **Install Now**. Ce n'est plus strictement obligatoire (voir plus bas), mais cela simplifie l'usage de `pip`/`python` depuis l'Invite de commandes.
4. Si GIMP était déjà ouvert, redémarrez-le après l'installation de Python pour qu'il prenne en compte la nouvelle installation.
#### Étape 2 — Installer le moteur IA
 
Ce greffon utilise le mode processeur (**CPU**) standard, pour garantir une compatibilité universelle sans exiger de carte graphique spécifique.
 
1. Ouvrez l'**Invite de commandes** Windows (tapez `cmd` dans la barre de recherche du menu Démarrer).
2. Installez la bibliothèque `rembg` :
```cmd
   pip install "rembg[cpu,cli]"
```
3. *(Recommandé)* Pré-téléchargez le modèle IA (~40 Mo) pour que le premier détourage dans GIMP soit rapide :
```cmd
   python -c "from rembg import new_session; new_session('u2netp')"
```
 
#### Étape 3 — Installer le greffon dans GIMP
 
1. Téléchargez le fichier `ia_detourage.py` de ce dépôt.
2. Ouvrez **GIMP 3.0** et allez dans **Édition ▸ Préférences ▸ Dossiers ▸ Greffons**.
3. Placez `ia_detourage.py` dans votre dossier personnel de greffons (généralement `C:\Users\VotreNom\AppData\Roaming\GIMP\3.0\plug-ins`).
4. Redémarrez GIMP.
**C'est tout — aucun fichier à modifier, aucun chemin à configurer.** Le greffon est désormais disponible dans le menu :
**Image ▸ Calque ▸ Transparence ▸ Détourer le calque (IA)...**
 
### Utilisation
 
1. Ouvrez ou sélectionnez le calque à traiter.
2. Allez dans **Image ▸ Calque ▸ Transparence ▸ Détourer le calque (IA)...**.
3. Au tout premier lancement, le greffon recherche sur votre système une installation Python valide disposant de `rembg` — cela ajoute quelques secondes, une seule fois ; le résultat est ensuite mis en cache.
4. Patientez pendant la barre de progression — le traitement prend environ **40 secondes par image**, selon la puissance de votre processeur.
5. L'arrière-plan est automatiquement converti en transparence une fois le traitement terminé.
### Comment fonctionne la détection automatique de Python
 
Les anciennes versions de ce greffon nécessitaient de modifier manuellement le fichier `.py` pour y indiquer un chemin Python en dur, car GIMP 3 embarque son propre `python.exe` interne qui serait sinon utilisé par erreur (il ne dispose pas de `rembg`, et n'en disposera jamais). Cette version détecte seule une installation Python valide et distincte, en essayant plusieurs méthodes indépendantes dans l'ordre jusqu'à ce que l'une fonctionne — elle ne repose donc pas sur un seul mécanisme fragile (comme un PATH système obsolète) :
 
1. **Recherche via le PATH** (`where`/`which python`) — fonctionne la plupart du temps, mais peut échouer si GIMP a été lancé avant que Python ne soit ajouté au PATH système.
2. **Le lanceur `py`** (Windows) — lit les installations Python directement depuis le registre Windows, indépendamment du PATH.
3. **Lecture directe du registre** (Windows) — même principe, interrogé directement en repli.
4. **Scan disque** (Windows) — vérifie les emplacements d'installation standards (`AppData\Local\Programs\Python`, `Program Files`) en dernier recours.
Chaque candidat trouvé est réellement testé (`import rembg`) avant d'être accepté — le greffon ne devine jamais. Le Python interne de GIMP est toujours explicitement exclu. Le résultat est mis en cache (dans le dossier de configuration de GIMP), donc cette recherche ne s'exécute qu'une seule fois ; si ce Python mis en cache devient invalide par la suite (par exemple si `rembg` est désinstallé), le cache est automatiquement effacé et le greffon relance une recherche au prochain lancement — sans intervention manuelle de votre part.
 
### Dépannage
 
| Symptôme | Cause probable | Solution |
|---|---|---|
| Le greffon n'apparaît pas dans le menu | Mauvais dossier de greffons, ou GIMP non redémarré | Vérifiez le chemin du dossier (Étape 3) et redémarrez GIMP |
| Erreur « Module IA introuvable » | Aucune installation Python avec `rembg` n'a pu être trouvée automatiquement | Ouvrez l'Invite de commandes et lancez `pip install "rembg[cpu,cli]"`, puis relancez simplement le greffon — aucune modification de fichier n'est nécessaire |
| La détection retombe sur un Python périmé/invalide | Le système a changé depuis la dernière détection réussie (Python déplacé, désinstallé, etc.) | Relancez simplement le greffon — l'entrée invalide est détectée et une nouvelle recherche se déclenche automatiquement |
| Premier lancement très lent | Modèle IA non pré-téléchargé, ou première détection Python | Exécutez la commande `new_session('u2netp')` de l'Étape 2 pour pré-télécharger le modèle ; le délai de détection ponctuel est normal et ne se produit qu'une seule fois |
 
### macOS / Linux — pistes d'adaptation non testées
 
> ⚠️ **Ces indications sont une proposition, sans certitude qu'elles fonctionnent telles quelles.** Ce greffon a été écrit et testé uniquement sous Windows. La détection automatique inclut un repli `which python3` qui devrait fonctionner sur macOS/Linux, mais les stratégies du lanceur `py`, de lecture du registre et de scan disque sont spécifiques à Windows et se désactivent simplement sur les autres systèmes — la détection y repose donc uniquement sur le PATH, veillez à ce que Python y soit correctement présent. Attendez-vous à devoir ajuster vous-même certains chemins et permissions.
 
- **Python & pip** : macOS et la plupart des distributions Linux incluent déjà Python 3. Vérifiez avec `python3 --version` dans un terminal. S'il est absent, installez-le via [python.org](https://www.python.org/downloads/) (macOS) ou votre gestionnaire de paquets, par exemple `sudo apt install python3 python3-pip` (Debian/Ubuntu).
- **Installation de rembg** : utilisez `pip3` plutôt que `pip` si Python 2 et 3 sont tous les deux présents :
```bash
  pip3 install "rembg[cpu,cli]"
```
- **Pré-téléchargement du modèle** :
```bash
  python3 -c "from rembg import new_session; new_session('u2netp')"
```
- **Dossier des greffons** — c'est le point qui nécessite le plus probablement un ajustement :
  - **macOS** : généralement `~/Library/Application Support/GIMP/3.0/plug-ins`
  - **Linux** : généralement `~/.config/GIMP/3.0/plug-ins`
  - Vous pouvez confirmer le chemin exact depuis GIMP via **Édition ▸ Préférences ▸ Dossiers ▸ Greffons**.
- **Permissions du script** : sur macOS/Linux, il peut être nécessaire de rendre le fichier exécutable :
```bash
  chmod +x ia_detourage.py
```
- **Ligne shebang** : le script commence déjà par `#!/usr/bin/env python3`, ce qui devrait suffire pour que GIMP le détecte correctement hors Windows.
Si vous parvenez à le faire fonctionner de façon fiable sous macOS ou Linux, les contributions/PR documentant la procédure exacte sont les bienvenues.
 
### Licence
 
* licence MIT*
