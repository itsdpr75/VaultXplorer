import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import json
import os
import sqlite3
import shutil
import configparser
from PIL import Image, ImageTk
from typing import List, Dict, Optional
import zipfile
from datetime import datetime
from pathlib import Path

# Global CustomTkinter configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = 'config.ini'
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
        else:
            self.create_default_config()

    def create_default_config(self):
        self.config['Paths'] = {
            'database': 'assets.db',
            'assets_folder': 'assets',
            'resources': 'resources'
        }
        self.config['Colors'] = {
            'primary_button': '#2FA572',
            'hover_button': '#248C61',
            'secondary_button': '#3B8ED0',
            'hover_secondary': '#36719F'
        }
        self.save_config()

    def save_config(self):
        with open(self.config_path, 'w') as f:
            self.config.write(f)

    def get_path(self, key: str) -> str:
        return self.config.get('Paths', key)

    def get_color(self, key: str) -> str:
        return self.config.get('Colors', key)

class Database:
    def __init__(self, config: Config):
        self.config = config
        self.conn = sqlite3.connect(self.config.get_path('database'))
        self.create_tables()
    
    def create_tables(self):
        with self.conn:
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
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS asset_tags (
                    asset_id INTEGER,
                    tag_id INTEGER,
                    FOREIGN KEY (asset_id) REFERENCES assets (id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id),
                    PRIMARY KEY (asset_id, tag_id)
                )
            ''')

class FolderTree(ctk.CTkFrame):
    def __init__(self, master, db: Database, on_folder_select=None):
        super().__init__(master)
        
        self.db = db
        self.on_folder_select = on_folder_select
        
        # Folder Tree
        self.tree = ttk.Treeview(self, show="tree")
        self.tree.pack(expand=True, fill="both")
        
        # Add Folder Button
        self.add_button = ctk.CTkButton(
            self,
            text="+ New Folder",
            command=self.add_folder,
            fg_color=self.db.config.get_color('secondary_button'),
            hover_color=self.db.config.get_color('hover_secondary')
        )
        self.add_button.pack(pady=5)
        
        self.load_folders()
        
    def load_folders(self):
        self.tree.delete(*self.tree.get_children())
        
        # Load folders from database
        folders = self.db.get_folders()
        for folder in folders:
            self.tree.insert(
                folder['parent_id'] or '',
                'end',
                folder['id'],
                text=folder['name']
            )
            
    def add_folder(self):
        dialog = ctk.CTkInputDialog(
            text="Enter folder name:",
            title="New Folder"
        )
        
        folder_name = dialog.get_input()
        if folder_name:
            selected = self.tree.selection()
            parent_id = selected[0] if selected else None
            
            self.db.add_folder(folder_name, parent_id)
            self.load_folders()
            
class RoundedFrame(ctk.CTkFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(corner_radius=10)

class ConfigWindow(ctk.CTkToplevel):
    def __init__(self, master, config: Config):
        super().__init__(master)
        self.config = config
        self.title("VaultXplorer Configuration")
        self.geometry("500x600")
        self.create_widgets()

    def create_widgets(self):
        paths_frame = RoundedFrame(self)
        paths_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(paths_frame, text="Paths Configuration", font=("Helvetica", 16, "bold")).pack(pady=5)
        
        self.db_path_var = tk.StringVar(value=self.config.get_path('database'))
        self.create_path_entry(paths_frame, "Database Location:", self.db_path_var)
        
        self.assets_path_var = tk.StringVar(value=self.config.get_path('assets_folder'))
        self.create_path_entry(paths_frame, "Assets Folder:", self.assets_path_var)
        
        self.resources_path_var = tk.StringVar(value=self.config.get_path('resources'))
        self.create_path_entry(paths_frame, "Resources Folder:", self.resources_path_var)
        
        colors_frame = RoundedFrame(self)
        colors_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(colors_frame, text="Color Configuration", font=("Helvetica", 16, "bold")).pack(pady=5)
        
        self.primary_color_var = tk.StringVar(value=self.config.get_color('primary_button'))
        self.create_color_picker(colors_frame, "Primary Button Color:", self.primary_color_var)
        
        self.hover_color_var = tk.StringVar(value=self.config.get_color('hover_button'))
        self.create_color_picker(colors_frame, "Primary Hover Color:", self.hover_color_var)
        
        self.secondary_color_var = tk.StringVar(value=self.config.get_color('secondary_button'))
        self.create_color_picker(colors_frame, "Secondary Button Color:", self.secondary_color_var)
        
        self.hover_secondary_var = tk.StringVar(value=self.config.get_color('hover_secondary'))
        self.create_color_picker(colors_frame, "Secondary Hover Color:", self.hover_secondary_var)

        buttons_frame = RoundedFrame(self)
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(
            buttons_frame,
            text="Apply",
            command=self.save_config,
            fg_color=self.config.get_color('primary_button'),
            hover_color=self.config.get_color('hover_button')
        ).pack(side="left", padx=5, pady=5, expand=True)
        
        ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=self.destroy,
            fg_color=self.config.get_color('secondary_button'),
            hover_color=self.config.get_color('hover_secondary')
        ).pack(side="left", padx=5, pady=5, expand=True)
        
    def create_path_entry(self, parent, label: str, variable: tk.StringVar):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(frame, text=label).pack(side="left", padx=5)
        
        entry = ctk.CTkEntry(frame, textvariable=variable)
        entry.pack(side="left", expand=True, fill="x", padx=5)
        
        ctk.CTkButton(
            frame,
            text="Browse",
            command=lambda: self.browse_path(variable),
            width=70,
            fg_color=self.config.get_color('secondary_button'),
            hover_color=self.config.get_color('hover_secondary')
        ).pack(side="right", padx=5)

    def create_color_picker(self, parent, label: str, variable: tk.StringVar):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(frame, text=label).pack(side="left", padx=5)
        
        entry = ctk.CTkEntry(frame, textvariable=variable)
        entry.pack(side="left", expand=True, fill="x", padx=5)
        
        preview = ctk.CTkFrame(frame, width=30, height=30)
        preview.configure(fg_color=variable.get())
        preview.pack(side="right", padx=5)
        
        variable.trace_add("write", lambda *args: preview.configure(fg_color=variable.get()))
        
    def browse_path(self, variable: tk.StringVar):
        path = filedialog.askdirectory()
        if path:
            variable.set(path)
            
    def save_config(self):
        self.config.config['Paths'] = {
            'database': self.db_path_var.get(),
            'assets_folder': self.assets_path_var.get(),
            'resources': self.resources_path_var.get()
        }
        
        self.config.config['Colors'] = {
            'primary_button': self.primary_color_var.get(),
            'hover_button': self.hover_color_var.get(),
            'secondary_button': self.secondary_color_var.get(),
            'hover_secondary': self.hover_secondary_var.get()
        }
        
        self.config.save_config()
        self.destroy()
class AssetCard(RoundedFrame):
    def __init__(self, master, asset_data: Dict, on_click=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.asset_data = asset_data
        self.on_click = on_click
        
        # Load image
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
        
        # Asset information
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
        
        self.title("Asset Configuration")
        self.geometry("400x600")
        self.resizable(False, False)
        self.overrideredirect(True)
        
        self.create_widgets(asset_data)
        
    def create_widgets(self, asset_data: Dict):
        title_frame = RoundedFrame(self)
        title_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(title_frame, text=asset_data['name']).pack(pady=5)
        
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
        
        export_button = ctk.CTkButton(
            self,
            text="Export Asset",
            command=lambda: self.export_asset(asset_data)
        )
        export_button.pack(pady=20)
        
        close_button = ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy
        )
        close_button.pack(pady=5)
        
    def export_asset(self, asset_data: Dict):
        export_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip")]
        )
        
        if export_path:
            with zipfile.ZipFile(export_path, 'w') as zf:
                base_path = asset_data['path']
                resolution = self.resolution_var.get()
                lod = self.lod_var.get()
                
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
        self.geometry("600x800")
        
        self.create_widgets()
        
    def create_widgets(self):
        path_frame = self.create_section("Asset Location")
        
        self.path_var = tk.StringVar()
        path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.path_var,
            placeholder_text="Select the folder containing your asset files"
        )
        path_entry.pack(side="left", expand=True, fill="x", padx=5)
        
        browse_button = ctk.CTkButton(
            path_frame,
            text="Browse",
            command=self.browse_path,
            fg_color=self.db.config.get_color('secondary_button'),
            hover_color=self.db.config.get_color('hover_secondary')
        )
        browse_button.pack(side="right", padx=5)
        
        name_frame = self.create_section("Asset Name")
        self.name_var = tk.StringVar()
        name_entry = ctk.CTkEntry(
            name_frame,
            textvariable=self.name_var,
            placeholder_text="Enter a unique name for your asset"
        )
        name_entry.pack(fill="x", padx=5)
        
        type_frame = self.create_section("Asset Type")
        types = ["Model", "Material", "Texture"]
        self.type_var = ctk.StringVar(value=types[0])
        type_combo = ctk.CTkComboBox(
            type_frame,
            values=types,
            variable=self.type_var,
            command=self.on_type_change
        )
        type_combo.pack(pady=5)
        
        env_frame = self.create_section("Environment")
        environments = ["Indoor", "Outdoor", "Both"]
        self.env_var = ctk.StringVar(value=environments[0])
        env_combo = ctk.CTkComboBox(
            env_frame,
            values=environments,
            variable=self.env_var
        )
        env_combo.pack(pady=5)
        
        tags_frame = self.create_section("Tags")
        self.tags_var = tk.StringVar()
        tags_entry = ctk.CTkEntry(
            tags_frame,
            textvariable=self.tags_var,
            placeholder_text="Enter tags separated by commas (e.g., furniture, wood, modern)"
        )
        tags_entry.pack(pady=5)
        
        self.model_frame = self.create_section("3D Model Configuration")
        self.model_frame.pack_forget()
        
        self.model_path_var = tk.StringVar()
        model_entry = ctk.CTkEntry(
            self.model_frame,
            textvariable=self.model_path_var,
            placeholder_text="Path to .fbx, .obj or other 3D model file"
        )
        model_entry.pack(fill="x", padx=5)
        
        lod_label = ctk.CTkLabel(self.model_frame, text="LOD Levels")
        lod_label.pack(pady=(10,5))
        
        self.lod_vars = []
        for i in range(3):
            lod_var = tk.StringVar()
            lod_entry = ctk.CTkEntry(
                self.model_frame,
                textvariable=lod_var,
                placeholder_text=f"LOD{i} model path"
            )
            lod_entry.pack(fill="x", padx=5, pady=2)
            self.lod_vars.append(lod_var)
        
        textures_frame = self.create_section("Textures")
        
        self.texture_entries = {}
        texture_types = [
            "Color/Albedo", "Normal", "Roughness", "Specular", 
            "Displacement", "Metalness", "Ambient Occlusion",
            "Anisotropy", "Opacity", "Opacity Mask"
        ]
        
        for tex_type in texture_types:
            tex_frame = ctk.CTkFrame(textures_frame)
            tex_frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(tex_frame, text=tex_type).pack(side="left", padx=5)
            
            tex_var = tk.StringVar()
            tex_entry = ctk.CTkEntry(tex_frame, textvariable=tex_var)
            tex_entry.pack(side="left", expand=True, fill="x", padx=5)
            
            self.texture_entries[tex_type] = tex_var
            
            browse_btn = ctk.CTkButton(
                tex_frame,
                text="Browse",
                width=70,
                command=lambda v=tex_var: self.browse_texture(v),
                fg_color=self.db.config.get_color('secondary_button'),
                hover_color=self.db.config.get_color('hover_secondary')
            )
            browse_btn.pack(side="right", padx=5)
        
        add_texture_btn = ctk.CTkButton(
            textures_frame,
            text="+ Add Texture Type",
            command=self.add_texture_type,
            fg_color=self.db.config.get_color('secondary_button'),
            hover_color=self.db.config.get_color('hover_secondary')
        )
        add_texture_btn.pack(pady=10)
        
        save_button = ctk.CTkButton(
            self,
            text="Save Asset",
            command=self.save_asset,
            fg_color=self.db.config.get_color('primary_button'),
            hover_color=self.db.config.get_color('hover_button')
        )
        save_button.pack(pady=20)
        
    def create_section(self, title: str) -> ctk.CTkFrame:
        frame = RoundedFrame(self)
        frame.pack(fill="x", padx=10, pady=5)
        
        title_label = ctk.CTkLabel(frame, text=title, font=("Helvetica", 12, "bold"))
        title_label.pack(anchor="w", padx=5, pady=2)
        
        return frame
    
    def on_type_change(self, _):
        if self.type_var.get() == "Model":
            self.model_frame.pack(after=self.tags_frame)
        else:
            self.model_frame.pack_forget()
            
    def browse_texture(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.tiff *.tga *.exr")]
        )
        if path:
            var.set(path)
            
    def add_texture_type(self):
        dialog = ctk.CTkInputDialog(
            text="Enter new texture type name:",
            title="Add Texture Type"
        )
        
        new_type = dialog.get_input()
        if new_type and new_type not in self.texture_entries:
            tex_frame = ctk.CTkFrame(self.textures_frame)
            tex_frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(tex_frame, text=new_type).pack(side="left", padx=5)
            
            tex_var = tk.StringVar()
            tex_entry = ctk.CTkEntry(tex_frame, textvariable=tex_var)
            tex_entry.pack(side="left", expand=True, fill="x", padx=5)
            
            self.texture_entries[new_type] = tex_var
            
            browse_btn = ctk.CTkButton(
                tex_frame,
                text="Browse",
                width=70,
                command=lambda v=tex_var: self.browse_texture(v)
            )
            browse_btn.pack(side="right", padx=5)
class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.config = Config()
        self.db = Database(self.config)
        
        self.title("VaultXplorer")
        self.geometry("1280x720")
        self.minsize(854, 480)
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.load_resources()
        self.create_sidebar()
        self.create_main_content()
        
    def load_resources(self):
        # Load SVG icons
        resources_path = Path(self.config.get_path('resources'))
        self.icons = {
            'logo': ImageTk.PhotoImage(Image.open(resources_path / 'logo.svg')),
            'home': ImageTk.PhotoImage(Image.open(resources_path / 'home.svg')),
            'search': ImageTk.PhotoImage(Image.open(resources_path / 'search.svg')),
            'folder': ImageTk.PhotoImage(Image.open(resources_path / 'folder.svg')),
            'settings': ImageTk.PhotoImage(Image.open(resources_path / 'settings.svg')),
            'reload': ImageTk.PhotoImage(Image.open(resources_path / 'reload.svg')),
            'magnifier': ImageTk.PhotoImage(Image.open(resources_path / 'magnifier.svg'))
        }
        
    def create_sidebar(self):
        sidebar = RoundedFrame(self)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        
        # Logo
        logo_label = ctk.CTkLabel(
            sidebar,
            image=self.icons['logo'],
            text=""
        )
        logo_label.pack(pady=20)
        
        # Navigation buttons
        nav_buttons = [
            ("Home", "home", self.icons['home']),
            ("Search", "search", self.icons['search']),
            ("Saved Folders", "folders", self.icons['folder'])
        ]
        
        for text, command, icon in nav_buttons:
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                image=icon,
                command=lambda cmd=command: self.navigate(cmd),
                fg_color="transparent",
                hover_color=("gray70", "gray30")
            )
            btn.pack(pady=5, padx=10, fill="x")
        
        # Folder tree (initially hidden)
        self.folder_tree = FolderTree(sidebar, self.db)
        self.folder_tree.pack_forget()
        
        # Settings and Reload buttons
        reload_button = ctk.CTkButton(
            sidebar,
            text="Reload Database",
            image=self.icons['reload'],
            command=self.reload_database,
            fg_color=self.config.get_color('secondary_button'),
            hover_color=self.config.get_color('hover_secondary')
        )
        reload_button.pack(pady=5, padx=10, side="bottom", fill="x")
        
        settings_button = ctk.CTkButton(
            sidebar,
            text="Settings",
            image=self.icons['settings'],
            command=self.show_settings,
            fg_color=self.config.get_color('secondary_button'),
            hover_color=self.config.get_color('hover_secondary')
        )
        settings_button.pack(pady=5, padx=10, side="bottom", fill="x")
        
        # Add Asset button
        add_button = ctk.CTkButton(
            sidebar,
            text="+ Add Asset",
            command=self.show_add_asset_window,
            fg_color=self.config.get_color('primary_button'),
            hover_color=self.config.get_color('hover_button')
        )
        add_button.pack(pady=5, padx=10, side="bottom", fill="x")
        
    def create_main_content(self):
        main_frame = RoundedFrame(self)
        main_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Search bar and filters in one line
        search_frame = RoundedFrame(main_frame)
        search_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        search_frame.grid_columnconfigure(0, weight=1)
        
        # Search entry
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.update_assets())
        
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Search assets by name, type or tag..."
        )
        search_entry.pack(side="left", expand=True, fill="x", padx=5)
        
        # Asset type combo
        self.type_var = tk.StringVar(value="All")
        type_combo = ctk.CTkComboBox(
            search_frame,
            values=["All", "Model", "Material", "Texture"],
            variable=self.type_var,
            command=self.update_assets,
            width=120,
            placeholder_text="Asset Type"
        )
        type_combo.pack(side="left", padx=5)
        
        # Environment combo
        self.env_var = tk.StringVar(value="All")
        env_combo = ctk.CTkComboBox(
            search_frame,
            values=["All", "Indoor", "Outdoor", "Both"],
            variable=self.env_var,
            command=self.update_assets,
            width=120,
            placeholder_text="Environment"
        )
        env_combo.pack(side="left", padx=5)
        
        # Search button with magnifier icon
        search_button = ctk.CTkButton(
            search_frame,
            text="",
            image=self.icons['magnifier'],
            width=40,
            command=self.update_assets,
            fg_color=self.config.get_color('primary_button'),
            hover_color=self.config.get_color('hover_button')
        )
        search_button.pack(side="left", padx=5)
        
        # Tags Frame
        self.tags_frame = RoundedFrame(main_frame)
        self.tags_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        self.selected_tags = set()
        self.update_tags()
        
        # Assets Grid (with scroll)
        self.assets_canvas = ctk.CTkScrollableFrame(main_frame)
        self.assets_canvas.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        
        self.update_assets()
    def reload_database(self):
        self.db = Database(self.config)
        self.update_assets()
        self.update_tags()
        
    def show_settings(self):
        ConfigWindow(self, self.config)
    
    def navigate(self, section: str):
        if section == "home":
            self.folder_tree.pack_forget()
            self.show_recent_assets()
        elif section == "search":
            self.folder_tree.pack_forget()
            self.search_var.set("")
            self.update_assets()
        elif section == "folders":
            # Toggle folder tree visibility
            if self.folder_tree.winfo_ismapped():
                self.folder_tree.pack_forget()
            else:
                self.folder_tree.pack(after=self.folder_tree.master.winfo_children()[3],
                                    pady=5, padx=10, fill="x")
    def update_tags(self):
        for widget in self.tags_frame.winfo_children():
            widget.destroy()
        
        all_tags = self.db.get_all_tags()
        
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
        for widget in self.assets_canvas.winfo_children():
            widget.destroy()
        
        assets = self.db.search_assets(
            query=self.search_var.get(),
            asset_type=self.type_var.get() if self.type_var.get() != "All" else None,
            environment=self.env_var.get() if self.env_var.get() != "All" else None,
            tags=list(self.selected_tags) if self.selected_tags else None
        )
        
        row = 0
        col = 0
        max_cols = 4
        
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
    
    def show_recent_assets(self):
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
