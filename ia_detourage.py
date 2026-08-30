#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import tempfile
import subprocess
import gi

# === CONFIGURATION UTILISATEUR ============================================
# Par défaut, utilise le Python déclaré dans le PATH de Windows.
# Si une erreur survient, remplacez "python" par votre chemin absolu.
# Exemple : CHEMIN_PYTHON = r"C:\Users\nom\AppData\Local\Programs\Python\Python31\python.exe"
# CHEMIN_PYTHON = r"C:\Users\votre_nom\AppData\Local\Programs\Python\Python314\python.exe"
# CHEMIN_PYTHON = "python"
CHEMIN_PYTHON = "python"
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
            
            # Utilisation de la configuration définie en haut du fichier
            python_exe = CHEMIN_PYTHON
            
            # Création d'un script Python temporaire pour forcer l'usage du GPU (CUDA)
            script_path = os.path.join(temp_dir, "run_rembg_cuda.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(f"""
from rembg import remove, new_session
from PIL import Image

# 1. Tenter d'utiliser CUDA (GPU), sinon basculer sur le CPU
session = new_session('u2netp', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])

# 2. Ouvrir l'image exportée par GIMP
img = Image.open(r"{file_in_path}")

# 3. Appliquer le détourage avec les paramètres de l'interface
out = remove(
    img, 
    session=session, 
    alpha_matting={use_alpha_matting},
    alpha_matting_foreground_threshold={fg_thresh},
    alpha_matting_background_threshold={bg_thresh},
    alpha_matting_erode_size={erode_val}
)

# 4. Sauvegarder le résultat pour GIMP
out.save(r"{file_out_path}")
""")
                
            cmd = [python_exe, script_path]

            # Exécution du script
            subprocess.run(cmd, check=True, creationflags=0x08000000)
            
            # Nettoyage du fichier temporaire
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

            # FIN SILENCIEUSE ET PROPRE
            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

        except Exception as e:
            Gimp.message(f"Erreur du greffon IA :\n{str(e)}")
            return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error())

if __name__ == '__main__':
    Gimp.main(IaDetouragePlugin.__gtype__, sys.argv)