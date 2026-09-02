#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import glob
import tempfile
import subprocess
import time
import shutil
import venv
import gi

gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio


# ============================================================================
# Utilitaires environnement / cache
# ============================================================================

def _creation_flags():
    """Flag pour éviter l'ouverture d'une fenêtre console sur Windows. 0 ailleurs."""
    return 0x08000000 if os.name == "nt" else 0


def get_cache_path():
    """Retourne le chemin du fichier de cache de l'environnement Python."""
    try:
        return os.path.join(Gimp.directory(), "ia_detourage_python_cache.txt")
    except Exception:
        return os.path.join(tempfile.gettempdir(), "gimp_ia_detourage_python_cache.txt")


def get_clean_env():
    """Nettoie les variables d'environnement héritées de GIMP."""
    env_clean = os.environ.copy()
    env_clean.pop('PYTHONPATH', None)
    env_clean.pop('PYTHONHOME', None)

    if 'PATH' in env_clean:
        chemins = env_clean['PATH'].split(os.pathsep)
        chemins_propres = [c for c in chemins if 'gimp' not in c.lower()]
        env_clean['PATH'] = os.pathsep.join(chemins_propres)

    return env_clean


def invalidate_cache():
    cache_file = get_cache_path()
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
        except OSError:
            pass


# ============================================================================
# Stratégies de recherche d'un interpréteur Python
# ============================================================================

def _candidats_via_conventions_unix():
    """Stratégie A (Linux/macOS) : Vérifie les emplacements venv habituels
    au cas où l'utilisateur en aurait déjà créé un (ex: l'abonné Eric)."""
    if os.name == "nt":
        return []
    
    home = os.path.expanduser("~")
    candidats = [
        os.path.join(home, ".local", "share", "gimp_ia_detourage", "venv", "bin", "python3"),
        os.path.join(home, "rembg", ".venv", "bin", "python3"),
        os.path.join(home, ".venvs", "rembg", "bin", "python3"),
        os.path.join(home, ".virtualenvs", "rembg", "bin", "python3")
    ]
    return candidats


def _candidats_via_path(env_clean):
    candidats = []
    noms_commande = ["python3", "python"] if os.name != "nt" else ["python", "python3"]

    if os.name == "nt":
        for cmd in noms_commande:
            try:
                out = subprocess.check_output(
                    ["where", cmd], text=True, stderr=subprocess.DEVNULL,
                    creationflags=_creation_flags(), timeout=5, env=env_clean
                )
                candidats += [l.strip() for l in out.splitlines() if l.strip()]
            except Exception:
                pass
    else:
        try:
            out = subprocess.check_output(
                ["which", "-a", "python3"], text=True, stderr=subprocess.DEVNULL,
                timeout=5, env=env_clean
            )
            candidats += [l.strip() for l in out.splitlines() if l.strip()]
        except Exception:
            pass

    for cmd in noms_commande:
        found = shutil.which(cmd, path=env_clean.get('PATH', os.defpath))
        if found:
            candidats.append(found)

    return candidats


def _candidats_via_py_launcher(env_clean):
    if os.name != "nt": return []
    candidats = []
    try:
        out = subprocess.check_output(
            ["py", "-0p"], text=True, stderr=subprocess.DEVNULL,
            creationflags=_creation_flags(), timeout=5, env=env_clean
        )
        for ligne in out.splitlines():
            ligne = ligne.strip()
            if ligne.lower().endswith("python.exe"):
                chemin = ligne.split()[-1]
                candidats.append(chemin)
    except Exception:
        pass
    return candidats


def _candidats_via_registre():
    if os.name != "nt": return []
    candidats = []
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                racine = winreg.OpenKey(hive, r"Software\Python\PythonCore")
            except OSError:
                continue
            try:
                i = 0
                while True:
                    try:
                        version = winreg.EnumKey(racine, i)
                    except OSError:
                        break
                    i += 1
                    try:
                        chemin_key = winreg.OpenKey(racine, f"{version}\\InstallPath")
                        chemin, _ = winreg.QueryValueEx(chemin_key, "ExecutablePath")
                        candidats.append(chemin)
                    except OSError:
                        continue
            finally:
                winreg.CloseKey(racine)
    except Exception:
        pass
    return candidats


def _candidats_via_scan_disque():
    if os.name != "nt": return []
    candidats = []
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    motifs = []
    if local_appdata:
        motifs.append(os.path.join(local_appdata, "Programs", "Python", "Python3*", "python.exe"))
    motifs.append(os.path.join(program_files, "Python3*", "python.exe"))
    motifs.append(os.path.join(program_files_x86, "Python3*", "python.exe"))

    for motif in motifs:
        candidats += glob.glob(motif)

    return candidats


def find_valid_python():
    gimp_bin = os.path.dirname(sys.executable)
    env_clean = get_clean_env()

    candidats = []
    candidats += _candidats_via_conventions_unix()
    candidats += _candidats_via_path(env_clean)
    candidats += _candidats_via_py_launcher(env_clean)
    candidats += _candidats_via_registre()
    candidats += _candidats_via_scan_disque()

    candidats = list(dict.fromkeys(candidats))

    for exe in candidats:
        if not exe or not os.path.exists(exe):
            continue
        if os.path.dirname(exe).lower() == gimp_bin.lower():
            continue

        try:
            r = subprocess.run(
                [exe, "-c", "import rembg"], capture_output=True,
                timeout=10, creationflags=_creation_flags(), env=env_clean
            )
            if r.returncode == 0:
                return exe
        except Exception:
            continue

    return None


def get_cached_python(force_refresh=False):
    cache_file = get_cache_path()

    if not force_refresh and os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_exe = f.read().strip()
        if cached_exe and os.path.exists(cached_exe):
            return cached_exe

    exe = find_valid_python()
    if exe:
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(exe)
    else:
        invalidate_cache()
    return exe


# ============================================================================
# Création automatique de l'environnement virtuel (Linux/macOS)
# ============================================================================

def setup_unix_venv():
    """Option B : Crée un venv dédié et installe les dépendances."""
    home = os.path.expanduser("~")
    venv_dir = os.path.join(home, ".local", "share", "gimp_ia_detourage", "venv")
    python_exe = os.path.join(venv_dir, "bin", "python3")

    if not os.path.exists(venv_dir):
        Gimp.progress_set_text("Création de l'environnement virtuel local...")
        try:
            venv.create(venv_dir, with_pip=True)
        except Exception as e:
            raise Exception(
                f"Impossible de créer l'environnement virtuel.\n"
                f"Sur certaines distributions (comme Ubuntu), il manque le paquet de base.\n"
                f"Ouvrez un terminal et tapez :\nsudo apt install python3-venv\n\nDétail: {e}"
            )

    Gimp.progress_set_text("Installation du module IA (peut durer plusieurs minutes)...")
    env_clean = get_clean_env()
    
    # Installation de rembg et onnxruntime pour l'optimisation matérielle
    process = subprocess.Popen(
        [python_exe, "-m", "pip", "install", "--upgrade", "pip", "rembg[cpu,cli]", "onnxruntime"],
        env=env_clean,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    while process.poll() is None:
        Gimp.progress_pulse()
        time.sleep(0.2)

    if process.returncode != 0:
        _, stderr = process.communicate()
        raise Exception(f"Erreur lors de l'installation des dépendances IA :\n{stderr}")

    return python_exe


# ============================================================================
# Plugin GIMP
# ============================================================================

class IaDetouragePlugin(Gimp.PlugIn):
    __gtype_name__ = 'IaDetouragePlugin'

    def do_query_procedures(self):
        return ["python-fu-ia-detourage"]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, self.run, None)
        procedure.set_image_types("*")
        procedure.set_menu_label("Détourer le calque (IA)...")
        procedure.add_menu_path("<Image>/Layer/Transparency/")
        procedure.set_attribution("Miguel Pineau", "Miguel Pineau", "2026")

        procedure.add_boolean_argument("alpha-matting", "Améliorer les détails fins (Alpha Matting)", "Plus lent", False, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("fg-threshold", "Seuil d'avant-plan", "(0-255)", 0, 255, 240, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("bg-threshold", "Seuil d'arrière-plan", "(0-255)", 0, 255, 10, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("erode-size", "Taille d'érosion", "(0-255)", 0, 255, 10, GObject.ParamFlags.READWRITE)

        return procedure

    def run(self, procedure, run_mode, image, drawables, config, run_data):
        try:
            if len(drawables) != 1:
                Gimp.message("Veuillez sélectionner un seul calque.")
                return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, GLib.Error())

            drawable = drawables[0]

            if run_mode == Gimp.RunMode.INTERACTIVE:
                gi.require_version('GimpUi', '3.0')
                from gi.repository import GimpUi

                GimpUi.init("ia_detourage")
                dialog = GimpUi.ProcedureDialog.new(procedure, config)
                dialog.fill(None)
                if not dialog.run():
                    dialog.destroy()
                    return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
                dialog.destroy()

            use_alpha_matting = config.get_property("alpha-matting")
            fg_thresh = config.get_property("fg-threshold")
            bg_thresh = config.get_property("bg-threshold")
            erode_val = config.get_property("erode-size")

            Gimp.context_push()
            image.undo_group_start()

            temp_dir = tempfile.gettempdir()
            file_in_path = os.path.join(temp_dir, "gimp_rembg_in.png")
            file_out_path = os.path.join(temp_dir, "gimp_rembg_out.png")

            Gimp.progress_init("Exportation du calque...")
            file_in = Gio.File.new_for_path(file_in_path)

            try:
                Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, file_in)
            except Exception:
                Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, file_in, None)

            Gimp.progress_set_text("Recherche de l'environnement Python...")
            python_exe = get_cached_python()

            if not python_exe:
                if os.name == "nt":
                    raise Exception(
                        "Le module IA n'a pas été trouvé dans les environnements Python de "
                        "votre système.\n\nVeuillez ouvrir l'Invite de commandes (cmd) Windows "
                        "et taper exactement :\npip install \"rembg[cpu,cli]\""
                    )
                else:
                    # Linux/macOS : On lance l'auto-installation
                    python_exe = setup_unix_venv()
                    if python_exe:
                        # Mise à jour du cache
                        with open(get_cache_path(), 'w', encoding='utf-8') as f:
                            f.write(python_exe)
                    else:
                        raise Exception("L'installation automatique de l'environnement virtuel a échoué.")

            Gimp.progress_set_text("Détourage IA en arrière-plan...")

            script_path = os.path.join(temp_dir, "run_rembg_worker.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(f"""
import sys
try:
    from rembg import remove, new_session
    from PIL import Image
except ImportError:
    print("ERREUR_MODULE_MANQUANT", file=sys.stderr)
    sys.exit(1)

session = new_session('u2netp')
img = Image.open(r"{file_in_path}")
out = remove(
    img,
    session=session,
    alpha_matting={use_alpha_matting},
    alpha_matting_foreground_threshold={fg_thresh},
    alpha_matting_background_threshold={bg_thresh},
    alpha_matting_erode_size={erode_val}
)
out.save(r"{file_out_path}")
""")

            env_clean = get_clean_env()

            process = subprocess.Popen(
                [python_exe, script_path],
                env=env_clean,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=_creation_flags()
            )

            while process.poll() is None:
                Gimp.progress_pulse()
                time.sleep(0.2)

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                if "ERREUR_MODULE_MANQUANT" in stderr:
                    invalidate_cache()
                    raise Exception(
                        "Le module IA n'a pas été trouvé par Python. Le cache a été réinitialisé.\n"
                        "Veuillez relancer le greffon pour déclencher une nouvelle configuration."
                    )
                else:
                    raise Exception(f"Détail technique du plantage :\n{stderr}")

            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except OSError:
                    pass

            Gimp.progress_set_text("Intégration du résultat...")
            file_out = Gio.File.new_for_path(file_out_path)

            new_layers = None
            if hasattr(Gimp, 'file_load_layers'):
                new_layers = Gimp.file_load_layers(Gimp.RunMode.NONINTERACTIVE, image, file_out)
            else:
                new_layers = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, file_out)

            if new_layers:
                new_layer = new_layers[0]
                new_layer.set_name(f"{drawable.get_name()} (détouré)")
                position = image.get_item_position(drawable)
                image.insert_layer(new_layer, None, position)

            for p in [file_in_path, file_out_path]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

            image.undo_group_end()
            Gimp.context_pop()
            Gimp.displays_flush()

            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

        except Exception as e:
            try:
                image.undo_group_end()
                Gimp.context_pop()
            except Exception:
                pass

            Gimp.message(f"Erreur du greffon IA :\n{str(e)}")
            return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error())


if __name__ == '__main__':
    Gimp.main(IaDetouragePlugin.__gtype__, sys.argv)
