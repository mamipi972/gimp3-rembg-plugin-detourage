#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ATTENTION - CE FICHIER DOIT RESTER EN ASCII PUR.
# Une version identique ne differant que par des caracteres accentues dans les
# chaines et les commentaires n'etait plus executee par GIMP : le greffon
# disparaissait des menus sans le moindre message, aucune de ses methodes
# n'etant seulement atteinte. La correlation est etablie par bissection, le
# mecanisme ne l'est pas. N'introduisez aucun caractere au-dela de 0x7F, y
# compris dans les commentaires, et verifiez-le avant chaque livraison.

# Greffon GIMP 3.0 - Detourage par IA (rembg / ONNX Runtime)
# Conforme au noyau du scenario v3 : sections 1, 2, 3, 4, 5, 7, 10, 13, 14, 20.
# Aucune commande n'est jamais demandee a l'utilisateur.

import os
import re
import sys
import json
import glob
import time
import shutil
import signal
import tempfile
import subprocess

import gi

gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio


# ============================================================================
# Constantes - toute valeur citee dans la documentation doit venir d'ici
# ============================================================================

VERSION_GREFFON = "3.11.0"
NOM_PROCEDURE = "python-fu-ia-detourage"
NOM_DOSSIER_PARTAGE = "ai_suite_shared"
# Identifiant du greffon dans les ressources partagees de la suite. Il ne
# derive pas de NOM_PROCEDURE : celui-ci porte un prefixe "python-fu-" qui n'a
# rien a faire dans un fichier de donnees.
NOM_GREFFON = "ia_detourage"

# Section 10 : au-dela de ce seuil, aucun telechargement automatique. Le
# greffon affiche alors le chemin exact ou deposer le fichier. En deca, le
# telechargement est lance seul, avec annonce prealable de la taille.
SEUIL_TELECHARGEMENT_AUTO_MO = 1024

MODELES = {
    "u2netp": {
        "fichier": "u2netp.onnx",
        "taille_mo": 4.4,
        "titre": "Rapide",
    },
    "u2net": {
        "fichier": "u2net.onnx",
        "taille_mo": 168.0,
        "titre": "Meilleure qualite",
    },
    "isnet-general-use": {
        "fichier": "isnet-general-use.onnx",
        "taille_mo": 170.0,
        "titre": "Contours fins, cheveux et feuillage",
    },
}
MODELE_DEFAUT = "u2netp"
MODELES_AUTORISES = tuple(MODELES)

ALPHA_MATTING_DEFAUT = False
SEUIL_AVANT_PLAN_DEFAUT = 240
SEUIL_ARRIERE_PLAN_DEFAUT = 10
EROSION_DEFAUT = 10
REINSTALLER_DEFAUT = False

# Bornes de l'interpreteur d'amorcage. Le plancher vient de rembg, le plafond
# est la derniere version reellement validee. Au-dela du plafond, un candidat
# reste utilisable en dernier recours : le refuser reviendrait a declarer
# qu'aucun Python n'existe alors qu'il y en a un.
# Canaux de decouverte d'un interpreteur. Seuls les trois premiers reposent sur
# une declaration du systeme : un Python embarque dans une application tierce
# (Blender, Krita, FreeCAD, suites 3D) n'y figure jamais. Un venv bati sur un
# tel interpreteur cesse de fonctionner des que l'application est mise a jour ou
# desinstallee, sans que rien ne relie la panne a la cause.
CANAUX_FIABLES = ("registre", "lanceur_py", "installation_standard")
CANAL_PATH = "path"
CANAL_VENV = "venv_conventionnel"

VERSION_PYTHON_MIN = (3, 10)
VERSION_PYTHON_MAX_VALIDEE = (3, 14)

VARIANTE_CPU = "onnx-cpu"
VARIANTE_GPU = "onnx-gpu"
GPU_DEFAUT = False

EXIGENCES_PIP = {
    VARIANTE_CPU: (
        "rembg[cpu]>=2.0.56,<3",
        "onnxruntime>=1.16,<2",
        "numpy>=1.24,<3",
        "pillow>=9,<12",
        "pymatting>=1.1,<2",
    ),
    VARIANTE_GPU: (
        "rembg[gpu]>=2.0.56,<3",
        "onnxruntime-gpu>=1.16,<2",
        "numpy>=1.24,<3",
        "pillow>=9,<12",
        "pymatting>=1.1,<2",
    ),
}

# La case de la fenetre gouverne le materiel de calcul, pas seulement
# l'environnement installe : sans cette liste, un Python systeme equipe de
# onnxruntime-gpu calculait sur la carte alors que la case etait decochee.
FOURNISSEURS = {
    VARIANTE_CPU: ("CPUExecutionProvider",),
    VARIANTE_GPU: ("CUDAExecutionProvider", "CPUExecutionProvider"),
}

# cuDNN n'est pas dans le CUDA Toolkit : c'est un telechargement distinct chez
# NVIDIA, que le greffon ne peut pas demander a l'utilisateur (regle n 1). Mais
# NVIDIA le publie aussi sur PyPI. On tente les variantes dans l'ordre, sans
# jamais faire echouer l'installation : la sonde d'inference tranchera, et le
# repli processeur existe.
EXIGENCES_CUDNN = (
    "nvidia-cudnn-cu13>=9,<10",
    "nvidia-cudnn-cu12>=9,<10",
)

# Prefixe repere : une raison destinee a etre reprise dans un autre message ne
# doit pas trainer derriere elle la queue de journal de celui d'origine.
RAISON_SEULE = "[RAISON] "

# Tailles mesurees le 12/09/2026 : 566 Mo pour l'environnement processeur,
# 1,89 Go pour celui a base d'onnxruntime-gpu et cuDNN. pip a besoin de place
# pour decompresser en plus de l'occupation finale, d'ou une marge.
ESPACE_LIBRE_MINIMAL = {
    VARIANTE_CPU: 2 * 1024 * 1024 * 1024,
    VARIANTE_GPU: 5 * 1024 * 1024 * 1024,
}

SONDE_MODULES = "import rembg, onnxruntime, PIL, pymatting"
# Verifier que CUDA figure parmi les fournisseurs disponibles ne prouve rien :
# il y figure meme sans cuDNN, et l'echec ne survient qu'au premier noeud de
# convolution, en pleine inference. Seule une inference reelle valide.
SONDE_CUDA = (
    "import sys;"
    "from rembg import remove, new_session;"
    "from PIL import Image;"
    "s = new_session('u2netp',"
    " providers=['CUDAExecutionProvider', 'CPUExecutionProvider']);"
    "remove(Image.new('RGB', (320, 320)), session=s);"
    "sys.exit(0 if 'CUDAExecutionProvider'"
    " in s.inner_session.get_providers() else 1)"
)

DELAI_SONDE = 20
# Un import a froid de la pile complete (rembg, scipy, scikit-image, numba,
# llvmlite, onnxruntime) depasse largement 20 secondes au premier lancement,
# analyse antivirus comprise. Une sonde trop courte fait passer une
# installation reussie pour un module inutilisable.
DELAI_SONDE_IMPORT = 240
DELAI_CREATION_VENV = 120
DELAI_PIP = 900
DELAI_WORKER = 600
INTERVALLE_POLLING = 0.2
QUEUE_LOG_AFFICHEE = 800

MARQUEUR_OK = "[IA_OK]"
MARQUEUR_MOTEUR = "[IA_MOTEUR]"
MARQUEUR_MATERIEL = "[IA_MATERIEL]"
MARQUEUR_ERR_PARAMS = "[IA_ERR_PARAMS]"
MARQUEUR_ERR_IMPORT = "[IA_ERR_IMPORT]"
MARQUEUR_ERR_IMAGE = "[IA_ERR_IMAGE]"
MARQUEUR_ERR_MODELE = "[IA_ERR_MODELE]"
MARQUEUR_ERR_ECRITURE = "[IA_ERR_ECRITURE]"
MARQUEUR_ERR_MEMOIRE = "[IA_ERR_MEMOIRE]"
MARQUEUR_ERR_INATTENDU = "[IA_ERR_INATTENDU]"

EXPLICATIONS_MARQUEURS = {
    MARQUEUR_ERR_PARAMS: "Le fichier de parametres n'a pas pu etre relu par le worker.",
    MARQUEUR_ERR_IMPORT: "Le module IA n'est pas importable dans cet environnement.",
    MARQUEUR_ERR_IMAGE: "L'image exportee depuis GIMP n'a pas pu etre relue.",
    MARQUEUR_ERR_MODELE: "Le modele IA n'a pas pu etre charge ou applique.",
    MARQUEUR_ERR_ECRITURE: "Le fichier resultat n'a pas pu etre ecrit sur le disque.",
    MARQUEUR_ERR_MEMOIRE: "Memoire insuffisante pour traiter une image de cette taille.",
    MARQUEUR_ERR_INATTENDU: "Erreur non prevue dans le worker.",
}

VARIABLES_A_PURGER = (
    "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONEXECUTABLE",
    "LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT",
    "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH",
    "DYLD_INSERT_LIBRARIES", "DYLD_FALLBACK_LIBRARY_PATH",
    "GI_TYPELIB_PATH", "GDK_PIXBUF_MODULE_FILE", "GDK_PIXBUF_MODULEDIR",
    "GSETTINGS_SCHEMA_DIR", "GEGL_PATH", "BABL_PATH",
)


# ============================================================================
# Section 1 - worker sans aucune interpolation, parametres par fichier JSON
# ============================================================================

CODE_WORKER = r'''
import sys
import json
import traceback

MARQUEUR_OK = "[IA_OK]"
MARQUEUR_MOTEUR = "[IA_MOTEUR]"
MARQUEUR_MATERIEL = "[IA_MATERIEL]"
MARQUEUR_ERR_PARAMS = "[IA_ERR_PARAMS]"
MARQUEUR_ERR_IMPORT = "[IA_ERR_IMPORT]"
MARQUEUR_ERR_IMAGE = "[IA_ERR_IMAGE]"
MARQUEUR_ERR_MODELE = "[IA_ERR_MODELE]"
MARQUEUR_ERR_ECRITURE = "[IA_ERR_ECRITURE]"
MARQUEUR_ERR_MEMOIRE = "[IA_ERR_MEMOIRE]"
MARQUEUR_ERR_INATTENDU = "[IA_ERR_INATTENDU]"


def emettre(marqueur, detail=""):
    texte = marqueur
    if detail:
        texte += " " + str(detail).replace("\n", " ").replace("\r", " ")[:500]
    print(texte, flush=True)


def echouer(marqueur, detail=""):
    emettre(marqueur, detail)
    sys.exit(1)


def materiel_depuis_fournisseurs(fournisseurs):
    tete = fournisseurs[0] if fournisseurs else ""
    if "CUDA" in tete or "Tensorrt" in tete or "TensorRT" in tete:
        return "GPU NVIDIA"
    if "Dml" in tete or "DirectML" in tete:
        return "GPU DirectML"
    if "CoreML" in tete:
        return "GPU Apple"
    if "ROCM" in tete or "MIGraphX" in tete:
        return "GPU AMD"
    return "processeur"


def main():
    if len(sys.argv) < 2:
        echouer(MARQUEUR_ERR_PARAMS, "aucun chemin de parametres fourni")

    try:
        with open(sys.argv[1], "r", encoding="utf-8") as flux:
            params = json.load(flux)
        chemin_entree = params["entree"]
        chemin_sortie = params["sortie"]
        modele = params["modele"]
    except Exception as erreur:
        echouer(MARQUEUR_ERR_PARAMS, erreur)

    try:
        from rembg import remove, new_session
        from PIL import Image
    except Exception as erreur:
        echouer(MARQUEUR_ERR_IMPORT, erreur)

    try:
        image = Image.open(chemin_entree)
        image.load()
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
    except Exception as erreur:
        echouer(MARQUEUR_ERR_IMAGE, erreur)

    # Le materiel est impose par l'appelant, pas deduit de ce que la roue
    # installee sait faire : un onnxruntime-gpu present dans un Python systeme
    # ne doit pas calculer sur la carte quand la case est decochee.
    demandes = params.get("fournisseurs") or []
    try:
        import onnxruntime
        disponibles = list(onnxruntime.get_available_providers())
    except Exception:
        disponibles = []
    retenus = [f for f in demandes if f in disponibles]

    try:
        if retenus:
            try:
                session = new_session(modele, providers=retenus)
            except TypeError:
                # Anciennes versions de rembg sans parametre providers.
                session = new_session(modele)
        else:
            session = new_session(modele)
    except MemoryError:
        echouer(MARQUEUR_ERR_MEMOIRE, "chargement du modele")
    except Exception as erreur:
        echouer(MARQUEUR_ERR_MODELE, erreur)

    fournisseurs = []
    try:
        fournisseurs = list(session.inner_session.get_providers())
    except Exception:
        fournisseurs = retenus or disponibles
    materiel = materiel_depuis_fournisseurs(fournisseurs)

    try:
        sortie = remove(
            image,
            session=session,
            alpha_matting=bool(params.get("alpha_matting", False)),
            alpha_matting_foreground_threshold=int(params.get("seuil_avant_plan", 240)),
            alpha_matting_background_threshold=int(params.get("seuil_arriere_plan", 10)),
            alpha_matting_erode_size=int(params.get("erosion", 10)),
        )
    except MemoryError:
        echouer(MARQUEUR_ERR_MEMOIRE, "inference")
    except Exception as erreur:
        echouer(MARQUEUR_ERR_MODELE, erreur)

    try:
        if sortie.mode != "RGBA":
            sortie = sortie.convert("RGBA")
        sortie.save(chemin_sortie)
    except Exception as erreur:
        echouer(MARQUEUR_ERR_ECRITURE, erreur)

    emettre(MARQUEUR_MOTEUR, modele)
    emettre(MARQUEUR_MATERIEL, materiel)
    emettre(MARQUEUR_OK)


try:
    main()
except SystemExit:
    raise
except Exception:
    emettre(MARQUEUR_ERR_INATTENDU, traceback.format_exc())
    sys.exit(1)
'''


# ============================================================================
# Section 2 - isolation d'environnement
# ============================================================================

def chemin_journal_diagnostic():
    """Un greffon qui echoue a l'enregistrement ne laisse aucune trace dans
    l'interface : GIMP avale sa sortie d'erreur en mode graphique. On ecrit
    donc le traceback dans un fichier que l'utilisateur peut ouvrir."""
    for base in (
        os.environ.get("APPDATA", ""),
        os.path.expanduser("~"),
        tempfile.gettempdir(),
    ):
        if base and os.path.isdir(base):
            return os.path.join(base, "ia_detourage_diagnostic.log")
    return "ia_detourage_diagnostic.log"


def journaliser(etape, erreur=None):
    import traceback
    try:
        with open(chemin_journal_diagnostic(), "a", encoding="utf-8") as flux:
            flux.write("=== %s - %s - greffon %s\n"
                       % (time.strftime("%Y-%m-%d %H:%M:%S"), etape,
                          VERSION_GREFFON))
            flux.write("python worker : %s\n" % sys.version.replace("\n", " "))
            if erreur is not None:
                flux.write(traceback.format_exc())
            flux.write("\n")
    except Exception:
        pass


def appel_protege(etape, fonction, *args):
    """Enregistre un appel d'API sans jamais laisser une exception faire
    disparaitre le greffon en entier. Retourne True si l'appel a abouti."""
    try:
        fonction(*args)
        return True
    except Exception as erreur:
        journaliser(etape, erreur)
        return False


def est_windows():
    return os.name == "nt"


def conserver_fichiers_travail():
    """Mode de test : IA_DETOURAGE_DEBUG=1 conserve le dossier de travail et
    ses journaux, que le traitement reussisse ou non."""
    return os.environ.get("IA_DETOURAGE_DEBUG", "").strip() not in ("", "0")


def est_flatpak():
    return os.path.exists("/.flatpak-info")


def drapeaux_creation():
    return 0x08000000 if est_windows() else 0


def options_processus():
    """Section 3 : creationflags sous Windows uniquement, groupe de processus
    dedie sous POSIX pour pouvoir tuer toute la descendance du worker."""
    if est_windows():
        return {"creationflags": 0x08000000}
    return {"start_new_session": True}


def racines_cuda():
    """Dossiers d'installation du Toolkit CUDA, du plus recent au plus ancien."""
    if not est_windows():
        return []
    racines = []
    declaree = os.environ.get("CUDA_PATH", "")
    if declaree and os.path.isdir(declaree):
        racines.append(declaree)
    programmes = os.environ.get("ProgramFiles", r"C:\Program Files")
    motif = os.path.join(programmes, "NVIDIA GPU Computing Toolkit", "CUDA", "v*")
    for chemin in sorted(glob.glob(motif), reverse=True):
        if chemin not in racines:
            racines.append(chemin)
    return racines


def chemins_dll_nvidia():
    """DLL livrees par les paquets pip nvidia-* dans les environnements du
    greffon. onnxruntime-gpu les cherche sur le PATH du processus."""
    if not est_windows():
        return []
    chemins = []
    for variante in (VARIANTE_GPU, VARIANTE_CPU):
        motif = os.path.join(dossier_venv(variante), "Lib", "site-packages",
                             "nvidia", "*", "bin")
        for chemin in sorted(glob.glob(motif)):
            if chemin not in chemins:
                chemins.append(chemin)
    return chemins


def chemins_dll_cuda():
    """Sous GIMP, le PATH du processus n'expose pas forcement le Toolkit.
    onnxruntime-gpu charge ses DLL depuis le PATH : sans elles, le fournisseur
    CUDA ne s'enregistre pas, le calcul retombe sur le processeur, et rien ne
    distingue ce cas d'une machine sans carte graphique."""
    chemins = []
    for racine in racines_cuda():
        for sous_dossier in ("bin", os.path.join("bin", "x64"), "libnvvp"):
            candidat = os.path.join(racine, sous_dossier)
            if os.path.isdir(candidat) and candidat not in chemins:
                chemins.append(candidat)
    return chemins


def env_propre():
    env = os.environ.copy()

    for variable in VARIABLES_A_PURGER:
        env.pop(variable, None)

    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # PYTHONIOENCODING seul ne suffit pas : une partie des journaux revenait en
    # UTF-16 et devenait illisible une fois relue en UTF-8.
    env["PYTHONUTF8"] = "1"
    env["U2NET_HOME"] = dossier_modeles()

    if "PATH" in env:
        entrees = [c for c in env["PATH"].split(os.pathsep) if "gimp" not in c.lower()]
    else:
        entrees = []

    for chemin in chemins_dll_cuda() + chemins_dll_nvidia():
        if chemin not in entrees:
            entrees.insert(0, chemin)

    env["PATH"] = os.pathsep.join(e for e in entrees if e)

    return env


# ============================================================================
# Section 10 - dossier partage entre greffons de la suite
# ============================================================================

def dossier_partage():
    try:
        base = Gimp.directory()
    except Exception:
        base = os.path.join(os.path.expanduser("~"), ".gimp_ia_suite")
    chemin = os.path.join(base, NOM_DOSSIER_PARTAGE)
    os.makedirs(chemin, exist_ok=True)
    return chemin


def dossier_journaux():
    chemin = os.path.join(dossier_partage(), "logs")
    os.makedirs(chemin, exist_ok=True)
    return chemin


INCIDENTS_CONSERVES = 10
# Fichier depose dans chaque archive pour dire quel greffon l'a produite. Le
# dossier logs/ est partage par toute la suite : sans ce marqueur, un greffon
# ne sait pas distinguer ses archives de celles des autres.
NOM_FICHIER_INCIDENT = "incident.json"
# Age au-dela duquel une archive que personne ne revendique peut etre
# supprimee. Elles viennent des versions anterieures a ce marqueur.
JOURS_ARCHIVES_ORPHELINES = 30


def archiver_journaux(dossier_execution):
    """Section 13 amendee : le dossier de travail est bien detruit, mais jamais
    avant d'avoir mis a l'abri ce qui permet de comprendre l'echec. Sans cela,
    un rapport de bogue exploitable suppose que l'utilisateur pose une variable
    d'environnement avant de lancer GIMP - ce que personne ne fera."""
    try:
        fichiers = [n for n in os.listdir(dossier_execution)
                    if n.endswith(".log") or n == "parametres.json"]
    except OSError:
        return None
    if not fichiers:
        return None

    # Deux incidents dans la meme seconde ne doivent pas s'ecraser : le second
    # archivage reutiliserait le meme dossier et remplacerait les journaux du
    # premier, alors que c'est justement dans une serie d'echecs rapproches
    # qu'ils comptent. Les microsecondes rendent le nom unique ; la purge, elle,
    # ne se fie plus au nom.
    horodatage = "%s-%06d" % (time.strftime("%Y-%m-%d_%H-%M-%S"),
                              time.time_ns() // 1000 % 1000000)
    cible = os.path.join(dossier_journaux(), horodatage)
    try:
        os.makedirs(cible, exist_ok=True)
        _ecrire_marque_incident(cible, horodatage)
        for nom in fichiers:
            shutil.copy2(os.path.join(dossier_execution, nom),
                         os.path.join(cible, nom))
    except OSError:
        return None

    _purger_journaux()
    return cible


def _ecrire_marque_incident(cible, horodatage, contexte=None):
    """Depose dans l'archive le fichier qui dit quel greffon l'a produite.

    Il est ecrit avant la copie des journaux : si celle-ci echoue a mi-chemin,
    l'archive reste identifiable, donc purgeable par son proprietaire.
    """
    try:
        with open(os.path.join(cible, NOM_FICHIER_INCIDENT), "w",
                  encoding="utf-8") as flux:
            json.dump({"greffon": NOM_GREFFON, "version": VERSION_GREFFON,
                       "plateforme": sys.platform, "horodatage": horodatage,
                       "contexte": contexte or {}}, flux, indent=2)
    except Exception:
        pass


def _lire_marque_incident(chemin):
    """(greffon, date du marqueur) ou (None, 0.0) si l'archive n'en a pas."""
    marque = os.path.join(chemin, NOM_FICHIER_INCIDENT)
    if not os.path.isfile(marque):
        return None, 0.0
    try:
        with open(marque, "r", encoding="utf-8", errors="replace") as flux:
            donnees = json.load(flux)
    except Exception:
        return None, 0.0
    if not isinstance(donnees, dict):
        return None, 0.0
    try:
        date = os.path.getmtime(marque)
    except OSError:
        date = 0.0
    return donnees.get("greffon"), date


def _purger_journaux(base=None):
    """Purge les archives de CE greffon, et rien d'autre.

    Le dossier logs/ est partage par toute la suite, et deux conventions de
    nommage y cohabitent : "2026-09-16_19-44-05" ici, "20260916-194405-000123"
    chez d'autres greffons. En ASCII le tiret (0x2D) precede le chiffre
    (0x30) : un tri alphabetique place donc systematiquement la premiere forme
    en tete, et la purge qui s'y fiait supprimait toujours les archives des
    greffons qui l'emploient - dont celles de ce greffon-ci - quel que soit
    leur age. Dix incidents d'un voisin suffisaient a effacer tout
    l'historique, sans le moindre message, puisqu'il n'y a pas d'incident
    quand un greffon fonctionne.

    On ne purge donc que ce qu'on a produit, reconnaissable a son
    incident.json, et l'on date par ce fichier plutot que par le nom du
    dossier : aucune convention de nommage n'entre plus en jeu.

    Les archives que personne ne revendique - celles d'avant ce marqueur - ne
    sont supprimees qu'a deux conditions reunies : etre plus vieilles que
    JOURS_ARCHIVES_ORPHELINES, et ne pas figurer parmi les
    INCIDENTS_CONSERVES plus recentes. Un greffon de la suite qui n'aurait pas
    encore recu ce correctif garde ainsi ses archives recentes, et le stock
    ancien se resorbe quand meme.

    Retourne la liste des chemins supprimes, pour que le comportement soit
    verifiable autrement que par une inspection du dossier.
    """
    base = base or dossier_journaux()
    miennes = []
    orphelines = []
    try:
        entrees = os.listdir(base)
    except OSError:
        return []
    for nom in entrees:
        chemin = os.path.join(base, nom)
        if not os.path.isdir(chemin):
            continue
        greffon, date = _lire_marque_incident(chemin)
        if greffon == NOM_GREFFON:
            miennes.append((date, nom, chemin))
        elif greffon is None:
            try:
                date = os.path.getmtime(chemin)
            except OSError:
                date = 0.0
            orphelines.append((date, nom, chemin))
    miennes.sort()
    orphelines.sort()
    limite = time.time() - JOURS_ARCHIVES_ORPHELINES * 86400
    condamnees = [chemin for _, _, chemin in miennes[:-INCIDENTS_CONSERVES]]
    condamnees += [chemin for date, _, chemin
                   in orphelines[:-INCIDENTS_CONSERVES] if date < limite]
    for chemin in condamnees:
        shutil.rmtree(chemin, ignore_errors=True)
    return condamnees


def dossier_modeles():
    chemin = os.path.join(dossier_partage(), "models")
    os.makedirs(chemin, exist_ok=True)
    return chemin


def chemin_modele(modele):
    """Emplacement a plat, celui que le greffon annonce a l'utilisateur quand
    un depot manuel est necessaire."""
    return os.path.join(dossier_modeles(), MODELES[modele]["fichier"])


def chemins_modele_existants(modele):
    """rembg ne stocke pas ses poids au meme endroit selon sa version : a plat
    dans U2NET_HOME pour les unes, sous models/<nom>/<nom>.onnx pour les
    autres. Ne tester que la premiere disposition faisait croire le modele
    absent alors qu'il etait la, et rendait le seuil de la section 10
    inoperant. On cherche donc le fichier partout sous le dossier des
    modeles."""
    nom = MODELES[modele]["fichier"]
    trouves = []
    for racine, _dossiers, fichiers in os.walk(dossier_modeles()):
        if nom in fichiers:
            chemin = os.path.join(racine, nom)
            try:
                if os.path.getsize(chemin) > 0:
                    trouves.append(chemin)
            except OSError:
                pass
    return trouves


def chemin_canonique_modele(modele):
    """Emplacement ou rembg lit et ecrit reellement ses poids : a plat dans
    U2NET_HOME. Verifie par observation - apres suppression des fichiers a
    plat, rembg les a retelecharges au meme endroit, en ignorant une
    arborescence models/<nom>/ pourtant presente. Toute disposition imbriquee
    trouvee ailleurs sous models/ est donc un residu, et non l'inverse."""
    return chemin_modele(modele)


def normaliser_emplacement_modele(modele):
    """L'utilisateur depose son fichier a l'endroit simple qu'on lui indique ;
    le greffon le range ensuite la ou le moteur le cherche. Deplacer plutot que
    copier evite d'immobiliser deux fois plusieurs centaines de megaoctets."""
    canonique = chemin_canonique_modele(modele)
    autres = [c for c in chemins_modele_existants(modele)
              if os.path.normcase(c) != os.path.normcase(canonique)]

    taille_canonique = 0
    try:
        if os.path.exists(canonique):
            taille_canonique = os.path.getsize(canonique)
    except OSError:
        taille_canonique = 0

    if taille_canonique > 0:
        # Le modele est deja en place. Les copies restees ailleurs sous
        # models/ ne sont jamais lues par le moteur : elles immobilisent du
        # disque sans servir. On ne supprime que celles dont la taille est
        # identique, et uniquement dans le dossier que le greffon gere.
        for chemin in autres:
            try:
                if os.path.getsize(chemin) == taille_canonique:
                    os.remove(chemin)
            except OSError:
                pass
        _purger_dossiers_vides(dossier_modeles())
        return canonique

    if not autres:
        return None

    try:
        os.makedirs(os.path.dirname(canonique), exist_ok=True)
        shutil.move(autres[0], canonique)
        for chemin in autres[1:]:
            try:
                if os.path.getsize(chemin) == os.path.getsize(canonique):
                    os.remove(chemin)
            except OSError:
                pass
        _purger_dossiers_vides(dossier_modeles())
        return canonique
    except OSError:
        return autres[0]


def _purger_dossiers_vides(racine):
    """Un rangement qui laisse des dossiers vides derriere lui donne
    l'impression de n'avoir rien fait."""
    for dossier, _sous, _fichiers in sorted(os.walk(racine), reverse=True):
        if os.path.normcase(dossier) == os.path.normcase(racine):
            continue
        try:
            if not os.listdir(dossier):
                os.rmdir(dossier)
        except OSError:
            pass


def modele_present(modele):
    return bool(chemins_modele_existants(modele))


def libelle_modele(modele):
    """Le nom technique seul ne dit rien a un debutant, et 176 Mo sans
    contexte se lit comme un poids sur disque deja acquis. On annonce donc
    l'effet visible, puis le nom, puis ce que le choix va reellement couter."""
    fiche = MODELES[modele]
    taille = ("%.1f" % fiche["taille_mo"]).replace(".0", "").replace(".", ",")
    if fiche["taille_mo"] <= SEUIL_TELECHARGEMENT_AUTO_MO:
        cout = " (" + taille + " Mo a telecharger)"
    else:
        cout = " (" + taille + " Mo, a deposer manuellement)"
    return fiche["titre"] + " - " + modele + cout


def verifier_seuil_telechargement(modele):
    """Retourne un message d'annonce si un telechargement va avoir lieu, None
    sinon, et leve une exception si la taille depasse le seuil de la section 10."""
    if modele_present(modele):
        return None

    taille = MODELES[modele]["taille_mo"]

    if taille > SEUIL_TELECHARGEMENT_AUTO_MO:
        raise RuntimeError(
            "Le modele " + modele + " pese " + str(int(taille)) + " Mo, au-dela "
            "du seuil de " + str(SEUIL_TELECHARGEMENT_AUTO_MO) + " Mo en deca "
            "duquel le greffon telecharge seul.\n\n"
            "Telechargez le fichier " + MODELES[modele]["fichier"] + " et "
            "deposez-le dans :\n" + dossier_modeles() + "\n\n"
            "Le greffon le rangera ensuite automatiquement a l'endroit ou le "
            "moteur le cherche : inutile de creer des sous-dossiers.\n\n"
            "Ou choisissez un modele plus leger dans la liste."
        )

    return ("Telechargement du modele " + modele + " (" + str(int(taille))
            + " Mo, une seule fois)...")


def signature_environnement(variante):
    return variante + "|" + "|".join(EXIGENCES_PIP[variante])


def sonde_de_variante(variante):
    return SONDE_CUDA if variante == VARIANTE_GPU else SONDE_MODULES


def cuda_runtime_detecte():
    """Section 16 : on sonde le runtime CUDA, pas le pilote. nvcuda.dll existe
    des qu'un pilote NVIDIA est installe, y compris sans Toolkit ni cuDNN, et
    conduirait a telecharger la roue GPU pour rien."""
    if est_windows():
        return bool(racines_cuda())

    try:
        import ctypes.util
        return ctypes.util.find_library("cudart") is not None
    except Exception:
        return False


def dossier_venv(variante):
    return os.path.join(dossier_partage(), "venv-" + variante)


def python_du_venv(variante):
    if est_windows():
        return os.path.join(dossier_venv(variante), "Scripts", "python.exe")
    return os.path.join(dossier_venv(variante), "bin", "python3")


# ============================================================================
# Section 4 - marqueur d'environnement (pas d'import de validation au lancement)
# ============================================================================

def chemin_marqueur(variante):
    return os.path.join(dossier_partage(), "ai_suite_env_" + variante + ".json")


def lire_marqueur(variante):
    try:
        with open(chemin_marqueur(variante), "r", encoding="utf-8") as flux:
            return json.load(flux)
    except Exception:
        return None


def ecrire_marqueur(variante, donnees):
    try:
        with open(chemin_marqueur(variante), "w", encoding="utf-8") as flux:
            json.dump(donnees, flux, ensure_ascii=False, indent=2)
    except OSError:
        pass


def invalider_marqueur(variante):
    try:
        os.remove(chemin_marqueur(variante))
    except OSError:
        pass


def _marqueur_a_jour(variante):
    marqueur = lire_marqueur(variante)
    if not marqueur:
        return None
    if marqueur.get("version") != VERSION_GREFFON:
        return None
    if marqueur.get("signature") != signature_environnement(variante):
        return None
    return marqueur


def marqueur_valide(variante):
    marqueur = _marqueur_a_jour(variante)
    if not marqueur or marqueur.get("etat") != "pret":
        return None
    interpreteur = marqueur.get("python")
    if interpreteur and os.path.exists(interpreteur):
        return interpreteur
    return None


def marqueur_en_echec(variante):
    marqueur = _marqueur_a_jour(variante)
    if not marqueur or marqueur.get("etat") != "echec":
        return None
    return marqueur.get("message") or "cause non enregistree"


def materiel_deja_constate(variante):
    marqueur = _marqueur_a_jour(variante)
    if not marqueur:
        return None
    return marqueur.get("materiel_constate")


def enregistrer_materiel_constate(variante, materiel):
    marqueur = _marqueur_a_jour(variante)
    if not marqueur:
        return
    marqueur["materiel_constate"] = materiel
    ecrire_marqueur(variante, marqueur)


# ============================================================================
# Section 3 - detection multi-strategies, chaque candidat teste par execution
# ============================================================================

def est_stub_windowsapps(chemin):
    return "windowsapps" in chemin.lower()


def _candidats_venvs_conventionnels():
    if est_windows():
        return []
    maison = os.path.expanduser("~")
    chemins = [
        os.path.join(maison, ".local", "share", "gimp_ia_detourage", "venv", "bin", "python3"),
        os.path.join(maison, "rembg", ".venv", "bin", "python3"),
        os.path.join(maison, ".venvs", "rembg", "bin", "python3"),
        os.path.join(maison, ".virtualenvs", "rembg", "bin", "python3"),
    ]
    return [(c, CANAL_VENV) for c in chemins]


def _candidats_via_path(env):
    candidats = []
    noms = ["python", "python3"] if est_windows() else ["python3", "python"]

    if est_windows():
        for nom in noms:
            try:
                sortie = subprocess.check_output(
                    ["where", nom], text=True, stderr=subprocess.DEVNULL,
                    timeout=5, env=env, creationflags=drapeaux_creation(),
                )
                candidats += [l.strip() for l in sortie.splitlines() if l.strip()]
            except Exception:
                pass
    else:
        try:
            sortie = subprocess.check_output(
                ["which", "-a", "python3"], text=True, stderr=subprocess.DEVNULL,
                timeout=5, env=env,
            )
            candidats += [l.strip() for l in sortie.splitlines() if l.strip()]
        except Exception:
            pass

    for nom in noms:
        trouve = shutil.which(nom, path=env.get("PATH", os.defpath))
        if trouve:
            candidats.append(trouve)

    return [(c, CANAL_PATH) for c in candidats]


def _candidats_via_lanceur_py(env):
    """Le format de `py -0p` place le chemin apres le tag de version, separe par
    des espaces : un simple split()[-1] casse des que le chemin en contient."""
    if not est_windows():
        return []
    candidats = []
    try:
        sortie = subprocess.check_output(
            ["py", "-0p"], text=True, stderr=subprocess.DEVNULL,
            timeout=5, env=env, creationflags=drapeaux_creation(),
        )
        for ligne in sortie.splitlines():
            trouve = re.search(r"[A-Za-z]:\\.*?python(?:w)?\.exe", ligne, re.IGNORECASE)
            if trouve:
                candidats.append(trouve.group(0))
    except Exception:
        pass
    return [(c, "lanceur_py") for c in candidats]


def _candidats_via_registre():
    """Les deux ruches, les deux arborescences et les deux vues 32/64 bits."""
    if not est_windows():
        return []
    candidats = []
    try:
        import winreg
    except Exception:
        return []

    ruches = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    arborescences = (r"Software\Python\PythonCore", r"Software\WOW6432Node\Python\PythonCore")
    vues = (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY)

    for ruche in ruches:
        for arborescence in arborescences:
            for vue in vues:
                try:
                    racine = winreg.OpenKey(ruche, arborescence, 0, winreg.KEY_READ | vue)
                except OSError:
                    continue
                try:
                    index = 0
                    while True:
                        try:
                            version = winreg.EnumKey(racine, index)
                        except OSError:
                            break
                        index += 1
                        try:
                            cle = winreg.OpenKey(
                                racine, version + r"\InstallPath", 0, winreg.KEY_READ | vue
                            )
                        except OSError:
                            continue
                        try:
                            try:
                                chemin, _ = winreg.QueryValueEx(cle, "ExecutablePath")
                                if chemin:
                                    candidats.append(chemin)
                            except OSError:
                                pass
                            try:
                                dossier, _ = winreg.QueryValueEx(cle, "")
                                if dossier:
                                    candidats.append(os.path.join(dossier, "python.exe"))
                            except OSError:
                                pass
                        finally:
                            winreg.CloseKey(cle)
                finally:
                    winreg.CloseKey(racine)

    return [(c, "registre") for c in candidats]


def _candidats_via_scan_disque():
    if not est_windows():
        return []
    candidats = []
    local = os.environ.get("LOCALAPPDATA", "")
    programmes = os.environ.get("ProgramFiles", r"C:\Program Files")
    programmes_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    motifs = []
    if local:
        motifs.append(os.path.join(local, "Programs", "Python", "Python3*", "python.exe"))
    motifs.append(os.path.join(programmes, "Python3*", "python.exe"))
    motifs.append(os.path.join(programmes_x86, "Python3*", "python.exe"))

    for motif in motifs:
        candidats += glob.glob(motif)

    return [(c, "installation_standard") for c in candidats]


def interpreteur_embarque(chemin):
    """Heuristique : un dossier ancetre contient un executable qui n'est pas un
    outil Python, signe d'un interpreteur livre avec une application. Elle sert
    a declasser un candidat, jamais a le rejeter seule : le canal de decouverte
    reste le critere principal."""
    if not est_windows():
        return False
    autorises = ("python.exe", "pythonw.exe", "pip.exe", "py.exe", "venvlauncher.exe")
    dossier = os.path.dirname(os.path.abspath(chemin))
    for _ in range(4):
        parent = os.path.dirname(dossier)
        if not parent or parent == dossier:
            break
        dossier = parent
        try:
            contenu = os.listdir(dossier)
        except OSError:
            break
        for nom in contenu:
            if not nom.lower().endswith(".exe"):
                continue
            if nom.lower() in autorises:
                continue
            if nom.lower().startswith("python"):
                continue
            return True
    return False


def lister_candidats(env):
    """Retourne des couples (chemin, canal) dedoublonnes, existants, hors
    binaire de GIMP. Ordre : canaux fiables d'abord, puis le reste, puis les
    interpreteurs manifestement embarques, puis les stubs WindowsApps."""
    dossier_gimp = os.path.dirname(os.path.abspath(sys.executable))

    bruts = []
    bruts += _candidats_via_registre()
    bruts += _candidats_via_lanceur_py(env)
    bruts += _candidats_via_scan_disque()
    bruts += _candidats_via_path(env)
    bruts += _candidats_venvs_conventionnels()

    # Le premier canal rencontre gagne : l'ordre ci-dessus place les fiables
    # en tete, donc un meme interpreteur vu par le registre et par le PATH est
    # retenu comme venant du registre.
    connus = {}
    for chemin, canal in bruts:
        if not chemin or not os.path.exists(chemin):
            continue
        if os.path.dirname(os.path.abspath(chemin)).lower() == dossier_gimp.lower():
            continue
        cle = os.path.normcase(os.path.abspath(chemin))
        if cle not in connus:
            connus[cle] = (chemin, canal)

    fiables, autres, embarques, stubs = [], [], [], []
    for chemin, canal in connus.values():
        if est_stub_windowsapps(chemin):
            stubs.append((chemin, canal))
        elif canal in CANAUX_FIABLES:
            fiables.append((chemin, canal))
        elif interpreteur_embarque(chemin):
            embarques.append((chemin, canal + "_embarque"))
        else:
            autres.append((chemin, canal))

    return fiables + autres + embarques + stubs


def sonder_detaille(interpreteur, expression, env, delai=DELAI_SONDE_IMPORT):
    """Retourne "ok", "delai" ou "echec". Section 14 : un depassement de delai
    et un import impossible demandent deux messages differents, et les
    confondre envoie l'utilisateur sur une fausse piste."""
    try:
        resultat = subprocess.run(
            [interpreteur, "-c", expression],
            capture_output=True, timeout=delai, env=env, **options_processus()
        )
        return "ok" if resultat.returncode == 0 else "echec"
    except subprocess.TimeoutExpired:
        return "delai"
    except Exception:
        return "echec"


def _sonder(interpreteur, expression, env, delai=DELAI_SONDE_IMPORT):
    return sonder_detaille(interpreteur, expression, env, delai) == "ok"


def trouver_python_avec_ia(env, variante):
    expression = sonde_de_variante(variante)
    for interpreteur, canal in lister_candidats(env):
        if _sonder(interpreteur, expression, env):
            return interpreteur, canal
    return None, None


def _sonder_version(interpreteur, env):
    """Version majeure/mineure d'un candidat, et capacite a creer un venv,
    en une seule execution."""
    expression = (
        "import sys, venv, ensurepip;"
        "print(sys.version_info[0], sys.version_info[1])"
    )
    try:
        resultat = subprocess.run(
            [interpreteur, "-c", expression],
            capture_output=True, text=True, timeout=DELAI_SONDE,
            env=env, **options_processus()
        )
        if resultat.returncode != 0:
            return None
        morceaux = resultat.stdout.split()
        return int(morceaux[0]), int(morceaux[1])
    except Exception:
        return None


def trouver_python_bootstrap(env):
    """Python systeme capable de creer un venv. rembg n'a pas a y etre present.
    On retient la version la plus recente parmi celles validees, et on ne se
    rabat sur une version plus neuve que si aucune validee n'est disponible."""
    candidats = list(lister_candidats(env))
    deja = set(os.path.normcase(c) for c, _ in candidats)
    for repli in ("/usr/bin/python3", "/usr/local/bin/python3", "/opt/homebrew/bin/python3"):
        if os.path.exists(repli) and os.path.normcase(repli) not in deja:
            candidats.append((repli, "installation_standard"))

    # Deux paniers : les canaux fiables d'abord, le reste seulement si aucun
    # candidat fiable ne convient. L'ordre au sein d'un panier reste celui de
    # la section 3 : version validee la plus recente, puis version plus neuve.
    paniers = {True: {"validees": [], "recentes": []},
               False: {"validees": [], "recentes": []}}

    for interpreteur, canal in candidats:
        if est_stub_windowsapps(interpreteur):
            continue
        version = _sonder_version(interpreteur, env)
        if version is None or version < VERSION_PYTHON_MIN:
            continue
        panier = paniers[canal in CANAUX_FIABLES]
        cle = "validees" if version <= VERSION_PYTHON_MAX_VALIDEE else "recentes"
        panier[cle].append((version, interpreteur, canal))

    for fiable in (True, False):
        for cle in ("validees", "recentes"):
            groupe = paniers[fiable][cle]
            if groupe:
                groupe.sort(key=lambda entree: entree[0], reverse=True)
                _, interpreteur, canal = groupe[0]
                return interpreteur, canal

    return None, None


# ============================================================================
# Section 5 - Popen + polling, sortie capturee par fichier et jamais par PIPE
# ============================================================================

def _tuer_arbre(processus):
    try:
        if est_windows():
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(processus.pid)],
                capture_output=True, timeout=15, creationflags=drapeaux_creation(),
            )
        else:
            os.killpg(os.getpgid(processus.pid), signal.SIGKILL)
    except Exception:
        try:
            processus.kill()
        except Exception:
            pass


def _lire_journal(chemin):
    """Le journal melange la sortie de Python et celle des bibliotheques
    natives, qui n'utilisent pas forcement le meme encodage. Une lecture en
    UTF-8 pur rendait une partie du texte illisible, donc inexploitable pour
    diagnostiquer - alors que c'est precisement son role."""
    try:
        with open(chemin, "rb") as flux:
            brut = flux.read()
    except OSError:
        return ""
    if not brut:
        return ""
    if b"\x00" in brut[:200]:
        for codec in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                return brut.decode(codec)
            except Exception:
                pass
    for codec in ("utf-8", "cp1252", "latin-1"):
        try:
            return brut.decode(codec)
        except Exception:
            pass
    return brut.decode("utf-8", errors="replace")


def executer_avec_animation(commande, env, chemin_journal, delai, texte):
    """Retourne (code_retour, journal). code_retour vaut None en cas de depassement
    du delai. Le descripteur du journal est ferme par le `with` qui englobe la
    boucle de polling : sans cela le fichier reste verrouille sous Windows."""
    Gimp.progress_set_text(texte)

    with open(chemin_journal, "w", encoding="utf-8", errors="replace") as journal:
        processus = subprocess.Popen(
            commande, env=env, stdout=journal, stderr=subprocess.STDOUT,
            **options_processus()
        )
        debut = time.time()
        depassement = False
        try:
            while processus.poll() is None:
                Gimp.progress_pulse()
                time.sleep(INTERVALLE_POLLING)
                if time.time() - debut > delai:
                    depassement = True
                    break
        finally:
            if processus.poll() is None:
                _tuer_arbre(processus)
                try:
                    processus.wait(timeout=15)
                except Exception:
                    pass

    if depassement:
        return None, _lire_journal(chemin_journal)
    return processus.returncode, _lire_journal(chemin_journal)


# ============================================================================
# Section 14 - lecture des marqueurs et troncature du detail technique
# ============================================================================

def extraire_marqueur(journal):
    for ligne in journal.splitlines():
        ligne = ligne.strip()
        for marqueur in EXPLICATIONS_MARQUEURS:
            if ligne.startswith(marqueur):
                return marqueur, ligne[len(marqueur):].strip()
    return None, ""


def valeur_marqueur(journal, marqueur):
    for ligne in journal.splitlines():
        ligne = ligne.strip()
        if ligne.startswith(marqueur):
            return ligne[len(marqueur):].strip()
    return ""


def message_echec(journal, entete, code=None, variante=None):
    marqueur, detail = extraire_marqueur(journal)
    morceaux = [entete]

    if marqueur:
        morceaux.append(EXPLICATIONS_MARQUEURS[marqueur])
        if detail:
            morceaux.append(detail[:QUEUE_LOG_AFFICHEE])
        return "\n\n".join(morceaux)

    minuscules = journal.lower()
    if "cudnn" in minuscules:
        morceaux.append(
            "Le moteur a bien trouve CUDA mais pas cuDNN, qui est une "
            "bibliotheque distincte a installer separement depuis le site de "
            "NVIDIA. Le CUDA Toolkit ne la contient pas.\n\n"
            "Decochez l'option GPU pour travailler des maintenant sur le "
            "processeur : le resultat sera identique, seulement plus lent."
        )
    elif "out of memory" in minuscules or "cuda_error" in minuscules:
        morceaux.append(
            "La carte graphique n'a pas assez de memoire pour cette image. "
            "Essayez un modele plus leger, ou decochez l'option GPU."
        )

    queue = journal.strip()[-QUEUE_LOG_AFFICHEE:]
    if queue:
        morceaux.append(queue)
        return "\n\n".join(morceaux)

    # Section 14 : une sortie entierement vide est un diagnostic en soi. Le
    # worker emet un marqueur sur chacune de ses sorties en echec ; n'avoir
    # rien du tout signifie que le processus est mort avant d'executer la
    # moindre ligne Python, donc au chargement des bibliotheques natives.
    morceaux.append(
        "Le processus de traitement n'a produit aucune sortie et s'est "
        "termine avec le code " + str(code) + "."
    )
    morceaux.append(
        "Une sortie vide designe un arret au niveau du systeme, avant toute "
        "execution de code Python : bibliotheque native introuvable ou "
        "incompatible. Sous Windows, le code -1073741515 correspond a une DLL "
        "manquante, et -1073741795 a une instruction non supportee."
    )
    if variante == VARIANTE_GPU:
        morceaux.append(
            "L'option GPU est active : la cause la plus probable est une "
            "version de CUDA ou de cuDNN differente de celle attendue par "
            "onnxruntime-gpu. Decochez l'option pour verifier que le reste "
            "fonctionne."
        )
    morceaux.append(
        "Pour obtenir le detail, definissez la variable d'environnement "
        "IA_DETOURAGE_DEBUG=1 avant de lancer GIMP : le dossier de travail "
        "est alors conserve et son chemin affiche, ce qui permet de relancer "
        "le worker a la main depuis une invite de commandes."
    )
    return "\n\n".join(morceaux)


# ============================================================================
# Section 4 et 17 - installation et reparation de l'environnement
# ============================================================================

def espace_libre(chemin):
    """Espace du volume portant ce chemin. Remonte au premier parent existant :
    le dossier cible peut ne pas encore avoir ete cree."""
    sonde = os.path.abspath(chemin)
    while sonde and not os.path.exists(sonde):
        parent = os.path.dirname(sonde)
        if parent == sonde:
            break
        sonde = parent
    try:
        return shutil.disk_usage(sonde).free
    except Exception:
        return None


def verifier_espace_disque(chemin, variante):
    """Refuser tot vaut mieux qu'un disque plein au milieu d'un telechargement
    de plusieurs centaines de megaoctets, qui laisse en plus un environnement a
    moitie peuple."""
    requis = ESPACE_LIBRE_MINIMAL[variante]
    libre = espace_libre(chemin)
    if libre is None or libre >= requis:
        return
    go = 1024.0 * 1024.0 * 1024.0
    raison = (
        "Espace disque insuffisant pour installer le moteur IA.\n\n"
        "Requis : %.1f Go. Disponible : %.1f Go sur le volume de :\n%s\n\n"
        "Liberez de la place, puis relancez le greffon."
        % (requis / go, libre / go, chemin)
    )
    raise RuntimeError(RAISON_SEULE + raison)


def _installer_paquets(interpreteur, env, dossier_execution, variante):
    verifier_espace_disque(dossier_venv(variante), variante)

    journal_pip = os.path.join(dossier_execution, "installation_pip.log")

    executer_avec_animation(
        [interpreteur, "-m", "pip", "install", "--upgrade", "pip"],
        env, os.path.join(dossier_execution, "installation_pip_amorce.log"),
        DELAI_PIP, "Preparation de l'installeur de paquets...",
    )

    commande = [interpreteur, "-m", "pip", "install", "--only-binary=:all:"]
    commande += list(EXIGENCES_PIP[variante])

    if variante == VARIANTE_GPU:
        texte = "Installation du moteur IA pour GPU NVIDIA (long au premier lancement)..."
    else:
        texte = "Installation du module IA (plusieurs minutes au premier lancement)..."

    code, journal = executer_avec_animation(
        commande, env, journal_pip, DELAI_PIP, texte,
    )

    if code is None:
        raise RuntimeError(
            "L'installation du module IA a depasse le delai de "
            + str(DELAI_PIP // 60) + " minutes.\n\n"
            "Verifiez votre connexion Internet ou un proxy d'entreprise qui "
            "bloquerait pip, puis relancez le greffon."
        )

    if variante == VARIANTE_GPU:
        journal += "\n" + _installer_cudnn(interpreteur, env, dossier_execution)

    return journal


def _installer_cudnn(interpreteur, env, dossier_execution):
    """Tentative sans consequence : si aucune variante ne s'installe, la sonde
    d'inference le constatera et le greffon basculera sur le processeur."""
    for index, exigence in enumerate(EXIGENCES_CUDNN):
        journal_cudnn = os.path.join(
            dossier_execution, "installation_cudnn_%d.log" % index)
        code, journal = executer_avec_animation(
            [interpreteur, "-m", "pip", "install", "--only-binary=:all:",
             exigence],
            env, journal_cudnn, DELAI_PIP,
            "Installation des bibliotheques cuDNN...",
        )
        if code == 0:
            return "cuDNN installe : " + exigence
    return "Aucune variante de cuDNN n'a pu etre installee."


def preparer_moteur(dossier_execution, forcer_reinstallation, variante_demandee):
    """Retourne (interpreteur, variante_effective, avertissement).

    Une option GPU qui ne peut pas aboutir ne doit pas faire echouer le
    detourage : le calque sur processeur, accompagne d'une explication, vaut
    mieux qu'un message d'erreur. Le repli est signale, jamais silencieux.
    """
    if variante_demandee != VARIANTE_GPU:
        interpreteur = assurer_environnement(
            dossier_execution, forcer_reinstallation, VARIANTE_CPU)
        return interpreteur, VARIANTE_CPU, None

    if not cuda_runtime_detecte():
        raison = ("aucun runtime CUDA n'a ete trouve sur ce poste. Le pilote "
                  "graphique ne suffit pas : il faut le CUDA Toolkit, "
                  "telechargeable sur le site de NVIDIA.")
    else:
        try:
            interpreteur = assurer_environnement(
                dossier_execution, forcer_reinstallation, VARIANTE_GPU)
            return interpreteur, VARIANTE_GPU, None
        except Exception as erreur:
            texte = str(erreur).strip()
            if RAISON_SEULE in texte:
                raison = texte.split(RAISON_SEULE, 1)[1].strip()
            else:
                # Message non prevu pour la reprise : on ne garde que sa
                # premiere phrase, sans la queue de journal qui la suit.
                raison = texte.split("\n\n", 1)[0].strip()
            raison = raison[:QUEUE_LOG_AFFICHEE]

    interpreteur = assurer_environnement(
        dossier_execution, forcer_reinstallation, VARIANTE_CPU)
    avertissement = (
        "L'option carte graphique a ete demandee mais n'a pas pu etre "
        "utilisee : " + raison + "\n\n"
        "Le detourage a ete effectue sur le processeur. Le resultat est "
        "identique, seulement plus lent. Decochez l'option pour ne plus voir "
        "ce message."
    )
    return interpreteur, VARIANTE_CPU, avertissement


def assurer_environnement(dossier_execution, forcer_reinstallation, variante):
    """Retourne le chemin d'un interpreteur ou leve une exception explicite.
    Jamais de retour vide a gerer chez l'appelant."""
    if not forcer_reinstallation:
        interpreteur = marqueur_valide(variante)
        if interpreteur:
            return interpreteur

        echec = marqueur_en_echec(variante)
        if echec:
            raise RuntimeError(
                "Une precedente installation de l'environnement IA a echoue :\n"
                + echec + "\n\n"
                "Cochez Reinstaller l'environnement IA dans la fenetre du "
                "greffon pour relancer la tentative."
            )
    else:
        invalider_marqueur(variante)

    env = env_propre()

    Gimp.progress_set_text("Recherche d'un environnement Python...")

    if not forcer_reinstallation:
        interpreteur, canal = trouver_python_avec_ia(env, variante)
        if interpreteur:
            ecrire_marqueur(variante, {
                "version": VERSION_GREFFON,
                "signature": signature_environnement(variante),
                "python": interpreteur,
                "origine": "systeme",
                "canal": canal,
                "decouvert_le": time.strftime("%Y-%m-%d %H:%M:%S"),
                "etat": "pret",
            })
            return interpreteur

    if est_flatpak():
        raise RuntimeError(
            "GIMP fonctionne dans un bac a sable Flatpak : aucun interpreteur "
            "Python du systeme n'est accessible depuis ce bac a sable, et le "
            "greffon ne peut donc pas installer le module IA lui-meme.\n\n"
            "Utilisez une installation de GIMP native (paquet de la "
            "distribution, AppImage ou installeur officiel) pour ce greffon."
        )

    interpreteur = python_du_venv(variante)
    amorce_retenue = None
    canal_amorce = None

    if forcer_reinstallation and os.path.isdir(dossier_venv(variante)):
        Gimp.progress_set_text("Suppression de l'ancien environnement...")
        shutil.rmtree(dossier_venv(variante), ignore_errors=True)

    try:
        if not os.path.exists(interpreteur):
            amorce, canal_amorce = trouver_python_bootstrap(env)
            if not amorce:
                raise RuntimeError(
                    "Aucun interpreteur Python du systeme utilisable n'a ete "
                    "trouve pour creer l'environnement dedie a l'IA.\n\n"
                    "Le greffon a besoin de Python "
                    + ".".join(str(n) for n in VERSION_PYTHON_MIN)
                    + " ou plus recent. Installez-le depuis python.org "
                    "(Windows, macOS) ou par le gestionnaire de paquets de "
                    "votre distribution (paquets python3 et python3-venv), "
                    "puis relancez le greffon.\n\n"
                    "L'alias Python du Microsoft Store n'est pas un "
                    "interpreteur et n'est pas pris en compte."
                )

            amorce_retenue = amorce
            Gimp.progress_set_text("Creation de l'environnement dedie...")
            journal_venv = os.path.join(dossier_execution, "creation_venv.log")
            code, journal = executer_avec_animation(
                [amorce, "-m", "venv", dossier_venv(variante)],
                env, journal_venv, DELAI_CREATION_VENV,
                "Creation de l'environnement dedie...",
            )

            # La creation peut echouer sans exception : on controle le resultat
            # reel sur disque, pas seulement le code retour.
            if code is None or code != 0 or not os.path.exists(interpreteur):
                raise RuntimeError(
                    "Impossible de creer l'environnement virtuel dans :\n"
                    + dossier_venv(variante) + "\n\n"
                    + journal.strip()[-QUEUE_LOG_AFFICHEE:] + "\n\n"
                    "Sur Debian et Ubuntu, le paquet python3-venv est souvent "
                    "absent de l'installation de base."
                )

        # La validation doit porter sur la variante demandee : verifier
        # seulement l'import laisse passer un environnement GPU depourvu de
        # fournisseur CUDA, qui calcule ensuite sur le processeur en silence.
        sonde = sonde_de_variante(variante)

        if sonder_detaille(interpreteur, sonde, env) != "ok":
            journal = _installer_paquets(interpreteur, env, dossier_execution, variante)

            # L'installation vient de creer des dossiers de DLL que le PATH
            # capture plus haut ignore : les paquets nvidia-* posent leurs
            # bibliotheques dans le site-packages qui n'existait pas encore.
            # Sans ce recalcul, la validation echoue au premier lancement et ne
            # reussit qu'au suivant, ce qui est indefendable a l'usage.
            env = env_propre()

            etat = sonder_detaille(interpreteur, sonde, env)

            if etat == "delai":
                raise RuntimeError(
                    "L'installation s'est terminee, mais la verification "
                    "finale a depasse " + str(DELAI_SONDE_IMPORT // 60)
                    + " minutes.\n\n"
                    "Le premier chargement de la pile IA est long, surtout "
                    "avec un antivirus actif. Relancez le filtre : la "
                    "verification devrait aboutir, les fichiers etant "
                    "desormais en cache."
                )

            if etat != "ok" and variante == VARIANTE_GPU:
                # Distinguer un environnement casse d'un environnement complet
                # mais sans CUDA : la correction n'est pas la meme.
                if sonder_detaille(interpreteur, SONDE_MODULES, env) == "ok":
                    # Les paquets sont la, mais l'inference de validation a
                    # echoue : la cause est presque toujours cuDNN absent ou
                    # une serie CUDA differente de celle qu'attend la roue.
                    cause = "le calcul sur carte graphique n'a pas abouti"
                    if "cudnn" in journal.lower():
                        cause = ("cuDNN est introuvable. C'est une "
                                 "bibliotheque distincte du CUDA Toolkit, que "
                                 "le greffon a tente d'installer sans y "
                                 "parvenir")
                    elif "cuda" in journal.lower():
                        cause = ("la version de CUDA installee ne correspond "
                                 "pas a celle qu'attend le moteur")
                    raise RuntimeError(RAISON_SEULE + cause)

            if etat != "ok":
                raise RuntimeError(
                    "L'installation du module IA s'est terminee sans erreur "
                    "mais le module reste inutilisable.\n\n"
                    + journal.strip()[-QUEUE_LOG_AFFICHEE:]
                )

    except Exception as erreur:
        ecrire_marqueur(variante, {
            "version": VERSION_GREFFON,
            "signature": signature_environnement(variante),
            "python": interpreteur,
            "origine": "venv",
            "amorce": amorce_retenue,
            "canal": canal_amorce,
            "decouvert_le": time.strftime("%Y-%m-%d %H:%M:%S"),
            "etat": "echec",
            "message": str(erreur)[:QUEUE_LOG_AFFICHEE],
        })
        raise

    # Section 24 : consigner le canal et la date. Un chemin d'interpreteur seul
    # ne permet pas, trois mois plus tard, de savoir comment il a ete trouve ni
    # s'il faut fermer cette voie.
    ecrire_marqueur(variante, {
        "version": VERSION_GREFFON,
        "signature": signature_environnement(variante),
        "python": interpreteur,
        "origine": "venv",
        "amorce": amorce_retenue,
        "canal": canal_amorce,
        "decouvert_le": time.strftime("%Y-%m-%d %H:%M:%S"),
        "etat": "pret",
    })
    return interpreteur


# ============================================================================
# Section 7 et 19 - helpers d'API GIMP
# ============================================================================

def est_precision_8_bits(precision):
    """GIMP 3 expose plusieurs precisions 8 bits (lineaire, non lineaire,
    perceptuelle). N'importe laquelle convient a un export PNG ; convertir vers
    une autre variante 8 bits ne ferait que toucher a la gestion du gamma."""
    for nom in ("U8_LINEAR", "U8_NON_LINEAR", "U8_PERCEPTUAL"):
        valeur = getattr(Gimp.Precision, nom, None)
        if valeur is not None and precision == valeur:
            return True
    return False


def lire_option(config, nom, defaut):
    """Si l'argument n'a pas pu etre enregistre, la valeur par defaut s'applique
    et le greffon reste fonctionnel."""
    try:
        valeur = config.get_property(nom)
    except Exception:
        return defaut
    return defaut if valeur is None else valeur


def lire_decalages(drawable):
    """Section 19 : ne jamais lire un tuple d'API par indice fixe. On filtre les
    booleens et on retient les deux derniers entiers."""
    try:
        resultat = drawable.get_offsets()
    except Exception:
        return 0, 0
    if isinstance(resultat, (tuple, list)):
        entiers = [v for v in resultat if isinstance(v, int) and not isinstance(v, bool)]
        if len(entiers) >= 2:
            return entiers[-2], entiers[-1]
    return 0, 0


def normaliser_calques(resultat):
    if resultat is None:
        return []
    if isinstance(resultat, (list, tuple)):
        return [element for element in resultat if hasattr(element, "set_name")]
    if hasattr(resultat, "set_name"):
        return [resultat]
    return []


def _essayer_sauvegarde(image, drawable, fichier, chemin):
    """Chaque variante connue est tentee, puis le resultat reel est verifie :
    une variante peut ne lever aucune exception sans produire de fichier."""
    variantes = (
        lambda: Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, fichier, None),
        lambda: Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, fichier),
        lambda: Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, [drawable], fichier),
        lambda: Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, 1, [drawable], fichier),
    )

    for variante in variantes:
        try:
            variante()
        except Exception:
            pass
        if os.path.exists(chemin) and os.path.getsize(chemin) > 0:
            return True
        try:
            os.remove(chemin)
        except OSError:
            pass

    return False


def exporter_drawable(image, drawable, chemin):
    """Exporte le seul calque selectionne, pas le composite visible, en 8 bits."""
    fichier = Gio.File.new_for_path(chemin)
    image_tampon = None

    try:
        image_tampon = Gimp.Image.new(
            drawable.get_width(), drawable.get_height(), image.get_base_type()
        )
        copie = Gimp.Layer.new_from_drawable(drawable, image_tampon)
        image_tampon.insert_layer(copie, None, 0)

        try:
            copie.set_offsets(0, 0)
        except Exception:
            pass
        try:
            if image.get_base_type() == Gimp.ImageBaseType.INDEXED:
                image_tampon.convert_rgb()
        except Exception:
            pass
        try:
            copie.add_alpha()
        except Exception:
            pass
        try:
            # Section 20 : un PNG 16 bits relu en uint16 blanchit l'image. Mais
            # convert_precision echoue si l'image est deja a la precision
            # demandee, et GIMP journalise ce refus dans la console d'erreurs
            # avant meme que le try/except ne recupere la main. On ne convertit
            # donc que si la precision n'est pas deja sur 8 bits.
            if not est_precision_8_bits(image_tampon.get_precision()):
                image_tampon.convert_precision(Gimp.Precision.U8_NON_LINEAR)
        except Exception:
            pass

        if _essayer_sauvegarde(image_tampon, copie, fichier, chemin):
            return True
    except Exception:
        pass
    finally:
        if image_tampon is not None:
            try:
                image_tampon.delete()
            except Exception:
                pass

    # Repli : export du composite si la duplication du calque est impossible
    # (cas d'un masque ou d'un canal selectionne).
    return _essayer_sauvegarde(image, drawable, fichier, chemin)


def charger_calque_resultat(image, chemin, nom):
    fichier = Gio.File.new_for_path(chemin)

    if hasattr(Gimp, "file_load_layers"):
        try:
            calques = normaliser_calques(
                Gimp.file_load_layers(Gimp.RunMode.NONINTERACTIVE, image, fichier)
            )
            if calques:
                return calques[0]
        except Exception:
            pass

    if hasattr(Gimp, "file_load_layer"):
        try:
            calques = normaliser_calques(
                Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, fichier)
            )
            if calques:
                return calques[0]
        except Exception:
            pass

    # Repli complet : image temporaire puis extraction du visible. Ne jamais
    # retourner SUCCESS sans avoir insere quoi que ce soit.
    image_chargee = None
    for tentative in (
        lambda: Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, fichier),
        lambda: Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, fichier, None),
    ):
        try:
            image_chargee = tentative()
            if image_chargee is not None:
                break
        except Exception:
            continue

    if image_chargee is None:
        return None

    try:
        return Gimp.Layer.new_from_visible(image_chargee, image, nom)
    except Exception:
        return None
    finally:
        try:
            image_chargee.delete()
        except Exception:
            pass


# ============================================================================
# Greffon
# ============================================================================

class IaDetouragePlugin(Gimp.PlugIn):
    __gtype_name__ = 'IaDetouragePlugin'

    def do_set_i18n(self, nom_procedure):
        return False

    def do_query_procedures(self):
        journaliser("do_query_procedures appele")
        return [NOM_PROCEDURE]

    def do_create_procedure(self, name):
        try:
            return self._creer_procedure(name)
        except Exception as erreur:
            journaliser("do_create_procedure a echoue", erreur)
            raise

    def _creer_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, self.run, None
        )

        # Ces appels n'etaient pas proteges : une exception sur l'un d'eux fait
        # disparaitre le greffon des menus sans le moindre message.
        appel_protege("set_image_types", procedure.set_image_types, "*")

        appel_protege("set_menu_label", procedure.set_menu_label,
                      "Detourer le calque (IA)...")

        if not appel_protege("add_menu_path", procedure.add_menu_path,
                             "<Image>/Layer/Transparency/"):
            appel_protege("add_menu_path repli", procedure.add_menu_path,
                          "<Image>/Filters/")

        appel_protege(
            "set_documentation", procedure.set_documentation,
            "Detoure le calque selectionne par un modele IA",
            "Exporte le calque, le traite par rembg dans un processus separe, "
            "puis reinjecte le resultat comme nouveau calque.",
            name,
        )
        appel_protege("set_attribution", procedure.set_attribution,
                      "Miguel Pineau", "Miguel Pineau", "2026")

        # Section 7 : chaque ajout est isole. Un echec d'enregistrement ne doit
        # jamais empecher le greffon d'apparaitre dans le menu.
        try:
            choix = Gimp.Choice.new()
            for rang, nom_modele in enumerate(MODELES_AUTORISES):
                choix.add(
                    nom_modele, rang, libelle_modele(nom_modele),
                    "Telecharge automatiquement au premier usage"
                    if MODELES[nom_modele]["taille_mo"] <= SEUIL_TELECHARGEMENT_AUTO_MO
                    else "A deposer manuellement dans le dossier des modeles",
                )
            procedure.add_choice_argument(
                "modele", "Modele de detourage",
                "Determine la qualite du contour et la duree du traitement",
                choix, MODELE_DEFAUT, GObject.ParamFlags.READWRITE
            )
        except Exception:
            pass

        try:
            procedure.add_boolean_argument(
                "alpha-matting", "Affiner les contours (plus lent)",
                "Retravaille la bordure du detourage. Active les trois reglages "
                "suivants, sans effet tant que cette case est decochee.",
                ALPHA_MATTING_DEFAUT, GObject.ParamFlags.READWRITE
            )
        except Exception:
            pass

        try:
            procedure.add_int_argument(
                "fg-threshold", "Certitude pour garder un pixel",
                "Plus la valeur est haute, plus le greffon doit etre sur avant "
                "de conserver un pixel (0-255)",
                0, 255, SEUIL_AVANT_PLAN_DEFAUT, GObject.ParamFlags.READWRITE
            )
        except Exception:
            pass

        try:
            procedure.add_int_argument(
                "bg-threshold", "Certitude pour effacer un pixel",
                "Plus la valeur est basse, plus le greffon doit etre sur avant "
                "d'effacer un pixel (0-255)",
                0, 255, SEUIL_ARRIERE_PLAN_DEFAUT, GObject.ParamFlags.READWRITE
            )
        except Exception:
            pass

        try:
            procedure.add_int_argument(
                "erode-size", "Largeur de la zone incertaine",
                "Epaisseur de la bordure sur laquelle le contour est recalcule "
                "(0-255)",
                0, 255, EROSION_DEFAUT, GObject.ParamFlags.READWRITE
            )
        except Exception:
            pass

        try:
            procedure.add_boolean_argument(
                "gpu", "Utiliser la carte graphique NVIDIA (installation supplementaire)",
                "Decochee, le calcul se fait sur le processeur, meme si une "
                "carte est disponible. Cochee, le greffon installe un moteur "
                "distinct, nettement plus volumineux, et demande explicitement "
                "le fournisseur CUDA. Sans runtime CUDA sur le poste, l'option "
                "est refusee avant tout telechargement.",
                GPU_DEFAUT, GObject.ParamFlags.READWRITE
            )
        except Exception:
            pass

        try:
            procedure.add_boolean_argument(
                "reinstaller", "Reparer l'installation (si le filtre ne fonctionne plus)",
                "Reconstruit entierement les composants installes par le "
                "greffon avant de lancer le traitement",
                REINSTALLER_DEFAUT, GObject.ParamFlags.READWRITE
            )
        except Exception as erreur:
            journaliser("add_boolean_argument reinstaller", erreur)

        return procedure

    def run(self, procedure, run_mode, image, drawables, config, run_data):
        if len(drawables) != 1:
            Gimp.message("Veuillez selectionner un seul calque.")
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR, GLib.Error()
            )

        drawable = drawables[0]

        if run_mode == Gimp.RunMode.INTERACTIVE:
            try:
                gi.require_version('GimpUi', '3.0')
                from gi.repository import GimpUi

                GimpUi.init("ia_detourage")
                dialogue = GimpUi.ProcedureDialog.new(procedure, config)

                # Les trois seuils n'ont aucun effet tant que l'affinage est
                # decoche. Les laisser actifs conduit l'utilisateur a les
                # regler sans rien constater, sans moyen de comprendre.
                # La signature de set_sensitive a varie entre revisions : en
                # cas d'echec, les champs restent simplement actifs.
                for nom_champ in ("fg-threshold", "bg-threshold", "erode-size"):
                    try:
                        dialogue.set_sensitive(
                            nom_champ, False, config, "alpha-matting", False
                        )
                    except Exception:
                        try:
                            dialogue.set_sensitive(nom_champ, False, config,
                                                   "alpha-matting")
                        except Exception:
                            pass

                dialogue.fill(None)
                accepte = dialogue.run()
                dialogue.destroy()
                if not accepte:
                    return procedure.new_return_values(
                        Gimp.PDBStatusType.CANCEL, GLib.Error()
                    )
            except Exception as erreur:
                Gimp.message("Impossible d'afficher la fenetre du greffon :\n" + str(erreur))
                return procedure.new_return_values(
                    Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error()
                )

        modele = str(lire_option(config, "modele", MODELE_DEFAUT))
        if modele not in MODELES_AUTORISES:
            modele = MODELE_DEFAUT

        parametres = {
            "modele": modele,
            "alpha_matting": bool(lire_option(config, "alpha-matting", ALPHA_MATTING_DEFAUT)),
            "seuil_avant_plan": int(lire_option(config, "fg-threshold", SEUIL_AVANT_PLAN_DEFAUT)),
            "seuil_arriere_plan": int(lire_option(config, "bg-threshold", SEUIL_ARRIERE_PLAN_DEFAUT)),
            "erosion": int(lire_option(config, "erode-size", EROSION_DEFAUT)),
        }
        reinstaller = bool(lire_option(config, "reinstaller", REINSTALLER_DEFAUT))
        variante = VARIANTE_GPU if bool(lire_option(config, "gpu", GPU_DEFAUT)) else VARIANTE_CPU

        # Section 13 : un dossier unique par execution, contenant l'image source,
        # la sortie, le script worker, les parametres et tous les journaux.
        dossier_execution = tempfile.mkdtemp(prefix="gimp_ia_detourage_")

        # Section 7 : deux drapeaux, pour ne depiler que ce qui a ete empile.
        contexte_empile = False
        groupe_annulation_ouvert = False

        try:
            Gimp.progress_init("Exportation du calque...")

            chemin_entree = os.path.join(dossier_execution, "entree.png")
            chemin_sortie = os.path.join(dossier_execution, "sortie.png")
            chemin_params = os.path.join(dossier_execution, "parametres.json")
            chemin_worker = os.path.join(dossier_execution, "worker.py")
            chemin_journal = os.path.join(dossier_execution, "worker.log")

            if not exporter_drawable(image, drawable, chemin_entree):
                raise RuntimeError(
                    "L'exportation du calque vers un fichier temporaire a echoue.\n\n"
                    "Aucune variante connue de Gimp.file_save n'a produit de "
                    "fichier exploitable dans :\n" + dossier_execution
                )

            interpreteur, variante, avertissement_moteur = preparer_moteur(
                dossier_execution, reinstaller, variante)

            parametres["fournisseurs"] = list(FOURNISSEURS[variante])
            parametres["entree"] = chemin_entree
            parametres["sortie"] = chemin_sortie

            with open(chemin_params, "w", encoding="utf-8") as flux:
                json.dump(parametres, flux, ensure_ascii=False)

            with open(chemin_worker, "w", encoding="utf-8", newline="\n") as flux:
                flux.write(CODE_WORKER)

            # Section 10 : le seuil est controle avant de lancer le worker, pour
            # que le refus soit explicite plutot qu'un telechargement subi.
            normaliser_emplacement_modele(modele)
            annonce = verifier_seuil_telechargement(modele)
            texte_animation = annonce or "Detourage IA en cours..."

            code, journal = executer_avec_animation(
                [interpreteur, chemin_worker, chemin_params],
                env_propre(), chemin_journal, DELAI_WORKER,
                texte_animation,
            )

            if code is None:
                raise RuntimeError(
                    "Le detourage a depasse le delai de "
                    + str(DELAI_WORKER // 60) + " minutes et a ete interrompu.\n\n"
                    "Reessayez sur une image plus petite, ou avec le modele "
                    "u2netp et sans Alpha Matting."
                )

            if MARQUEUR_ERR_IMPORT in journal:
                invalider_marqueur(variante)
                raise RuntimeError(
                    "Le module IA n'est plus importable dans l'environnement "
                    "enregistre. La detection a ete reinitialisee.\n\n"
                    "Relancez simplement le greffon : il reconstruira "
                    "l'environnement automatiquement."
                )

            # Section 12 : le succes se mesure a la production d'un fichier de
            # sortie non vide, pas au code retour ni a la reussite de l'IA.
            if not (os.path.exists(chemin_sortie) and os.path.getsize(chemin_sortie) > 0):
                raise RuntimeError(
                    message_echec(journal, "Le detourage a echoue.",
                                  code, variante))

            moteur = valeur_marqueur(journal, MARQUEUR_MOTEUR) or modele
            materiel = valeur_marqueur(journal, MARQUEUR_MATERIEL) or "materiel inconnu"

            # Section 18 : l'ecart entre ce qui a ete demande et ce qui a ete
            # constate est signale une fois, puis memorise. Le nom du calque
            # reste ensuite la seule trace.
            avertissement = avertissement_moteur
            if (avertissement is None and variante == VARIANTE_GPU
                    and materiel == "processeur"
                    and materiel_deja_constate(variante) != materiel):
                avertissement = (
                    "L'option GPU NVIDIA est active, mais le calcul s'est fait "
                    "sur le processeur : le moteur n'a pas pu enregistrer le "
                    "fournisseur CUDA.\n\n"
                    "Le dossier bin du CUDA Toolkit est pourtant expose au moteur. "
                    "Verifiez la presence des DLL cuDNN 9 a cote, et que la "
                    "version du Toolkit correspond a celle attendue par "
                    "onnxruntime-gpu. "
                    "Ce message ne sera plus affiche."
                )
            enregistrer_materiel_constate(variante, materiel)

            Gimp.progress_set_text("Integration du resultat...")

            # Section 20 : le nom du calque est la seule trace persistante.
            nom_calque = drawable.get_name() + " (" + moteur + " sur " + materiel + ")"
            calque = charger_calque_resultat(image, chemin_sortie, nom_calque)

            if calque is None:
                raise RuntimeError(
                    "Le detourage a reussi mais le fichier resultat n'a pas pu "
                    "etre reimporte dans GIMP.\n\n"
                    "Aucune variante de chargement de calque n'est disponible "
                    "dans cette version de GIMP."
                )

            decalage_x, decalage_y = lire_decalages(drawable)

            Gimp.context_push()
            contexte_empile = True
            image.undo_group_start()
            groupe_annulation_ouvert = True

            parent = None
            try:
                parent = drawable.get_parent()
            except Exception:
                parent = None

            try:
                position = image.get_item_position(drawable)
            except Exception:
                position = 0

            calque.set_name(nom_calque)
            image.insert_layer(calque, parent, position)
            try:
                calque.set_offsets(decalage_x, decalage_y)
            except Exception:
                pass

            Gimp.displays_flush()
            Gimp.progress_end()

            if avertissement:
                Gimp.message(avertissement)

            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

        except Exception as erreur:
            try:
                Gimp.progress_end()
            except Exception:
                pass
            texte = "Greffon de detourage IA :\n\n" + str(erreur).replace(
                RAISON_SEULE, "")
            archive = archiver_journaux(dossier_execution)
            if archive:
                texte += (
                    "\n\nLes fichiers de diagnostic ont ete copies dans :\n"
                    + archive + "\n\n"
                    "Ce dossier est essentiel pour comprendre la panne : il "
                    "contient le journal du traitement et les parametres "
                    "employes. Joignez-le a tout signalement, sans quoi le "
                    "probleme ne peut pas etre reproduit."
                )
            if conserver_fichiers_travail():
                texte += "\n\nFichiers de travail conserves dans :\n" + dossier_execution
            Gimp.message(texte)
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error()
            )

        finally:
            if groupe_annulation_ouvert:
                try:
                    image.undo_group_end()
                except Exception:
                    pass
            if contexte_empile:
                try:
                    Gimp.context_pop()
                except Exception:
                    pass
            if not conserver_fichiers_travail():
                shutil.rmtree(dossier_execution, ignore_errors=True)


if __name__ == '__main__':
    try:
        Gimp.main(IaDetouragePlugin.__gtype__, sys.argv)
    except Exception as erreur:
        journaliser("Gimp.main a echoue", erreur)
        raise
