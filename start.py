import subprocess
import sys
import os

def start_process(command, cwd=None, prefix=""):
    print(f"Starting {prefix}: {' '.join(command)}")
    is_windows = os.name == 'nt'
    
    # Use npm.cmd on Windows
    if is_windows and command[0] == 'npm':
        command[0] = 'npm.cmd'
        
    # npm needs shell=True on Windows usually
    use_shell = is_windows and command[0].startswith('npm')
    
    return subprocess.Popen(
        command,
        cwd=cwd,
        shell=use_shell
    )

def main():
    print("=== Starting ScriptSim Services ===")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_dir = os.path.join(root_dir, "frontend")
    
    # Add Node.js to PATH to ensure npm is found
    node_path = r"C:\Program Files\nodejs"
    if os.name == 'nt' and os.path.exists(node_path) and node_path.lower() not in os.environ.get("PATH", "").lower():
        os.environ["PATH"] += os.pathsep + node_path
    
    # Install Next.js dependencies if they don't exist
    if not os.path.exists(os.path.join(dashboard_dir, "node_modules")):
        print("Installing dashboard dependencies... (this may take a minute)")
        npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
        subprocess.run([npm_cmd, "install"], cwd=dashboard_dir, shell=(os.name == 'nt'))
        
    # Always clear Next.js cache so route changes are picked up on restart
    next_cache = os.path.join(dashboard_dir, ".next")
    if os.path.exists(next_cache):
        print("Cleaning Next.js cache...")
        import shutil
        try:
            shutil.rmtree(next_cache)
        except Exception as e:
            pass

    processes = []
    
    try:
        # 1. Start Demo App (Shop)
        shop_app = start_process(
            [sys.executable, "app.py"], 
            cwd=os.path.join(root_dir, "apps", "shop"),
            prefix="ShopApp"
        )
        processes.append(shop_app)

        # 2. Start Job Board App
        job_app = start_process(
            [sys.executable, "app.py"],
            cwd=os.path.join(root_dir, "apps", "job_board"),
            prefix="JobApp"
        )
        processes.append(job_app)

        # 3. Start Doctor Booking App
        doctor_app = start_process(
            [sys.executable, "app.py"],
            cwd=os.path.join(root_dir, "apps", "doctor_booking"),
            prefix="DocApp"
        )
        processes.append(doctor_app)
        
        # 4. Start API
        # Run uvicorn as a module from the backend directory
        api = start_process(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8000"],
            cwd=os.path.join(root_dir, "backend"),
            prefix="API"
        )
        processes.append(api)
        
        # 5. Start Dashboard
        dashboard = start_process(
            ["npm", "run", "dev"],
            cwd=dashboard_dir,
            prefix="Dashboard"
        )
        processes.append(dashboard)

        print("\n==============================================")
        print("All services are starting up!")
        print(" - Shop App:       http://localhost:5000")
        print(" - Job Board:      http://localhost:5001")
        print(" - Doctor Booking: http://localhost:5002")
        print(" - Dashboard:      http://localhost:3000")
        print(" - API:            http://localhost:8000")
        print("==============================================")
        print("Press Ctrl+C to stop all services.\n")
        
        # Wait indefinitely until interrupted
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\nShutting down all services...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("All services stopped.")

if __name__ == "__main__":
    main()