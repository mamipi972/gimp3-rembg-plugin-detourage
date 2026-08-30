# GIMP 3 - Greffon de Détourage IA (AI Background Removal)

*(English version below)*

🇫🇷 **Greffon ultra-stable pour GIMP 3.0 permettant de détourer automatiquement vos images grâce à l'Intelligence Artificielle (via `rembg`).**

Contrairement à d'autres solutions, ce script utilise une approche en "sous-marin" (subprocess). Le modèle IA ne s'exécute pas directement dans l'espace mémoire de GIMP, ce qui garantit que le logiciel de retouche ne plantera jamais, même en cas de dépassement de mémoire ou d'erreur matérielle.

## 🛠️ Prérequis
* **GIMP 3.0** ou supérieur.
* **Python 3.10** ou supérieur.
  ⚠️ *Lors de l'installation de Python sous Windows, vous devez impérativement cocher la case **"Add python.exe to PATH"**.*

## 🚀 Installation (Windows)
1. Ouvrez l'Invite de commandes (cmd) et installez le moteur IA avec cette commande :
   `pip install "rembg[cpu,cli]"`
2. Téléchargez le fichier `ia_detourage.py` de ce dépôt.
3. Placez-le dans le dossier des greffons de GIMP (généralement accessible via *Édition > Préférences > Dossiers > Greffons*).
4. Redémarrez GIMP. Le greffon se trouve dans `Image > Calque > Transparence > Détourer le calque (IA)...`.

⏱️ **Note sur les performances :** Par défaut, cette configuration utilise votre processeur (CPU) pour garantir une compatibilité maximale. Le détourage prend environ 40 secondes par image.

* **Mode GPU (NVIDIA CUDA) :** ~5 secondes par image *(nécessite `onnxruntime-gpu` et l'environnement CUDA/cuDNN)*.
* **Mode CPU (Standard) :** ~40 secondes par image *(compatibilité universelle sans configuration matérielle)*.

---

🇬🇧 **Ultra-stable GIMP 3.0 plugin for automatic AI background removal (powered by `rembg`).**

Unlike other plugins, this script uses a subprocess approach. The AI model does not run directly within GIMP's memory space, ensuring your image editor will never crash due to memory out-of-bounds or hardware conflicts.

## 🛠️ Requirements
* **GIMP 3.0** or higher.
* **Python 3.10** or higher.
  ⚠️ *When installing Python on Windows, you must check the **"Add python.exe to PATH"** box.*

## 🚀 Installation (Windows)
1. Open Command Prompt (cmd) and install the AI engine using this command:
   `pip install "rembg[cpu,cli]"`
2. Download the `ia_detourage.py` file from this repository.
3. Place it in your GIMP plug-ins folder (usually found via *Edit > Preferences > Folders > Plug-ins*).
4. Restart GIMP. You can find the plugin under `Image > Layer > Transparency > Détourer le calque (IA)...`.

⏱️ **Performance Note:** By default, this setup uses your processor (CPU) for maximum compatibility. Background removal takes about 40 seconds per image.
* **GPU Mode (NVIDIA CUDA):** ~5 seconds per image *(requires `onnxruntime-gpu` and CUDA/cuDNN environment)*.
* **CPU Mode (Standard):** ~40 seconds per image *(universal compatibility with zero hardware config)*.