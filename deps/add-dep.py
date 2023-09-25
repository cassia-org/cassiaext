import sys
import os
import re
import subprocess

if (len(sys.argv) != 2):
    print("Usage: python add-dep.py <URL>")
    print("Example: python add-dep.py https://gitlab.freedesktop.org/xorg/lib/libxt/-/tree/libXt-1.3.0")
    exit(1)

url = sys.argv[1]

# Extract repo name and tag name
if (url.startswith("https://gitlab")):
    # Eg: https://gitlab.freedesktop.org/xorg/lib/libxt/-/tree/libXt-1.3.0?ref_type=tags
    # repo_name = libxt
    # tag_name = libXt-1.3.0
    # clone_url = https://gitlab.freedesktop.org/xorg/lib/libxt.git
    res = re.search(r"\/([a-zA-Z0-9\.\-\_]+)\/-\/tree\/([a-zA-Z0-9\.\-\_]+)", url)
    repo_name = res.group(1)
    tag_name = res.group(2)
    clone_url = re.search(r"(.*)\/-\/tree\/", url).group(1) + ".git"

    print(f"Adding GitLab dependency: {repo_name} @ {tag_name} ({clone_url})")
elif (url.startswith("https://github")):
    # Eg: https://github.com/libexpat/libexpat/tree/R_2_5_0
    # repo_name = libexpat
    # tag_name = R_2_5_0
    # clone_url = https://github.com/libexpat/libexpat.git
    res = re.search(r"\/([a-zA-Z0-9\.\-\_]+)\/tree\/([a-zA-Z0-9\.\-\_]+)", url)
    repo_name = res.group(1)
    tag_name = res.group(2)
    clone_url = re.search(r"(.*)\/tree\/", url).group(1) + ".git"

    print(f"Adding GitHub dependency: {repo_name} @ {tag_name} ({clone_url})")
else:
    print("Error: Unsupported URL")
    exit(1)

# Check if the dependency already exists
script_dir = os.path.dirname(os.path.realpath(__file__))
if os.path.exists(os.path.join(script_dir, repo_name)):
    print(f"Error: Dependency {repo_name} already exists")
    exit(1)

# Add submodule and checkout tag using subprocess with stdout redirected
# to sys.stdout so that the output is printed to the console
subprocess.run(["git", "submodule", "add", clone_url], stdout=sys.stdout, cwd=script_dir)
subprocess.run(["git", "checkout", tag_name], stdout=sys.stdout, cwd=os.path.join(script_dir, repo_name))

# Open README.md and append the dependency
with open(os.path.join(script_dir, "README.md"), "a+") as readme:
    # Find ``` closing tag and insert the dependency before it
    readme.seek(0)
    readme_lines = readme.readlines()
    for i in reversed(range(len(readme_lines))):
        if readme_lines[i].startswith("```"):
            print(f"Inserting dependency at line {i} in README.md");
            readme_lines.insert(i, f"{repo_name} - {tag_name}\n")
            break
    if i == 0:
        print("Error: Could not find closing ``` tag in README.md")
        exit(1)

    # Write the new README.md
    readme.seek(0)
    readme.truncate()
    readme.writelines(readme_lines)

