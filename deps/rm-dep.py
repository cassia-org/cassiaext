#!/usr/bin/env python3

import sys
import os
import re
import subprocess

if (len(sys.argv) != 2):
    print("Usage: python rm-dep.py <NAME>")
    print("Example: python rm-dep.py libxt")
    exit(1)

name = sys.argv[1]

# Check if the dependency exists
script_dir = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(os.path.join(script_dir, name)):
    print(f"Error: Dependency {name} does not exist")
    exit(1)

# Find script directory relative to the git root
git_root = subprocess.run(["git", "rev-parse", "--show-toplevel"], stdout=subprocess.PIPE, cwd=script_dir)
if (git_root.returncode != 0):
    print("Error: Failed to find git root")
    exit(1)
git_root = git_root.stdout.decode("utf-8").strip()
rel_script_dir = os.path.relpath(script_dir, git_root)
rel_module_dir = os.path.join(rel_script_dir, name)
print(f"Removing dependency {name} ({rel_module_dir})")

# Remove submodule with git and rm
if (subprocess.run(["git", "submodule", "deinit", "-f", rel_module_dir], stdout=sys.stdout, cwd=git_root).returncode != 0):
    print(f"Error: Failed to deinit submodule {name}")
    exit(1)
if (subprocess.run(["git", "rm", "-f", rel_module_dir], stdout=sys.stdout, cwd=git_root).returncode != 0):
    print(f"Error: Failed to git rm submodule {name}")
    exit(1)
if (subprocess.run(["rm", "-rf", os.path.join(git_root, ".git/modules", rel_module_dir)], stdout=sys.stdout, cwd=git_root).returncode != 0):
    print(f"Error: Failed to remove submodule {name} from .git/modules")
    exit(1)
if (subprocess.run(["git", "config", "--remove-section", f"submodule.{rel_module_dir}"], stdout=sys.stdout, cwd=git_root)):
    print(f"Error: Failed to remove submodule {name} from .git/config")
    exit(1)

# Open README.md and remove the dependency
with open(os.path.join(script_dir, "README.md"), "a+") as readme:
    # Find ``` opening tag
    readme.seek(0)
    readme_lines = readme.readlines()
    tag_line = -1
    for i in range(len(readme_lines)):
        if readme_lines[i].startswith("```"):
            tag_line = i
            break

    if tag_line == -1:
        print("Error: README.md is malformed")
        exit(1)

    # Find the dependency and remove it
    dep_line = -1
    for i in range(tag_line + 1, len(readme_lines)):
        if readme_lines[i].startswith(name):
            dep_line = i
            break

    if dep_line == -1:
        print(f"Error: Dependency {name} does not exist in README.md")
        exit(1)

    # Remove the dependency
    del readme_lines[dep_line]

    # Write the new README.md
    readme.seek(0)
    readme.truncate()
    readme.writelines(readme_lines)

print(f"Removed dependency {name}")