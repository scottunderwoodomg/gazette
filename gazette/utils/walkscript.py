import os

def print_dir_tree(start_path):
    for root, dirs, files in os.walk(start_path):
        level = root.replace(start_path, '').count(os.sep)
        indent = '  ' * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = '  ' * (level + 1)
        for f in files:
            print(f'{subindent}{f}')

print_dir_tree(os.path.dirname(os.path.abspath(__file__)))

