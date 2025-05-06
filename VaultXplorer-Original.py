import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import json
import os
import sqlite3
import shutil
from PIL import Image, ImageTk
from typing import List, Dict, Optional
import zipfile
from datetime import datetime

# Configuración global de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('assets.db')
        self.create_tables()
    
    def create_tables(self):
        with self.conn:
            # Tabla principal de assets
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    type TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    image_path TEXT,
                    size INTEGER,
                    date_added TIMESTAMP
                )
            ''')
            
            # Tabla de tags
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                )
            ''')
            
            # Tabla de relación asset-tag
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS asset_tags (
                    asset_id INTEGER,
                    tag_id INTEGER,
                    FOREIGN KEY (asset_id) REFERENCES assets (id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id),
                    PRIMARY KEY (asset_id, tag_id)
                )
            ''')

    def add_asset(self, asset_data: dict) -> int:
        with self.conn:
            cursor = self.conn.execute('''
                INSERT INTO assets (name, path, type, environment, image_path, size, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                asset_data['name'],
                asset_data['path'],
                asset_data['type'],
                asset_data['environment'],
                asset_data['image_path'],
                asset_data['size'],
                datetime.now().isoformat()
            ))
            return cursor.lastrowid

    def add_tags(self, asset_id: int, tags: List[str]):
        with self.conn:
            for tag in tags:
                # Insertar o obtener tag
                self.conn.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag,))
                tag_id = self.conn.execute('SELECT id FROM tags WHERE name = ?', (tag,)).fetchone()[0]
                
                # Relacionar tag con asset
                self.conn.execute('''
                    INSERT OR IGNORE INTO asset_tags (asset_id, tag_id)
                    VALUES (?, ?)
                ''', (asset_id, tag_id))

    def get_all_tags(self) -> List[str]:
        cursor = self.conn.execute('SELECT name FROM tags ORDER BY name')
        return [row[0] for row in cursor.fetchall()]

    def search_assets(self, query: str, asset_type: str = None, environment: str = None, tags: List[str] = None) -> List[Dict]:
        sql = '''
            SELECT DISTINCT a.* FROM assets a
            LEFT JOIN asset_tags at ON a.id = at.asset_id
            LEFT JOIN tags t ON at.tag_id = t.id
            WHERE 1=1
        '''
        params = []

        if query:
            sql += ' AND a.name LIKE ?'
            params.append(f'%{query}%')

        if asset_type:
            sql += ' AND a.type = ?'
            params.append(asset_type)

        if environment:
            sql += ' AND a.environment = ?'
            params.append(environment)

        if tags:
            placeholders = ','.join('?' for _ in tags)
            sql += f' AND t.name IN ({placeholders})'
            params.extend(tags)

        cursor = self.conn.execute(sql, params)
        return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

class RoundedFrame(ctk.CTkFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(corner_radius=10)

class AssetCard(RoundedFrame):
    def __init__(self, master, asset_data: Dict, on_click=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.asset_data = asset_data
        self.on_click = on_click
        
        # Cargar imagen
        try:
            image = Image.open(asset_data['image_path'])
            image = image.resize((150, 150))
            photo = ImageTk.PhotoImage(image)
            
            self.image_label = ctk.CTkLabel(self, image=photo, text="")
            self.image_label.image = photo
            self.image_label.pack(pady=5)
        except:
            self.image_label = ctk.CTkLabel(self, text="No Image")
            self.image_label.pack(pady=5)
        
        # Información del asset
        self.name_label = ctk.CTkLabel(self, text=asset_data['name'])
        self.name_label.pack()
        
        self.type_label = ctk.CTkLabel(self, text=f"Type: {asset_data['type']}")
        self.type_label.pack()
        
        self.bind('<Button-1>', lambda e: self._on_click())
        
    def _on_click(self):
        if self.on_click:
            self.on_click(self.asset_data)

class AssetConfigWindow(ctk.CTkToplevel):
    def __init__(self, master, asset_data: Dict):
        super().__init__(master)
        
        # Configurar ventana
        self.title("Asset Configuration")
        self.geometry("400x600")
        self.resizable(False, False)
        
        # Eliminar decoraciones de ventana
        self.overrideredirect(True)
        
        # Agregar contenido
        self.create_widgets(asset_data)
        
    def create_widgets(self, asset_data: Dict):
        # Título
        title_frame = RoundedFrame(self)
        title_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(title_frame, text=asset_data['name']).pack(pady=5)
        
        # Opciones de textura
        texture_frame = RoundedFrame(self)
        texture_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(texture_frame, text="Texture Resolution").pack()
        
        resolutions = ["2K", "4K", "8K"]
        self.resolution_var = ctk.StringVar(value=resolutions[0])
        resolution_combo = ctk.CTkComboBox(
            texture_frame,
            values=resolutions,
            variable=self.resolution_var
        )
        resolution_combo.pack(pady=5)
        
        # LOD Selection
        lod_frame = RoundedFrame(self)
        lod_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(lod_frame, text="LOD Level").pack()
        
        lods = ["LOD0", "LOD1", "LOD2"]
        self.lod_var = ctk.StringVar(value=lods[0])
        lod_combo = ctk.CTkComboBox(
            lod_frame,
            values=lods,
            variable=self.lod_var
        )
        lod_combo.pack(pady=5)
        
        # Export Button
        export_button = ctk.CTkButton(
            self,
            text="Export Asset",
            command=lambda: self.export_asset(asset_data)
        )
        export_button.pack(pady=20)
        
        # Close Button
        close_button = ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy
        )
        close_button.pack(pady=5)
        
    def export_asset(self, asset_data: Dict):
        # Crear archivo ZIP con las configuraciones seleccionadas
        export_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip")]
        )
        
        if export_path:
            with zipfile.ZipFile(export_path, 'w') as zf:
                # Añadir archivos según configuración
                base_path = asset_data['path']
                resolution = self.resolution_var.get()
                lod = self.lod_var.get()
                
                # Añadir archivos relevantes según configuración
                for root, _, files in os.walk(base_path):
                    for file in files:
                        if resolution in file or lod in file:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, base_path)
                            zf.write(file_path, arcname)

class AddAssetWindow(ctk.CTkToplevel):
    def __init__(self, master, db: Database, on_asset_added=None):
        super().__init__(master)
        
        self.db = db
        self.on_asset_added = on_asset_added
        
        self.title("Add New Asset")
        self.geometry("500x700")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Asset Path
        path_frame = RoundedFrame(self)
        path_frame.pack(fill="x", padx=10, pady=5)
        
        self.path_var = tk.StringVar()
        path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.path_var,
            placeholder_text="Asset Path"
        )
        path_entry.pack(side="left", expand=True, fill="x", padx=5)
        
        browse_button = ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self.browse_path
        )
        browse_button.pack(side="right", padx=5)
        
        # Asset Name
        self.name_var = tk.StringVar()
        name_entry = ctk.CTkEntry(
            self,
            textvariable=self.name_var,
            placeholder_text="Asset Name"
        )
        name_entry.pack(fill="x", padx=15, pady=5)
        
        # Asset Type
        type_frame = RoundedFrame(self)
        type_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(type_frame, text="Asset Type").pack()
        
        types = ["Model", "Material", "Texture"]
        self.type_var = ctk.StringVar(value=types[0])
        type_combo = ctk.CTkComboBox(
            type_frame,
            values=types,
            variable=self.type_var
        )
        type_combo.pack(pady=5)
        
        # Environment
        env_frame = RoundedFrame(self)
        env_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(env_frame, text="Environment").pack()
        
        environments = ["Indoor", "Outdoor", "Both"]
        self.env_var = ctk.StringVar(value=environments[0])
        env_combo = ctk.CTkComboBox(
            env_frame,
            values=environments,
            variable=self.env_var
        )
        env_combo.pack(pady=5)
        
        # Tags
        tags_frame = RoundedFrame(self)
        tags_frame.pack(fill="x", padx=10, pady=5)
        
        self.tags_var = tk.StringVar()
        tags_entry = ctk.CTkEntry(
            tags_frame,
            textvariable=self.tags_var,
            placeholder_text="Tags (comma separated)"
        )
        tags_entry.pack(pady=5)
        
        # Texture Template
        texture_frame = RoundedFrame(self)
        texture_frame.pack(fill="x", padx=10, pady=5)
        
        self.texture_var = tk.StringVar(value="texture_{{res}}.png")
        texture_entry = ctk.CTkEntry(
            texture_frame,
            textvariable=self.texture_var,
            placeholder_text="Texture filename template"
        )
        texture_entry.pack(pady=5)
        
        # Save Button
        save_button = ctk.CTkButton(
            self,
            text="Save Asset",
            command=self.save_asset
        )
        save_button.pack(pady=20)
        
    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
            
    def save_asset(self):
        # Crear datos del asset
        asset_data = {
            'name': self.name_var.get(),
            'path': self.path_var.get(),
            'type': self.type_var.get(),
            'environment': self.env_var.get(),
            'image_path': os.path.join(self.path_var.get(), "preview.png"),
            'size': os.path.getsize(self.path_var.get()) if os.path.exists(self.path_var.get()) else 0
        }
        
        # Guardar en base de datos
        asset_id = self.db.add_asset(asset_data)
        
        # Procesar y guardar tags
        tags = [tag.strip() for tag in self.tags_var.get().split(',') if tag.strip()]
        self.db.add_tags(asset_id, tags)
        
        # Generar archivo JSON
        json_data = {
            **asset_data,
            'tags': tags,
            'texture_template': self.texture_var.get()
        }
        
        json_path = os.path.join(self.path_var.get(), "asset_info.json")
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=4)
        
        if self.on_asset_added:
            self.on_asset_added()
            
        self.destroy()

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.db = Database()
        
        self.title("3D Asset Manager")
        self.geometry("1280x720")  # 16:9 aspect ratio
        self.minsize(854, 480)  # Minimum 16:9 size
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.create_sidebar()
        self.create_main_content()
        
    def create_sidebar(self):
        sidebar = RoundedFrame(self)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        
        # Logo
        logo_label = ctk.CTkLabel(
            sidebar,
            text="Asset\nManager",
            font=("Helvetica", 20, "bold")
        )
        logo_label.pack(pady=20)
        
        # Botones de navegación
        nav_buttons = [
            ("Home", "home"),
            ("Search", "search"),
            ("Saved Folders", "folders")
        ]
        
        for text, command in nav_buttons:
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                command=lambda cmd=command: self.navigate(cmd),
                fg_color="transparent",
                hover_color=("gray70", "gray30")
            )
            btn.pack(pady=5, padx=10, fill="x")
        
        # Botón de añadir asset
        add_button = ctk.CTkButton(
            sidebar,
            text="+ Add Asset",
            command=self.show_add_asset_window,
            fg_color="#2FA572",
            hover_color="#248C61"
        )
        add_button.pack(pady=20, padx=10, side="bottom", fill="x")
        
    def create_main_content(self):
        # Frame principal
        main_frame = RoundedFrame(self)
        main_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Barra de búsqueda
        search_frame = RoundedFrame(main_frame)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.update_assets())
        
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Search assets..."
        )
        search_entry.grid(row=0, column=0, sticky="ew", padx=5)
        
        # Filtros
        filter_frame = RoundedFrame(main_frame)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # ComboBox para tipo de asset
        self.type_var = tk.StringVar()
        type_combo = ctk.CTkComboBox(
            filter_frame,
            values=["All", "Model", "Material", "Texture"],
            variable=self.type_var,
            command=self.update_assets
        )
        type_combo.pack(side="left", padx=5)
        
        # ComboBox para entorno
        self.env_var = tk.StringVar()
        env_combo = ctk.CTkComboBox(
            filter_frame,
            values=["All", "Indoor", "Outdoor", "Both"],
            variable=self.env_var,
            command=self.update_assets
        )
        env_combo.pack(side="left", padx=5)
        
        # Tags Frame
        self.tags_frame = RoundedFrame(filter_frame)
        self.tags_frame.pack(side="left", expand=True, fill="x", padx=5)
        
        self.selected_tags = set()
        self.update_tags()
        
        # Assets Grid (con scroll)
        self.assets_canvas = ctk.CTkScrollableFrame(main_frame)
        self.assets_canvas.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        self.update_assets()
        
    def update_tags(self):
        # Limpiar tags actuales
        for widget in self.tags_frame.winfo_children():
            widget.destroy()
        
        # Obtener todos los tags de la base de datos
        all_tags = self.db.get_all_tags()
        
        # Crear botones para cada tag
        for tag in all_tags:
            tag_button = ctk.CTkButton(
                self.tags_frame,
                text=tag,
                width=30,
                fg_color="gray30" if tag in self.selected_tags else "transparent",
                command=lambda t=tag: self.toggle_tag(t)
            )
            tag_button.pack(side="left", padx=2)
        
    def toggle_tag(self, tag: str):
        if tag in self.selected_tags:
            self.selected_tags.remove(tag)
        else:
            self.selected_tags.add(tag)
        
        self.update_tags()
        self.update_assets()
        
    def update_assets(self, *args):
        # Limpiar grid actual
        for widget in self.assets_canvas.winfo_children():
            widget.destroy()
        
        # Obtener assets filtrados
        assets = self.db.search_assets(
            query=self.search_var.get(),
            asset_type=self.type_var.get() if self.type_var.get() != "All" else None,
            environment=self.env_var.get() if self.env_var.get() != "All" else None,
            tags=list(self.selected_tags) if self.selected_tags else None
        )
        
        # Crear grid de assets
        row = 0
        col = 0
        max_cols = 4  # Número de columnas en la cuadrícula
        
        for asset in assets:
            card = AssetCard(
                self.assets_canvas,
                asset_data=asset,
                on_click=self.show_asset_config
            )
            card.grid(row=row, column=col, padx=5, pady=5)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def navigate(self, section: str):
        # Implementar navegación entre secciones
        if section == "home":
            self.show_recent_assets()
        elif section == "search":
            self.search_var.set("")
            self.update_assets()
        elif section == "folders":
            self.show_saved_folders()
    
    def show_recent_assets(self):
        # Mostrar assets recientes
        pass
    
    def show_saved_folders(self):
        # Mostrar carpetas guardadas
        pass
    
    def show_add_asset_window(self):
        AddAssetWindow(self, self.db, self.update_assets)
    
    def show_asset_config(self, asset_data: Dict):
        AssetConfigWindow(self, asset_data)

def main():
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()