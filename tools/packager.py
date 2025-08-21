import sys, os, zipfile

def zip_project(project_dir, out_zip):
    if not os.path.isdir(project_dir):
        print("Project dir does not exist:", project_dir)
        return
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(project_dir):
            for f in files:
                path = os.path.join(root, f)
                arc = os.path.relpath(path, project_dir)
                z.write(path, arc)
    print("Zipped", out_zip)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: packager.py <project_dir> <out_zip>")
    else:
        zip_project(sys.argv[1], sys.argv[2])
