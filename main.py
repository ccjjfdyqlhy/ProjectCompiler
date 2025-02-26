import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import importlib.util
import queue
import io
import contextlib

# 修改导入工具模块的函数
def import_tool(name):
    spec = importlib.util.spec_from_file_location(
        name, 
        str(Path(__file__).parent / f"{name}.py")  # 改为直接从同级目录导入
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ConsoleRedirector(io.StringIO):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def write(self, text):
        if text.strip():  # 只处理非空文本
            self.queue.put(text)

    def flush(self):
        pass

class ConfigTab(QWidget):
    def __init__(self, config_obj, parent=None):
        super().__init__(parent)
        self.config = config_obj
        self.setupUI()

    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 创建配置表单
        form = QFormLayout()
        self.config_widgets = {}
        
        for section in self.config.config.sections():
            group = QGroupBox(section)
            group_layout = QFormLayout()
            
            for key, value in self.config.config[section].items():
                if isinstance(value, str) and value.lower() in ('true', 'false'):
                    widget = QCheckBox()
                    widget.setChecked(value.lower() == 'true')
                else:
                    widget = QLineEdit()
                    widget.setText(str(value))
                    
                self.config_widgets[(section, key)] = widget
                group_layout.addRow(key.replace('_', ' ').title() + ":", widget)
            
            group.setLayout(group_layout)
            layout.addWidget(group)
        
        # 添加保存按钮
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.saveConfig)
        layout.addWidget(save_btn)
        
        # 添加滚动区域
        scroll = QScrollArea()
        container = QWidget()
        container.setLayout(layout)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    def saveConfig(self):
        for (section, key), widget in self.config_widgets.items():
            if isinstance(widget, QCheckBox):
                value = str(widget.isChecked()).lower()
            else:
                value = widget.text()
            self.config.config[section][key] = value
            
        self.config.save_config()
        QMessageBox.information(self, "成功", "配置已保存")

class ToolDescriptionWidget(QWidget):
    def __init__(self, tool_name, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        desc = QTextEdit()
        desc.setReadOnly(True)
        
        # 工具说明字典
        descriptions = {
            "Comp-Package_py": """
<h2>Python项目编译与打包工具 (Cython + PyInstaller)</h2>

<h3>工作原理</h3>
- 使用Cython将Python代码编译为本地扩展模块
- 使用PyInstaller打包为独立可执行程序
- 自动处理资源文件和依赖关系

<h3>主要特性</h3>
• 性能提升：
  - 通过Cython编译提供优于纯Python的性能
  - 适中的性能增益，平衡开发效率

• 代码保护：
  - 将源码编译为.pyd/.so扩展模块
  - 显著增加反编译难度
  - 比单独使用PyInstaller提供更好的保护

• 易用性：
  - 交互式配置界面
  - 自动资源文件处理
  - 平衡灵活性和易用性

<h3>局限性</h3>
• 编译时间较长（包含Cython编译步骤）
• 生成程序体积较大
• 跨平台构建受限
• 部分复杂库可能需要额外配置

<h3>适用场景</h3>
• 需要平衡性能和保护的商业项目
• 包含敏感算法的应用程序
• 对易用性有要求的团队项目
• 需要自动化构建流程的项目

<h3>配置说明</h3>
1. General部分:
   - clean_temp: 是否清理临时文件
   - compiler_path: C编译器路径
   - confirm_before_compile: 是否确认编译

2. Cython部分:
   - compiler: 编译器选择
   - optimization_level: 优化级别
   - language_level: Python版本

3. PyInstaller部分:
   - console: 是否显示控制台
   - one_file: 是否生成单文件
   - icon_path: 程序图标路径

<h3>最佳实践</h3>
• 将核心逻辑放在子模块中
• 主入口文件保持简单
• 提前测试所有第三方库兼容性
• 谨慎处理动态导入
""",
            
            "Nuitka_py": """
<h2>Nuitka Python编译器</h2>

<h3>工作原理</h3>
- 将Python代码转换为C语言代码
- 使用本地C编译器生成机器码
- 完全替代CPython解释器

<h3>主要特性</h3>
• 性能优势：
  - 显著的性能提升
  - 特别适合计算密集型任务
  - 可达到数倍的速度提升

• 代码保护：
  - 直接编译为机器码
  - 极难反编译
  - 最高级别的源码保护

• 兼容性：
  - 接近系统底层
  - 稳定的跨平台支持
  - 广泛的库支持

<h3>局限性</h3>
• 需要较长编译时间
• 配置选项繁多且复杂
• 依赖本地C编译器
• 部分特殊库可能不兼容

<h3>适用场景</h3>
• 对性能要求极高的应用
• 需要最强代码保护的商业软件
• 计算密集型科学计算程序
• 大规模后端服务程序

<h3>编译选项说明</h3>
1. 基本选项:
   - standalone: 独立可执行文件模式
   - onefile: 单文件模式
   - follow_imports: 是否跟踪导入

2. 优化选项:
   - jobs: 编译线程数
   - lto: 链接时优化
   - remove_output: 移除中间文件

3. 平台特定选项:
   - windows_console_mode: 控制台模式
   - windows_icon: 程序图标
   - company_name: 公司名称

<h3>最佳实践</h3>
• 仔细规划项目结构
• 避免动态代码执行
• 测试不同优化级别
• 关注编译警告信息
""",
            
            "Obfuscate_js": """
JavaScript代码混淆工具

主要功能:
- 代码压缩和混淆
- 变量名称混淆
- 字符串加密

参数说明:
1. 项目路径: 包含JS文件的目录
2. 压缩代码: 移除空白和注释
3. 混淆变量名: 替换变量名为短字符

优势:
- 有效防止代码抄袭
- 减小文件体积
- 支持ES6+语法

使用场景:
- 前端代码保护
- Web应用发布
- 商业JS库分发
            """,
            
            "Compress_html": """
HTML文件压缩工具

主要功能:
- HTML文件压缩
- CSS/JS内联代码压缩
- 自动优化HTML结构

参数说明:
1. 项目路径: 包含HTML文件的目录
2. 删除注释: 移除HTML注释
3. 压缩空白: 优化空白字符

优势:
- 提升加载速度
- 减小文件体积
- 保持代码功能

使用场景:
- 网站发布优化
- 静态页面部署
- CDN部署前处理
            """,
            
            "pyinstxtractor": """
PyInstaller程序解包工具

主要功能:
- 提取PyInstaller打包的程序
- 还原Python字节码文件
- 分析程序结构

参数说明:
1. EXE文件: 要解包的程序文件

注意事项:
- 仅支持PyInstaller打包的程序
- 需要与目标程序使用相同Python版本
- 某些加密保护的程序可能无法提取

使用场景:
- 程序分析和学习
- 兼容性测试
- 问题程序诊断
            """
        }
        
        desc.setHtml(descriptions.get(tool_name, "暂无说明"))
        desc.setMinimumWidth(300)
        layout.addWidget(desc)

class ToolTab(QWidget):
    def __init__(self, tool_name, tool_module, parent=None):
        super().__init__(parent)
        self.tool_name = tool_name
        self.tool_module = tool_module
        self.console_queue = queue.Queue()
        
        # 初始化配置对象 (除了pyinstxtractor)
        if tool_name != "pyinstxtractor":
            if hasattr(tool_module, 'CompilerConfig'):
                self.config = tool_module.CompilerConfig()
            elif hasattr(tool_module, 'NuitkaConfig'):
                self.config = tool_module.NuitkaConfig()
            elif hasattr(tool_module, 'ObfuscatorConfig'):
                self.config = tool_module.ObfuscatorConfig()
        
        self.setupUI()

    def setupUI(self):
        # 主布局使用QHBoxLayout
        main_layout = QHBoxLayout(self)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 工具说明
        description = ToolDescriptionWidget(self.tool_name)
        left_layout.addWidget(description)
        
        # 工具特定的控件
        controls = QWidget()
        self.form_layout = QFormLayout(controls)
        self.setupToolSpecificControls()
        left_layout.addWidget(controls)

        # 控制按钮
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("运行")
        self.run_button.clicked.connect(self.runTool)
        button_layout.addWidget(self.run_button)
        
        # 仅为非pyinstxtractor工具添加配置按钮
        if self.tool_name != "pyinstxtractor":
            self.config_button = QPushButton("配置")
            self.config_button.clicked.connect(self.showConfig)
            button_layout.addWidget(self.config_button)
            
        left_layout.addLayout(button_layout)
        
        # 右侧控制台输出
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 添加"控制台输出"标签
        console_label = QLabel("控制台输出:")
        right_layout.addWidget(console_label)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        # 设置等宽字体
        self.console.setFont(QFont("Courier New", 10))
        right_layout.addWidget(self.console)
        
        # 添加分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # 设置左右面板的初始大小比例
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # 定时器用于更新控制台输出
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.updateConsole)
        self.update_timer.start(100)

    def showConfig(self):
        config_dialog = QDialog(self)
        config_dialog.setWindowTitle("工具配置")
        config_dialog.setModal(True)
        
        layout = QVBoxLayout(config_dialog)
        config_tab = ConfigTab(self.config)
        layout.addWidget(config_tab)
        
        config_dialog.exec()

    def setupToolSpecificControls(self):
        if self.tool_name == "Comp-Package_py":
            self.setupPythonCompilerControls()
        elif self.tool_name == "Nuitka_py":
            self.setupNuitkaControls()
        elif self.tool_name == "Obfuscate_js":
            self.setupJSObfuscatorControls()
        elif self.tool_name == "Compress_html":
            self.setupHTMLCompressorControls()
        elif self.tool_name == "pyinstxtractor":
            self.setupPyInstExtractorControls()

    def setupPythonCompilerControls(self):
        self.project_path = QLineEdit()
        self.main_file = QLineEdit()
        self.browse_project = QPushButton("浏览...")
        self.browse_project.clicked.connect(lambda: self.browsePath(self.project_path))

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.project_path)
        path_layout.addWidget(self.browse_project)

        self.form_layout.addRow("项目路径:", path_layout)
        self.form_layout.addRow("主文件:", self.main_file)

        # 编译选项
        self.clean_temp = QCheckBox("清理临时文件")
        self.show_console = QCheckBox("显示控制台")
        self.clean_temp.setChecked(True)
        self.show_console.setChecked(True)

        self.form_layout.addRow("", self.clean_temp)
        self.form_layout.addRow("", self.show_console)

    def setupNuitkaControls(self):
        # Nuitka特定的控件设置
        self.project_path = QLineEdit()
        self.browse_project = QPushButton("浏览...")
        self.browse_project.clicked.connect(lambda: self.browsePath(self.project_path))

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.project_path)
        path_layout.addWidget(self.browse_project)

        self.form_layout.addRow("项目路径:", path_layout)
        
        self.standalone = QCheckBox("独立可执行文件")
        self.onefile = QCheckBox("单文件模式")
        self.standalone.setChecked(True)
        
        self.form_layout.addRow("", self.standalone)
        self.form_layout.addRow("", self.onefile)

    def setupJSObfuscatorControls(self):
        # JavaScript混淆器特定的控件设置
        self.project_path = QLineEdit()
        self.browse_project = QPushButton("浏览...")
        self.browse_project.clicked.connect(lambda: self.browsePath(self.project_path))

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.project_path)
        path_layout.addWidget(self.browse_project)

        self.form_layout.addRow("项目路径:", path_layout)
        
        self.minify = QCheckBox("压缩代码")
        self.mangle = QCheckBox("混淆变量名")
        self.minify.setChecked(True)
        self.mangle.setChecked(True)
        
        self.form_layout.addRow("", self.minify)
        self.form_layout.addRow("", self.mangle)

    def setupHTMLCompressorControls(self):
        # HTML压缩器特定的控件设置
        self.project_path = QLineEdit()
        self.browse_project = QPushButton("浏览...")
        self.browse_project.clicked.connect(lambda: self.browsePath(self.project_path))

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.project_path)
        path_layout.addWidget(self.browse_project)

        self.form_layout.addRow("项目路径:", path_layout)
        
        self.remove_comments = QCheckBox("删除注释")
        self.collapse_whitespace = QCheckBox("压缩空白")
        self.remove_comments.setChecked(True)
        self.collapse_whitespace.setChecked(True)
        
        self.form_layout.addRow("", self.remove_comments)
        self.form_layout.addRow("", self.collapse_whitespace)

    def setupPyInstExtractorControls(self):
        # PyInstaller提取器特定的控件设置
        self.file_path = QLineEdit()
        self.browse_file = QPushButton("浏览...")
        self.browse_file.clicked.connect(lambda: self.browsePath(self.file_path, "File"))

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.file_path)
        path_layout.addWidget(self.browse_file)

        self.form_layout.addRow("EXE文件:", path_layout)

    def browsePath(self, line_edit, mode="Dir"):
        if mode == "Dir":
            path = QFileDialog.getExistingDirectory(self, "选择目录")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if path:
            line_edit.setText(path)

    def updateConsole(self):
        try:
            while True:
                text = self.console_queue.get_nowait()
                self.console.append(text.rstrip())
                self.console.verticalScrollBar().setValue(
                    self.console.verticalScrollBar().maximum()
                )
        except queue.Empty:
            pass

    def runTool(self):
        # 清空控制台
        self.console.clear()
        
        # 重定向stdout到我们的队列
        redirector = ConsoleRedirector(self.console_queue)
        
        # 创建工作线程
        self.worker_thread = QThread()
        
        # 创建工作类
        class Worker(QObject):
            def __init__(self, tool, redirector):
                super().__init__()
                self.tool = tool
                self.redirector = redirector
            
            def run(self):
                with contextlib.redirect_stdout(self.redirector):
                    if self.tool.tool_name == "Comp-Package_py":
                        self.tool.runPythonCompiler()
                    elif self.tool.tool_name == "Nuitka_py":
                        self.tool.runNuitka()
                    elif self.tool.tool_name == "Obfuscate_js":
                        self.tool.runJSObfuscator()
                    elif self.tool.tool_name == "Compress_html":
                        self.tool.runHTMLCompressor()
                    elif self.tool.tool_name == "pyinstxtractor":
                        self.tool.runPyInstExtractor()
                self.tool.worker_thread.quit()

        # 创建工作对象
        self.worker = Worker(self, redirector)
        self.worker.moveToThread(self.worker_thread)
        
        # 连接信号
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        
        # 启动线程
        self.worker_thread.start()

    def runPythonCompiler(self):
        # 实现Python编译器的运行逻辑
        compiler = self.tool_module.ProjectCompiler(
            self.project_path.text(),
            self.main_file.text()
        )
        compiler.config.config['General']['clean_temp'] = str(self.clean_temp.isChecked())
        compiler.config.config['PyInstaller']['console'] = str(self.show_console.isChecked())
        compiler.config.config['General']['confirm_before_compile'] = 'false'  # 禁用确认
        compiler.compile_project()

    def runNuitka(self):
        # 实现Nuitka编译器的运行逻辑
        compiler = self.tool_module.NuitkaCompiler(
            self.project_path.text(),
            self.main_file.text()
        )
        compiler.config.config['General']['confirm_before_compile'] = 'false'  # 禁用确认
        compiler.config.config['Nuitka']['standalone'] = str(self.standalone.isChecked())
        compiler.config.config['Nuitka']['onefile'] = str(self.onefile.isChecked())
        compiler.compile_project()

    def runJSObfuscator(self):
        # 实现JavaScript混淆器的运行逻辑
        obfuscator = self.tool_module.JSObfuscator(
            self.project_path.text()
        )
        obfuscator.config.config['General']['confirm_before_process'] = 'false'  # 禁用确认
        obfuscator.process_project()

    def runHTMLCompressor(self):
        # 实现HTML压缩器的运行逻辑
        compressor = self.tool_module.HTMLObfuscator(
            self.project_path.text()
        )
        compressor.config.config['General']['confirm_before_process'] = 'false'  # 禁用确认
        compressor.process_project()

    def runPyInstExtractor(self):
        # 实现PyInstaller提取器的运行逻辑
        if not self.file_path.text():
            print("请选择要提取的EXE文件")
            return
            
        arch = self.tool_module.PyInstArchive(self.file_path.text())
        if arch.open():
            if arch.checkFile():
                if arch.getCArchiveInfo():
                    arch.parseTOC()
                    arch.extractFiles()
                    arch.close()
                    print("提取完成")
                    return
            arch.close()
        print("提取失败")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("项目编译工具集")
        self.setupUI()

    def setupUI(self):
        self.setMinimumSize(800, 600)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 导入并添加工具
        tools = [
            ("Python打包器", "Comp-Package_py"),
            ("Nuitka编译器", "Nuitka_py"),
            ("JS混淆器", "Obfuscate_js"),
            ("HTML压缩器", "Compress_html"),
            ("PyInstaller提取器", "pyinstxtractor")
        ]

        for title, module_name in tools:
            try:
                module = import_tool(module_name)
                tab = ToolTab(module_name, module)
                self.tabs.addTab(tab, title)
            except Exception as e:
                print(f"加载{title}失败: {str(e)}")

        # 添加菜单栏
        self.setupMenuBar()

    def setupMenuBar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.showAbout)
        help_menu.addAction(about_action)

    def showAbout(self):
        QMessageBox.about(self, 
            "关于项目编译工具集",
            "项目编译工具集 v1.0\n\n"
            "一个集成了多种编译和混淆工具的图形界面程序。\n"
            "支持Python、JavaScript、HTML等多种项目类型的处理。"
        )

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion风格
    
    # 设置应用程序样式
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
