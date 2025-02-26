import os
import sys
import time
import shutil
import argparse
import configparser
import subprocess
from typing import List, Set, Dict, Any
from pathlib import Path

TOOL_NAME = "JavaScript 项目混淆工具"
VERSION = "0.1.0"

def show_tool_info():
    print(f"\n{TOOL_NAME} v{VERSION}")
    print("="*50 + "\n")

class ObfuscatorConfig:
    DEFAULT_CONFIG = {
        'General': {
            'clean_temp': 'true',
            'confirm_before_process': 'true'
        },
        'Obfuscator': {
            'compact': 'true',
            'control-flow-flattening': 'true',
            'control-flow-flattening-threshold': '0.75',
            'dead-code-injection': 'true',
            'dead-code-injection-threshold': '0.4',
            'string-array': 'true',
            'string-array-threshold': '0.75',
            'unicode-escape-sequence': 'true'
        }
    }

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = Path.home() / '.jsobfuscator' / 'config.ini'
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

class JSObfuscator:
    def __init__(self, project_path: str | Path, config: ObfuscatorConfig = None):
        if not Path(project_path).exists():
            raise ValueError(f"项目路径不存在: {project_path}")
        self.project_path = os.path.abspath(project_path)
        self.output_dir = os.path.join(self.project_path, 'dist')
        self.config = config or ObfuscatorConfig()

    def collect_js_files(self) -> List[str]:
        """收集所有JS文件"""
        js_files = []
        exclude_dirs = {'node_modules', 'dist', '.git', '.svn'}
        
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith('.js'):
                    js_files.append(os.path.join(root, file))
        return js_files

    def create_obfuscator_config(self) -> dict:
        """创建混淆器配置"""
        obf_config = {}
        for key, value in self.config.config['Obfuscator'].items():
            if value.lower() in ('true', 'false'):
                obf_config[key] = value.lower() == 'true'
            elif value.replace('.', '').isdigit():
                obf_config[key] = float(value)
            else:
                obf_config[key] = value
        return obf_config

    def obfuscate_file(self, js_file: str):
        """混淆单个JS文件"""
        rel_path = os.path.relpath(js_file, self.project_path)
        output_path = os.path.join(self.output_dir, rel_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        config = self.create_obfuscator_config()
        config_str = ' '.join([f'--{k} {str(v).lower()}' for k, v in config.items()])
        
        cmd = f'javascript-obfuscator "{js_file}" --output "{output_path}" {config_str}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"混淆失败 {js_file}: {result.stderr}")
            return False
        return True

    def process_project(self):
        if self.config.config['General'].getboolean('confirm_before_process'):
            if not self._confirm_process():
                print("取消处理")
                return

        start_time = time.time()

        try:
            print("1. 收集JavaScript文件...")
            js_files = self.collect_js_files()
            if not js_files:
                print("未找到JavaScript文件！")
                return

            print(f"找到 {len(js_files)} 个JavaScript文件")
            print("2. 开始混淆处理...")
            
            success_count = 0
            for file in js_files:
                print(f"处理: {os.path.relpath(file, self.project_path)}")
                if self.obfuscate_file(file):
                    success_count += 1

            total_time = time.time() - start_time
            minutes = int(total_time // 60)
            seconds = total_time % 60

            print(f"\n混淆完成！成功: {success_count}/{len(js_files)}")
            print(f"总用时: {minutes}分{seconds:.1f}秒")
            print(f"输出目录: {self.output_dir}")

        except Exception as e:
            print(f"处理过程中出错: {str(e)}")
            raise

    def _confirm_process(self) -> bool:
        return input("确认开始混淆处理? (y/N): ").lower() == 'y'

def main():
    show_tool_info()
    parser = argparse.ArgumentParser(description='JavaScript项目混淆工具')
    parser.add_argument('project_path', nargs='?', help='项目路径')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认所有提示')
    
    # 添加混淆器配置参数
    for key in ObfuscatorConfig.DEFAULT_CONFIG['Obfuscator']:
        parser.add_argument(f'--obfuscator_{key}', help=f'混淆器 {key} 配置')

    args = parser.parse_args()
    config = ObfuscatorConfig()

    if args.config:
        _interactive_config(config)
        return

    if not args.project_path:
        print("=== 交互模式 ===")
        args.project_path = input("请输入项目路径: ").strip()

    try:
        config.update_from_args(vars(args))
        if args.yes:
            config.config['General']['confirm_before_process'] = 'false'
        obfuscator = JSObfuscator(args.project_path, config)
        obfuscator.process_project()
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)

def _interactive_config(config: ObfuscatorConfig):
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)
