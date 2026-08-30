# ✂️ GIMP 3 — AI Background Removal Plugin
 
**Ultra-stable GIMP 3.0 plugin for automatic AI background removal, powered by [`rembg`](https://github.com/danielgatis/rembg).**
 
Unlike other plugins, this script runs the AI model in a **separate subprocess** instead of inside GIMP's own memory space — so your image editor will never crash, no matter what happens. It also includes an animated progress bar and smart error dialogs to help you fix missing dependencies quickly.
 
🇬🇧 [English](#-english) · 🇫🇷 [Français](#-français)
 
---
 
## 🇬🇧 English
 
### Features
 
- 🛡️ **Crash-proof** — the AI model runs outside GIMP's process
- 📊 **Live progress bar** while the image is processed
- 🩺 **Smart error dialogs** if a dependency is missing or misconfigured
- 💻 **CPU-only mode** — works on any machine, no GPU required
### Requirements
 
| Requirement | Version |
|---|---|
| GIMP | 3.0+ |
| Python | 3.9+ (with `pip`) |
| OS | Windows (see notes below for macOS/Linux) |
 
### Installation
 
#### Step 1 — Install Python
 
1. Download Python from [python.org/downloads](https://www.python.org/downloads/).
2. Run the installer.
3. ⚠️ **Critical:** on the very first installation screen, check the box **"Add python.exe to PATH"** before clicking **Install Now**.
4. Restart your computer (or at least close GIMP if it was open) so the new PATH variable takes effect.
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
The plugin is now available under:
**Image ▸ Layer ▸ Transparency ▸ Remove Background (AI)...**
 
### Usage
 
1. Open or select the layer you want to process.
2. Go to **Image ▸ Layer ▸ Transparency ▸ Remove Background (AI)...**.
3. Wait for the progress bar — processing takes roughly **40 seconds per image**, depending on your CPU.
4. The background is automatically converted to transparency once processing completes.
### Troubleshooting
 
| Symptom | Likely cause | Fix |
|---|---|---|
| Plugin doesn't appear in the menu | Wrong plug-ins folder, or GIMP not restarted | Double-check the folder path in Step 3 and restart GIMP |
| "Python not found" error | Python not added to PATH | Reinstall Python and check "Add python.exe to PATH" |
| "rembg not found" error | `pip install` step skipped or failed | Re-run `pip install "rembg[cpu,cli]"` in `cmd` |
| First run is very slow | AI model not pre-downloaded | Run the `new_session('u2netp')` command from Step 2 |
 
### macOS / Linux — untested adaptation notes
 
> ⚠️ **These instructions are only a proposal.** This plugin was written and tested on Windows only — the steps below are educated guesses at what would need to change on macOS or Linux, with **no guarantee that they will work as-is**. Expect to debug paths and permissions yourself.
 
- **Python & pip**: macOS and most Linux distributions already ship with Python 3. Check with `python3 --version` in a terminal. If missing, install it via [python.org](https://www.python.org/downloads/) (macOS) or your package manager, e.g. `sudo apt install python3 python3-pip` (Debian/Ubuntu).
- **PATH**: the "Add python.exe to PATH" step is Windows-specific and not needed on macOS/Linux, since `python3`/`pip3` are normally already on the PATH.
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
- **Shebang line**: the script may need a `#!/usr/bin/env python3` line at the top to run correctly outside Windows — check the `.py` file if GIMP fails to detect it.
If you get it working reliably on macOS or Linux, contributions/PRs documenting the exact steps are welcome.
 
### License
 
* licence MIT *
 
---
 
## 🇫🇷 Français
 
### Fonctionnalités
 
- 🛡️ **Anti-crash** — le modèle IA s'exécute en dehors du processus de GIMP
- 📊 **Barre de progression animée** pendant le traitement
- 🩺 **Messages d'erreur clairs** en cas de dépendance manquante ou mal configurée
- 💻 **Mode CPU** — fonctionne sur n'importe quel ordinateur, sans carte graphique dédiée
### Prérequis
 
| Élément | Version |
|---|---|
| GIMP | 3.0+ |
| Python | 3.9+ (avec `pip`) |
| Système | Windows (voir remarques ci-dessous pour macOS/Linux) |
 
### Installation
 
#### Étape 1 — Installer Python
 
L'IA a besoin de Python pour fonctionner. Si vous l'avez déjà installé **et ajouté au PATH**, passez à l'étape 2.
 
1. Téléchargez la dernière version de Python sur le site officiel : [python.org/downloads](https://www.python.org/downloads/).
2. Lancez le programme d'installation.
3. ⚠️ **Étape cruciale :** sur le tout premier écran de l'installateur, **cochez impérativement la case « Add python.exe to PATH »** en bas de la fenêtre avant de cliquer sur **Install Now**. Sans cela, GIMP ne trouvera pas Python.
4. Une fois l'installation terminée, redémarrez votre ordinateur (ou au minimum fermez GIMP s'il était ouvert) pour appliquer la nouvelle variable système.
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
Le greffon est désormais disponible dans le menu :
**Image ▸ Calque ▸ Transparence ▸ Détourer le calque (IA)...**
 
### Utilisation
 
1. Ouvrez ou sélectionnez le calque à traiter.
2. Allez dans **Image ▸ Calque ▸ Transparence ▸ Détourer le calque (IA)...**.
3. Patientez pendant la barre de progression — le traitement prend environ **40 secondes par image**, selon la puissance de votre processeur.
4. L'arrière-plan est automatiquement converti en transparence une fois le traitement terminé.
### Dépannage
 
| Symptôme | Cause probable | Solution |
|---|---|---|
| Le greffon n'apparaît pas dans le menu | Mauvais dossier de greffons, ou GIMP non redémarré | Vérifiez le chemin du dossier (Étape 3) et redémarrez GIMP |
| Erreur « Python introuvable » | Python non ajouté au PATH | Réinstallez Python en cochant « Add python.exe to PATH » |
| Erreur « rembg introuvable » | Étape `pip install` oubliée ou échouée | Relancez `pip install "rembg[cpu,cli]"` dans `cmd` |
| Premier lancement très lent | Modèle IA non pré-téléchargé | Exécutez la commande `new_session('u2netp')` de l'Étape 2 |
 
### macOS / Linux — pistes d'adaptation non testées
 
> ⚠️ **Ces indications sont une proposition, sans certitude qu'elles fonctionnent telles quelles.** Ce greffon a été écrit et testé uniquement sous Windows — ce qui suit correspond à ce qu'il faudrait probablement adapter sur macOS ou Linux, mais attendez-vous à devoir ajuster vous-même certains chemins et permissions.
 
- **Python & pip** : macOS et la plupart des distributions Linux incluent déjà Python 3. Vérifiez avec `python3 --version` dans un terminal. S'il est absent, installez-le via [python.org](https://www.python.org/downloads/) (macOS) ou votre gestionnaire de paquets, par exemple `sudo apt install python3 python3-pip` (Debian/Ubuntu).
- **PATH** : l'étape « Add python.exe to PATH » est spécifique à Windows et n'est pas nécessaire sur macOS/Linux, car `python3`/`pip3` sont normalement déjà accessibles.
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
- **Ligne shebang** : le script pourrait nécessiter une ligne `#!/usr/bin/env python3` en tout début de fichier pour être correctement détecté hors Windows — vérifiez le fichier `.py` si GIMP ne le détecte pas.
Si vous parvenez à le faire fonctionner de façon fiable sous macOS ou Linux, les contributions/PR documentant la procédure exacte sont les bienvenues.
 
### Licence
 
*licence MIT*
