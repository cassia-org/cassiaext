#!/usr/bin/env python3

import sys
import os
import re
import subprocess

class Patch:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        # Populate subject field from reading the patch file
        with open(path, "r") as patch_file:
            for line in patch_file.readlines():
                if line.startswith("Subject:"):
                    self.subject = line[8:].strip()
                    break

# List all patches in the patches directory
script_dir = os.path.dirname(os.path.realpath(__file__))
patches = []
for file in os.listdir(os.path.join(script_dir, "patches")):
    if file.endswith(".patch"):
        patches.append(Patch(os.path.join(script_dir, "patches", file), file))

# Read dependencies with patches from README.md
class PatchedDependency:
    def __init__(self, name, tag):
        self.name = name
        self.tag = tag
        self.patches = []

with open(os.path.join(script_dir, "README.md"), "r") as readme:
    readme_lines = readme.readlines()
    start_line = -1
    for i in range(len(readme_lines)):
        if readme_lines[i].startswith("```"):
            start_line = i + 1
            break

    if (start_line == -1):
        print("Error: README.md is malformed")
        exit(1)

    deps = []
    for i in range(start_line, len(readme_lines)):
        line = readme_lines[i]
        if (line == "\n"):
            continue
        elif (line.startswith("```")):
            break
        # Eg: libXt - libXt-1.3.0
        res = re.search(r"([a-zA-Z0-9\.\-\_]+) - ([a-zA-Z0-9\.\-\_]+)", line)
        name = res.group(1)
        for patch in patches:
            if patch.name.startswith(name):
                deps.append(PatchedDependency(name, res.group(2)))
                break

# Fill in the patches for each dependency
for dep in deps:
    for patch in patches:
        if patch.name.startswith(dep.name):
            # Append to patches with sorting by name with lexographic order
            # This is to ensure that the patches are applied in the correct order
            i = 0
            while i < len(dep.patches) and dep.patches[i].name < patch.name:
                i += 1
            dep.patches.insert(i, patch)

# Print dependencies
print("Patches:")
for dep in deps:
    print(f"- {dep.name}")
    for patch in dep.patches:
            print(f"  - \"{patch.subject}\"")

# Ask for confirmation
if (input("Are you sure you want to apply all patches? (y/n) ") != "y"):
    exit(0)

# Apply all patches
for dep in deps:
    print(f"Applying patches for {dep.name}")
    # Double check that the repository is on the correct tag
    desc = subprocess.run(["git", "describe", "--exact-match", "--tags"], cwd=os.path.join(script_dir, dep.name), capture_output=True, text=True)
    if (desc.returncode != 0):
        print(f"Error: Failed to get tag for {dep.name}, this could be due to the repository already being patched, it can be reset with reset-deps.py")
        exit(1)
    if (desc.stdout.strip() != dep.tag):
        print(f"Error: {dep.name} is not on the correct tag ({desc.stdout.strip()} != {dep.tag}), run reset-deps.py")
        exit(1)

    # Ensure there's no uncommitted changes
    status = subprocess.run(["git", "status", "-uno", "--porcelain=v1"], cwd=os.path.join(script_dir, dep.name), capture_output=True, text=True)
    if (status.returncode != 0):
        print(f"Error: Failed to check status for {dep.name}")
        exit(1)
    if (status.stdout != ""):
        print(f"Error: {dep.name} has uncommitted changes, reset them manually or via reset-deps.py")
        exit(1)

    for patch in dep.patches:
        # Apply the patch
        print(f"Applying patch {patch.name}")
        if (subprocess.run(["git", "apply", "--ignore-space-change", "--ignore-whitespace", patch.path], stdout=sys.stdout, cwd=os.path.join(script_dir, dep.name)).returncode != 0):
            print(f"Error: Failed to apply patch {patch.name}")
            exit(1)

    # Commit the changes as a single commit
    if (subprocess.run(["git", "add", "-A"], stdout=sys.stdout, cwd=os.path.join(script_dir, dep.name)).returncode != 0):
        print(f"Error: Failed to add changes for {dep.name}")
        exit(1)
    if (subprocess.run(["git", "commit", "-m", f"Apply Cassia patches"], stdout=sys.stdout, cwd=os.path.join(script_dir, dep.name)).returncode != 0):
        print(f"Error: Failed to commit changes for {dep.name}")
        exit(1)