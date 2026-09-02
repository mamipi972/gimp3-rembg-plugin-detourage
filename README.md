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
 
## macOS / Linux — Automated Installation (Zero-Config)

This plugin is fully compatible with **macOS** and **Linux**. To comply with the standards of recent Linux distributions — particularly Ubuntu and Debian, which discourage global installations via `pip` — the plugin manages its own dependencies automatically.

### How does it work?

When the plugin is launched from GIMP for the first time, it checks whether an existing virtual environment is available. If none is found, it automatically creates an isolated virtual environment.

It then downloads and installs `rembg` and all of its dependencies into this environment.

### Installation

1. **Prerequisites**

   macOS and most Linux distributions already include Python 3.

   On Debian/Ubuntu, however, you may need to install the package required to create virtual environments:

   ```bash
   sudo apt install python3-venv
   ```

2. **Plugin directory**

   Place the `ia_detourage.py` file in GIMP's plugin directory.

   - **macOS**: usually `~/Library/Application Support/GIMP/3.0/plug-ins`
   - **Linux**: usually `~/.config/GIMP/3.0/plug-ins`

   > **Tip:** You can confirm the exact path in GIMP via **Edit ▸ Preferences ▸ Folders ▸ Plug-ins**.

3. **Script permissions**

   On macOS and Linux, the script must be made executable so that GIMP can detect it:

   ```bash
   chmod +x ia_detourage.py
   ```

4. **First launch**

   The first time you use the plugin in GIMP, please wait a few moments.

   A progress bar will indicate the download of the AI module and its pre-trained model.

   Subsequent launches will start immediately.

## License

This plugin is distributed under the **MIT License**.
 
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
 ## macOS / Linux — Installation automatisée (Zero-Config)

Ce greffon est pleinement compatible avec **macOS** et **Linux**. Pour respecter les standards des distributions récentes — notamment Ubuntu et Debian, qui déconseillent les installations globales via `pip` — le greffon gère automatiquement ses propres dépendances.

### Comment ça fonctionne ?

Au premier lancement depuis GIMP, si le greffon ne trouve pas d'environnement virtuel existant, il en crée automatiquement un, de manière isolée. Il télécharge ensuite et installe `rembg` ainsi que toutes ses dépendances.

### Installation

1. **Prérequis**

   macOS et la plupart des distributions Linux incluent déjà Python 3.

   Sur Debian/Ubuntu, il peut toutefois être nécessaire d'installer le paquet permettant de créer des environnements virtuels :

   ```bash
   sudo apt install python3-venv
   ```

2. **Dossier des greffons**

   Placez le fichier `ia_detourage.py` dans le dossier des greffons de GIMP.

   - **macOS** : généralement `~/Library/Application Support/GIMP/3.0/plug-ins`
   - **Linux** : généralement `~/.config/GIMP/3.0/plug-ins`

   > **Astuce :** vous pouvez confirmer le chemin exact depuis GIMP via **Édition ▸ Préférences ▸ Dossiers ▸ Greffons**.

3. **Permissions du script**

   Sur macOS et Linux, le script doit être rendu exécutable pour que GIMP puisse le détecter :

   ```bash
   chmod +x ia_detourage.py
   ```

4. **Premier lancement**

   Lors de votre première utilisation du greffon dans GIMP, patientez quelques instants.

   Une barre de progression vous indiquera le téléchargement du module d'IA et de son modèle pré-entraîné.

   Les lancements suivants seront immédiats.

## Licence

Ce greffon est distribué sous **licence MIT**.
