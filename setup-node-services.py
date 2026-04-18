import os
import subprocess

BASE = "services-node"

services = {
    "grievance-service": {
        "port": 3001,
        "dirs": ["src/routes", "src/controllers", "src/db"],
        "files": [
            "server.js",
            ".env",
            "src/app.js",
            "src/db/pool.js",
            "src/routes/grievance.routes.js",
            "src/controllers/grievance.controller.js",
        ],
        "packages": "express pg dotenv cors helmet uuid",
        "dev_packages": "nodemon",
    },
    "analytics-service": {
        "port": 3002,
        "dirs": ["src/routes", "src/controllers", "src/db"],
        "files": [
            "server.js",
            ".env",
            "src/app.js",
            "src/db/pool.js",
            "src/routes/analytics.routes.js",
            "src/controllers/analytics.controller.js",
        ],
        "packages": "express pg dotenv cors helmet",
        "dev_packages": "nodemon",
    },
    "certificate-service": {
        "port": 3003,
        "dirs": ["src/routes", "src/controllers", "src/db", "src/templates"],
        "files": [
            "server.js",
            ".env",
            "src/app.js",
            "src/db/pool.js",
            "src/routes/certificate.routes.js",
            "src/controllers/certificate.controller.js",
            "src/templates/certificate.html",
        ],
        "packages": "express pg dotenv cors helmet handlebars uuid",
        "dev_packages": "nodemon",
    },
}

for service, config in services.items():
    service_path = os.path.join(BASE, service)
    print(f"\n{'='*50}")
    print(f"Setting up {service}...")
    print(f"{'='*50}")

    # Create directories
    for d in config["dirs"]:
        full_dir = os.path.join(service_path, d)
        os.makedirs(full_dir, exist_ok=True)
        print(f"  ✅ Created dir:  {full_dir}")

    # Create files
    for f in config["files"]:
        full_file = os.path.join(service_path, f)
        if not os.path.exists(full_file):
            open(full_file, "w").close()
        print(f"  ✅ Created file: {full_file}")

    # npm init
    print(f"\n  📦 Running npm init...")
    subprocess.run("npm init -y", shell=True, cwd=service_path)

    # Update package.json scripts
    import json
    pkg_path = os.path.join(service_path, "package.json")
    with open(pkg_path, "r") as f:
        pkg = json.load(f)
    pkg["scripts"] = {
        "start": "node server.js",
        "dev": "nodemon server.js"
    }
    with open(pkg_path, "w") as f:
        json.dump(pkg, f, indent=2)
    print(f"  ✅ Updated package.json scripts")

    # npm install
    print(f"\n  📦 Installing packages...")
    subprocess.run(f"npm install {config['packages']}", shell=True, cwd=service_path)
    subprocess.run(f"npm install --save-dev {config['dev_packages']}", shell=True, cwd=service_path)

    # Write .env
    env_content = f"""PORT={config['port']}
NODE_ENV=development
DATABASE_URL=postgresql://postgres:yourpassword@db.zlxvbxiilorwhuipknom.supabase.co:5432/postgres
AUTH_SERVICE_URL=http://localhost:8001
"""
    with open(os.path.join(service_path, ".env"), "w") as f:
        f.write(env_content)
    print(f"  ✅ Written .env")

print(f"\n{'='*50}")
print("✅ All services initialized successfully!")
print("="*50)