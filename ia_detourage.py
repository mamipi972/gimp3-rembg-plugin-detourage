#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import tempfile
import subprocess
import time
import gi

# === CONFIGURATION UTILISATEUR ============================================
# Chemin absolu (pour vos tests locaux actuels) :
CHEMIN_PYTHON = r"C:\Users\name\AppData\Local\Programs\Python\Python314\python.exe"

# ⚠️ Pour la version publique à distribuer, remettez simplement : 
# CHEMIN_PYTHON = "python"
# ==========================================================================

gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

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
            
            Gimp.progress_set_text("Détourage IA en arrière-plan...")
            
            python_exe = CHEMIN_PYTHON
            
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

# L'IA détecte automatiquement CPU ou GPU en fonction de ce qui est installé
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
                
            cmd = [python_exe, script_path]

# --- NETTOYAGE DE LA BULLE GIMP ---
            env_windows = os.environ.copy()
            env_windows.pop('PYTHONPATH', None)
            env_windows.pop('PYTHONHOME', None)
            
            # On supprime GIMP du PATH pour forcer Windows à utiliser le vrai Python
            if 'PATH' in env_windows:
                chemins = env_windows['PATH'].split(os.pathsep)
                chemins_propres = [c for c in chemins if 'gimp' not in c.lower()]
                env_windows['PATH'] = os.pathsep.join(chemins_propres)
# ----------------------------------

            # --- Lancement en arrière-plan sans bloquer GIMP ---
            process = subprocess.Popen(
                cmd, 
                env=env_windows, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                creationflags=0x08000000
            )
           
            # Boucle d'attente : on anime la barre tant que l'IA travaille
            while process.poll() is None:
                Gimp.progress_pulse()  # Fait faire un va-et-vient à la barre
                time.sleep(0.2)        # Courte pause de 200ms
            
            # L'IA a terminé, on récupère le texte de la console
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                if "ERREUR_MODULE_MANQUANT" in stderr:
                    raise Exception("Le module IA n'a pas été trouvé par Python.\n\nVeuillez ouvrir l'Invite de commandes (cmd) Windows et taper exactement :\npip install \"rembg[cpu,cli]\"")
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
            # Fermeture de sécurité du groupe d'annulation (empêche l'erreur 'inconsistent state')
            try:
                image.undo_group_end()
                Gimp.context_pop()
            except:
                pass
                
            Gimp.message(f"Erreur du greffon IA :\n{str(e)}")
            return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error())

if __name__ == '__main__':
    Gimp.main(IaDetouragePlugin.__gtype__, sys.argv)
