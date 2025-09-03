import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
import queue
import re

# 确保PyInstaller已安装
try:
    import PyInstaller
except ImportError:
    result = messagebox.askyesno("PyInstaller未安装", "检测到未安装PyInstaller，是否现在安装？")
    if result:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
        messagebox.showinfo("安装成功", "PyInstaller已安装成功！")
    else:
        messagebox.showerror("错误", "PyInstaller未安装，无法继续打包！")
        sys.exit(1)

class PackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python打包工具 v1.1")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 初始化变量
        self.main_script_path = tk.StringVar()
        self.icon_path = tk.StringVar()
        self.output_name = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.enable_upx = tk.BooleanVar(value=False)  # 默认禁用UPX
        self.pack_option_var = tk.StringVar(value="single_dir")  # 默认打包为文件夹
        
        # 初始化文件列表
        self.resource_files = []
        self.clean_files = []
        
        # 初始化日志队列
        self.log_queue = queue.Queue()
        self.clean_log_queue = queue.Queue()
        
        # 初始化线程
        self.pack_thread = None
        self.clean_thread = None
        
        # 创建界面
        self.create_widgets()
    
    def create_widgets(self):
        # 创建标签页
        self.tab_control = ttk.Notebook(self.root)
        
        # 创建设置标签页
        self.settings_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.settings_tab, text="打包设置")
        
        # 创建日志标签页
        self.log_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.log_tab, text="打包日志")
        
        # 创建清洗代码标签页
        self.clean_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.clean_tab, text="清洗代码")
        
        # 设置标签页内容
        main_frame = ttk.LabelFrame(self.settings_tab, text="主程序设置")
        main_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(main_frame, text="主程序文件:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.main_script_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="浏览...", command=self.select_main_script).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(main_frame, text="图标文件:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.icon_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="浏览...", command=self.select_icon).grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Label(main_frame, text="输出名称:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_name, width=50).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(main_frame, text="输出目录:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_dir, width=50).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="浏览...", command=self.select_output_dir).grid(row=3, column=2, padx=5, pady=5)
        
        # 删除终端选择相关代码，直接在Python环境中执行
        
        # 资源文件
        resource_frame = ttk.LabelFrame(self.settings_tab, text="额外资源文件")
        resource_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        list_frame = ttk.Frame(resource_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.resource_listbox = tk.Listbox(list_frame, height=8, yscrollcommand=scrollbar.set)
        self.resource_listbox.pack(fill="both", expand=True)
        scrollbar.config(command=self.resource_listbox.yview)
        
        button_frame = ttk.Frame(resource_frame)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(button_frame, text="添加文件", command=self.add_resource_file).pack(side="left", padx=5)
        ttk.Button(button_frame, text="添加文件夹", command=self.add_resource_folder).pack(side="left", padx=5)
        ttk.Button(button_frame, text="删除选中", command=self.remove_resource).pack(side="left", padx=5)
        ttk.Button(button_frame, text="清空列表", command=self.clear_resources).pack(side="left", padx=5)
        
        option_frame = ttk.LabelFrame(self.settings_tab, text="打包选项")
        option_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Radiobutton(option_frame, text="打包成单文件", variable=self.pack_option_var, value="single_file", command=self.update_options).pack(side="left", padx=10, pady=5)
        ttk.Radiobutton(option_frame, text="打包成文件夹", variable=self.pack_option_var, value="single_dir", command=self.update_options).pack(side="left", padx=10, pady=5)
        ttk.Radiobutton(option_frame, text="依次执行两种打包", variable=self.pack_option_var, value="both", command=self.update_options).pack(side="left", padx=10, pady=5)
        ttk.Checkbutton(option_frame, text="启用UPX压缩", variable=self.enable_upx).pack(side="left", padx=10, pady=5)
        
        action_frame = ttk.Frame(self.settings_tab)
        action_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(action_frame, text="清理构建文件", command=self.clean_build).pack(side="left", padx=5)
        ttk.Button(action_frame, text="开始打包", command=self.start_pack).pack(side="right", padx=5)
        
        # 日志标签页内容
        log_frame = ttk.Frame(self.log_tab)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        log_label = ttk.Label(log_frame, text="打包日志:")
        log_label.pack(anchor="w", padx=5, pady=5)
        
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        log_scrollbar = ttk.Scrollbar(log_text_frame)
        log_scrollbar.pack(side="right", fill="y")
        
        self.log_text = tk.Text(log_text_frame, wrap=tk.WORD, yscrollcommand=log_scrollbar.set, height=20)
        self.log_text.pack(fill="both", expand=True)
        log_scrollbar.config(command=self.log_text.yview)
        
        progress_frame = ttk.Frame(log_frame)
        progress_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(progress_frame, text="打包进度:").pack(side="left", padx=5)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(side="left", padx=5, fill="x", expand=True)
        
        pack_control_frame = ttk.Frame(log_frame)
        pack_control_frame.pack(fill="x", padx=5, pady=5)
        
        self.stop_button = ttk.Button(pack_control_frame, text="停止打包", command=self.stop_pack_process, state="disabled")
        self.stop_button.pack(side="right", padx=5)
        
        self.clear_log_button = ttk.Button(pack_control_frame, text="清空日志", command=self.clear_log)
        self.clear_log_button.pack(side="right", padx=5)
        
        # 清洗代码标签页内容
        clean_frame = ttk.Frame(self.clean_tab)
        clean_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        file_frame = ttk.LabelFrame(clean_frame, text="选择要处理的文件")
        file_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        clean_scrollbar = ttk.Scrollbar(list_frame)
        clean_scrollbar.pack(side="right", fill="y")
        
        self.clean_listbox = tk.Listbox(list_frame, height=8, yscrollcommand=clean_scrollbar.set)
        self.clean_listbox.pack(fill="both", expand=True)
        clean_scrollbar.config(command=self.clean_listbox.yview)
        
        file_button_frame = ttk.Frame(file_frame)
        file_button_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(file_button_frame, text="添加文件", command=self.add_clean_file).pack(side="left", padx=5)
        ttk.Button(file_button_frame, text="添加文件夹", command=self.add_clean_folder).pack(side="left", padx=5)
        ttk.Button(file_button_frame, text="删除选中", command=self.remove_clean_file).pack(side="left", padx=5)
        ttk.Button(file_button_frame, text="清空列表", command=self.clear_clean_files).pack(side="left", padx=5)
        
        # 清理选项框架
        option_frame = ttk.LabelFrame(clean_frame, text="清理选项")
        option_frame.pack(fill="x", padx=5, pady=5)
        
        # 初始化清理选项变量
        self.remove_single_var = tk.BooleanVar(value=True)
        self.remove_multi_var = tk.BooleanVar(value=True)
        self.remove_empty_var = tk.BooleanVar(value=True)
        
        # 添加清理选项复选框
        ttk.Checkbutton(option_frame, text="删除单行注释", variable=self.remove_single_var).pack(side="left", padx=10, pady=5)
        ttk.Checkbutton(option_frame, text="删除多行注释", variable=self.remove_multi_var).pack(side="left", padx=10, pady=5)
        ttk.Checkbutton(option_frame, text="删除多余空行", variable=self.remove_empty_var).pack(side="left", padx=10, pady=5)
        
        log_frame = ttk.LabelFrame(clean_frame, text="处理日志")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        clean_log_text_frame = ttk.Frame(log_frame)
        clean_log_text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        clean_log_scrollbar = ttk.Scrollbar(clean_log_text_frame)
        clean_log_scrollbar.pack(side="right", fill="y")
        
        self.clean_log_text = tk.Text(clean_log_text_frame, wrap=tk.WORD, yscrollcommand=clean_log_scrollbar.set, height=8)
        self.clean_log_text.pack(fill="both", expand=True)
        clean_log_scrollbar.config(command=self.clean_log_text.yview)
        
        clean_control_frame = ttk.Frame(log_frame)
        clean_control_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(clean_control_frame, text="开始处理", command=self.start_clean_process).pack(side="right", padx=5)
        self.clear_clean_log_button = ttk.Button(clean_control_frame, text="清空日志", command=self.clear_clean_log)
        self.clear_clean_log_button.pack(side="right", padx=5)
        
        # 显示标签页
        self.tab_control.pack(expand=True, fill="both")
        
        # 设置默认标签页为设置页
        self.tab_control.select(self.settings_tab)
        
        # 启动日志更新
        self.update_log()
        
        # 启动清洗代码日志更新
        self.update_clean_log()
    
    def update_options(self):
        # 更新选项状态，由于使用了StringVar和不同的值，Radiobutton会自动处理互斥选择
        # 这里可以添加额外的逻辑，例如根据选择的选项更新界面
        pass
    
    def _select_file(self, title, filetypes, callback):
        """通用方法：选择文件"""
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        if file_path:
            callback(file_path)
    
    def _select_directory(self, title, callback):
        """通用方法：选择目录"""
        dir_path = filedialog.askdirectory(
            title=title
        )
        if dir_path:
            callback(dir_path)
    
    def select_main_script(self):
        def on_file_selected(file_path):
            self.main_script_path.set(file_path)
            # 如果没有设置输出名称，使用主程序文件名作为默认值
            if not self.output_name.get() or self.output_name.get() == "MyApp":
                base_name = os.path.basename(file_path)
                name_without_ext = os.path.splitext(base_name)[0]
                self.output_name.set(name_without_ext)
            
            # 设置输出目录为.py文件所在目录下的dist文件夹
            main_script_dir = os.path.dirname(os.path.abspath(file_path))
            dist_dir = os.path.join(main_script_dir, "dist")
            self.output_dir.set(dist_dir)
        
        self._select_file("选择主程序文件", [("Python文件", "*.py"), ("所有文件", "*.*")], on_file_selected)
    
    def select_icon(self):
        self._select_file("选择图标文件", [("图标文件", "*.ico"), ("所有文件", "*.*")], self.icon_path.set)
    
    def select_output_dir(self):
        self._select_directory("选择输出目录", self.output_dir.set)
    
    def _add_to_list(self, listbox, items_list, items, title="选择资源文件", filetypes=None):
        """通用方法：添加项目到列表"""
        if not filetypes:
            filetypes = [("所有文件", "*.*")]
            
        for item in items:
            if item not in items_list:
                items_list.append(item)
                listbox.insert(tk.END, item)
    
    def add_resource_file(self):
        file_paths = filedialog.askopenfilenames(
            title="选择资源文件",
            filetypes=[("所有文件", "*.*")]
        )
        self._add_to_list(self.resource_listbox, self.resource_files, file_paths)
    
    def add_resource_folder(self):
        self._select_directory("选择资源文件夹", lambda dir_path: self._add_to_list(self.resource_listbox, self.resource_files, [dir_path]))
    
    def remove_resource(self):
        selected_indices = self.resource_listbox.curselection()
        for index in sorted(selected_indices, reverse=True):
            self.resource_listbox.delete(index)
            del self.resource_files[index]
    
    def clear_resources(self):
        self.resource_listbox.delete(0, tk.END)
        self.resource_files.clear()
    
    def _get_root_directory(self):
        """获取根目录"""
        return os.path.dirname(os.path.abspath(self.main_script_path.get())) if self.main_script_path.get() else os.path.dirname(os.path.abspath(__file__))
    
    def clean_build(self, show_message=True):
        # 清理构建文件
        root_dir = self._get_root_directory()
        for dir_name in ["build", "dist", "__pycache__"]:
            dir_path = os.path.join(root_dir, dir_name)
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path, ignore_errors=True)
        
        # 清理.spec文件
        for file in os.listdir(root_dir):
            if file.endswith(".spec"):
                os.remove(os.path.join(root_dir, file))
        
        if show_message:
            messagebox.showinfo("清理完成", "构建文件已清理完成！")
    
    def clean_build_files_only(self, show_log=False):
        """
        只清理build文件夹和spec文件，保留dist文件夹
        :param show_log: 是否在日志中显示清理信息
        """
        try:
            root_dir = self._get_root_directory()
            
            # 清理文件夹和文件
            clean_items = [
                ("build", "build文件夹"),
                ("__pycache__", "__pycache__文件夹")
            ]
            
            for dir_name, display_name in clean_items:
                dir_path = os.path.join(root_dir, dir_name)
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path, ignore_errors=True)
                    if show_log:
                        self.update_log(f"已清理{display_name}: {dir_path}\n")
            
            # 清理.spec文件
            for file in os.listdir(root_dir):
                if file.endswith(".spec"):
                    spec_file = os.path.join(root_dir, file)
                    os.remove(spec_file)
                    if show_log:
                        self.update_log(f"已清理spec文件: {spec_file}\n")
            
            return True
        except Exception as e:
            if show_log:
                self.update_log(f"清理构建文件时出错: {str(e)}\n")
            return False
    
    def validate_inputs(self):
        # 验证输入
        if not self.main_script_path.get():
            messagebox.showerror("错误", "请选择主程序文件！")
            return False
        
        if not os.path.exists(self.main_script_path.get()):
            messagebox.showerror("错误", "主程序文件不存在！")
            return False
        
        return True
        
    def _set_button_state(self, button_text, state):
        """通用方法：设置按钮状态"""
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button) and child.cget("text") == button_text:
                        child.config(state=state)
                        break
    
    def start_pack(self):
        # 验证输入
        if not self.validate_inputs():
            return
        
        # 禁用开始按钮，防止重复点击
        self._set_button_state("开始打包", "disabled")
        
        # 清理之前的构建
        self.clean_build(show_message=True)
        
        # 清空日志
        self.clear_log()
        
        # 切换到日志标签页
        self.tab_control.select(self.log_tab)
        
        # 重置进度条
        self.progress_var.set(0)
        
        # 启用停止按钮
        self.stop_button.config(state="normal")
        
        # 重置停止标志
        self.stop_pack = False
        
        # 在新线程中执行打包
        self.pack_thread = threading.Thread(target=self._pack_process)
        self.pack_thread.daemon = True
        self.pack_thread.start()
    
    def _pack_process(self):
        try:
            # 清理之前的构建文件，但不显示弹窗
            self.clean_build(show_message=False)
            
            # 准备资源文件和图标参数
            resources = []
            for item in self.resource_listbox.get(0, tk.END):
                resources.append(item)
                
            icon_param = ""
            # 如果用户在工具中设置了图标，优先使用用户设置的图标
            if self.icon_path.get() and os.path.exists(self.icon_path.get()):
                icon_param = f"--icon={self.icon_path.get()}"
            else:
                # 如果用户没有设置图标，尝试从代码中检测图标设置
                main_script = self.main_script_path.get()
                if main_script and os.path.exists(main_script):
                    detected_icon = self._detect_icon_from_code(main_script, resources)
                    if detected_icon and os.path.exists(detected_icon):
                        icon_param = f"--icon={detected_icon}"
                        self.update_log(f"检测到代码中设置的图标: {detected_icon}\n")
            
            # 根据选择的选项执行打包
            if self.pack_option_var.get() == "single_file":
                self._build_single_file(resources, icon_param)
            elif self.pack_option_var.get() == "single_dir":
                self._build_folder(resources, icon_param)
            elif self.pack_option_var.get() == "both":
                self._build_single_file(resources, icon_param)
                self._build_folder(resources, icon_param)
                
            self.update_log("打包完成！")
            
            # 自动清理build文件夹和spec文件
            self.update_log("正在清理多余的构建文件...\n")
            self.clean_build_files_only(show_log=True)
            self.update_log("构建文件清理完成。\n")
            
            # 打开输出目录
            try:
                # 获取主程序文件的目录
                main_script_dir = os.path.dirname(os.path.abspath(self.main_script_path.get()))
                dist_dir = os.path.join(main_script_dir, "dist")
                
                # 在控制台中执行命令打开目录
                if sys.platform == "win32":
                    subprocess.run(f"explorer {dist_dir}", shell=True)
                # 在macOS上使用open打开目录
                elif sys.platform == "darwin":
                    subprocess.run(f"open {dist_dir}", shell=True)
                # 在Linux上使用xdg-open打开目录
                else:
                    subprocess.run(f"xdg-open {dist_dir}", shell=True)
                    
                self.update_log(f"已打开输出目录: {dist_dir}\n")
            except Exception as e:
                self.update_log(f"打开输出目录失败: {str(e)}\n")
            
            # 重新启用开始按钮
            self._set_button_state("开始打包", "normal")
        except Exception as e:
            self.update_log(f"打包失败: {str(e)}")
            
            # 重新启用开始按钮
            self._set_button_state("开始打包", "normal")
    
    def _prepare_resource_params(self, resources):
        """准备资源文件参数"""
        resource_params = []
        for resource in resources:
            if os.path.exists(resource):
                root_dir = os.path.dirname(os.path.abspath(self.main_script_path.get()))
                rel_path = os.path.relpath(resource, root_dir)
                separator = ";" if sys.platform == "win32" else ":"
                if os.path.isfile(resource):
                    dest_path = os.path.dirname(rel_path)
                else:
                    dest_path = os.path.basename(rel_path) if rel_path != "." else ""
                if not dest_path:
                    dest_path = "."
                resource_path = resource if ' ' not in resource else f'"{resource}"'
                resource_params.extend(["--add-data", f"{resource_path}{separator}{dest_path}"])
        return resource_params
    
    def _build_common_params(self, build_type, icon_param):
        """构建PyInstaller命令的通用参数"""
        # 获取主程序文件的目录
        main_script_dir = os.path.dirname(os.path.abspath(self.main_script_path.get()))
        dist_dir = os.path.join(main_script_dir, "dist")
        
        # 构建PyInstaller命令
        cmd = [
            "python",  # 使用系统Python环境
            "-m", "PyInstaller",
            build_type,  # "--onefile" 或 "--onedir"
            "--windowed",
            "--collect-all=tkinter",
            f"--name={self.output_name.get()}",
            f"--distpath={dist_dir}"
        ]
        
        if not self.enable_upx.get():
            cmd.append("--noupx")
        
        if icon_param:
            cmd.append(icon_param)
        
        return cmd
    
    def _build_single_file(self, resources, icon_param):
        self.log_queue.put("开始打包成单文件...\n")
        
        # 准备资源文件参数
        resource_params = self._prepare_resource_params(resources)
        
        # 构建PyInstaller命令
        cmd = self._build_common_params("--onefile", icon_param)
        cmd.extend(resource_params)
        cmd.append(self.main_script_path.get())
        
        # 执行命令
        self._execute_command(cmd)
        
        if not self.stop_pack:
            self.log_queue.put("单文件打包完成\n")
            self.progress_var.set(50 if self.pack_option_var.get() == "both" else 100)
    
    def _build_folder(self, resources, icon_param):
        self.log_queue.put("开始打包成文件夹...\n")
        
        # 准备资源文件参数
        resource_params = self._prepare_resource_params(resources)
        
        # 构建PyInstaller命令
        cmd = self._build_common_params("--onedir", icon_param)
        cmd.extend(resource_params)
        cmd.append(self.main_script_path.get())
        
        # 执行命令
        self._execute_command(cmd)
        
        if not self.stop_pack:
            self.log_queue.put("文件夹打包完成\n")
            self.progress_var.set(100)
    
    def _detect_icon_from_code(self, main_script, resources):
        """
        从代码中检测图标设置
        :param main_script: 主程序文件路径
        :param resources: 资源文件列表
        :return: 检测到的图标文件路径，如果没有检测到则返回None
        """
        try:
            # 读取主程序文件内容
            with open(main_script, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找可能的图标文件路径
            icon_patterns = [
                # tkinter iconbitmap
                r'root\.iconbitmap\(["\']([^"\']+\.ico)["\']\)',
                r'root\.iconbitmap\(["\']([^"\']+\.png)["\']\)',
                # tkinter wm_iconbitmap
                r'root\.wm_iconbitmap\(["\']([^"\']+\.ico)["\']\)',
                r'root\.wm_iconbitmap\(["\']([^"\']+\.png)["\']\)',
                # 其他可能的图标设置
                r'icon\s*=\s*["\']([^"\']+\.ico)["\']',
                r'icon\s*=\s*["\']([^"\']+\.png)["\']',
                r'application\.icon\s*=\s*["\']([^"\']+\.ico)["\']',
                r'application\.icon\s*=\s*["\']([^"\']+\.png)["\']',
            ]
            
            # 检查代码中的图标设置
            for pattern in icon_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    icon_path = matches[0]
                    # 如果是相对路径，转换为绝对路径
                    if not os.path.isabs(icon_path):
                        main_script_dir = os.path.dirname(os.path.abspath(main_script))
                        abs_icon_path = os.path.join(main_script_dir, icon_path)
                        if os.path.exists(abs_icon_path):
                            return abs_icon_path
                    elif os.path.exists(icon_path):
                        return icon_path
            
            # 检查资源文件中是否有图标文件
            main_script_dir = os.path.dirname(os.path.abspath(main_script))
            for resource in resources:
                if os.path.exists(resource):
                    # 如果是.ico文件，直接返回
                    if resource.lower().endswith('.ico'):
                        return resource
                    # 如果是目录，检查目录中是否有.ico文件
                    elif os.path.isdir(resource):
                        for file in os.listdir(resource):
                            if file.lower().endswith('.ico'):
                                return os.path.join(resource, file)
            
            # 检查主程序文件所在目录中是否有.ico文件
            if os.path.isdir(main_script_dir):
                for file in os.listdir(main_script_dir):
                    if file.lower().endswith('.ico'):
                        return os.path.join(main_script_dir, file)
            
            # 检查常见的图标文件名
            common_icon_names = ['icon.ico', 'app.ico', 'main.ico', 'favicon.ico']
            for icon_name in common_icon_names:
                icon_path = os.path.join(main_script_dir, icon_name)
                if os.path.exists(icon_path):
                    return icon_path
            
            return None
        except Exception as e:
            self.update_log(f"检测图标时出错: {str(e)}\n")
            return None
    
    def _execute_command(self, cmd):
        try:
            # 记录执行的命令（用于日志显示）
            cmd_str = ' '.join(cmd)
            self.log_queue.put(f"执行命令: {cmd_str}\n")
            
            # 直接在Python环境中执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 实时读取输出并更新到日志
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.log_queue.put(output.strip() + '\n')
                    
                    # 更新进度条（简单估算）
                    if "INFO" in output or "Building" in output:
                        current_progress = self.progress_var.get()
                        if current_progress < 90:
                            self.progress_var.set(min(current_progress + 5, 90))
            
            # 获取返回码
            return_code = process.poll()
            
            if return_code != 0:
                raise subprocess.CalledProcessError(return_code, cmd)
            
            # 更新进度条到100%
            if not self.stop_pack:
                self.progress_var.set(100)
                
        except Exception as e:
            if not self.stop_pack:
                self.log_queue.put(f"执行命令时出错: {str(e)}\n")
                raise e
    
    def _update_text_widget(self, text_widget, log_queue, message=None):
        """通用方法：更新文本控件"""
        # 如果提供了消息，将其添加到队列中
        if message is not None:
            log_queue.put(message)
        
        # 从队列中获取日志并更新到文本框
        try:
            while True:
                line = log_queue.get_nowait()
                text_widget.insert(tk.END, line)
                text_widget.see(tk.END)  # 自动滚动到底部
        except queue.Empty:
            pass
        
        # 定期更新
        self.root.after(100, lambda: self._update_text_widget(text_widget, log_queue))
    
    def update_log(self, message=None):
        self._update_text_widget(self.log_text, self.log_queue, message)
    
    def stop_pack_process(self):
        self.stop_pack = True
        self.log_queue.put("正在停止打包...\n")
        self.stop_button.config(state="disabled")
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.progress_var.set(0)
    
    def add_clean_file(self):
        file_paths = filedialog.askopenfilenames(
            title="选择要处理的文件",
            filetypes=[("Python文件", "*.py"), ("所有文件", "*.*")]
        )
        self._add_to_list(self.clean_listbox, self.clean_files, file_paths)
    
    def add_clean_folder(self):
        def on_folder_selected(dir_path):
            # 遍历文件夹中的所有.py文件
            py_files = []
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        py_files.append(file_path)
            self._add_to_list(self.clean_listbox, self.clean_files, py_files)
        
        self._select_directory("选择要处理的文件夹", on_folder_selected)
    
    def remove_clean_file(self):
        selected_indices = self.clean_listbox.curselection()
        for index in sorted(selected_indices, reverse=True):
            self.clean_listbox.delete(index)
            del self.clean_files[index]
    
    def clear_clean_files(self):
        self.clean_listbox.delete(0, tk.END)
        self.clean_files.clear()
    
    def start_clean_process(self):
        if not self.clean_files:
            messagebox.showerror("错误", "请先添加要处理的文件！")
            return
        
        # 清空日志
        self.clear_clean_log()
        
        # 在新线程中执行处理
        self.clean_thread = threading.Thread(target=self._clean_process)
        self.clean_thread.daemon = True
        self.clean_thread.start()
    
    def _clean_process(self):
        total_files = len(self.clean_files)
        if total_files == 0:
            self.clean_log_queue.put("没有文件需要处理\n")
            return
            
        self.clean_log_queue.put(f"开始处理 {total_files} 个文件...\n")
        
        processed_count = 0
        success_count = 0
        error_count = 0
        
        # 获取用户选择的清理选项
        remove_single = hasattr(self, 'remove_single_var') and self.remove_single_var.get()
        remove_multi = hasattr(self, 'remove_multi_var') and self.remove_multi_var.get()
        remove_empty = hasattr(self, 'remove_empty_var') and self.remove_empty_var.get()
        
        # 记录开始时间
        import time
        start_time = time.time()
        
        for file_path in self.clean_files:
            try:
                # 更新进度
                processed_count += 1
                progress = int((processed_count / total_files) * 100)
                self.clean_log_queue.put(f"[{progress}%] 正在处理: {file_path}\n")
                
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    self.clean_log_queue.put(f"错误: 文件不存在 - {file_path}\n")
                    error_count += 1
                    continue
                
                # 检查文件是否为Python文件
                if not file_path.lower().endswith('.py'):
                    self.clean_log_queue.put(f"警告: 跳过非Python文件 - {file_path}\n")
                    continue
                
                # 获取文件大小，用于日志记录
                file_size = os.path.getsize(file_path)
                self.clean_log_queue.put(f"文件大小: {file_size / 1024:.2f} KB\n")
                
                # 调用重构后的方法，删除注释和多余空行
                new_file_path = self.remove_comments_from_file(
                    file_path,
                    remove_single,  # 删除单行注释
                    remove_multi,  # 删除多行注释
                    remove_empty   # 删除多余空行
                )
                
                if new_file_path:
                    # 计算文件大小变化
                    if os.path.exists(new_file_path):
                        new_file_size = os.path.getsize(new_file_path)
                        size_reduction = ((file_size - new_file_size) / file_size) * 100
                        self.clean_log_queue.put(f"处理完成: {new_file_path} (大小减少: {size_reduction:.1f}%)\n")
                    else:
                        self.clean_log_queue.put(f"处理完成: {new_file_path}\n")
                    success_count += 1
                else:
                    self.clean_log_queue.put(f"处理失败: {file_path}\n")
                    error_count += 1
                    
            except Exception as e:
                self.clean_log_queue.put(f"处理出错: {file_path} - {str(e)}\n")
                error_count += 1
                
            # 添加短暂延迟，避免UI卡顿
            import time
            time.sleep(0.1)
        
        # 计算总耗时
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        
        # 输出总结信息
        self.clean_log_queue.put(f"\n处理完成！\n")
        self.clean_log_queue.put(f"总文件数: {total_files}\n")
        self.clean_log_queue.put(f"成功处理: {success_count}\n")
        self.clean_log_queue.put(f"处理失败: {error_count}\n")
        self.clean_log_queue.put(f"总耗时: {int(minutes)}分{int(seconds)}秒\n")
        
        # 如果有错误，提供错误总结
        if error_count > 0:
            self.clean_log_queue.put(f"\n注意: 有 {error_count} 个文件处理失败，请检查上述错误信息\n")
    
    def remove_comments_from_file(self, file_path, remove_single, remove_multi, remove_empty):
        """
        使用AST和tokenize模块智能删除Python文件中的注释，保留代码结构和缩进
        结合正则表达式和AST分析，提高注释删除的准确性和效率
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                source_code = file.read()
            
            # 使用AST模块解析代码结构
            import ast
            import io
            import tokenize
            
            # 首先使用正则表达式删除多行注释（'''或"""包围的内容）
            # 这样可以避免AST解析时将文档字符串识别为节点
            if remove_multi:
                # 使用非贪婪匹配，避免匹配到字符串中的三引号
                pattern = r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'
                # 但要保留文档字符串（在模块、类或函数定义后的第一个字符串）
                # 所以我们先找到所有文档字符串的位置
                
                # 解析AST树，找到所有文档字符串的位置
                try:
                    tree = ast.parse(source_code)
                    docstring_positions = set()
                    
                    # 遍历AST树，找到所有有文档字符串的节点
                    for node in ast.walk(tree):
                        if (isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and 
                            ast.get_docstring(node) is not None):
                            # 获取文档字符串的起始和结束行号
                            docstring = ast.get_docstring(node)
                            # 文档字符串通常在节点定义的下一行开始
                            doc_start_line = node.lineno + 1 if hasattr(node, 'lineno') else 1
                            # 计算文档字符串的行数
                            doc_lines = docstring.count('\n') + 1
                            doc_end_line = doc_start_line + doc_lines - 1
                            docstring_positions.add((doc_start_line, doc_end_line))
                except SyntaxError:
                    # 如果AST解析失败，则不保留任何文档字符串
                    docstring_positions = set()
                
                # 分割源代码为行
                lines = source_code.split('\n')
                new_lines = []
                i = 0
                
                while i < len(lines):
                    line = lines[i]
                    # 检查当前行是否是文档字符串的开始
                    is_docstring_start = False
                    docstring_end_line = i
                    
                    for start, end in docstring_positions:
                        if i + 1 == start:  # 行号从1开始，列表索引从0开始
                            is_docstring_start = True
                            docstring_end_line = end - 1  # 转换为0-based索引
                            break
                    
                    if is_docstring_start:
                        # 保留文档字符串
                        while i <= docstring_end_line and i < len(lines):
                            new_lines.append(lines[i])
                            i += 1
                    else:
                        # 检查是否是多行注释的开始
                        if '"""' in line or "'''" in line:
                            # 找到三引号的开始和结束位置
                            triple_single_start = line.find("'''")
                            triple_double_start = line.find('"""')
                            
                            # 确定使用的是哪种三引号
                            if triple_single_start != -1 and (triple_double_start == -1 or triple_single_start < triple_double_start):
                                quote_type = "'''"
                                start_pos = triple_single_start
                            else:
                                quote_type = '"""'
                                start_pos = triple_double_start
                            
                            # 检查三引号是否在同一行结束
                            end_pos = line.find(quote_type, start_pos + 3)
                            if end_pos != -1:
                                # 同一行开始和结束，删除这部分
                                line = line[:start_pos] + line[end_pos + 3:]
                                new_lines.append(line)
                            else:
                                # 多行注释，跳过直到找到结束的三引号
                                i += 1
                                found_end = False
                                while i < len(lines):
                                    if quote_type in lines[i]:
                                        # 找到结束的三引号
                                        end_pos = lines[i].find(quote_type)
                                        # 保留结束三引号之后的内容
                                        remaining_content = lines[i][end_pos + 3:]
                                        if remaining_content.strip():
                                            new_lines.append(remaining_content)
                                        found_end = True
                                        break
                                    i += 1
                                
                                if not found_end:
                                    # 没有找到结束的三引号，保留原始行
                                    new_lines.append(line)
                        else:
                            new_lines.append(line)
                        i += 1
                
                # 重新组合源代码
                source_code = '\n'.join(new_lines)
            
            # 使用tokenize模块处理单行注释和格式化
            source_buffer = io.StringIO(source_code)
            tokens = list(tokenize.generate_tokens(source_buffer.readline))
            
            # 处理token，移除单行注释
            processed_tokens = []
            for token in tokens:
                token_type = token[0]
                token_string = token[1]
                
                # 跳过单行注释
                if token_type == tokenize.COMMENT and remove_single:
                    continue
                
                # 保留其他token
                processed_tokens.append(token)
            
            # 重建源代码，保留原始格式
            output_lines = []
            current_line = 1
            current_col = 0
            line_buffer = []
            
            for token in processed_tokens:
                token_type = token[0]
                token_string = token[1]
                start_pos = token[2]  # (srow, scol)
                end_pos = token[3]    # (erow, ecol)
                
                # 处理行号变化
                while current_line < start_pos[0]:
                    if line_buffer or current_line == 1:
                        output_lines.append(''.join(line_buffer) + '\n')
                    line_buffer = []
                    current_line += 1
                    current_col = 0
                
                # 处理列位置变化（添加空格）
                while current_col < start_pos[1]:
                    line_buffer.append(' ')
                    current_col += 1
                
                # 添加token内容
                line_buffer.append(token_string)
                current_col = end_pos[1]
                
                # 如果是换行符，立即添加到输出行中
                if token_type == tokenize.NEWLINE or token_type == tokenize.ENDMARKER:
                    output_lines.append(''.join(line_buffer))
                    line_buffer = []
                    current_line += 1
                    current_col = 0
            
            # 添加最后一行（如果有）
            if line_buffer:
                output_lines.append(''.join(line_buffer))
            
            # 处理多余空行
            if remove_empty:
                # 删除连续的多个空行，只保留一个
                cleaned_lines = []
                prev_empty = False
                
                for line in output_lines:
                    is_empty = not line.strip()
                    
                    # 如果当前行不是空行，或者前一行不是空行，则保留
                    if not is_empty or not prev_empty:
                        cleaned_lines.append(line)
                    
                    prev_empty = is_empty
                
                # 删除文件末尾的空行
                while cleaned_lines and not cleaned_lines[-1].strip():
                    cleaned_lines.pop()
                
                output_lines = cleaned_lines
            
            # 创建新文件名
            dir_name, file_name = os.path.split(file_path)
            base_name, ext = os.path.splitext(file_name)
            new_file_name = f"{base_name}_no_comments{ext}"
            new_file_path = os.path.join(dir_name, new_file_name)
            
            # 写入新文件
            with open(new_file_path, 'w', encoding='utf-8') as file:
                file.writelines(output_lines)
            
            return new_file_path
        except Exception as e:
            self.clean_log_queue.put(f"处理文件时出错: {str(e)}\n")
            return None
    
    def update_clean_log(self):
        self._update_text_widget(self.clean_log_text, self.clean_log_queue)
    
    def clear_clean_log(self):
        self.clean_log_text.delete(1.0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = PackApp(root)
    root.mainloop()


