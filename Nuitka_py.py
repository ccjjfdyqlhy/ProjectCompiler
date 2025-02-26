import os
import sys
import time
import shutil
import argparse
import configparser
from pathlib import Path
from typing import Dict, Any

TOOL_NAME = "Python 3 项目 Nuitka 编译工具"
VERSION = "0.1.0"

class NuitkaConfig:
    DEFAULT_CONFIG = {
        'General': {
            'clean_temp': 'true',
            'confirm_before_compile': 'true'
        },
        'Nuitka': {
            'standalone': 'true',
            'onefile': 'false',
            'windows_icon': '',
            'company_name': '',
            'product_name': '',
            'file_version': '',
            'show_progress': 'true',
            'show_memory': 'false',
            'jobs': 'auto',
            'lto': 'auto',
            # 新增编译选项
            'windows_console_mode': 'force',  # force/disable/attach/hide
            'follow_imports': 'true',
            'include_package_data': '',  # 格式: package_name:*.txt,package_name2
            'include_data_files': '',    # 格式: source=dest,source2=dest2
            'noinclude_dlls': '',        # 格式: pattern1,pattern2
            'prefer_source_code': 'true',
            'python_flag': '',           # no_site/no_warnings/no_asserts
            'remove_output': 'false',
            'unstripped': 'false',       # 保留调试信息
            'low_memory': 'false',       # 低内存模式
            'disable_console': 'false',   # 禁用控制台
            'file_description': '',       # 文件描述
            'copyright': '',              # 版权信息
            'trademarks': '',             # 商标信息
            'output_dir': '',             # 新增：输出目录配置
            'module_name_choice': 'original'  # 新增：模块名称选择模式
        }
    }

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = Path.home() / '.projectcompiler' / 'nuitka_config.ini'
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

class NuitkaCompiler:
    def __init__(self, project_path: str | Path, main_file: str, config: NuitkaConfig = None):
        if not Path(project_path).exists():
            raise ValueError(f"项目路径不存在: {project_path}")
        if not main_file.endswith('.py'):
            raise ValueError("主入口文件必须是Python文件")
            
        self.project_path = os.path.abspath(project_path)
        self.main_file = main_file
        self.project_name = Path(project_path).name
        self.config = config or NuitkaConfig()
        
        # 添加输出目录设置
        self.dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dist'))
        self.output_dir = os.path.join(self.dist_dir, self.project_name)
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def build_nuitka_command(self) -> str:
        """构建Nuitka编译命令"""
        cmd_parts = [
            'python -m nuitka',
            f'"{os.path.join(self.project_path, self.main_file)}"',
            f'--output-dir="{self.output_dir}"'  # 添加输出目录参数
        ]

        nuitka_config = self.config.config['Nuitka']
        
        # 基本选项
        if nuitka_config.getboolean('standalone'):
            cmd_parts.append('--standalone')
        
        if nuitka_config.getboolean('onefile'):
            cmd_parts.append('--onefile')
            
        if nuitka_config.getboolean('show_progress'):
            cmd_parts.append('--show-progress')
            
        if nuitka_config.getboolean('show_memory'):
            cmd_parts.append('--show-memory')

        # 修改：移除之前的输出目录设置，使用类中定义的输出目录
        if nuitka_config['output_dir']:
            print("警告: 配置中的 output_dir 设置将被忽略，统一使用 dist 目录")

        # 模块名称选择
        if nuitka_config['module_name_choice']:
            cmd_parts.append(f'--module-name-choice={nuitka_config["module_name_choice"]}')

        # Windows特定选项
        if os.name == 'nt':
            if nuitka_config['windows_icon']:
                cmd_parts.append(f'--windows-icon-from-ico="{nuitka_config["windows_icon"]}"')
            
            console_mode = nuitka_config['windows_console_mode']
            if console_mode in ['force', 'disable', 'attach', 'hide']:
                cmd_parts.append(f'--windows-console-mode={console_mode}')

        # 版本信息
        for info_key in ['company_name', 'product_name', 'file_version', 
                        'file_description', 'copyright', 'trademarks']:
            if nuitka_config[info_key]:
                cmd_parts.append(f'--{info_key.replace("_", "-")}="{nuitka_config[info_key]}"')

        # 数据文件支持
        if nuitka_config['include_package_data']:
            for package_data in nuitka_config['include_package_data'].split(','):
                if package_data:
                    cmd_parts.append(f'--include-package-data={package_data}')
                    
        if nuitka_config['include_data_files']:
            for data_file in nuitka_config['include_data_files'].split(','):
                if data_file:
                    cmd_parts.append(f'--include-data-files={data_file}')

        if nuitka_config['noinclude_dlls']:
            for pattern in nuitka_config['noinclude_dlls'].split(','):
                if pattern:
                    cmd_parts.append(f'--noinclude-dlls={pattern}')

        # 编译优化选项
        if nuitka_config['jobs'] != 'auto':
            cmd_parts.append(f'--jobs={nuitka_config["jobs"]}')
            
        if nuitka_config['lto'] != 'auto':
            cmd_parts.append(f'--lto={nuitka_config["lto"]}')

        if nuitka_config.getboolean('prefer_source_code'):
            cmd_parts.append('--prefer-source-code')

        if nuitka_config.getboolean('remove_output'):
            cmd_parts.append('--remove-output')

        if nuitka_config.getboolean('unstripped'):
            cmd_parts.append('--unstripped')

        if nuitka_config.getboolean('low_memory'):
            cmd_parts.append('--low-memory')

        # Python标记
        if nuitka_config['python_flag']:
            for flag in nuitka_config['python_flag'].split(','):
                if flag:
                    cmd_parts.append(f'--python-flag={flag}')

        # 导入控制
        if nuitka_config.getboolean('follow_imports'):
            cmd_parts.append('--follow-imports')

        return ' '.join(cmd_parts)

    def compile_project(self):
        print(f"\n{TOOL_NAME} v{VERSION}")
        print("="*50 + "\n")
        
        if self.config.config['General'].getboolean('confirm_before_compile'):
            if not input("确认执行编译? (y/N): ").lower() == 'y':
                print("取消编译")
                return

        start_time = time.time()
        
        try:
            print("开始编译项目...")
            print(f"输出目录: {self.output_dir}")
            command = self.build_nuitka_command()
            print(f"执行命令: {command}")
            
            result = os.system(command)
            
            if result != 0:
                raise RuntimeError("编译失败")
                
            if self.config.config['General'].getboolean('clean_temp'):
                print("清理临时文件...")
                self._cleanup()
                
            total_time = time.time() - start_time
            minutes = int(total_time // 60)
            seconds = total_time % 60
            
            print(f"\n编译完成！总用时: {minutes}分{seconds:.1f}秒")
            print(f"输出文件在: {self.output_dir}")
            
        except Exception as e:
            print(f"编译过程中出错: {str(e)}")
            self._cleanup()
            raise

    def _cleanup(self):
        """清理临时文件，但保留dist目录"""
        build_dir = os.path.join(self.project_path, 'build')
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
            
        # 清理项目目录中的临时文件，但保留dist目录的内容
        for root, dirs, files in os.walk(self.project_path):
            if 'dist' in dirs:
                dirs.remove('dist')  # 不遍历dist目录
            for file in files:
                if file.endswith(('.pyd', '.so', '.pyo', '.pyc')):
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception as e:
                        print(f"警告: 无法删除文件 {file}: {e}")

def main():
    parser = argparse.ArgumentParser(description=f'{TOOL_NAME} - 用于编译Python项目的工具')
    parser.add_argument('project_path', nargs='?', help='项目路径')
    parser.add_argument('main_file', nargs='?', help='主入口文件')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认所有提示')
    
    # 添加Nuitka相关的命令行参数
    parser.add_argument('--standalone', action='store_true', help='创建独立可执行文件')
    parser.add_argument('--onefile', action='store_true', help='创建单文件可执行文件')
    parser.add_argument('--windows-icon', help='Windows可执行文件图标路径')
    parser.add_argument('--company-name', help='公司名称')
    parser.add_argument('--product-name', help='产品名称')
    parser.add_argument('--file-version', help='文件版本')
    
    # 添加新的Nuitka相关命令行参数
    parser.add_argument('--windows-console-mode', choices=['force', 'disable', 'attach', 'hide'], 
                       help='Windows控制台模式')
    parser.add_argument('--include-package-data', help='包含包数据文件，格式: package_name:*.txt')
    parser.add_argument('--include-data-files', help='包含数据文件，格式: source=dest')
    parser.add_argument('--noinclude-dlls', help='排除DLL文件，格式: pattern1,pattern2')
    parser.add_argument('--python-flag', help='Python标记，格式: flag1,flag2')
    parser.add_argument('--prefer-source-code', action='store_true', help='优先使用源代码')
    parser.add_argument('--remove-output', action='store_true', help='移除输出目录')
    parser.add_argument('--unstripped', action='store_true', help='保留调试信息')
    parser.add_argument('--low-memory', action='store_true', help='低内存模式')
    parser.add_argument('--file-description', help='文件描述')
    parser.add_argument('--copyright', help='版权信息')
    parser.add_argument('--trademarks', help='商标信息')
    parser.add_argument('--output-dir', help='输出目录路径')
    parser.add_argument('--module-name-choice', choices=['original', 'runtime'], 
                       default='original', help='模块名称选择模式')

    args = parser.parse_args()
    config = NuitkaConfig()

    if args.config:
        _interactive_config(config)
        return

    if not all([args.project_path, args.main_file]):
        _interactive_input(args)

    try:
        config.update_from_args(vars(args))
        if args.yes:
            config.config['General']['confirm_before_compile'] = 'false'
        compiler = NuitkaCompiler(args.project_path, args.main_file, config)
        compiler.compile_project()
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)

def _interactive_config(config: NuitkaConfig):
    print(f"\n{TOOL_NAME} v{VERSION}")
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户取消操作")
        sys.exit(1)
