import os
import sys
import time
import shutil
import argparse
import configparser
from typing import List, Set, Dict, Any
from pathlib import Path
from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext
import platform

TOOL_NAME = "Python 3 项目编译与发行版打包工具"
VERSION = "0.5.0"


def show_tool_info():
    print(f"\n{TOOL_NAME} v{VERSION}")
    print("="*50 + "\n")


cwd = os.getcwd()


class CompilerConfig:
    DEFAULT_CONFIG = {
        'General': {
            'clean_temp': 'true',
            'compiler_path': '',
            'confirm_before_compile': 'true'
        },
        'Cython': {
            'compiler': 'auto',
            'optimization_level': '-O2',
            'language_level': '3',
            'unix_compiler': 'gcc',
            'windows_compiler': 'msvc'
        },
        'PyInstaller': {
            'console': 'true',
            'one_file': 'false',  # 修改默认值为false
            'icon_path': '',
            'additional_data': ''
        }
    }

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = Path.home() / '.projectcompiler' / 'config.ini'
        self.load_config()

    def load_config(self):
        self.config.read_dict(self.DEFAULT_CONFIG)
        if self.config_file.exists():
            self.config.read(self.config_file)

    def save_config(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def update_from_args(self, args: Dict[str, Any]):
        for section in self.config.sections():
            for key in self.config[section]:
                arg_name = f"{section.lower()}_{key}"
                if arg_name in args and args[arg_name] is not None:
                    self.config[section][key] = str(args[arg_name])

    def get_config_dict(self) -> Dict[str, Dict[str, str]]:
        return {s: dict(self.config.items(s)) for s in self.config.sections()}


class ProjectCompiler:
    def __init__(self, project_path: str | Path, main_file: str, config: CompilerConfig = None) -> None:
        if not Path(project_path).exists():
            raise ValueError(f"项目路径不存在: {project_path}")
        if not main_file.endswith('.py'):
            raise ValueError("主入口文件必须是Python文件")
        self.project_path = os.path.abspath(project_path)
        self.main_file = main_file
        self.project_name = self._extract_project_name()

        self.build_dir = os.path.join(self.project_path, 'build', self.project_name)
        self.dist_dir = os.path.join(self.project_path, 'dist', self.project_name)
        self.temp_dir = os.path.join(self.project_path, 'temp', self.project_name)

        self.config = config or CompilerConfig()

        self.platform = platform.system().lower()
        self.compiler_settings = self._get_platform_compiler_settings()

    def _extract_project_name(self) -> str:
        path = Path(self.project_path)
        project_name = path.name
        if not project_name:
            project_name = path.parent.name
        return project_name

    def _get_suggested_output_name(self) -> str:
        return self.project_name

    def _get_platform_compiler_settings(self) -> dict:
        settings = {
            'extra_compile_args': [self.config.config['Cython']['optimization_level']]
        }

        if self.platform == 'windows':
            settings['compiler'] = self.config.config['Cython']['windows_compiler']
        else:
            settings['compiler'] = self.config.config['Cython']['unix_compiler']

        if self.config.config['General']['compiler_path']:
            settings['compiler_path'] = self.config.config['General']['compiler_path']

        if self.platform == 'linux':
            settings['extra_compile_args'].extend(['-fPIC'])
        elif self.platform == 'darwin':
            settings['extra_compile_args'].extend(['-Wno-unused-function'])

        return settings

    def collect_python_files(self) -> Set[str]:
        python_files = set()
        main_file_path = os.path.join(self.project_path, self.main_file)

        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    if file_path!= main_file_path:
                        python_files.add(file_path)

        return python_files

    def create_cython_files(self, python_files: Set[str]) -> List[str]:
        cython_files = []
        os.makedirs(self.temp_dir, exist_ok=True)

        for py_file in python_files:
            relative_path = os.path.relpath(py_file, self.project_path)
            pyx_file = os.path.join(self.temp_dir, 
                                   os.path.splitext(relative_path)[0] + '.pyx')

            os.makedirs(os.path.dirname(pyx_file), exist_ok=True)
            shutil.copy2(py_file, pyx_file)
            cython_files.append(pyx_file)

        return cython_files

    def build_extensions(self, cython_files: List[str]):
        try:
            extensions = []
            original_dir = os.getcwd()

            try:
                os.chdir(str(self.temp_dir))

                for pyx_file in cython_files:
                    relative_path = os.path.relpath(pyx_file, self.temp_dir)
                    module_name = os.path.splitext(relative_path)[0].replace(os.sep, '.')

                    ext = Extension(
                        module_name,
                        sources=[pyx_file],
                        extra_compile_args=self.compiler_settings['extra_compile_args'],
                        language='c++',
                    )
                    extensions.append(ext)

                if self.platform == 'windows':
                    if self.compiler_settings.get('compiler_path'):
                        os.environ['VS100COMNTOOLS'] = self.compiler_settings['compiler_path']
                else:
                    if self.compiler_settings.get('compiler_path'):
                        os.environ['CC'] = self.compiler_settings['compiler_path']
                        os.environ['CXX'] = self.compiler_settings['compiler_path']

                print("开始编译...")
                setup(
                    name='compiled_modules',
                    ext_modules=cythonize(
                        extensions,
                        compiler_directives={
                            'language_level': '3',
                            'boundscheck': False,
                            'wraparound': False,
                            'cdivision': True,  # 使用C除法
                            'infer_types': True,  # 类型推断优化
                            'nonecheck': False,  # 禁用None检查
                        }
                    ),
                    script_args=['build_ext', '--inplace']
                )

           # 新增：将编译后的文件移动到项目目录
                print("移动编译后的文件到项目目录...")
                for root, _, files in os.walk(self.temp_dir):
                    for file in files:
                        if file.endswith(('.pyd', '.so')):  # Windows用pyd，Linux/Mac用so
                            src_file = os.path.join(root, file)
                            # 计算相对路径，保持目录结构
                            rel_path = os.path.relpath(root, self.temp_dir)
                            dst_dir = os.path.join(self.project_path, rel_path)
                            os.makedirs(dst_dir, exist_ok=True)
                            dst_file = os.path.join(dst_dir, file)
                            shutil.copy2(src_file, dst_file)
                            print(f"已移动: {os.path.relpath(dst_file, self.project_path)}")

            finally:
                os.chdir(original_dir)

        except Exception as e:
            print(f"编译错误: {str(e)}")
            print(f"当前工作目录: {os.getcwd()}")
            print(f"临时目录: {self.temp_dir}")
            raise

    def collect_resource_files(self) -> List[tuple]:
        """收集项目中的资源文件"""
        resource_files = []
        exclude_dirs = {'build', 'dist', 'temp', '__pycache__', '.git', '.svn'}
        exclude_extensions = {'.py', '.pyc', '.pyo', '.pyd', '.so'}
        
        for root, dirs, files in os.walk(self.project_path):
            # 排除特定目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if os.path.splitext(file)[1] not in exclude_extensions:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, self.project_path)
                    # 返回 (源文件路径, 目标路径) 元组
                    resource_files.append((abs_path, rel_path))
        
        return resource_files

    def create_pyinstaller_spec(self):
        # 收集资源文件
        resource_files = self.collect_resource_files()
        
        # 收集编译后的pyd/so文件
        binaries = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(('.pyd', '.so')):
                    file_path = os.path.join(root, file)
                    rel_dir = os.path.dirname(os.path.relpath(file_path, self.project_path))
                    binaries.append((file_path, rel_dir or '.'))
        
        # 转换资源文件列表为PyInstaller格式
        datas_str = repr([(src, os.path.dirname(dst) or '.') for src, dst in resource_files])
        binaries_str = repr(binaries)
        
        spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    [r'{self.main_file}'],
    pathex=[r'{self.project_path}'],
    binaries={binaries_str},
    datas={datas_str},
    hiddenimports=[],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['*.py', '*.pyc', '*.pyo'],  # 排除所有Python源文件和字节码文件
    noarchive=False,
)

# 删除所有.py和.pyc文件
for d in a.datas.copy():
    if d[0].endswith(('.py', '.pyc', '.pyo')):
        a.datas.remove(d)

# 删除所有Python模块的.py和.pyc文件
for d in a.pure.copy():
    if d[0] + '.py' in [x[0] for x in a.pure]:
        a.pure.remove(d)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{self.project_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={self.config.config['PyInstaller'].getboolean('console')},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{self.project_name}'
)
"""
        spec_file = os.path.join(self.project_path, 'project.spec')
        with open(spec_file, 'w') as f:
            f.write(spec_content)
        return spec_file

    def compile_project(self):
        self._show_config()
        
        # 添加重要警告信息
        print("\n!!! 重要提示 !!!")
        print("=" * 50)
        print("为确保编译后程序正常运行，请确保：")
        print("1. 核心逻辑代码放在主入口文件引用的子模块中")
        print("2. 在主入口文件中导入所有子模块需要的外部库")
        print("3. 避免在子模块中直接导入外部库")
        print("=" * 50)
        
        # 修改确认逻辑，检查配置中的confirm_before_compile
        if self.config.config['General'].getboolean('confirm_before_compile'):
            if not input("\n我已经确认了以上事项 (y/N): ").lower() == 'y':
                print("取消编译")
                return
            
            # 第二次确认也应该被跳过
            if not self._confirm_compile():
                print("取消编译")
                return

        start_time = time.time()

        try:
            print("1. 收集Python文件...")
            python_files = self.collect_python_files()

            print("2. 创建Cython文件...")
            cython_files = self.create_cython_files(python_files)

            print("3. 编译扩展模块...")
            self.build_extensions(cython_files)

            print("4. 创建PyInstaller规范文件...")
            spec_file = self.create_pyinstaller_spec()

            print("5. 使用PyInstaller打包...")
            os.system(f"pyinstaller {spec_file}")

            if self.config.config['General'].getboolean('clean_temp'):
                print("6. 清理临时文件...")
                self.cleanup()
            else:
                print("跳过清理临时文件...")

            total_time = time.time() - start_time
            minutes = int(total_time // 60)
            seconds = total_time % 60

            print(f"\n编译完成！总用时: {minutes}分{seconds:.1f}秒")
            print("请检查PyInstaller输出以防发行版打包过程出错。如果成功，输出文件在 dist 目录中。")

        except Exception as e:
            print(f"编译过程中出错: {str(e)}")
            self.cleanup()
            raise

    def _show_config(self):
        print("\n=== 当前配置 ===")
        for section in self.config.config.sections():
            print(f"\n[{section}]")
            for key, value in self.config.config[section].items():
                print(f"{key} = {value}")
        print("\n")

    def _confirm_compile(self) -> bool:
        return input("确认执行编译? (y/N): ").lower() == 'y'

    def cleanup(self):
        """清理临时文件和已复制的编译文件"""
        dirs_to_clean = [self.temp_dir]
        
        # 如果设置了清理临时文件，也清理项目目录中的pyd/so文件
        if self.config.config['General'].getboolean('clean_temp'):
            print("清理编译生成的文件...")
            for root, _, files in os.walk(self.project_path):
                for file in files:
                    if file.endswith(('.pyd', '.so')):
                        try:
                            os.remove(os.path.join(root, file))
                        except Exception as e:
                            print(f"警告: 无法删除文件 {file}: {e}")

        for dir_path in dirs_to_clean:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)


def main():
    show_tool_info()
    parser = argparse.ArgumentParser(description=f'ProjectCompiler 中一个用于编译、打包 Python 3 项目的全平台开发者实用工具。')
    parser.add_argument('project_path', nargs='?', help='项目路径')
    parser.add_argument('main_file', nargs='?', help='主入口文件')
    parser.add_argument('--output', '-o', help='输出文件名')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认所有提示')

    parser.add_argument('--config', action='store_true', help='配置模式')
    parser.add_argument('--general_clean_temp', type=bool, help='是否清理临时文件')
    parser.add_argument('--general_compiler_path', help='编译器路径')
    parser.add_argument('--pyinstaller_output_name', help='输出文件名')
    parser.add_argument('--pyinstaller_console', type=bool, help='是否显示控制台')
    parser.add_argument('--pyinstaller_one_file', type=bool, help='是否打包为单文件')

    args = parser.parse_args()
    config = CompilerConfig()

    if args.config:
        _interactive_config(config)
        return

    if not all([args.project_path, args.main_file, args.output]):
        print("=== 交互模式 ===")
        _interactive_input(args)

    try:
        config.update_from_args(vars(args))
        compiler = ProjectCompiler(args.project_path, args.main_file, config)
        if args.yes:
            compiler.config.config['General']['confirm_before_compile'] = 'false'
        compiler.compile_project()
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


def _interactive_config(config: CompilerConfig):
    show_tool_info()
    print("=== 配置模式 ===")
    for section in config.config.sections():
        print(f"\n[{section}]")
        for key in config.config[section]:
            current = config.config[section][key]
            value = input(f"{key} [{current}]: ").strip()
            if value:
                config.config[section][key] = value

    config.save_config()
    print("\n配置已保存")


def _interactive_input(args):
    if not args.project_path:
        args.project_path = input("请输入项目路径: ").strip()
    if not args.main_file:
        args.main_file = input("请输入主入口文件: ").strip()
    if not args.output:
        suggested_name = ProjectCompiler(args.project_path, args.main_file)._get_suggested_output_name()
        args.output = input(f"请输入输出文件名 [{suggested_name}]: ").strip() or suggested_name


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户取消操作")
        sys.exit(1)
    except ValueError:
        print("错误: 提供的文件或目录不存在")
        sys.exit(1)