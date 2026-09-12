# ✂️ GIMP 3 — AI Background Removal Plugin

**Zero-configuration GIMP 3 plugin for AI background removal, powered by [`rembg`](https://github.com/danielgatis/rembg).**

The AI model runs in a **separate subprocess**, never inside GIMP's memory — your editor cannot be brought down by it. The plugin finds or builds its own Python environment on every platform, **including Windows**, without ever asking you to type a command.

🇬🇧 [English](#-english) · 🇫🇷 [Français](#-français)

> **Upgrading from v2.x?** Read [Migration](#migration-from-the-previous-version) / [Migration](#migration-depuis-la-version-précédente) first. The old version required `pip install` in a terminal. This one does not.

---

## 🇬🇧 English

### What's new in 3.7

| | v2.x | v3.7 |
|---|---|---|
| Windows setup | manual `pip install` in a terminal | fully automatic |
| Python environment | your system Python | dedicated, isolated, shared across the plugin suite |
| Model | `u2netp` only, hardcoded | three models, chosen in the dialog |
| Hardware | CPU only | CPU by default; ticking the GPU box changes the hardware, and falls back to the CPU with an explanation rather than failing |
| Repair | delete a folder by hand | a checkbox in the dialog |
| Traceability | layer named "(détouré)" | layer names the model **and** the hardware actually used |

### Features

- 🛡️ **Crash-proof** — the model runs outside GIMP's process
- 🤖 **Zero-configuration** — no file to edit, no command to type, on any platform
- 🎚️ **Three models** — pick speed or edge quality per image
- 🖥️ **Optional NVIDIA acceleration** — off by default, refused up-front if your machine can't actually use it
- 📊 **Animated progress bar** with distinct, readable error messages
- 🔎 **Honest reporting** — the layer name always states which model ran, and on which hardware

### Requirements

| Requirement | Version |
|---|---|
| GIMP | 3.0 or later (tested on 3.0 and 3.2) |
| Python | 3.10 or later, installed **separately from GIMP**, and not one bundled inside another application |
| Free disk space | **566 MB** installed for the CPU engine, **1.89 GB** for the GPU one; 2 GB resp. 5 GB free required to install |
| OS | Windows, macOS, Linux — **except Flatpak builds of GIMP** |

> ℹ️ GIMP ships its own internal Python (the one running this plugin). It is deliberately **never** used for the AI model: it isn't meant to manage packages. The plugin always uses a separate interpreter.

> ⚠️ **Flatpak is not supported.** The sandbox makes every system Python unreachable, so the plugin cannot build its environment. It detects this and says so. Use a native GIMP package, an AppImage, or the official installer.

### Installation

#### Step 1 — Install Python (once)

Download Python 3.10 or later from [python.org/downloads](https://www.python.org/downloads/) and run the installer. Ticking *"Add python.exe to PATH"* is convenient but **not required** — the plugin also reads the Windows registry and the `py` launcher, and prefers those.

> ⚠️ **A Python bundled inside another application does not qualify.** Blender, Krita, FreeCAD and similar tools ship their own interpreter. One of them was picked up in real use, and the environment built on it would have broken silently the day that application was updated. The plugin now ranks interpreters by how they were found — registry, `py` launcher and standard install locations first, `PATH` alone only as a fallback — and records the channel it used.

On macOS and most Linux distributions Python 3 is already there. On Debian and Ubuntu, also install the `venv` module:

```bash
sudo apt install python3-venv
```

If it's missing, the plugin shows you that exact command rather than a cryptic error.

#### Step 2 — Install the plugin

1. Download `ia_detourage.py` from this repository.
2. Find your plug-ins folder via **Edit ▸ Preferences ▸ Folders ▸ Plug-ins**. It is usually:
   - **Windows** — `%APPDATA%\GIMP\3.0\plug-ins` (or `\3.2\` depending on your version)
   - **macOS** — `~/Library/Application Support/GIMP/3.0/plug-ins`
   - **Linux** — `~/.config/GIMP/3.0/plug-ins`
3. Create a folder named **exactly** `ia_detourage` inside it, and place the file there:
   `plug-ins/ia_detourage/ia_detourage.py`
   The folder name must match the file name, case included.
4. On macOS and Linux only, make it executable:
   ```bash
   chmod +x ia_detourage.py
   ```
5. Restart GIMP.

**There is no step 3.** No `pip`, no terminal, no path to configure. The plugin appears under
**Layer ▸ Transparency ▸ Detourer le calque (IA)...**

#### Step 3 — First run

The first time you run the filter, the plugin builds its environment: it looks for a usable Python, creates a dedicated virtual environment, installs `rembg` and its dependencies, then downloads the model you selected. Expect **about ten seconds** for the CPU engine, or **about five minutes** if you ticked the GPU box, with the progress bar animating throughout. Every later run starts immediately.

If anything fails, you get a specific message — not a generic error — and nothing is left half-installed that a second run can't fix.

### Using it

1. Select the layer to process. **Only that layer is used**, not the flattened composite.
2. **Layer ▸ Transparency ▸ Detourer le calque (IA)...**
3. Pick a model, click **Valider**.
4. A new layer is inserted above the original, at the same position and offset, inside the same group. **Your original layer is never modified.**

#### The dialog at a glance

| Setting | Default | What it changes | What it costs |
|---|---|---|---|
| Model | Fast (`u2netp`) | Which network decides what is foreground | A one-off download: 4.4 MB, or 168–170 MB for the other two |
| Refine edges | off | Recomputes the boundary; **enables the three settings below it**, which do nothing on their own | Noticeably slower, and not always an improvement |
| Certainty to keep a pixel | 240 | Higher = more conservative about keeping | None beyond the refine step |
| Certainty to erase a pixel | 10 | Lower = more conservative about erasing | None beyond the refine step |
| Width of the uncertain zone | 10 | Thickness of the recomputed band | Wider is slower |
| Use the NVIDIA card | off | The **hardware** the model runs on | A second, much larger environment; falls back to the CPU if it can't work |
| Repair the installation | off | Rebuilds the environment before processing | A full reinstall, several minutes |

Nothing here modifies your image. Every run adds a **new layer** above the
original, at the same position and offset, inside the same group — so comparing
two settings means running twice and keeping the better layer.

#### Choosing a model

| Model | Download | Good for |
|---|---|---|
| `u2netp` | 4.4 MB | fast previews, simple subjects, clear separation |
| `u2net` | 168 MB | general use, better on complex backgrounds |
| `isnet-general-use` | 170 MB | fine edges — hair, fur, foliage, lace |

> **"Better quality" does not mean better on your image.** These models were trained on different data and genuinely disagree. `u2netp` sometimes keeps a thin element — a strap, a blade, a tassel — that `u2net` discards, and the reverse happens just as often. The models are cheap to re-run once downloaded: try two and keep the better layer. That is why the plugin inserts a new layer instead of replacing yours, and why the layer name states which model produced it.

#### How long it takes

Measured on a Ryzen 5 5500 / 16 GB / RTX 3050, on roughly 1 megapixel images,
from clicking *Valider* to the layer appearing.

| Situation | Time |
|---|---|
| First run, CPU engine — environment built and model downloaded | **~10 seconds** |
| First run, GPU engine — `onnxruntime-gpu` plus cuDNN | **~5 minutes** |
| Any later run, `u2netp` or `u2net`, on the processor | **~10 seconds** |
| Any later run, `u2net`, on the graphics card | **~10 seconds** |

Two things worth knowing before you choose.

The CPU engine installs in seconds, not minutes. The five-minute figure belongs
to the GPU variant alone, and almost all of it is downloading
`onnxruntime-gpu` and cuDNN.

**At this image size the graphics card buys you nothing measurable.** Ten
seconds either way: the time goes into loading the model and moving files, not
into inference. The GPU option starts to matter on much larger images or on
repeated batches — if that isn't your case, leave the box unticked and save
yourself a large download.

#### Refine edges (Alpha Matting)

Unchecked by default. When ticked, it recomputes the boundary and enables the three settings below it — which stay greyed out otherwise, because they do nothing on their own.

- **Certainty to keep a pixel** (default 240) — raise it and the plugin is more conservative about keeping pixels.
- **Certainty to erase a pixel** (default 10) — lower it and it is more conservative about erasing.
- **Width of the uncertain zone** (default 10) — thickness of the band that gets recomputed.

Refining is noticeably slower and is not always an improvement. Compare before keeping it.

#### NVIDIA acceleration

Unticked by default, and deliberately so.

**What the checkbox controls is the hardware.** Unticked, the plugin asks ONNX
Runtime for `CPUExecutionProvider` only — the computation runs on the processor
even if a usable card is present. Ticked, it installs a **second, separate
environment** built around `onnxruntime-gpu` and explicitly requests CUDA. The
two environments never share a folder: `onnxruntime` and `onnxruntime-gpu`
install to the same location inside a Python environment and would destroy each
other.

**Ticking it never breaks the filter.** The GPU path has three ways to fail —
no CUDA runtime on the machine, the install not completing, or the validation
inference not running on the card. In all three cases the plugin quietly builds
the CPU environment instead, produces your layer, and tells you in one sentence
why the card wasn't used. You get a result either way.

**What the card actually needs**, and this trips up most people:

| Component | Where it comes from | Notes |
|---|---|---|
| NVIDIA driver | Windows Update or nvidia.com | Necessary, far from sufficient |
| CUDA Toolkit | nvidia.com, separate download | The plugin checks for it before downloading anything |
| cuDNN 9 | **a separate download again**, or installed automatically by the plugin from PyPI | The Toolkit does *not* contain it |

The plugin tries to install cuDNN itself from PyPI (`nvidia-cudnn-cu13`, then
`nvidia-cudnn-cu12`) so you don't have to fetch it from NVIDIA. That attempt is
best-effort: if neither variant works, the validation inference fails, and you
fall back to the processor with an explanation.

**Validation is a real inference, not a capability check.** Asking ONNX Runtime
whether CUDA is "available" returns yes even when cuDNN is missing — the failure
only surfaces at the first convolution, in the middle of your actual work. So
the plugin runs the model on a small test image before trusting the
environment.

**The layer name always states what really happened**: `u2net sur GPU NVIDIA`
or `u2net sur processeur`. It is derived from the execution provider the session
actually used, never from the presence of a card.

Is it worth it? With `u2netp` on a modern processor, inference takes a second or
two and the GPU buys you little for several hundred megabytes of extra install.
With `u2net` or `isnet` on large images, the difference becomes real.

#### Repair the installation

If the filter stops working — a package removed, an interrupted install, a Python upgrade — tick **"Reparer l'installation"** and run it once. The environment is rebuilt from scratch. You never need to delete a folder by hand.

### Where things are stored

Everything lives in a folder shared by all plugins of this suite, inside GIMP's own configuration directory:

```
<GIMP config>/ai_suite_shared/
├── venv-onnx-cpu/            CPU engine — 566 MB
├── venv-onnx-gpu/            GPU engine — 1.89 GB, only if you tick the option
├── models/                   AI models, flat, shared between plugins
├── logs/                     diagnostic folders kept after a failure
├── ai_suite_env_onnx-cpu.json
└── ai_suite_env_onnx-gpu.json
```

Deleting `ai_suite_shared` resets everything; the plugin rebuilds it on the next run.

> **Note for corporate machines.** On Windows this sits under `AppData\Roaming`, which is synchronised at logon on roaming profiles. Several gigabytes there is a bad idea. If that's your situation, raise an issue — moving heavy data to `LOCALAPPDATA` is planned.


#### When something fails, send the log

If a run fails, the plugin copies everything useful — the worker's log, the pip
logs, the parameters it used — into a timestamped folder before deleting its
working directory:

```
<GIMP config>/ai_suite_shared/logs/2026-09-12_16-30-12/
```

The error message shows the exact path. **Attach that folder to any bug report.**
Without it a failure is a sentence like "it doesn't work", which cannot be
reproduced or diagnosed; with it, the cause is usually visible in the first few
lines. The ten most recent incidents are kept, older ones are removed
automatically.

You do not need to enable anything for this. `IA_DETOURAGE_DEBUG=1` still exists
and additionally keeps the whole working directory, but it is meant for
development, not for reporting a problem.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| The plugin doesn't appear in the menu at all | Wrong folder, folder name not matching the file name, GIMP not restarted, or the file isn't executable (macOS/Linux) | Re-check step 2. If it still doesn't appear, look for `ia_detourage_diagnostic.log` in `%APPDATA%` (Windows) or your home folder — the plugin writes there as soon as GIMP loads it. **No log file at all means GIMP never ran the file**, which points at the install location, not the plugin |
| "Aucun interpreteur Python du systeme utilisable" | No Python 3.10+ found outside GIMP | Install Python from python.org, or `sudo apt install python3 python3-venv` |
| "Impossible de creer l'environnement virtuel" | `python3-venv` missing | `sudo apt install python3-venv`, then run the filter again |
| Install times out after 15 minutes | No connection, or a corporate proxy blocking `pip` | Check the connection, then run the filter again |
| "Une precedente installation a echoue" | A failure was recorded so it isn't retried endlessly | Tick **"Reparer l'installation"** |
| "GIMP fonctionne dans un bac a sable Flatpak" | Flatpak build | Use a native package, an AppImage, or the official installer |
| GPU ticked, layer says "sur processeur" | The CUDA provider didn't register | The plugin already adds the Toolkit's `bin` folder to the engine's search path. What's usually missing is **cuDNN 9**, which must sit alongside the CUDA Toolkit, or a Toolkit version that doesn't match the one `onnxruntime-gpu` expects |
| GPU option refused before downloading | No CUDA Toolkit found | Install the CUDA Toolkit and cuDNN from NVIDIA, or untick the option and use the processor |
| Results look worse with the "better" model | Normal — see [Choosing a model](#choosing-a-model) | Run both and keep the better layer |
| "Not enough disk space to install the AI engine" | The plugin checks before downloading anything | Free up space: 2 GB for the CPU engine, 5 GB for the GPU one. The message states what's required, what's available and on which volume |
| "The GPU option was requested but could not be used: cuDNN is missing" | The CUDA Toolkit is installed but cuDNN is not, and the plugin's PyPI attempt didn't succeed | Your layer was still produced, on the processor. Either untick the box, or install cuDNN 9 from nvidia.com matching your CUDA series |
| GPU ticked, layer says "sur processeur", no warning shown | The warning is shown once per environment and then remembered | The layer name remains the permanent record |

To keep the working folder and its logs after a run, set the environment variable `IA_DETOURAGE_DEBUG=1` before starting GIMP. The folder path is then shown in error messages.

### Migration from the previous version

If you used v2.x, you were told to run `pip install "rembg[cpu,cli]"`. That installation is **still detected and reused** — nothing is broken, and you won't re-download anything.

Two things are worth doing anyway:

1. **Delete the old plugin file** before installing the new one. Both register the same procedure name (`python-fu-ia-detourage`) and GIMP will keep only one, without telling you which.
2. **Old leftovers you can remove**, once the new version works:
   - `<GIMP config>/ia_detourage_python_cache.txt` — the old interpreter cache, no longer read
   - `~/.u2net/` — the old model folder; models now live in `ai_suite_shared/models`

If you'd rather the plugin build its own clean environment instead of reusing your system installation, tick **"Reparer l'installation"** on the first run.

### For contributors

**The `.py` file must stay pure ASCII, comments included.** A version differing only by accented characters inside strings and comments was not executed by GIMP at all under Windows: the plugin vanished from the menus and from the procedure browser, with no message and no log entry. The correlation is established by bisection; the mechanism is not. French UI labels are therefore written without accents. This constraint applies to the code only — documentation stays in proper French.

Before any release:

```python
assert not any(ord(c) > 127 for c in open("ia_detourage.py", encoding="utf-8").read())
```

The plugin also self-checks: markers, JSON keys and property names are duplicated between the plugin and its embedded worker (which cannot interpolate anything, by design), so a comparison script must confirm both sets match.

### License

MIT.

---

## 🇫🇷 Français

### Ce qui change en 3.7

| | v2.x | v3.7 |
|---|---|---|
| Installation Windows | `pip install` à taper dans un terminal | entièrement automatique |
| Environnement Python | votre Python système | dédié, isolé, mutualisé entre les greffons de la suite |
| Modèle | `u2netp` seul, figé | trois modèles, choisis dans la fenêtre |
| Matériel | processeur uniquement | processeur par défaut ; cocher la case GPU change le matériel, et retombe sur le processeur avec une explication plutôt que d'échouer |
| Réparation | supprimer un dossier à la main | une case à cocher |
| Traçabilité | calque nommé « (détouré) » | le calque nomme le modèle **et** le matériel réellement utilisé |

### Fonctionnalités

- 🛡️ **Anti-crash** — le modèle s'exécute en dehors du processus de GIMP
- 🤖 **Zéro configuration** — aucun fichier à modifier, aucune commande à taper, sur toutes les plateformes
- 🎚️ **Trois modèles** — privilégiez la vitesse ou la finesse du contour selon l'image
- 🖥️ **Accélération NVIDIA optionnelle** — décochée par défaut, refusée d'emblée si votre machine ne peut pas réellement s'en servir
- 📊 **Barre de progression animée**, messages d'erreur distincts et lisibles
- 🔎 **Rapport honnête** — le nom du calque indique toujours quel modèle a tourné, et sur quel matériel

### Prérequis

| Élément | Version |
|---|---|
| GIMP | 3.0 ou plus (testé sur 3.0 et 3.2) |
| Python | 3.10 ou plus, installé **séparément de GIMP**, et pas celui embarqué dans une autre application |
| Espace disque libre | **566 Mo** installés pour le moteur processeur, **1,89 Go** pour celui du GPU ; 2 Go resp. 5 Go libres exigés pour installer |
| Système | Windows, macOS, Linux — **sauf les versions Flatpak de GIMP** |

> ℹ️ GIMP embarque son propre Python interne, celui qui exécute ce greffon. Il n'est volontairement **jamais** utilisé pour le modèle IA : il n'est pas prévu pour gérer des paquets. Le greffon passe toujours par un interpréteur distinct.

> ⚠️ **Flatpak n'est pas pris en charge.** Le bac à sable rend inaccessible tout Python du système, donc le greffon ne peut pas construire son environnement. Il le détecte et le dit. Utilisez un paquet natif, une AppImage ou l'installeur officiel.

### Installation

#### Étape 1 — Installer Python (une seule fois)

Téléchargez Python 3.10 ou plus sur [python.org/downloads](https://www.python.org/downloads/) et lancez l'installateur. Cocher « Add python.exe to PATH » est pratique mais **pas nécessaire** : le greffon lit aussi le registre Windows et le lanceur `py`, et les préfère.

> ⚠️ **Un Python embarqué dans une autre application ne convient pas.** Blender, Krita, FreeCAD et consorts livrent leur propre interpréteur. L'un d'eux a été retenu en usage réel, et l'environnement bâti dessus aurait cessé de fonctionner sans explication le jour de la mise à jour de cette application. Le greffon classe désormais les interpréteurs selon la manière dont ils ont été trouvés — registre, lanceur `py` et emplacements d'installation standards d'abord, `PATH` seul en dernier recours — et consigne le canal utilisé.

Sur macOS et la plupart des distributions Linux, Python 3 est déjà présent. Sur Debian et Ubuntu, ajoutez le module `venv` :

```bash
sudo apt install python3-venv
```

S'il manque, le greffon vous affiche cette commande exacte plutôt qu'une erreur incompréhensible.

#### Étape 2 — Installer le greffon

1. Téléchargez `ia_detourage.py` depuis ce dépôt.
2. Repérez votre dossier de greffons via **Édition ▸ Préférences ▸ Dossiers ▸ Greffons**. Généralement :
   - **Windows** — `%APPDATA%\GIMP\3.0\plug-ins` (ou `\3.2\` selon votre version)
   - **macOS** — `~/Library/Application Support/GIMP/3.0/plug-ins`
   - **Linux** — `~/.config/GIMP/3.0/plug-ins`
3. Créez-y un dossier nommé **exactement** `ia_detourage` et placez le fichier dedans :
   `plug-ins/ia_detourage/ia_detourage.py`
   Le nom du dossier doit correspondre au nom du fichier, casse comprise.
4. Sur macOS et Linux uniquement, rendez-le exécutable :
   ```bash
   chmod +x ia_detourage.py
   ```
5. Redémarrez GIMP.

**Il n'y a pas d'étape 3.** Ni `pip`, ni terminal, ni chemin à configurer. Le greffon apparaît dans
**Calque ▸ Transparence ▸ Detourer le calque (IA)...**

#### Étape 3 — Premier lancement

Au premier usage du filtre, le greffon construit son environnement : il cherche un Python utilisable, crée un environnement virtuel dédié, y installe `rembg` et ses dépendances, puis télécharge le modèle choisi. Comptez **une dizaine de secondes** pour le moteur processeur, ou **environ cinq minutes** si vous avez coché l'option GPU, barre de progression animée du début à la fin. Tous les lancements suivants démarrent immédiatement.

En cas d'échec, vous obtenez un message précis — pas une erreur générique — et rien ne reste à moitié installé qu'un second lancement ne sache réparer.

### Utilisation

1. Sélectionnez le calque à traiter. **Seul ce calque est utilisé**, pas le composite aplati.
2. **Calque ▸ Transparence ▸ Detourer le calque (IA)...**
3. Choisissez un modèle, cliquez sur **Valider**.
4. Un nouveau calque est inséré au-dessus de l'original, à la même position et au même décalage, dans le même groupe. **Votre calque d'origine n'est jamais modifié.**

#### La fenêtre en un coup d'œil

| Réglage | Défaut | Ce qu'il change | Ce qu'il coûte |
|---|---|---|---|
| Modèle | Rapide (`u2netp`) | Quel réseau décide ce qui est au premier plan | Un téléchargement unique : 4,4 Mo, ou 168 à 170 Mo pour les deux autres |
| Affiner les contours | décoché | Recalcule la bordure ; **active les trois réglages en dessous**, qui n'ont aucun effet seuls | Nettement plus lent, et pas toujours meilleur |
| Certitude pour garder un pixel | 240 | Plus haut = plus prudent avant de conserver | Rien au-delà de l'affinage |
| Certitude pour effacer un pixel | 10 | Plus bas = plus prudent avant d'effacer | Rien au-delà de l'affinage |
| Largeur de la zone incertaine | 10 | Épaisseur de la bande recalculée | Plus large, plus lent |
| Utiliser la carte NVIDIA | décoché | Le **matériel** sur lequel tourne le modèle | Un second environnement, bien plus lourd ; repli sur le processeur s'il ne peut pas fonctionner |
| Réparer l'installation | décoché | Reconstruit l'environnement avant traitement | Une réinstallation complète, plusieurs minutes |

Rien ici ne modifie votre image. Chaque exécution ajoute un **nouveau calque**
au-dessus de l'original, à la même position et au même décalage, dans le même
groupe — comparer deux réglages consiste donc à lancer deux fois et à garder le
meilleur calque.

#### Choisir un modèle

| Modèle | Téléchargement | Convient pour |
|---|---|---|
| `u2netp` | 4,4 Mo | aperçus rapides, sujets simples, séparation nette |
| `u2net` | 168 Mo | usage général, meilleur sur les fonds complexes |
| `isnet-general-use` | 170 Mo | contours fins — cheveux, poils, feuillage, dentelle |

> **« Meilleure qualité » ne veut pas dire meilleur sur votre image.** Ces modèles ont été entraînés sur des données différentes et se contredisent réellement. `u2netp` conserve parfois un élément fin — une sangle, une lame, un pompon — que `u2net` supprime, et l'inverse se produit tout aussi souvent. Une fois téléchargés, les modèles coûtent peu à relancer : essayez-en deux et gardez le meilleur calque. C'est précisément pour cela que le greffon ajoute un calque au lieu de remplacer le vôtre, et que le nom du calque indique quel modèle l'a produit.

#### Combien de temps cela prend

Mesures sur Ryzen 5 5500 / 16 Go / RTX 3050, sur des images d'environ un
mégapixel, du clic sur *Valider* jusqu'à l'apparition du calque.

| Situation | Durée |
|---|---|
| Premier lancement, moteur processeur — environnement construit et modèle téléchargé | **~10 secondes** |
| Premier lancement, moteur GPU — `onnxruntime-gpu` et cuDNN | **~5 minutes** |
| Tout lancement suivant, `u2netp` ou `u2net`, sur le processeur | **~10 secondes** |
| Tout lancement suivant, `u2net`, sur la carte graphique | **~10 secondes** |

Deux choses à savoir avant de choisir.

Le moteur processeur s'installe en quelques secondes, pas en minutes. Les cinq
minutes ne concernent que la variante GPU, et tiennent presque entièrement au
téléchargement d'`onnxruntime-gpu` et de cuDNN.

**À cette taille d'image, la carte graphique n'apporte rien de mesurable.** Dix
secondes dans les deux cas : le temps part dans le chargement du modèle et les
échanges de fichiers, pas dans l'inférence. L'option GPU ne devient utile que
sur des images bien plus grandes ou en traitement répété — si ce n'est pas votre
cas, laissez la case décochée et épargnez-vous un gros téléchargement.

#### Affiner les contours (Alpha Matting)

Décoché par défaut. Une fois coché, il recalcule la bordure et active les trois réglages situés en dessous — grisés sinon, puisqu'ils n'ont aucun effet seuls.

- **Certitude pour garder un pixel** (240 par défaut) — plus la valeur est haute, plus le greffon est prudent avant de conserver un pixel.
- **Certitude pour effacer un pixel** (10 par défaut) — plus elle est basse, plus il est prudent avant d'effacer.
- **Largeur de la zone incertaine** (10 par défaut) — épaisseur de la bande recalculée.

L'affinage est nettement plus lent et n'améliore pas toujours le résultat. Comparez avant de le conserver.

#### Accélération NVIDIA

Décochée par défaut, et ce n'est pas un oubli.

**Ce que la case gouverne, c'est le matériel.** Décochée, le greffon ne demande
à ONNX Runtime que `CPUExecutionProvider` : le calcul se fait sur le processeur
même si une carte utilisable est présente. Cochée, il installe un **second
environnement, séparé**, bâti autour d'`onnxruntime-gpu`, et réclame
explicitement CUDA. Les deux environnements ne partagent jamais de dossier :
`onnxruntime` et `onnxruntime-gpu` s'installent au même endroit dans un
environnement Python et se détruiraient mutuellement.

**La cocher ne casse jamais le filtre.** La voie GPU peut échouer de trois
façons — aucun runtime CUDA sur la machine, installation qui n'aboutit pas, ou
inférence de validation qui ne tourne pas sur la carte. Dans les trois cas, le
greffon construit l'environnement processeur à la place, produit votre calque,
et vous dit en une phrase pourquoi la carte n'a pas servi. Vous obtenez un
résultat dans tous les cas.

**Ce dont la carte a réellement besoin**, et c'est là que presque tout le monde
trébuche :

| Composant | D'où il vient | Remarque |
|---|---|---|
| Pilote NVIDIA | Windows Update ou nvidia.com | Nécessaire, très loin d'être suffisant |
| CUDA Toolkit | nvidia.com, téléchargement séparé | Le greffon vérifie sa présence avant de télécharger quoi que ce soit |
| cuDNN 9 | **encore un téléchargement distinct**, ou installé automatiquement par le greffon depuis PyPI | Le Toolkit ne le contient *pas* |

Le greffon tente d'installer cuDNN lui-même depuis PyPI (`nvidia-cudnn-cu13`,
puis `nvidia-cudnn-cu12`) pour vous éviter d'aller le chercher chez NVIDIA.
Cette tentative est sans conséquence : si aucune variante ne convient,
l'inférence de validation échoue et vous repassez sur le processeur avec une
explication.

**La validation est une vraie inférence, pas un contrôle de capacité.**
Demander à ONNX Runtime si CUDA est « disponible » renvoie oui même sans
cuDNN — l'échec ne survient qu'au premier nœud de convolution, en plein
travail. Le greffon exécute donc le modèle sur une petite image de test avant
de faire confiance à l'environnement.

**Le nom du calque dit toujours ce qui s'est réellement passé** : `u2net sur GPU
NVIDIA` ou `u2net sur processeur`. Il est dérivé du fournisseur d'exécution
réellement utilisé par la session, jamais de la présence d'une carte.

Cela en vaut-il la peine ? Avec `u2netp` sur un processeur moderne, l'inférence
prend une seconde ou deux et le GPU n'apporte pas grand-chose pour plusieurs
centaines de mégaoctets d'installation supplémentaire. Avec `u2net` ou `isnet`
sur de grandes images, la différence devient réelle.

#### Réparer l'installation

Si le filtre cesse de fonctionner — paquet supprimé, installation interrompue, Python mis à jour — cochez **« Reparer l'installation »** et lancez-le une fois. L'environnement est reconstruit intégralement. Vous n'avez jamais à supprimer un dossier à la main.

### Où sont stockées les données

Tout se trouve dans un dossier partagé par les greffons de cette suite, à l'intérieur du répertoire de configuration de GIMP :

```
<config GIMP>/ai_suite_shared/
├── venv-onnx-cpu/            moteur processeur — 566 Mo
├── venv-onnx-gpu/            moteur GPU — 1,89 Go, seulement si vous cochez l'option
├── models/                   modèles IA, à plat, partagés entre greffons
├── logs/                     dossiers de diagnostic conservés après un échec
├── ai_suite_env_onnx-cpu.json
└── ai_suite_env_onnx-gpu.json
```

Supprimer `ai_suite_shared` remet tout à zéro ; le greffon reconstruit au lancement suivant.

> **Remarque pour les postes d'entreprise.** Sous Windows, ce dossier est sous `AppData\Roaming`, synchronisé à l'ouverture de session sur les profils itinérants. Y placer plusieurs gigaoctets est une mauvaise idée. Si c'est votre cas, ouvrez une issue — le déplacement des données volumineuses vers `LOCALAPPDATA` est prévu.


#### Quand quelque chose échoue, envoyez le journal

Si un traitement échoue, le greffon copie tout ce qui est utile — le journal du
worker, les journaux pip, les paramètres employés — dans un dossier horodaté,
avant de supprimer son répertoire de travail :

```
<config GIMP>/ai_suite_shared/logs/2026-09-12_16-30-12/
```

Le message d'erreur affiche le chemin exact. **Joignez ce dossier à tout
signalement.** Sans lui, une panne se résume à « ça ne marche pas », ce qui ne
se reproduit ni ne se diagnostique ; avec lui, la cause est généralement lisible
dès les premières lignes. Les dix incidents les plus récents sont conservés, les
plus anciens supprimés automatiquement.

Vous n'avez rien à activer pour cela. `IA_DETOURAGE_DEBUG=1` existe toujours et
conserve en plus l'intégralité du dossier de travail, mais il s'adresse au
développement, pas au signalement d'un problème.

### Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Le greffon n'apparaît nulle part | Mauvais dossier, nom de dossier différent du nom de fichier, GIMP non redémarré, ou script non exécutable (macOS/Linux) | Revoyez l'étape 2. S'il reste absent, cherchez `ia_detourage_diagnostic.log` dans `%APPDATA%` (Windows) ou votre dossier personnel : le greffon y écrit dès que GIMP le charge. **Aucun fichier journal signifie que GIMP n'a jamais exécuté le fichier**, ce qui désigne l'emplacement d'installation, pas le greffon |
| « Aucun interpreteur Python du systeme utilisable » | Aucun Python 3.10+ trouvé en dehors de GIMP | Installez Python depuis python.org, ou `sudo apt install python3 python3-venv` |
| « Impossible de creer l'environnement virtuel » | `python3-venv` manquant | `sudo apt install python3-venv`, puis relancez le filtre |
| L'installation dépasse 15 minutes | Pas de connexion, ou un proxy d'entreprise bloque `pip` | Vérifiez la connexion, puis relancez le filtre |
| « Une precedente installation a echoue » | Un échec a été mémorisé pour ne pas être retenté sans fin | Cochez **« Reparer l'installation »** |
| « GIMP fonctionne dans un bac a sable Flatpak » | Version Flatpak | Utilisez un paquet natif, une AppImage ou l'installeur officiel |
| GPU coché, le calque indique « sur processeur » | Le fournisseur CUDA ne s'est pas enregistré | Le greffon expose déjà le dossier `bin` du Toolkit au moteur. Ce qui manque le plus souvent est **cuDNN 9**, qui doit se trouver à côté du CUDA Toolkit, ou une version de Toolkit différente de celle attendue par `onnxruntime-gpu` |
| Option GPU refusée avant tout téléchargement | Aucun CUDA Toolkit détecté | Installez le CUDA Toolkit et cuDNN depuis le site de NVIDIA, ou décochez l'option et utilisez le processeur |
| Le modèle « de meilleure qualité » donne un moins bon résultat | Normal — voir [Choisir un modèle](#choisir-un-modèle) | Lancez les deux et gardez le meilleur calque |
| « Espace disque insuffisant pour installer le moteur IA » | Le greffon vérifie avant tout téléchargement | Libérez de la place : 2 Go pour le moteur processeur, 5 Go pour celui du GPU. Le message indique le requis, le disponible et le volume concerné |
| « L'option carte graphique a été demandée mais n'a pas pu être utilisée : cuDNN est introuvable » | Le CUDA Toolkit est installé mais pas cuDNN, et la tentative du greffon via PyPI n'a pas abouti | Votre calque a quand même été produit, sur le processeur. Décochez la case, ou installez cuDNN 9 depuis nvidia.com dans la série correspondant à votre CUDA |
| GPU coché, le calque indique « sur processeur », sans avertissement | L'avertissement n'est affiché qu'une fois par environnement, puis mémorisé | Le nom du calque reste la trace permanente |

Pour conserver le dossier de travail et ses journaux après un traitement, définissez la variable d'environnement `IA_DETOURAGE_DEBUG=1` avant de démarrer GIMP. Le chemin du dossier apparaît alors dans les messages d'erreur.

### Migration depuis la version précédente

Si vous utilisiez la v2.x, on vous avait demandé de lancer `pip install "rembg[cpu,cli]"`. Cette installation est **toujours détectée et réutilisée** : rien n'est cassé et vous ne retéléchargez rien.

Deux gestes restent utiles :

1. **Supprimez l'ancien fichier du greffon** avant d'installer le nouveau. Les deux déclarent la même procédure (`python-fu-ia-detourage`) et GIMP n'en gardera qu'une, sans vous dire laquelle.
2. **Résidus supprimables**, une fois la nouvelle version fonctionnelle :
   - `<config GIMP>/ia_detourage_python_cache.txt` — l'ancien cache d'interpréteur, plus jamais lu
   - `~/.u2net/` — l'ancien dossier de modèles ; ils vivent désormais dans `ai_suite_shared/models`

Si vous préférez que le greffon construise son propre environnement propre plutôt que de réutiliser votre installation système, cochez **« Reparer l'installation »** au premier lancement.

### Pour les contributeurs

**Le fichier `.py` doit rester en ASCII pur, commentaires compris.** Une version ne différant que par des caractères accentués dans des chaînes et des commentaires n'était plus du tout exécutée par GIMP sous Windows : le greffon disparaissait des menus et du navigateur de procédures, sans message et sans entrée de journal. La corrélation est établie par bissection, le mécanisme ne l'est pas. Les libellés français de l'interface sont donc écrits sans accents. La contrainte ne vaut que pour le code — la documentation reste en français correct.

Avant toute publication :

```python
assert not any(ord(c) > 127 for c in open("ia_detourage.py", encoding="utf-8").read())
```

Le greffon impose aussi ses propres contrôles : les marqueurs, les clés JSON et les noms de propriétés sont dupliqués entre le greffon et son worker embarqué — lequel ne peut rien interpoler, par conception — donc un script de comparaison doit confirmer que les deux ensembles coïncident.

### Licence

MIT.
